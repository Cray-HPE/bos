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

from bos.operators.utils.boot_image_metadata.s3_boot_image_metadata import S3BootImageMetaData

LOGGER = logging.getLogger('bos.operators.utils.boot_image_metadata.factory')


class BootImageMetaDataUnknown(Exception):
    """
    Raised when a user requests a Provider provisioning mechanism that is not known
    """

class BootImageMetaDataFactory(object):
    """
    Conditionally create new instances of the BootImageMetadata based on
    the type of the BootImageMetaData specified
    """
    def __init__(self, boot_set):
        self.boot_set = boot_set

    def __call__(self):
        path_type = self.boot_set.get('type', None)
        if path_type:
            if path_type == 's3':
                return S3BootImageMetaData(self.boot_set)
            raise BootImageMetaDataUnknown(f"No BootImageMetaData class for type {path_type}")
