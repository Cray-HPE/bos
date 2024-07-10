#
# MIT License
#
# (C) Copyright 2019, 2021-2022, 2024 Hewlett Packard Enterprise Development LP
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
import re

import connexion

from bos.server.models.v2_session_template import V2SessionTemplate as SessionTemplate  # noqa: E501

class ParsingException(Exception):
    pass


def _canonize_xname(xname):
    """Ensure the xname is canonical.
    * Its components should be lowercase.
    * Any leading zeros should be stripped off.

    :param xname: xname to canonize
    :type xname: string

    :return: canonized xname
    :rtype: string
    """
    return re.sub(r'x0*(\d+)c0*(\d+)s0*(\d+)b0*(\d+)n0*(\d+)', r'x\1c\2s\3b\4n\5', xname.lower())


def _get_request_json():
    """
    Used by endpoints which are expecting a JSON payload in the request body.
    Returns the JSON payload.
    Raises an Exception otherwise
    """
    if not connexion.request.is_json:
        raise ParsingException("Non-JSON request received")
    return connexion.request.get_json()


def _sanitize_xnames(st_json):
    """
    Sanitize xnames - Canonize the xnames
    Args:
      st_json (dict): The Session Template as a JSON object

    Returns:
      Nothing
    """
    # There should always be a boot_sets field -- this function
    # is only called after the template has been verified
    for boot_set in st_json['boot_sets'].values():
        if 'node_list' not in boot_set:
            continue
        boot_set['node_list'] = [_canonize_xname(node) for node in boot_set['node_list']]


def _validate_sanitize_session_template(session_template_id, template_data):
    """
    Used when creating or patching session templates
    """
    # The boot_sets field is required.
    if "boot_sets" not in template_data:
        raise ParsingException("Missing required 'boot_sets' field")

    # All keys in the boot_sets mapping must match the 'name' fields in the
    # boot sets to which they map (if they contain a 'name' field).
    for bs_name, bs in template_data["boot_sets"].items():
        if "name" not in bs:
            # Set the field here -- this allows the name to be validated
            # per the schema later
            bs["name"] = bs_name
        elif bs["name"] != bs_name:
            raise ParsingException(f"boot_sets key ({bs_name}) does not match 'name' "
                                   f"field of corresponding boot set ({bs['name']})")

    # Convert the JSON request data into a SessionTemplate object.
    # Any exceptions raised here would be generated from the model
    # (i.e. bos.server.models.v2_session_template).
    SessionTemplate.from_dict(template_data)

    # We do not bother storing the boot set names inside the boot sets, so delete them.
    # We know every boot set has a name field because we verified that earlier.
    for bs in template_data["boot_sets"].values():
        del bs["name"]

    _sanitize_xnames(template_data)
    template_data['name'] = session_template_id
