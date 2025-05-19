#
# MIT License
#
# (C) Copyright 2021-2025 Hewlett Packard Enterprise Development LP
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
import copy
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from functools import partial, singledispatch
import logging
from typing import Any, Literal, cast

import connexion
from connexion.lifecycle import ConnexionResponse as CxResponse

from bos.common.tenant_utils import (get_tenant_component_set,
                                     get_tenant_from_header,
                                     is_valid_tenant_component,
                                     tenant_error_handler)
from bos.common.types.components import (ApplyStagedComponents,
                                         ApplyStagedStatus,
                                         ComponentData,
                                         ComponentDesiredState,
                                         ComponentRecord,
                                         ComponentStagedState,
                                         ComponentUpdateFilter,
                                         update_component_record)
from bos.common.utils import components_by_id, exc_type_msg, get_current_timestamp
from bos.common.values import (Phase,
                               Action,
                               Status,
                               EMPTY_ACTUAL_STATE,
                               EMPTY_BOOT_ARTIFACTS,
                               EMPTY_STAGED_STATE)
from bos.server import redis_db_utils as dbutils
from bos.server.controllers.utils import (_400_bad_request,
                                          _404_resource_not_found,
                                          BadRequest,
                                          ResourceNotFound)
from bos.server.options import get_v2_options_data
from bos.server.dbs.boot_artifacts import get_boot_artifacts, BssTokenUnknown
from bos.server.options import update_server_log_level
from bos.server.utils import get_request_json

LOGGER = logging.getLogger(__name__)
DB = dbutils.ComponentDBWrapper()
SESSIONS_DB = dbutils.SessionDBWrapper()

# Need to shorten some of these unwieldy type annotations
type CompAny = ComponentData | ComponentRecord

class ComponentNotFound(ResourceNotFound):
    """
    A component needed for an API request was not found
    """

    RESOURCE_TYPE: str = "Component"

@tenant_error_handler
@dbutils.redis_error_handler
def get_v2_components(
    ids: str | None=None,
    enabled: bool | None=None,
    session: str | None=None,
    staged_session: str | None=None,
    phase: str | None=None,
    status: str | None=None,
    start_after_id: str | None=None,
    page_size: int=0
) -> tuple[list[ComponentRecord], Literal[200]] | CxResponse:
    """Used by the GET /components API operation

    Allows filtering using a comma separated list of ids.
    """
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug(
        "GET /v2/components invoked get_v2_components with ids=%s enabled=%s session=%s "
        "staged_session=%s phase=%s status=%s start_after_id=%s page_size=%d", ids,
        enabled, session, staged_session, phase, status, start_after_id, page_size)
    if ids is not None:
        try:
            id_list = ids.split(',')
        except Exception as err:
            LOGGER.error("Error parsing component IDs: %s", exc_type_msg(err))
            return _400_bad_request(f"Error parsing the ids provided: {err}")
    else:
        id_list = None
    tenant = get_tenant_from_header() or None
    LOGGER.debug("GET /v2/components for tenant=%s with %d IDs specified",
                 tenant, len(id_list) if id_list else 0)
    response = get_v2_components_data(id_list=id_list,
                                      enabled=enabled,
                                      session=session,
                                      staged_session=staged_session,
                                      phase=phase,
                                      status=status,
                                      tenant=tenant,
                                      start_after_id=start_after_id,
                                      page_size=page_size,
                                      delete_timestamp=True)
    LOGGER.debug(
        "GET /v2/components returning data for tenant=%s on %d components",
        tenant, len(response))
    return response, 200

def get_v2_components_data(
    id_list: list[str] | None=None,
    enabled: bool | None=None,
    session: str | None=None,
    staged_session: str | None=None,
    phase: str | None=None,
    status: str | None=None,
    tenant: str | None=None,
    start_after_id: str | None=None,
    page_size: int=0,
    *,
    delete_timestamp: bool=False
) -> list[ComponentRecord]:
    """Used by the GET /components API operation

    Allows filtering using a comma separated list of ids.
    """
    id_set = _get_id_set(id_list, tenant)

    # If id_set is not None but is empty, that means no components in the system
    # will match our filter, so we can return an empty list immediately.
    if id_set is not None and not id_set:
        return []

    _component_filter_func = _get_component_filter_func(enabled=enabled,
                                                        session=session,
                                                        staged_session=staged_session,
                                                        phase=phase,
                                                        status=status,
                                                        delete_timestamp=delete_timestamp)

    return DB.get_all_filtered(filter_func=_component_filter_func,
                               start_after_key=start_after_id,
                               page_size=page_size,
                               specific_keys=id_set)

def _get_id_set(id_list: list[str] | None, tenant: str | None) -> set[str] | None:
    """
    Return the intersection of the IDs specified in id_list and the component IDs
    accessible to the specified tenant.
    If there are IDs in id_list and tenant is specified, and the intersection is empty,
    then return an empty set.
    If no IDs are in id_list, just return the IDs accessible to the specified tenant.
    If no tenant is specified, just return the IDs listed in id_list.
    If neither is specified, return None, which signals that any ID is valid.
    """
    tenant_components = get_tenant_component_set(tenant) if tenant else None

    if id_list is None:
        return tenant_components

    id_set = set(id_list)
    if tenant_components is not None:
        id_set.intersection_update(tenant_components)
    return id_set

def _get_component_filter_func(
    enabled: bool | None,
    session: str | None,
    staged_session: str | None,
    phase: str | None,
    status: str | None,
    delete_timestamp: bool
) -> Callable[[ComponentRecord], ComponentRecord | None]:
    """
    Return the filter function to be used by get_v2_components_data
    """
    if any([enabled, session, staged_session, phase, status]):
        return partial(_filter_component,
                       enabled=enabled,
                       session=session or None,
                       staged_session=staged_session or None,
                       phase=phase or None,
                       status=status or None,
                       delete_timestamp=delete_timestamp)
    return partial(_set_status, delete_timestamp=delete_timestamp)

def _filter_component(
    data: ComponentRecord,
    enabled: bool | None,
    session: str | None,
    staged_session: str | None,
    phase: str | None,
    status: str | None,
    delete_timestamp: bool
) -> ComponentRecord | None:
    # Do all of the checks we can before calculating status, to avoid doing it needlessly
    if enabled is not None and data.get('enabled', None) != enabled:
        return None
    if session is not None and data.get('session', None) != session:
        return None
    if staged_session is not None and \
       data.get('staged_state', {}).get('session', None) != staged_session:
        return None
    updated_data = _set_status(data, delete_timestamp=delete_timestamp)
    if (status_data := updated_data.get('status')) is not None:
        if phase is not None and status_data.get('phase') != phase:
            return None
        if status is not None and status_data.get('status') not in status.split(','):
            return None
    return updated_data

def _set_status(data: ComponentRecord, *, delete_timestamp: bool=False) -> ComponentRecord:
    """
    This sets the status field of the overall status.
    """
    if "status" not in data:
        data["status"] = {"phase": "", "status_override": ""}
    data['status']['status'] = _calculate_status(data)
    if delete_timestamp:
        del_timestamp(data)
    return data


def _calculate_status(data: CompAny) -> str:
    """
    Calculates and returns the status of a component
    """
    if not 'status' in data:
        LOGGER.debug(
            "No status in data: %s. This will have the effect of clearing any pre-existing phase.",
            data)
    status_data = data.get('status', {})
    override = status_data.get('status_override', '')
    if override:
        return override

    phase = status_data.get('phase', '')
    component = data.get('id', '')
    last_action_dict = data.get('last_action', {})
    last_action = last_action_dict.get('action', '')

    status = Status.stable
    if phase == Phase.powering_on:
        if last_action == Action.power_on and not last_action_dict.get(
                'failed', False):
            status = Status.power_on_called
        else:
            status = Status.power_on_pending
    elif phase == Phase.powering_off:
        if last_action == Action.power_off_gracefully:
            status = Status.power_off_gracefully_called
        elif last_action == Action.power_off_forcefully:
            status = Status.power_off_forcefully_called
        else:
            status = Status.power_off_pending
    elif phase == Phase.configuring:
        status = Status.configuring

    LOGGER.debug("Component: %s Last action: %s Phase: %s Status: %s",
                 component, last_action, phase, status)
    return status


@dbutils.redis_error_handler
def put_v2_components() -> tuple[list[ComponentRecord], Literal[200]] | CxResponse:
    """Used by the PUT /components API operation"""
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("PUT /v2/components invoked put_v2_components")
    try:
        data = cast(list[ComponentRecord], get_request_json())
    except Exception as err:
        LOGGER.error("Error parsing PUT request data: %s", exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    try:
        components = components_by_id(data)
    except KeyError:
        return _400_bad_request("At least one component is missing the required 'id' field")

    for comp_id in components:
        components[comp_id] = _set_auto_fields(components[comp_id])

    DB.mput(components)
    return list(components.values()), 200


@tenant_error_handler
@dbutils.redis_error_handler
def patch_v2_components(
    skip_bad_ids: bool=False
) -> tuple[list[ComponentRecord], Literal[200]] | CxResponse:
    """Used by the PATCH /components API operation"""
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("PATCH /v2/components invoked patch_v2_components (skip_bad_ids=%s)", skip_bad_ids)
    try:
        data = get_request_json()
    except Exception as err:
        LOGGER.error("Error parsing PATCH request data: %s", exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    try:
        current_component_data, component_patch_data = _parse_v2_components_bulk_patch(
                                                            data, skip_bad_ids=skip_bad_ids)
    except ComponentNotFound as err:
        LOGGER.warning(err)
        return _404_component_not_found(resource_id=err.resource_id)  # pylint: disable=redundant-keyword-arg
    except BadRequest as err:
        LOGGER.warning(err)
        return _400_bad_request(str(err))
    except Exception as err:
        LOGGER.error("Error parsing PATCH request data: %s", exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    if not current_component_data:
        LOGGER.debug("patch_v2_components: No components to patch")
        return [], 200

    try:
        for comp_id, comp in current_component_data.items():
            update_component_record(comp, component_patch_data[comp_id])
    except Exception as err:
        LOGGER.error("Error patching component data: %s", exc_type_msg(err))
        return _400_bad_request(f"Error patching the data provided: {err}")

    DB.mput(current_component_data)
    return list(current_component_data.values()), 200


@singledispatch
def _parse_v2_components_bulk_patch(
    data: Any, /, *, skip_bad_ids: bool
) -> tuple[dict[str, ComponentRecord],
           Mapping[str, ComponentData] | Mapping[str, ComponentRecord]]:
    """
    This is the fallback function, for cases where data does not match one of the
    later definitions. This will only happen if data is not a list or a dict.
    In theory, this should never be the case, because connexion should reject
    any such request before we get here.
    """
    raise BadRequest(f"Unexpected data type {type(data).__name__}")


@_parse_v2_components_bulk_patch.register(list)
def _(
    data: list[ComponentRecord], /, *, skip_bad_ids: bool
) -> tuple[dict[str, ComponentRecord], dict[str, ComponentRecord]]:
    """
    Set the automatic component fields for the specified patch data
    Extract the IDs from the specified list of component records, and get the current data for them
    """
    LOGGER.debug("_parse_v2_components_bulk_patch(list): %d components specified", len(data))
    try:
        patch_data = { comp_id: _set_auto_fields(patch_comp)
                       for comp_id, patch_comp in components_by_id(data).items() }
    except Exception as err:
        raise BadRequest(f"Error parsing the data provided: {exc_type_msg(err)}") from err

    components = _load_comps_from_id_list(list(patch_data), skip_bad_ids=skip_bad_ids)

    LOGGER.debug("_parse_v2_components_bulk_patch(list): %d components to be patched",
                 len(components))
    return components, patch_data


@_parse_v2_components_bulk_patch.register(dict)
def _(
    data: ComponentUpdateFilter, /, *, skip_bad_ids: bool
) -> tuple[dict[str, ComponentRecord], defaultdict[str, ComponentData]]:
    """
    Set the automatic component fields for the specified patch data.
    Remove its ID field, if present.
    Determine whether this is a session filter or an id filter, and get the current component data
    for the specified filter.
    """
    try:
        filters = data["filters"]
        patch = data["patch"]
    except KeyError as err:
        raise BadRequest(f"Request missing required '{err}' field") from err
    ids = filters.get("ids", None)
    session = filters.get("session", None)
    if ids and session:
        raise BadRequest("Multiple filters provided")
    if not ids and not session:
        raise BadRequest("No filter provided.")
    patch.pop("id", None)
    patch = _set_auto_fields(patch)
    # Because in this case we are applying the same patch data to every component, we
    # can just use a defaultdict that always returns our patch data
    patch_data: defaultdict[str, ComponentData] = defaultdict(lambda: patch)
    if ids:
        components = _update_filter_ids_to_components(ids,skip_bad_ids=skip_bad_ids)
    else:
        # session
        tenant = get_tenant_from_header()
        components = components_by_id(get_v2_components_data(session=session, tenant=tenant))
    LOGGER.debug("_parse_v2_components_bulk_patch(dict): %d IDs found in specified %s",
                 len(components), 'id list' if ids else 'session')
    return components, patch_data


def _update_filter_ids_to_components(ids: str, skip_bad_ids: bool) -> dict[str, ComponentRecord]:
    try:
        id_list = ids.split(',')
    except Exception as err:
        raise BadRequest(f"Error parsing the IDs provided: {exc_type_msg(err)}") from err

    return _load_comps_from_id_list(id_list, skip_bad_ids=skip_bad_ids)


def _load_comps_from_id_list(id_list: list[str], skip_bad_ids: bool) -> dict[str, ComponentRecord]:
    start_len = len(id_list)
    LOGGER.debug("_load_comps_from_id_list: %d IDs specified", start_len)
    tenant = get_tenant_from_header()

    if skip_bad_ids:
        if tenant:
            legal_component_ids = get_tenant_component_set(tenant)
            id_list = list(legal_component_ids.intersection(id_list))
            if len(id_list) != start_len:
                LOGGER.debug("After filtering out invalid IDs, %d IDs remain", len(id_list))
            if not id_list:
                return {}

        return DB.mget_skip_bad_keys(id_list)

    if tenant:
        _check_for_invalid_tenant_comp(id_list, tenant)

    try:
        return DB.mget(id_list)
    except dbutils.NotFoundInDB as exc:
        raise ComponentNotFound(exc.key) from exc


def _check_for_invalid_tenant_comp(comp_id_list: Iterable[str], tenant: str) -> None:
    """
    If any of the listed component IDs are not valid for the specified tenant, raise
    ComponentNotFound for one of the invalid IDs.
    """
    legal_component_ids = get_tenant_component_set(tenant)
    for comp_id in comp_id_list:
        if comp_id not in legal_component_ids:
            raise ComponentNotFound(comp_id)


@tenant_error_handler
@dbutils.redis_error_handler
def get_v2_component(component_id: str) -> tuple[ComponentRecord, Literal[200]] | CxResponse:
    """Used by the GET /components/{component_id} API operation"""
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("GET /v2/components/%s invoked get_v2_component",
                 component_id)
    if not is_valid_tenant_component(component_id, get_tenant_from_header()):
        LOGGER.warning("Component %s could not be found", component_id)
        return _404_component_not_found(resource_id=component_id)  # pylint: disable=redundant-keyword-arg
    try:
        component = DB.get(component_id)
    except dbutils.NotFoundInDB:
        LOGGER.warning("Component %s could not be found", component_id)
        return _404_component_not_found(resource_id=component_id)  # pylint: disable=redundant-keyword-arg
    component = _set_status(component)
    del_timestamp(component)
    return component, 200


@dbutils.redis_error_handler
def put_v2_component(component_id: str) -> tuple[ComponentRecord, Literal[200]] | CxResponse:
    """Used by the PUT /components/{component_id} API operation"""
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("PUT /v2/components/%s invoked put_v2_component",
                 component_id)
    try:
        data = cast(ComponentData, get_request_json())
    except Exception as err:
        LOGGER.error("Error parsing PUT '%s' request data: %s", component_id,
                     exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    # Strip the ID from the incoming data, if one was specified
    data.pop("id", None)
    # Create a new component and set the ID field
    new_component: ComponentRecord = { "id": component_id }
    # Fill in the other fields with the request body
    new_component.update(data)

    new_component = _set_auto_fields(new_component)
    DB.put(component_id, new_component)
    return new_component, 200


@tenant_error_handler
@dbutils.redis_error_handler
def patch_v2_component(component_id: str) -> tuple[ComponentRecord, Literal[200]] | CxResponse:
    """Used by the PATCH /components/{component_id} API operation"""
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("PATCH /v2/components/%s invoked patch_v2_component",
                 component_id)
    try:
        patch_data = cast(ComponentData, get_request_json())
    except Exception as err:
        LOGGER.error("Error parsing PATCH '%s' request data: %s", component_id,
                     exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    if not is_valid_tenant_component(component_id, get_tenant_from_header()):
        LOGGER.warning("Component %s could not be found", component_id)
        return _404_component_not_found(resource_id=component_id)  # pylint: disable=redundant-keyword-arg
    try:
        component = DB.get(component_id)
    except dbutils.NotFoundInDB:
        LOGGER.warning("Component %s could not be found", component_id)
        return _404_component_not_found(resource_id=component_id)  # pylint: disable=redundant-keyword-arg

    if "actual_state" in patch_data and not _validate_actual_state_change_is_allowed(component):
        LOGGER.warning("Not able to update actual state")
        return connexion.problem(
            status=409,
            title="Actual state can not be updated.",
            detail="BOS is currently changing the state of the node,"
            " and the actual state can not be accurately recorded")
    patch_data.pop("id", None)
    patch_data = _set_auto_fields(patch_data)
    update_component_record(component, patch_data)
    DB.put(component_id, component)
    return component, 200


def _validate_actual_state_change_is_allowed(current_data: CompAny) -> bool:
    if not current_data["enabled"]:
        # This component is not being managed on by BOS
        return True
    if _calculate_status(current_data) == Status.stable:
        # BOS believes the component is in the correct state
        return True
    if current_data["last_action"]["action"] == Action.power_on:
        # BOS just powered-on the component and is waiting for the new state to be reported
        return True
    # The component is being actively changed by BOS, and is going to be powered off or
    #   is in a state where the next action hasn't been determined.  Allowing the actual
    #   state to be updated can interfere with BOS' ability to determine the next action.
    #   e.g. When the actual_state is deleted by the setup operator to trigger a reboot
    return False


@tenant_error_handler
@dbutils.redis_error_handler
def delete_v2_component(component_id: str) -> tuple[None, Literal[204]] | CxResponse:
    """Used by the DELETE /components/{component_id} API operation"""
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("DELETE /v2/components/%s invoked delete_v2_component",
                 component_id)
    if not is_valid_tenant_component(component_id, get_tenant_from_header()):
        LOGGER.warning("Component %s could not be found", component_id)
        return _404_component_not_found(resource_id=component_id)  # pylint: disable=redundant-keyword-arg
    try:
        DB.delete(component_id)
    except dbutils.NotFoundInDB:
        LOGGER.warning("Component %s could not be found", component_id)
        return _404_component_not_found(resource_id=component_id)  # pylint: disable=redundant-keyword-arg

    return None, 204


@tenant_error_handler
@dbutils.redis_error_handler
def post_v2_apply_staged() -> tuple[ApplyStagedStatus, Literal[200]] | CxResponse:
    """Used by the POST /applystaged API operation"""
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("POST /v2/applystaged invoked post_v2_apply_staged")
    try:
        data = cast(ApplyStagedComponents, get_request_json())
    except Exception as err:
        LOGGER.error("Error parsing POST request data: %s", exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    response: ApplyStagedStatus = {"succeeded": [], "failed": [], "ignored": []}
    # Obtain latest desired behavior for how to clear staging information
    # for all components
    clear_staged = get_v2_options_data().get('clear_stage', False)
    try:
        xnames = data.get("xnames", [])
        allowed_xnames, rejected_xnames = _apply_tenant_limit(xnames)
        response["ignored"] = rejected_xnames
        for xname in allowed_xnames:
            try:
                if _apply_staged(xname, clear_staged):
                    response["succeeded"].append(xname)
                else:
                    response["ignored"].append(xname)
            except Exception:
                LOGGER.exception(
                    "An error was encountered while attempting to apply stage for node %s",
                    xname)
                response["failed"].append(xname)
    except Exception as err:
        LOGGER.error("Error parsing request data: %s", exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    return response, 200


def _apply_tenant_limit(component_list: list[str]) -> tuple[list[str], list[str]]:
    tenant = get_tenant_from_header()
    if not tenant:
        return component_list, []
    tenant_components = get_tenant_component_set(tenant)
    component_set = set(component_list)
    allowed_components = component_set.intersection(tenant_components)
    rejected_components = component_set.difference(tenant_components)
    return list(allowed_components), list(rejected_components)


def _apply_staged(component_id: str, clear_staged: bool=False) -> bool:
    try:
        data = DB.get(component_id)
    except dbutils.NotFoundInDB:
        return False
    staged_state = data.get("staged_state", EMPTY_STAGED_STATE)
    staged_session_id = staged_state.get("session", "")
    if not staged_session_id:
        return False
    try:
        _set_state_from_staged(data, staged_state, staged_session_id)
    except Exception as e:
        data["error"] = str(e)
        data["enabled"] = False
        raise e
    finally:
        # For both the successful and failed cases, we want the new session to own the node
        data["session"] = staged_session_id
        data["last_action"]["action"] = Action.apply_staged
        if clear_staged:
            data["staged_state"] = copy.deepcopy(EMPTY_STAGED_STATE)
        _set_auto_fields(data)
        DB.put(component_id, data)
    return True


def _set_state_from_staged(data: CompAny, staged_state: ComponentStagedState,
                           staged_session_name: str) -> None:
    tenant = get_tenant_from_header()
    try:
        session = SESSIONS_DB.tenanted_get(staged_session_name, tenant)
    except dbutils.NotFoundInDB as exc:
        raise Exception(
            "Staged session no longer exists "
            f"(session: {staged_session_name}, tenant: {tenant})"
        ) from exc
    operation = session["operation"]
    if operation == "shutdown":
        if any(staged_state.get("boot_artifacts", {}).values()):
            raise Exception(
                "Staged operation is shutdown but boot artifacts have been specified "
                f"(session: {staged_session_name}, tenant: {tenant})"
            )
    elif operation == "boot":
        if not all(staged_state.get("boot_artifacts", {}).values()):
            raise Exception(
                "Staged operation is boot but some boot artifacts have not been specified "
                f"(session: {staged_session_name}, tenant: {tenant})"
            )
    elif operation == "reboot":
        if not all(staged_state.get("boot_artifacts", {}).values()):
            raise Exception(
                "Staged operation is reboot but some boot artifacts have not been specified "
                f"(session: {staged_session_name}, tenant: {tenant})"
            )
        data["actual_state"] = copy.deepcopy(EMPTY_ACTUAL_STATE)
    else:
        raise Exception(
            f"Invalid operation ({operation}) in staged session "
            f"(session: {staged_session_name}, tenant: {tenant})"
        )
    data["desired_state"] = ComponentDesiredState(
        boot_artifacts=copy.deepcopy(staged_state.get("boot_artifacts", EMPTY_BOOT_ARTIFACTS)),
        configuration=staged_state.get("configuration", "")
    )
    data["enabled"] = True


def _set_auto_fields[CompAnyT: (ComponentData, ComponentRecord)](data: CompAnyT) -> CompAnyT:
    data = _populate_boot_artifacts(data)
    data = _set_last_updated(data)
    data = _set_on_hold_when_enabled(data)
    data = _clear_session_when_manually_updated(data)
    data = _clear_event_stats_when_desired_state_changes(data)
    return data

def _populate_boot_artifacts[CompAnyT: (ComponentData, ComponentRecord)](
    data: CompAnyT
) -> CompAnyT:
    """
    If there is a BSS Token present in the actual_state,
    then look up the boot artifacts and add them to the
    actual_state data.

    If the data contains any boot artifacts and the BSS
    token, then those boot artifacts will be overwritten.
    If there are boot artifacts and no BSS token, then
    they will not be overwritten. Further, if the boot
    artifacts are provided and the BSS token is unknown,
    the boot artifacts will not be overwritten.
    """
    try:
        token = data['actual_state']['bss_token']
    except KeyError:
        # Either actual_state or bss_token was not present.
        pass
    else:
        # Populate the boot artifacts using the bss_token
        if token:
            try:
                data['actual_state']['boot_artifacts'] = get_boot_artifacts(
                    token)
            except BssTokenUnknown:
                LOGGER.warning("Reported BSS Token '%s' is unknown.", token)
    return data


def del_timestamp(data: CompAny) -> None:
    """
    # The actual state boot artifacts dictionary contains a timestamp
    # that is used for internal references only; we should strip it
    # from any given data. The dictionary is modified in place, and
    # no return is given.
    """
    try:
        del data['actual_state']['boot_artifacts']['timestamp']
    except KeyError:
        pass


def _set_last_updated[CompAnyT: (ComponentData, ComponentRecord)](data: CompAnyT) -> CompAnyT:
    timestamp = get_current_timestamp()
    if 'actual_state' in data and isinstance(data['actual_state'], dict) and \
                                  data['actual_state'].keys() != {"bss_token"}:
        data['actual_state']['last_updated'] = timestamp
    if 'desired_state' in data and isinstance(data['desired_state'], dict) and \
                                   data['desired_state'].keys() != {"bss_token"}:
        data['desired_state']['last_updated'] = timestamp
    if 'staged_state' in data and isinstance(data['staged_state'], dict):
        data['staged_state']['last_updated'] = timestamp
    if 'last_action' in data and isinstance(data['last_action'], dict):
        data['last_action']['last_updated'] = timestamp
    return data

def _set_on_hold_when_enabled[CompAnyT: (ComponentData, ComponentRecord)](
    data: CompAnyT
) -> CompAnyT:
    """
    The status operator doesn't monitor disabled components, so this causes a delay until it can
    revaluate the component so that other operators don't act on old phase information.
    """
    if data.get("enabled"):
        if "status" not in data:
            data["status"] = {"status_override": Status.on_hold}
        else:
            data["status"]["status_override"] = Status.on_hold
    return data


def _clear_session_when_manually_updated[CompAnyT: (ComponentData, ComponentRecord)](
    data: CompAnyT
) -> CompAnyT:
    """
    If the desired state for a component is updated outside of the setup operator, that component
    should no longer be considered part of its original session.
    """
    if data.get("desired_state") and not data.get("session"):
        data["session"] = ""
    return data


def _clear_event_stats_when_desired_state_changes[CompAnyT: (ComponentData, ComponentRecord)](
    data: CompAnyT
) -> CompAnyT:
    desired_state = data.get("desired_state", {})
    if "boot_artifacts" in desired_state or "configuration" in desired_state:
        data["event_stats"] = {
            "power_on_attempts": 0,
            "power_off_graceful_attempts": 0,
            "power_off_forceful_attempts": 0
        }
    return data


_404_component_not_found = partial(_404_resource_not_found, resource_type="Component")
