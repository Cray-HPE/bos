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

import copy
import logging

from bos.common.tenant_utils import get_tenant_aware_key
from bos.common.utils import exc_type_msg
from bos.server.backup import backup_bos_data
from bos.server.models.v2_component import V2Component as Component
from bos.server.models.v2_component_actual_state import V2ComponentActualState as ComponentActualState
from bos.server.models.v2_options import V2Options as Options
from bos.server.models.v2_session import V2Session as Session
from bos.server.models.v2_session_status import V2SessionStatus as SessionStatus
import bos.server.redis_db_utils as dbutils
from bos.server.utils import _validate_sanitize_session_template


LOGGER = logging.getLogger('bos.server.migration')


class ValidationError(Exception):
    pass


def create_sanitized_session_template(data):
    """
    If there are any problems with the template, raise an exception
    Otherwise, return a tuple of the session template DB key and the session template itself

    I cannot envision a scenario where we end up with a session template in the database where
    the key doesn't line up with the name and tenant, but it does no harm to make sure
    """
    try:
        st_name = data["name"]
    except KeyError as exc:
        # In the unlikely event that this template has no name field, we don't want to keep it
        raise ValidationError("Missing required 'name' field") from exc

    new_data = copy.deepcopy(data)
    try:
        # Validate that the session template follows the API schema, and sanitize it
        _validate_sanitize_session_template(st_name, new_data)
    except Exception as exc:
        raise ValidationError(f"Validation failure: {exc_type_msg(exc)}") from exc

    new_key = get_tenant_aware_key(st_name, new_data.get("tenant", None)).encode()
    return new_key, new_data


def sanitize_session_templates():
    LOGGER.info("Sanitizing session templates")
    db=dbutils.get_wrapper(db='session_templates')
    response = db.get_keys()
    for st_key in response:
        data = db.get(st_key)
        try:
            new_key, new_data = create_sanitized_session_template(data)
        except ValidationError as exc:
            LOGGER.warning("Deleting session template (reason: %s): %s", exc, data)
            db.delete(st_key)
            continue
        if new_key == st_key and new_data == data:
            # No changes for this template
            continue
        # Either the key has changed, the data has changed, or both
        if new_key == st_key:
            # The template data has been modified
            LOGGER.warning("Modifying session template. Before: %s After: %s", data, new_data)
            db.put(st_key, new_data)
            continue
        if new_data == data:
            # This means that the template contents did not change, but its DB key did.
            # I don't anticipate this happening, but better to be sure that our keys are correct,
            # since in the past our patching code did not have a lot of safeguards.
            LOGGER.warning("Session template database key changing (old key: '%s', new key: '%s') "
                           "but template contents unchanged: %s", st_key, new_key, data)
            db.rename(st_key, new_key)
            continue
        # Finally, this means that the template contents changed AND the DB key did
        # I also don't anticipate this happening
        LOGGER.warning("Modifying session template and DB key (old key: '%s', new key: '%s'). "
                       "Before: %s After: %s", st_key, new_key, data, new_data)
        LOGGER.info("Removing old entry from database")
        db.delete(st_key)
        LOGGER.info("Adding modified session template under new key")
        db.put(new_key, new_data)
    LOGGER.info("Done sanitizing session templates")


def sanitize_options():
    LOGGER.info("Sanitizing options")
    db=dbutils.get_wrapper(db='options')
    options = db.get_all_as_dict()
    try:
        Options.from_dict(options)
    except:
        LOGGER.warning("options = %s", options)
        LOGGER.exception("Error with options")
    response = db.get_keys()
    for st_key in response:
        data = db.get(st_key)
        try:
            Options.from_dict({ str(st_key): data })
        except:
            LOGGER.exception("Error with option '%s' = '%s'", st_key, data)


def sanitize_sessions():
    LOGGER.info("Sanitizing sessions")
    db=dbutils.get_wrapper(db='sessions')
    response = db.get_keys()
    for st_key in response:
        data = db.get(st_key)
        try:
            Session.from_dict(data)
        except:
            LOGGER.warning("key = %s, data = %s", st_key, data)
            LOGGER.exception("Error with session")


def sanitize_session_statuses():
    LOGGER.info("Sanitizing session statuses")
    db=dbutils.get_wrapper(db='session_status')
    response = db.get_keys()
    for st_key in response:
        data = db.get(st_key)
        try:
            SessionStatus.from_dict(data)
        except:
            LOGGER.warning("key = %s, data = %s", st_key, data)
            LOGGER.exception("Error with session status")


def sanitize_components():
    LOGGER.info("Sanitizing components")
    db=dbutils.get_wrapper(db='components')
    response = db.get_keys()
    for st_key in response:
        data = db.get(st_key)
        try:
            Component.from_dict(data)
        except:
            LOGGER.warning("key = %s, data = %s", st_key, data)
            LOGGER.exception("Error with component")

def sanitize_bss_tokens_boot_artifacts():
    LOGGER.info("Sanitizing bss_tokens_boot_artifacts")
    db=dbutils.get_wrapper(db='bss_tokens_boot_artifacts')
    response = db.get_keys()
    for st_key in response:
        data = db.get(st_key)
        try:
            timestamp = data.pop("timestamp")
        except:
            LOGGER.warning("key = %s, data = %s", st_key, data)
            LOGGER.exception("Error with bss_tokens_boot_artifacts timestamp")
            continue
        comp_actual_state = { "boot_artifacts": data, "bss_token": str(st_key), "last_updated": timestamp }
        try:
            ComponentActualState.from_dict(comp_actual_state)
        except:
            LOGGER.warning("key = %s, data = %s, cas = %s", st_key, data, comp_actual_state)
            LOGGER.exception("Error with bss_tokens_boot_artifacts")


def perform_migrations():
    sanitize_options()
    sanitize_session_templates()
    sanitize_sessions()
    sanitize_session_statuses()
    sanitize_components()
    sanitize_bss_tokens_boot_artifacts()



if __name__ == "__main__":
    backup_bos_data("pre-migration")
    perform_migrations()
    backup_bos_data("post-migration")
