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
import jsonref
import jsonschema
import logging
import pkgutil

from bos.common.tenant_utils import get_tenant_aware_key
from bos.common.utils import exc_type_msg
from bos.server.backup import backup_bos_data
import bos.server.controllers.v2.options as options
from bos.server.controllers.v2.sessiontemplates import validate_sanitize_session_template
import bos.server.redis_db_utils as dbutils
from bos.server.utils import ParsingException


LOGGER = logging.getLogger('bos.server.migration')


def create_sanitized_session_template(data, api_schema):
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
        raise ParsingException("Missing required 'name' field") from exc

    new_data = copy.deepcopy(data)
    try:
        # Validate that the session template follows the API schema, and sanitize it
        validate_sanitize_session_template(st_name, new_data)
        jsonschema.validate(new_data, api_schema["V2SessionTemplate"])
    except Exception as exc:
        raise ParsingException(f"Validation failure: {exc_type_msg(exc)}") from exc

    new_key = get_tenant_aware_key(st_name, new_data.get("tenant", None)).encode()
    return new_key, new_data


def sanitize_session_templates(api_schema):
    LOGGER.info("Sanitizing session templates")
    db=dbutils.get_wrapper(db='session_templates')
    response = db.get_keys()
    for st_key in response:
        data = db.get(st_key)
        try:
            new_key, new_data = create_sanitized_session_template(data, api_schema)
        except ParsingException as exc:
            LOGGER.warning("Deleting session template (reason: %s): %s", exc, data)
            #db.delete(st_key)
            continue

        if new_key == st_key and new_data == data:
            # No changes for this template
            continue

        # Either the key has changed, the data has changed, or both

        # If the template data has been modified but not the key, just update it
        if new_key == st_key:
            LOGGER.warning("Modifying session template. Before: %s After: %s", data, new_data)
            #db.put(st_key, new_data)
            continue

        # This means that the DB key changed.
        # I don't anticipate this happening, but better to be sure that our keys are correct,
        # since in the past our patching code did not have a lot of safeguards.
        # Essentially this means that the name and/or tenant inside the template record generate
        # a hash key that does not match the one we are using. This is not good.
        LOGGER.warning("Deleting session template. Reason: db key should be '%s' but actually is "
                       "'%s'. Template = %s", new_key, st_key, data)
        #db.delete(st_key)
    LOGGER.info("Done sanitizing session templates")


def sanitize_options(api_schema):
    LOGGER.info("Sanitizing options")
    db=dbutils.get_wrapper(db='options')
    options_data = db.get(options.OPTIONS_KEY)
    new_options_data = {}
    for opt_name, opt_value in options_data.items():
        if opt_name not in options.DEFAULTS:
            LOGGER.warning("Removing unknown option '%s' with value '%s'", opt_name, opt_value)
            continue
        try:
            jsonschema.validate({ opt_name: opt_value }, api_schema["V2Options"])
        except Exception as exc:
            LOGGER.warning("Deleting option '%s' with value '%s'; reason: %s", opt_name, opt_value, exc)
            continue
        new_options_data[opt_name] = opt_value
    if options_data != new_options_data:
        LOGGER.info("Updating options. Old: %s; new: %s", options_data, new_options_data)
        #db.put(options.OPTIONS_KEY, new_options_data)
    LOGGER.info("Done sanitizing options")


def sanitize_sessions(api_schema):
    LOGGER.info("Sanitizing sessions")
    db=dbutils.get_wrapper(db='sessions')
    statusdb=dbutils.get_wrapper(db='session_status')
    response = db.get_keys()
    for st_key in response:
        data = db.get(st_key)
        try:
            jsonschema.validate(data, api_schema["V2Session"])
        except Exception as exc:
            LOGGER.warning("Deleting session (reason: %s): %s", exc, data)
            #db.delete(st_key)
            if st_key in statusdb:
                LOGGER.warning("Deleting session status %s", st_key)
                #statusdb.delete(st_key)
            continue

        new_key = get_tenant_aware_key(data['name'], data.get("tenant", None)).encode()
        if new_key == st_key:
            continue

        LOGGER.warning("Deleting session. Reason: db key should be '%s' but actually is "
                       "'%s'. Template = %s", new_key, st_key, data)
        #db.delete(st_key)
        if st_key in statusdb:
            LOGGER.warning("Deleting session status %s", st_key)
            #statusdb.delete(st_key)

    LOGGER.info("Done sanitizing sessions")


def sanitize_session_statuses(api_schema):
    LOGGER.info("Sanitizing session statuses")
    db=dbutils.get_wrapper(db='session_status')
    response = db.get_keys()
    for st_key in response:
        data = db.get(st_key)
        try:
            jsonschema.validate(data, api_schema["V2SessionExtendedStatus"])
        except:
            LOGGER.warning("key = %s, data = %s", st_key, data)
            LOGGER.exception("Error with session status")
    LOGGER.info("Done sanitizing session statuses")


def sanitize_components(api_schema):
    LOGGER.info("Sanitizing components")
    db=dbutils.get_wrapper(db='components')
    response = db.get_keys()
    for st_key in response:
        data = db.get(st_key)
        try:
            jsonschema.validate(data, api_schema["V2ComponentWithId"])
        except:
            LOGGER.warning("key = %s, data = %s", st_key, data)
            LOGGER.exception("Error with component")      
    LOGGER.info("Done sanitizing components")


def sanitize_bss_tokens_boot_artifacts(api_schema):
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
            jsonschema.validate(comp_actual_state, api_schema["V2ComponentActualState"])
        except:
            LOGGER.warning("key = %s, data = %s, cas = %s", st_key, data, comp_actual_state)
            LOGGER.exception("Error with bss_tokens_boot_artifacts")
    LOGGER.info("Done sanitizing bss_tokens_boot_artifacts")


def _replace_nullable(d: dict):
    if "nullable" in d and d["nullable"]:
        try:
            if isinstance(d["type"], list):
                d["type"].append("null")
            else:
                d["type"] = [ d["type"], "null" ]
        except KeyError:
            d["type"] = [ "object", "null" ]
    for v in d.values():
        _replace_nullable(v)


def perform_migrations():
    with open("/app/lib/bos/server/openapi/openapi.json") as f:
        oas_json = jsonref.load(f)
    api_schema = oas_json["components"]["schemas"]

    # The nullable keyword works for OAS but not for jsonschema
    _replace_nullable(api_schema)

    sanitize_options(api_schema)
    sanitize_session_templates(api_schema)
    sanitize_sessions(api_schema)
    sanitize_session_statuses(api_schema)
    sanitize_components(api_schema)
    sanitize_bss_tokens_boot_artifacts(api_schema)


if __name__ == "__main__":    
    #backup_bos_data("pre-migration")
    perform_migrations()
    #backup_bos_data("post-migration")
    pass