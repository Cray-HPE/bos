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

class BootImageMetaData:
    def __init__(self, boot_set):
        """
        Base class for BootImage Metadata object
        """
        self._boot_set = boot_set
        self.artifact_summary = {}

    @property
    def metadata(self):
        """
        Get the initial object metadata. This metadata may contain information
        about the other boot objects -- kernel, initrd, rootfs, kernel parameters.
        """
        return None

    @property
    def kernel(self):
        """
        Get the kernel
        """
        return None

    @property
    def initrd(self):
        """
        Get the initrd
        """
        return None

    @property
    def boot_parameters(self):
        """
        Get the boot parameters
        """
        return None

    @property
    def rootfs(self):
        """
        Get the kernel
        """
        return None

    @property
    def arch(self):
        """
        Get the arch
        """
        return None

class BootImageMetaDataBadRead(Exception):
    """
    The metadata for the boot image could not be read/retrieved.
    """
