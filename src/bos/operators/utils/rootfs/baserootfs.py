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
'''
Provisioning mechanism, base class
The assumption is the artifact info contains information about the rootfs.
'''
from abc import ABC
import logging

from bos.common.types.templates import BootSet
from bos.operators.utils.boot_image_metadata import BootImageArtifactSummary

LOGGER = logging.getLogger(__name__)

class BaseRootfsProvider(ABC):
    """
    This class is intended to be inherited by various kinds of root Provider provisioning
    mechanisms.
    """

    PROTOCOL: str | None = None
    DELIMITER = ':'

    def __init__(self, boot_set: BootSet, artifact_info: BootImageArtifactSummary) -> None:
        """
        Given a bootset, extrapolate the required boot parameter value.
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

        stripped_fields = [field for field in fields if field]
        return f"root={self.DELIMITER.join(fields)}" if stripped_fields else ''

    @property
    def provider_field(self) -> str:
        return self.artifact_info['rootfs']

    @property
    def provider_field_id(self) -> str:
        return self.artifact_info['rootfs_etag']

    @property
    def nmd_field(self) -> str:
        """
        The value to add to the kernel boot parameters for Node Memory Dump (NMD)
        parameter.
        """
        fields = []
        if self.provider_field:
            fields.append(f"url={self.provider_field}")
        if self.provider_field_id:
            fields.append(f"etag={self.provider_field_id}")
        return f"nmd_data={','.join(fields)}" if fields else ''
