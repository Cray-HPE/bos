#
# MIT License
#
# (C) Copyright 2021-2022, 2024 Hewlett Packard Enterprise Development LP
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
from bos.common.utils import exc_type_msg
from bos.operators.utils.boot_image_metadata.factory import BootImageMetaDataFactory
from bos.operators.utils.clients.s3 import S3Object, ArtifactNotFound

LOGGER = logging.getLogger('bos.server.controllers.v2.boot_set')

BOOT_SET_SUCCESS = 0
BOOT_SET_WARNING = 1
BOOT_SET_ERROR = 2

# Valid boot sets are required to have at least one of these fields
HARDWARE_SPECIFIER_FIELDS = ( "node_list", "node_roles_groups", "node_groups" )


def validate_boot_sets(session_template: dict,
                       operation: str,
                       template_name: str) -> tuple[str, int]:
    """
    Validates the boot sets listed in a session template.
    It ensures that there are boot sets.
    It checks that each boot set specifies nodes via at least one of the specifier fields.
    Ensures that the boot artifacts exist.

    Inputs:
      session_template (dict): Session template data
      operation (str): Requested operation
      template_name (str): The name of the session template; Note, during Session template
                                 creation, the name in the session template data does not have
                                 to match the name used to create the session template.
    Returns:
        Returns an error_code and a message
          error_code:
            0 -- Success
            1 -- Warning, not fatal
            2 -- Error, fatal


    """
    # Verify boot sets exist.
    if not session_template.get('boot_sets', None):
        msg = f"Session template '{template_name}' requires at least 1 boot set."
        return BOOT_SET_ERROR, msg

    for bs_name, bs in session_template['boot_sets'].items():
        # Verify that the hardware is specified
        specified = [bs.get(field, None)
                     for field in HARDWARE_SPECIFIER_FIELDS]
        if not any(specified):
            msg = f"Session template: '{template_name}' boot set: '{bs_name}' " \
                  f"must have at least one " \
                f"hardware specifier field provided (%s); None were provided." \
                % (', '.join(sorted(HARDWARE_SPECIFIER_FIELDS)))
            LOGGER.error(msg)
            return BOOT_SET_ERROR, msg
        if operation in ['boot', 'reboot']:
            # Verify that the boot artifacts exist
            try:
                image_metadata = BootImageMetaDataFactory(bs)()
            except Exception as err:
                msg = f"Session template: '{template_name}' boot set: '{bs_name}' " \
                    f"could not locate its boot artifacts. Error: " + exc_type_msg(err)
                LOGGER.error(msg)
                return BOOT_SET_ERROR, msg

            # Check boot artifacts' S3 headers
            for boot_artifact in ["kernel"]:
                try:
                    artifact = getattr(image_metadata.boot_artifacts, boot_artifact)
                    path = artifact ['link']['path']
                    etag = artifact['link']['etag']
                    obj = S3Object(path, etag)
                    _ = obj.object_header
                except Exception as err:
                    msg = f"Session template: '{template_name}' boot set: '{bs_name}' " \
                    f"could not locate its {boot_artifact}. Error: " + exc_type_msg(err)
                    LOGGER.error(msg)
                    return BOOT_SET_ERROR, msg

            warning_flag = False
            warn_msg = ""
            for boot_artifact in ["initrd", "boot_parameters"]:
                try:
                    artifact = getattr(image_metadata.boot_artifacts, boot_artifact)
                    if not artifact:
                        raise ArtifactNotFound(f"Session template: '{template_name}' "
                                               f"boot set: '{bs_name}' "
                                               f"does not contain a {boot_artifact}.")
                    path = artifact ['link']['path']
                    etag = artifact['link']['etag']
                    obj = S3Object(path, etag)
                    _ = obj.object_header
                except Exception as err:
                    msg = f"Session template: '{template_name}' boot set: '{bs_name}' " \
                    f"could not locate its {boot_artifact}. Warning: " + exc_type_msg(err)
                    LOGGER.warning(msg)
                    warning_flag = True
                    warn_msg = warn_msg + msg
            if warning_flag:
                return BOOT_SET_WARNING, warn_msg

    return BOOT_SET_SUCCESS, "Valid"
