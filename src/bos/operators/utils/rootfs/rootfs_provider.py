#
# MIT License
#
# (C) Copyright 2019-2025 Hewlett Packard Enterprise Development LP
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
'''
Created on Apr 29, 2019

@author: jsl
'''

from bos.common.types.templates import BootSet
from bos.operators.utils.boot_image_metadata import BootImageArtifactSummary

class RootfsProvider:
    """
    This class is intended to be inherited by various kinds of root Provider provisioning
    mechanisms.
    """

    PROTOCOL: str | None = None
    DELIMITER: str = ':'

    def __init__(self, boot_set: BootSet, artifact_info: BootImageArtifactSummary) -> None:
        """
        Given an bootset, extrapolate the required boot parameter value.
        """
        self.boot_set = boot_set
        self.artifact_info = artifact_info

    def __str__(self) -> str:
        """
        The value to add to the 'root=' kernel boot parameter.
        """
        fields = []
        if self.PROTOCOL:
            fields.append(self.PROTOCOL)

        if self.provider_field:
            fields.append(self.provider_field)
        else:
            fields.append("")

        if self.provider_field_id:
            fields.append(self.provider_field_id)
        else:
            fields.append("")

        rootfs_provider_passthrough = self.boot_set.get(
            'rootfs_provider_passthrough', None)
        if rootfs_provider_passthrough:
            fields.append(rootfs_provider_passthrough)

        return f"root={self.DELIMITER.join(fields)}" if any(fields) else ''

    @property
    def provider_field(self) -> str | None:
        return None

    @property
    def provider_field_id(self) -> str | None:
        return None

    @property
    def nmd_field(self) -> str | None:
        """
        The value to add to the kernel boot parameters for Node Memory Dump (NMD)
        parameter.
        """
        return None
