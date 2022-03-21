#
# MIT License
#
# (C) Copyright 2021-2022 Hewlett Packard Enterprise Development LP
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

import logging
from bos.operators.utils.boot_image_metadata.factory import BootImageMetaDataFactory
from bos.operators.utils.clients.s3 import S3Object

LOGGER = logging.getLogger('bos.server.controllers.v2.boot_set')


def validate_boot_sets(session_template: dict, operation: str) -> tuple[str, int]:
    """
    Validates the boot sets listed in a session template.
    It ensures that there are boot sets.
    It checks that each boot set specifies nodes via one of the specifier fields.
    Ensures that the boot artifacts exist.  
    
    Inputs:
      session_template (dict): Session template
      operation (str): Requested operation  
    Returns:
        On success, returns None
        On failure, returns anerror string
      
    """
    template_name = session_template['name']

    # Verify boot sets exist.
    if 'boot_sets' not in session_template or not session_template['boot_sets']:
        msg = f"Session template '{template_name}' must have one or more defined boot sets for " \
        "the creation of a session. It has none."
        return msg

    hardware_specifier_fields = ('node_roles_groups', 'node_list', 'node_groups')
    for bs_name, bs in session_template['boot_sets'].items():
        # Verify that the hardware is specified
        specified = [bs.get(field, None)
                     for field in hardware_specifier_fields]
        if not any(specified):
            msg = "Session template '%s' boot set '%s' must have at least one " \
                "hardware specifier field provided (%s); None were provided." \
                % (template_name, bs_name,
                   ', '.join(sorted(hardware_specifier_fields)))
            LOGGER.error(msg)
            return msg

        if operation in ['boot', 'reboot']:
            # Verify that the boot artifacts exist
            try:
                image_metadata = BootImageMetaDataFactory(bs)()
            except Exception as err:
                msg = f"Session template: {template_name} boot set: {bs_name} " \
                    f"could not locate its boot artifacts. Error: {err}"
                LOGGER.error(msg)
                return msg

            # Check boot artifacts' S3 headers
            for boot_artifact in ["kernel", "initrd", "boot_parameters"]:
                try:
                    artifact = getattr(image_metadata.boot_artifacts, boot_artifact)
                    path = artifact ['link']['path']
                    etag = artifact['link']['etag']
                    obj = S3Object(path, etag)
                    _ = obj.object_header
                except Exception as err:
                    msg = f"Session template: {template_name} boot set: {bs_name} " \
                    f"could not locate its {boot_artifact}. Error: {err}"
                    LOGGER.error(msg)
                    return msg
    return None

