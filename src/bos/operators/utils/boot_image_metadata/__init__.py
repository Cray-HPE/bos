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

from bos.common.types import BootSet

from abc import abstractmethod, ABC
from typing import TypedDict

class BootImageArtifactSummary(TypedDict, total=False):
    kernel: str
    initrd: str
    rootfs: str
    rootfs_etag: str
    boot_parameters: str
    boot_parameters_etag: str

class BootImageMetaData(ABC):
    """
    Base class for BootImage Metadata
    """

    def __init__(self, boot_set: BootSet) -> None:
        self._boot_set = boot_set
        self.artifact_summary: BootImageArtifactSummary = {}

    @property
    @abstractmethod
    def metadata(self):
        """
        Get the initial object metadata. This metadata may contain information
        about the other boot objects -- kernel, initrd, rootfs, kernel parameters.
        """

    @property
    @abstractmethod
    def kernel(self):
        """
        Get the kernel
        """

    @property
    @abstractmethod
    def initrd(self):
        """
        Get the initrd
        """

    @property
    @abstractmethod
    def boot_parameters(self):
        """
        Get the boot parameters
        """

    @property
    @abstractmethod
    def rootfs(self):
        """
        Get the kernel
        """


class BootImageError(Exception):
    """
    General error getting boot image
    """


class BootImageMetaDataBadRead(BootImageError):
    """
    The metadata for the boot image could not be read/retrieved.
    """
