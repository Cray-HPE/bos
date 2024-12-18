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

from bos.common.utils import exc_type_msg
from bos.operators.utils.boot_image_metadata.factory import BootImageMetaDataFactory
from bos.operators.utils.clients.s3 import S3Object, ArtifactNotFound

from .defs import LOGGER
from .exceptions import BootSetError, BootSetWarning


def validate_boot_artifacts(bs: dict):
    # Verify that the boot artifacts exist
    try:
        image_metadata = BootImageMetaDataFactory(bs)()
    except Exception as err:
        raise BootSetError(
            f"Can't find boot artifacts. Error: {exc_type_msg(err)}") from err

    # Check boot artifacts' S3 headers
    for boot_artifact in ["kernel"]:
        try:
            artifact = getattr(image_metadata.boot_artifacts, boot_artifact)
            path = artifact['link']['path']
            etag = artifact['link']['etag']
            obj = S3Object(path, etag)
            _ = obj.object_header
        except Exception as err:
            raise BootSetError(f"Can't find {boot_artifact} in "
                               f"{image_metadata.manifest_s3_url.url}. "
                               f"Error: {exc_type_msg(err)}") from err

    for boot_artifact in ["initrd", "boot_parameters"]:
        try:
            artifact = getattr(image_metadata.boot_artifacts, boot_artifact)
            if not artifact:
                raise ArtifactNotFound()
            path = artifact['link']['path']
            etag = artifact['link']['etag']
            obj = S3Object(path, etag)
            _ = obj.object_header
        except ArtifactNotFound as err:
            msg = f"{image_metadata.manifest_s3_url.url} doesn't contain a {boot_artifact}"
            # Plenty of images lack boot_parameters, and this is not a big deal.
            if boot_artifact != "boot_parameters":
                raise BootSetWarning(msg) from err
            LOGGER.info(msg)
        except Exception as err:
            raise BootSetWarning(
                f"Unable to check {boot_artifact} in {image_metadata.manifest_s3_url.url}. "
                f"Warning: {exc_type_msg(err)}") from err
