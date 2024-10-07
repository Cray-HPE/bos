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

from bos.common.utils import exc_type_msg, requests_retry_session
from bos.operators.utils.clients.ims import get_arch_from_image_data, get_image, \
                                            get_ims_id_from_s3_url, ImageNotFound
from bos.operators.utils.clients.s3 import S3Url
from bos.server.controllers.v2.options import OptionsData

from .defs import DEFAULT_ARCH
from .exceptions import BootSetArchMismatch, BootSetError, BootSetWarning, \
                        CannotValidateBootSetArch, NonImsImage

# Mapping from BOS boot set arch values to expected IMS image arch values
# Omits BOS Other value, since there is no corresponding IMS image arch value
EXPECTED_IMS_ARCH = {
    "ARM": "aarch64",
    "Unknown": "x86_64",
    "X86": "x86_64"
}


def validate_ims_boot_image(bs: dict, options_data: OptionsData) -> None:
    """
    If the boot set architecture is not set to Other, check that the IMS image
    architecture matches the boot set architecture (treating a boot set architecture
    of Unknown as X86)

    Otherwise, at least validate whether the boot image is in IMS, if we expect it to be.
    """
    try:
        bs_path = bs["path"]
    except KeyError as err:
        raise BootSetError("Missing required 'path' field") from err

    bs_arch = bs.get("arch", DEFAULT_ARCH)

    ims_id = get_ims_image_id(bs_path)

    # If IMS being inaccessible is not a fatal error, then reduce the number
    # of retries we make, to prevent a lengthy delay
    num_retries = 8 if options_data.ims_errors_fatal else 4

    try:
        image_data = get_ims_image_data(ims_id, num_retries)
    except ImageNotFound as err:
        if options_data.ims_images_must_exist:
            raise BootSetError(str(err)) from err
        raise BootSetWarning(str(err)) from err
    except Exception as err:
        if options_data.ims_errors_fatal:
            raise BootSetError(exc_type_msg(err)) from err
        if bs_arch != 'Other':
            # This means that this error is preventing us from validating the
            # boot set architecture
            raise CannotValidateBootSetArch(str(err)) from err
        # We weren't going to be validating the architecture, since it is Other,
        # but we should still log this as a warning
        raise BootSetWarning(str(err)) from err

    if bs_arch == 'Other':
        raise CannotValidateBootSetArch("Boot set arch set to 'Other'")

    try:
        ims_image_arch = get_arch_from_image_data(image_data)
    except Exception as err:
        # This most likely indicates that the IMS image data we got wasn't even a dict
        if options_data.ims_errors_fatal:
            raise BootSetError(exc_type_msg(err)) from err
        raise BootSetWarning(str(err)) from err

    if EXPECTED_IMS_ARCH[bs_arch] != ims_image_arch:
        raise BootSetArchMismatch(bs_arch=bs_arch, expected_ims_arch=EXPECTED_IMS_ARCH[bs_arch],
                                  actual_ims_arch=ims_image_arch)


def get_ims_image_id(path: str) -> str:
    """
    If the image is an IMS image, return its ID.
    Raise NonImsImage otherwise,
    Note that this does not actually check IMS to see if the ID
    exists.
    """
    s3_url = S3Url(path)
    ims_id = get_ims_id_from_s3_url(s3_url)
    if ims_id:
        return ims_id
    raise NonImsImage(f"Boot artifact S3 URL '{s3_url.url}' doesn't follow convention "
                      "for IMS images")


def get_ims_image_data(ims_id: str, num_retries: int|None=None) -> dict:
    """
    Query IMS to get the image data and return it,
    or raise an exception.
    """
    kwargs = { "image_id": ims_id }
    if num_retries is not None:
        # A pylint bug generates a false positive error for this call
        # https://github.com/pylint-dev/pylint/issues/2271
        kwargs['session'] = requests_retry_session(retries=4) # pylint: disable=redundant-keyword-arg
    return get_image(**kwargs)