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
from collections.abc import Iterable
from functools import partial
import logging
from typing import Literal, cast

import connexion
from connexion.lifecycle import ConnexionResponse as CxResponse

from bos.common.tenant_utils import (get_tenant_component_set,
                                     get_tenant_from_header,
                                     is_valid_tenant_component,
                                     tenant_error_handler)
from bos.common.types.components import ComponentRecord, update_component_record
from bos.common.types.general import JsonDict
from bos.common.utils import components_by_id, exc_type_msg, get_current_timestamp
from bos.common.values import Phase, Action, Status, EMPTY_STAGED_STATE, EMPTY_BOOT_ARTIFACTS
from bos.server import redis_db_utils as dbutils
from bos.server.controllers.utils import _400_bad_request, _404_resource_not_found
from bos.server.options import get_v2_options_data
from bos.server.dbs.boot_artifacts import get_boot_artifacts, BssTokenUnknown
from bos.server.options import update_server_log_level
from bos.server.utils import get_request_json

LOGGER = logging.getLogger(__name__)
DB = dbutils.ComponentDBWrapper()
SESSIONS_DB = dbutils.SessionDBWrapper()


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
        page_size: int=0) -> tuple[list[ComponentRecord], Literal[200]] | CxResponse:
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


def get_v2_components_data(id_list: list[str] | None=None,
                           enabled: bool | None=None,
                           session: str | None=None,
                           staged_session: str | None=None,
                           phase: str | None=None,
                           status: str | None=None,
                           tenant: str | None=None,
                           start_after_id: str | None=None,
                           page_size: int=0,
                           delete_timestamp: bool=False) -> list[ComponentRecord]:
    """Used by the GET /components API operation

    Allows filtering using a comma separated list of ids.
    """
    tenant_components = get_tenant_component_set(tenant) if tenant else None

    if id_list is not None:
        id_set = set(id_list)
        if tenant_components is not None:
            id_set.intersection_update(tenant_components)
    else:
        id_set = tenant_components

    # If id_set is not None but is empty, that means no components in the system
    # will match our filter, so we can return an empty list immediately.
    if id_set is not None and not id_set:
        return []

    if any([id_set, enabled, session, staged_session, phase, status]):
        _component_filter_func = partial(_filter_component,
                                         id_set=id_set,
                                         enabled=enabled,
                                         session=session or None,
                                         staged_session=staged_session or None,
                                         phase=phase or None,
                                         status=status or None,
                                         delete_timestamp=delete_timestamp)
    else:
        _component_filter_func = partial(_set_status,
                                         delete_timestamp=delete_timestamp)

    return DB.get_all_filtered(filter_func=_component_filter_func,
                               start_after_key=start_after_id,
                               page_size=page_size)


def _filter_component(data: ComponentRecord,
                      id_set: set[str] | None=None,
                      enabled: bool | None=None,
                      session: str | None=None,
                      staged_session: str | None=None,
                      phase: str | None=None,
                      status: str | None=None,
                      delete_timestamp: bool=False) -> ComponentRecord | None:
    # Do all of the checks we can before calculating status, to avoid doing it needlessly
    if id_set is not None and data["id"] not in id_set:
        return None
    if enabled is not None and data.get('enabled', None) != enabled:
        return None
    if session is not None and data.get('session', None) != session:
        return None
    if staged_session is not None and \
       data.get('staged_state', {}).get('session', None) != staged_session:
        return None
    updated_data = _set_status(data)

    status_data = updated_data.get('status')
    if phase is not None and status_data.get('phase') != phase:
        return None
    if status is not None and status_data.get('status') not in status.split(
            ','):
        return None
    if delete_timestamp:
        del_timestamp(updated_data)
    return updated_data


def _set_status(data: ComponentRecord, delete_timestamp: bool = False) -> ComponentRecord:
    """
    This sets the status field of the overall status.
    """
    if "status" not in data:
        data["status"] = {"phase": "", "status_override": ""}
    data['status']['status'] = _calculate_status(data)
    if delete_timestamp:
        del_timestamp(data)
    return data


def _calculate_status(data: ComponentRecord) -> str:
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

    status = status = Status.stable
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
def patch_v2_components() -> tuple[list[ComponentRecord], Literal[200]] | CxResponse:
    """Used by the PATCH /components API operation"""
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("PATCH /v2/components invoked patch_v2_components")
    try:
        data = get_request_json()
    except Exception as err:
        LOGGER.error("Error parsing PATCH request data: %s", exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    if isinstance(data, list):
        return patch_v2_components_list(data)
    if isinstance(data, dict):
        return patch_v2_components_dict(data)

    LOGGER.error("Unexpected data type %s", str(type(data)))
    return _400_bad_request(f"Unexpected data type {type(data).__name__}")


def patch_v2_components_list(
    data: list[ComponentRecord]
) -> tuple[list[ComponentRecord], Literal[200]] | CxResponse:

    LOGGER.debug("patch_v2_components_list: %d components specified", len(data))
    try:
        patch_data = components_by_id(data)
    except Exception as err:
        LOGGER.error("Error parsing patch data: %s", exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    try:
        components = _load_comps_from_id_list(list(patch_data))
    except KeyError as exc:
        LOGGER.warning("Component %s could not be found", exc)
        return _404_component_not_found(resource_id=str(exc))  # pylint: disable=redundant-keyword-arg

    try:
        for comp_id, patch_comp in patch_data.items():
            update_component_record(components[comp_id], _set_auto_fields(patch_comp))
    except Exception as err:
        LOGGER.error("Error patching component data: %s", exc_type_msg(err))
        return _400_bad_request(f"Error patching the data provided: {err}")

    DB.mput(components)
    return list(components.values()), 200


def patch_v2_components_dict(data: JsonDict) -> tuple[list[ComponentRecord],
                                                      Literal[200]] | CxResponse:
    filters = data.get("filters", {})
    ids = filters.get("ids", None)
    session = filters.get("session", None)
    if ids and session:
        LOGGER.warning("Multiple filters provided")
        return _400_bad_request("Multiple filters provided")
    if not ids and not session:
        LOGGER.warning("No filter provided")
        return _400_bad_request("No filter provided.")
    if ids:
        try:
            id_list = ids.split(',')
        except Exception as err:
            LOGGER.error("Error parsing the IDs provided: %s",
                         exc_type_msg(err))
            return _400_bad_request(f"Error parsing the ids provided: {err}")

        try:
            components = _load_comps_from_id_list(id_list)
        except KeyError as exc:
            LOGGER.warning("Component %s could not be found", exc)
            return _404_component_not_found(resource_id=str(exc))  # pylint: disable=redundant-keyword-arg
    else:
        # session
        components = components_by_id(get_v2_components_data(session=session,
                                                             tenant=get_tenant_from_header()))
        LOGGER.debug(
            "patch_v2_components_dict: %d IDs found for specified session",
            len(components))
    patch = data.get("patch")
    patch.pop("id", None)
    patch = _set_auto_fields(patch)
    try:
        for comp in components.values():
            update_component_record(comp, patch)
    except Exception as err:
        LOGGER.error("Error patching component data: %s", exc_type_msg(err))
        return _400_bad_request(f"Error patching the data provided: {err}")

    DB.mput(components)
    return list(components.values()), 200


def _load_comps_from_id_list(id_list: list[str]) -> dict[str, ComponentRecord]:
    # Make sure all of the components exist and belong to this tenant (if any)
    LOGGER.debug("patch_v2_components: %d IDs specified", len(id_list))
    invalid_comp_id = _get_invalid_comp_id_for_tenant(id_list, get_tenant_from_header())
    if invalid_comp_id is not None:
        raise KeyError(invalid_comp_id)

    try:
        return DB.mget(id_list)
    except dbutils.NotFoundInDB as exc:
        raise KeyError(exc.key) from exc


def _get_invalid_comp_id_for_tenant(comp_id_list: Iterable[str], tenant: str | None) -> str | None:
    """
    If no tenant is specified, return None.
    If any of the listed component IDs are not valid for the specified tenant, return one of the
    invalid IDs.
    Otherwise return None.
    """
    if not tenant:
        return None
    legal_component_ids = get_tenant_component_set(tenant)
    for comp_id in comp_id_list:
        if comp_id not in legal_component_ids:
            return comp_id
    return None


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
        data = cast(ComponentRecord, get_request_json())
    except Exception as err:
        LOGGER.error("Error parsing PUT '%s' request data: %s", component_id,
                     exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    data['id'] = component_id
    data = _set_auto_fields(data)
    DB.put(component_id, data)
    return data, 200


@tenant_error_handler
@dbutils.redis_error_handler
def patch_v2_component(component_id: str) -> tuple[ComponentRecord, Literal[200]] | CxResponse:
    """Used by the PATCH /components/{component_id} API operation"""
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("PATCH /v2/components/%s invoked patch_v2_component",
                 component_id)
    try:
        patch_data = cast(ComponentRecord, get_request_json())
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


def _validate_actual_state_change_is_allowed(current_data: ComponentRecord) -> bool:
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
def post_v2_apply_staged() -> tuple[JsonDict, Literal[200]] | CxResponse:
    """Used by the POST /applystaged API operation"""
    # For all entry points into the server, first refresh options and update log level if needed
    update_server_log_level()

    LOGGER.debug("POST /v2/applystaged invoked post_v2_apply_staged")
    try:
        data = get_request_json()
    except Exception as err:
        LOGGER.error("Error parsing POST request data: %s", exc_type_msg(err))
        return _400_bad_request(f"Error parsing the data provided: {err}")

    response = {"succeeded": [], "failed": [], "ignored": []}
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
    staged_state = data.get("staged_state", {})
    staged_session_id = staged_state.get("session", "")
    if not staged_session_id:
        return False
    try:
        response = _set_state_from_staged(data)
    except Exception as e:
        data["error"] = str(e)
        data["enabled"] = False
        raise e
    finally:
        # For both the successful and failed cases, we want the new session to own the node
        data["session"] = staged_session_id
        data["last_action"]["action"] = Action.apply_staged
        if clear_staged:
            data["staged_state"] = EMPTY_STAGED_STATE
        _set_auto_fields(data)
        DB.put(component_id, data)
    return response


def _set_state_from_staged(data: ComponentRecord) -> Literal[True]:
    staged_state = data.get("staged_state", {})
    staged_session_name = staged_state.get("session", "")
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
        _copy_staged_to_desired(data)
    elif operation == "boot":
        if not all(staged_state.get("boot_artifacts", {}).values()):
            raise Exception(
                "Staged operation is boot but some boot artifacts have not been specified "
                f"(session: {staged_session_name}, tenant: {tenant})"
            )
        _copy_staged_to_desired(data)
    elif operation == "reboot":
        if not all(staged_state.get("boot_artifacts", {}).values()):
            raise Exception(
                "Staged operation is reboot but some boot artifacts have not been specified "
                f"(session: {staged_session_name}, tenant: {tenant})"
            )
        _copy_staged_to_desired(data)
        data["actual_state"] = {
            "boot_artifacts": EMPTY_BOOT_ARTIFACTS,
            "bss_token": ""
        }
    else:
        raise Exception(
            f"Invalid operation ({operation}) in staged session "
            f"(session: {staged_session_name}, tenant: {tenant})"
        )
    data["enabled"] = True
    return True


def _copy_staged_to_desired(data: ComponentRecord) -> None:
    staged_state = data.get("staged_state", {})
    data["desired_state"] = {
        "boot_artifacts": staged_state.get("boot_artifacts", {}),
        "configuration": staged_state.get("configuration", "")
    }


def _set_auto_fields(data: ComponentRecord) -> ComponentRecord:
    data = _populate_boot_artifacts(data)
    data = _set_last_updated(data)
    data = _set_on_hold_when_enabled(data)
    data = _clear_session_when_manually_updated(data)
    data = _clear_event_stats_when_desired_state_changes(data)
    return data


def _populate_boot_artifacts(data: ComponentRecord) -> ComponentRecord:
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


def del_timestamp(data: ComponentRecord) -> None:
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


def _set_last_updated(data: ComponentRecord) -> ComponentRecord:
    timestamp = get_current_timestamp()
    for section in [
            'actual_state', 'desired_state', 'staged_state', 'last_action'
    ]:
        if section in data and isinstance(
                data[section], dict) and data[section].keys() != {"bss_token"}:
            data[section]['last_updated'] = timestamp
    return data


def _set_on_hold_when_enabled(data: ComponentRecord) -> ComponentRecord:
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


def _clear_session_when_manually_updated(data: ComponentRecord) -> ComponentRecord:
    """
    If the desired state for a component is updated outside of the setup operator, that component
    should no longer be considered part of it's original session.
    """
    if data.get("desired_state") and not data.get("session"):
        data["session"] = ""
    return data


def _clear_event_stats_when_desired_state_changes(data: ComponentRecord) -> ComponentRecord:
    desired_state = data.get("desired_state", {})
    if "boot_artifacts" in desired_state or "configuration" in desired_state:
        data["event_stats"] = {
            "power_on_attempts": 0,
            "power_off_graceful_attempts": 0,
            "power_off_forceful_attempts": 0
        }
    return data


_404_component_not_found = partial(_404_resource_not_found, resource_type="Component")
