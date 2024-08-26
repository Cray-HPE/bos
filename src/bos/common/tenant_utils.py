#
# MIT License
#
# (C) Copyright 2023-2024 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

import functools
import logging
import hashlib
from flask import Flask, request, jsonify
from threading import Thread
from datetime import datetime, timedelta
from collections import defaultdict
import connexion
from requests.exceptions import HTTPError
from kubernetes import client, config
from bos.common.utils import exc_type_msg, requests_retry_session, PROTOCOL

LOGGER = logging.getLogger('bos.common.tenant_utils')

TENANT_HEADER = "Cray-Tenant-Name"
SERVICE_NAME = 'cray-tapms/v1alpha2'
BASE_ENDPOINT = f"{PROTOCOL}://{SERVICE_NAME}"
TENANT_ENDPOINT = f"{BASE_ENDPOINT}/tenants" # CASMPET-6433 changed this from tenant to tenants

# K8S Clients for reading Tapms CRD information
config.load_incluster_config()
api_instance = client.CustomObjectsApi()

# Webhook Server Information
WEBHOOK = Flask(__name__)
WEBHOOK.logger.setLevel(LOGGER.getEffectiveLevel())

class InvalidTenantException(Exception):
    pass

class TapmsClient(Thread):
    """
    A TAPMS client is a client side cacheable client that offloads the cost of repeated TAPMS calls into an in-memory
    cache. This cache is perodically repopulated, and automatically updated when new information arrives
    through TAPMS' supported webhook.

    This class extends the threading.Thread class, allowing the implemented server set of features to update
    periodically in the background.

    TAPMS implements per tenant webhooks as well as a global webhook. BOS will use the global webhook so that
    all information pertaining to tenancy will be made available to it. For more information on how this information is
    made available to other downstream clients, refer to:
    https://github.com/Cray-HPE/docs-csm/blob/release/1.6/operations/multi-tenancy/Create_a_Tenant.md

    """
    K8S_CRD_GROUP = 'tapms.hpe.com'
    K8S_CRD_VERSION = 'v1alpha3'
    K8S_CRD_PLURAL = 'Tenants'
    def __init__(self, stale_timeout=1024, *args, **kwargs):
        """
        Initialize a TAPMS client with an in-memory cache and a timeout value. Args and Kwargs are passthrough options
        used when instantiating the thread class variables.
        """
        self.stale_timeout = timedelta(seconds=stale_timeout)
        self.session = requests_retry_session()

        # These dictionaries use the associated TAPMS URIs for storing information and timestamps about retrieval
        self.tenant_data = defaultdict(None)
        self.tenant_data_last_updated = defaultdict(None)

        # These are necessary routines used to respond to asynchronous webhook listening via a flask app framework.
        super().__init__(name='TAPMS Client', *args, **kwargs)

    def get_tenant_data(self, tenant_name):
        url = f"{TENANT_ENDPOINT}/{tenant_name}"
        # Either return what we have, or get what we need, store it, then return what we have
        if self.is_stale(tenant_name):
            response = self.session.get(url)
            try:
                response.raise_for_status()
            except HTTPError as e:
                LOGGER.error("Failed getting tenant data from tapms: %s", exc_type_msg(e))
                if response.status_code == 404:
                    raise InvalidTenantException(f"Data not found for tenant {tenant_name}") from e
                raise
            self.tenant_data[tenant_name] = response.json()
            self.tenant_data_last_updated = datetime.now()
        return self.tenant_data[tenant_name]

    def is_stale(self, tenant_name):
        """
        Compares the current timestamp against when we last updated. If the timestamp is too old, we return true so that
        the data can be refreshed and stored once again.
        """
        if not self.tenant_data_last_updated:
            # In this case, we do not have any record of this information, so the None state is by definition stale.
            return True
        data_entry_age = datetime.now() > self.tenant_data_last_updated[tenant_name]
        return data_entry_age > self.stale_timeout

    def start(self):
        """
        Instantiates the flask webhook responder, allowing it to respond asynchronously to updates from TAPMS.
        """
        WEBHOOK.run(host='0.0.0.0', port=5000)

    @WEBHOOK.route('/some/webhook', methods=['POST'])
    def handle_response(self):
        request_info = request.get_json()
        LOGGER.info('Request recevied from tapms!')
        LOGGER.info(request_info)


def get_tenant_from_header():
    tenant = ""
    if TENANT_HEADER in connexion.request.headers:
        tenant = connexion.request.headers[TENANT_HEADER]
        if not tenant:
            tenant = ""
    return tenant


def add_tenant_to_headers(tenant, headers=None):
    if not headers:
        headers = {}
    headers[TENANT_HEADER] = tenant
    return headers


def get_new_tenant_header(tenant):
    return add_tenant_to_headers(tenant)


def get_tenant_aware_key(key, tenant):
    if not tenant:
        # The no tenant case should already be standardized, but this adds some safety.
        tenant = ""
    tenant_hash = hashlib.sha1(tenant.encode()).hexdigest()
    key_hash = hashlib.sha1(key.encode()).hexdigest()
    return f"{tenant_hash}-{key_hash}"


def get_tenant_data(tenant, session=None):
    if not session:
        session = requests_retry_session()
    url = f"{TENANT_ENDPOINT}/{tenant}"
    response = session.get(url)
    try:
        response.raise_for_status()
    except HTTPError as e:
        LOGGER.error("Failed getting tenant data from tapms: %s", exc_type_msg(e))
        if response.status_code == 404:
            raise InvalidTenantException(f"Data not found for tenant {tenant}") from e
        raise
    return response.json()


def get_tenant_component_set(tenant: str) -> set:
    components = []
    data = get_tenant_data(tenant)
    status = data.get("status", {})
    for resource in status.get("tenantresources", []):
        components.append(resource.get("xnames", []))
    return set().union(*components)


def validate_tenant_exists(tenant: str) -> bool:
    try:
        get_tenant_data(tenant)
        return True
    except InvalidTenantException:
        return False


def tenant_error_handler(func):
    """Decorator for returning errors if there is an exception when calling tapms"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except InvalidTenantException as e:
            LOGGER.debug("Invalid tenant: %s", exc_type_msg(e))
            return connexion.problem(
                status=400, title='Invalid tenant',
                detail=str(e))
    return wrapper


def reject_invalid_tenant(func):
    """Decorator for preemptively validating the tenant exists"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tenant = get_tenant_from_header()
        if tenant and not validate_tenant_exists(tenant):
            LOGGER.debug("The provided tenant does not exist")
            return connexion.problem(
                status=400, title="Invalid tenant",
                detail=str("The provided tenant does not exist"))
        return func(*args, **kwargs)
    return wrapper
