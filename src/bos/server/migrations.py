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
from bos.server.utils import _validate_sanitize_session_template
import bos.server.redis_db_utils as dbutils

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
    changed=0
    for st_key in response:
        data = db.get(st_key)
        try:
            new_key, new_data = create_sanitized_session_template(data)
        except ValidationError as exc:
            LOGGER.warning("Deleting session template (reason: %s): %s", exc, data)
            db.delete(data)
            continue
        if new_key == st_key and new_data == data:
            # No changes for this template
            continue
        # Either the key has changed, the data has changed, or both
        changed+=1
        if new_key == st_key:
            # The template data has been modified
            LOGGER.warning("Modifying session template. Before: %s After: %s", data, new_data)
            db.put(st_key, new_data)
            continue
        if new_data == data:
            # This means that the template contents did not change, but its DB key did.
            # I don't anticipate this happening, but better to be sure that our keys are correct,
            # since in the past our patching code did not have a lot of safeguards.
            LOGGER.warning("Session template database key changing, but template contents "
                           "unchanged: %s", data)
        else:
            # Finally, this means that the template contents changed AND the DB key did
            # I also don't anticipate this happening
            LOGGER.warning("Modifying session template and DB key (old key: '%s', new key: '%s'). "
                        "Before: %s After: %s", st_key, new_key, data, new_data)
        LOGGER.info("Removing old entry from database")
        db.delete(st_key)
        LOGGER.info("Adding modified session template under new key")
        db.put(new_key, new_data)
    LOGGER.info("Done sanitizing session templates")


def perform_migrations():
    sanitize_session_templates()


if __name__ == "__main__":
    perform_migrations()
