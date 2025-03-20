#
# MIT License
#
# (C) Copyright 2023-2025 Hewlett Packard Enterprise Development LP
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

from collections.abc import Callable
import functools
import logging
import hashlib
from typing import ParamSpec, TypeVar

import connexion
import requests
from requests.exceptions import HTTPError

from bos.common.types.general import JsonDict
from bos.common.utils import exc_type_msg, retry_session_get, PROTOCOL

LOGGER = logging.getLogger(__name__)

TENANT_HEADER = "Cray-Tenant-Name"
SERVICE_NAME = 'cray-tapms/v1alpha3'  # CASMCMS-9125: Currently when TAPMS bumps this version, it
# breaks backwards compatiblity, so BOS needs to update this
# whenever TAPMS does.
BASE_ENDPOINT = f"{PROTOCOL}://{SERVICE_NAME}"
TENANT_ENDPOINT = f"{BASE_ENDPOINT}/tenants"  # CASMPET-6433 changed this from tenant to tenants


class InvalidTenantException(Exception):
    pass


def get_tenant_from_header() -> str | None:
    if TENANT_HEADER in connexion.request.headers:
        return connexion.request.headers[TENANT_HEADER] or None
    return None


def add_tenant_to_headers(tenant: str, headers: JsonDict | None=None) -> JsonDict:
    if not headers:
        headers = {}
    headers[TENANT_HEADER] = tenant
    return headers


def get_new_tenant_header(tenant: str) -> JsonDict:
    return add_tenant_to_headers(tenant)


def get_tenant_aware_key(key: str, tenant: str | None) -> str:
    if not tenant:
        # The no tenant case should already be standardized, but this adds some safety.
        tenant = ""
    tenant_hash = hashlib.sha1(tenant.encode()).hexdigest()
    key_hash = hashlib.sha1(key.encode()).hexdigest()
    return f"{tenant_hash}-{key_hash}"


def get_tenant_data(tenant: str, session: requests.Session | None = None) -> JsonDict:
    url = f"{TENANT_ENDPOINT}/{tenant}"
    with retry_session_get(url, session=session) as response:
        try:
            response.raise_for_status()
        except HTTPError as e:
            LOGGER.error("Failed getting tenant data from tapms: %s",
                         exc_type_msg(e))
            if response.status_code == 404:
                raise InvalidTenantException(
                    f"Data not found for tenant {tenant}") from e
            raise
        return response.json()


def get_tenant_component_set(tenant: str) -> set[str]:
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

P1 = ParamSpec("P1")
R1 = TypeVar("R1")

def tenant_error_handler(func: Callable[P1, R1]) -> Callable[P1, R1]:
    """Decorator for returning errors if there is an exception when calling tapms"""

    @functools.wraps(func)
    def wrapper(*args: P1.args, **kwargs: P1.kwargs) -> R1:
        try:
            return func(*args, **kwargs)
        except InvalidTenantException as e:
            LOGGER.debug("Invalid tenant: %s", exc_type_msg(e))
            return connexion.problem(status=400,
                                     title='Invalid tenant',
                                     detail=str(e))

    return wrapper

P2 = ParamSpec("P2")
R2 = TypeVar("R2")

def reject_invalid_tenant(func: Callable[P2, R2]) -> Callable[P2, R2]:
    """Decorator for preemptively validating the tenant exists"""

    @functools.wraps(func)
    def wrapper(*args: P2.args, **kwargs: P2.kwargs) -> R2:
        tenant = get_tenant_from_header()
        if tenant and not validate_tenant_exists(tenant):
            LOGGER.debug("The provided tenant does not exist")
            return connexion.problem(
                status=400,
                title="Invalid tenant",
                detail=str("The provided tenant does not exist"))
        return func(*args, **kwargs)

    return wrapper
