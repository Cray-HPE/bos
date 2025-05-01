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

class ArtifactNotFound(Exception):
    """
    A boot artifact could not be located.
    """


class ManifestNotFound(Exception):
    """
    The image manifest could not be found.
    """


class ManifestTooBig(Exception):
    """
    The image manifest is larger than MAX_MANIFEST_SIZE_BYTES
    (almost certainly meaning it is not actually a manifest file)
    """


class TooManyArtifacts(Exception):
    """
    One and only one artifact was expected to be found. More than one artifact
    was found.
    """


class S3MissingConfiguration(Exception):
    """
    We were missing configuration information needed to contact S3.
    """


class S3ObjectNotFound(Exception):
    """
    The S3 object could not be found.
    """


class BootImageError(Exception):
    """
    General error getting boot image
    """


class BootImageMetadataBadRead(BootImageError):
    """
    The metadata for the boot image could not be read/retrieved.
    """


class BootImageMetadataUnknown(BootImageError):
    """
    Raised when a user requests a Provider provisioning mechanism that is not known
    """
