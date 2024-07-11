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

import connexion
import functools
import logging
import hashlib
from requests.exceptions import HTTPError
from bos.common.utils import exc_type_msg, requests_retry_session, PROTOCOL

LOGGER = logging.getLogger('bos.common.tenant_utils')

TENANT_HEADER = "Cray-Tenant-Name"
SERVICE_NAME = 'cray-tapms/v1alpha2'
BASE_ENDPOINT = "%s://%s" % (PROTOCOL, SERVICE_NAME)
TENANT_ENDPOINT = "%s/tenants" % BASE_ENDPOINT ## CASMPET-6433 changed this from tenant to tenants


class InvalidTenantException(Exception):
    pass


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
        components.append(resource.get("xnames",[]))
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
