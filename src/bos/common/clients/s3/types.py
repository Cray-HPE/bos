#
# MIT License
#
# (C) Copyright 2021-2025 Hewlett Packard Enterprise Development LP
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

from typing import TypedDict


class ImageArtifactLinkManifest(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/ims/blob/develop/src/server/helper.py
    """
    path: str
    etag: str
    type: str


class ImageArtifactManifest(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/ims/blob/develop/src/server/helper.py
    """
    link: ImageArtifactLinkManifest
    type: str
    md5: str


class ImageManifest(TypedDict, total=False):
    """
    https://github.com/Cray-HPE/ims/blob/develop/src/server/helper.py
    """
    version: str
    created: str
    artifacts: list[ImageArtifactManifest]


class BootImageArtifactSummary(TypedDict, total=False):
    kernel: str
    initrd: str
    rootfs: str
    rootfs_etag: str
    boot_parameters: str | None
    boot_parameters_etag: str | None
