#
# MIT License
#
# (C) Copyright 2022-2025 Hewlett Packard Enterprise Development LP
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
"""
Function to return the appropriate rootfs provider class for a given boot set
"""

import logging

from bos.common.clients.s3 import BootImageArtifactSummary
from bos.common.types.templates import BootSet
from bos.common.values import RootfsProvider as RootfsProviderValues

from .rootfs_provider import RootfsProvider
from .sbps_provider import SBPSProvider

LOGGER = logging.getLogger(__name__)

class ProviderNotImplemented(Exception):
    """
    Raised when a user requests a Provider Provisioning mechanism that isn't yet supported
    """

def get_provider(boot_set: BootSet, artifact_info: BootImageArtifactSummary) -> RootfsProvider:
    """
    Inputs:
        boot_set: A boot set from the session template data
        artifact_info: The artifact summary from the boot_set.
                       This is a dictionary containing keys which are boot artifacts
                       (kernel, initrd, roots, and kernel boot parameters);
                       the values are the paths to those boot artifacts in S3.
                       It also contains the etags for the rootfs and kerenl boot parameters.
    Returns a new instance of rootfilesystem provider, for this boot set.
    """
    try:
        provider_name = boot_set['rootfs_provider']
    except KeyError:
        # Default to RootfsProvider
        return RootfsProvider(boot_set, artifact_info)
    if provider_name == RootfsProviderValues.sbps:
        return SBPSProvider(boot_set, artifact_info)
    msg = f"Unsupported rootfs_provider ('{provider_name}') specified in boot set: {boot_set}"
    LOGGER.error(msg)
    raise ProviderNotImplemented(msg)
