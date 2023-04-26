#
# MIT License
#
# (C) Copyright 2023 Hewlett Packard Enterprise Development LP
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
import logging
from requests.exceptions import HTTPError
from bos.common.utils import requests_retry_session, PROTOCOL

LOGGER = logging.getLogger('bos.common.tenant_utils')

TENANT_HEADER = "Cray-Tenant-Name"
SERVICE_NAME = 'cray-tapms-server.tapms-operator.svc.cluster.local:2875/apis/tapms/v1' ## CASMPET-6433 will simplify this endpoint
BASE_ENDPOINT = "%s://%s" % (PROTOCOL, SERVICE_NAME)
TENANT_ENDPOINT = "%s/tenant" % BASE_ENDPOINT ## CASMPET-6433 will change this from tenant to tenants


class InvalidTenantException(Exception):
    pass


def get_tenant_from_header():
    if TENANT_HEADER in connexion.request.headers:
        return connexion.request.headers[TENANT_HEADER]
    return None


def add_tenant_to_headers(tenant, headers=None):
    if not headers:
        headers = {}
    headers[TENANT_HEADER] = tenant
    return headers


def get_new_tenant_header(tenant):
    return add_tenant_to_headers(tenant)


def get_tenant_aware_key(key, tenant):
    if tenant:
        return f"{tenant}_{key}"
    return key


def get_tenant_data(tenant, session=None):
    if not session:
        session = requests_retry_session()
    url = f"{TENANT_ENDPOINT}/{tenant}"
    response = session.get(url)
    try:
        response.raise_for_status()
    except HTTPError as e:
        LOGGER.error("Failed getting tenant data from tapms: %s", e)
        if response.status_code == 404:
            raise InvalidTenantException(f"Data not found for tenant {tenant}") from e
        else:
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

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except InvalidTenantException as e:
            return connexion.problem(
                status=400, title='Invalid tenant',
                detail=str(e))
    return wrapper


def reject_invalid_tenant(func):
    """Decorator for preemptively validating the tenant exists"""

    def wrapper(*args, **kwargs):
        tenant = get_tenant_from_header()
        if tenant and not validate_tenant_exists(tenant):
            return connexion.problem(
                status=400, title="Invalid tenant",
                detail=str("The provided tenant does not exist"))
        return func(*args, **kwargs)
    return wrapper


def no_v1_multi_tenancy_support(func):
    """Decorator for returning errors if the endpoint doesn't support multi-tenancy"""

    def wrapper(*args, **kwargs):
        if get_tenant_from_header():
            return connexion.problem(
                status=400, title="Multi-tenancy not supported",
                detail=str("BOS v1 endpoints do not support multi-tenancy and a tenant was specified in the header"))
        return func(*args, **kwargs)
    return wrapper
