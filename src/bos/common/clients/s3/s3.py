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

import json
import logging
import os
import threading
from typing import cast, TYPE_CHECKING
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError, ParamValidationError
from botocore.config import Config as BotoConfig

from bos.common.utils import cached_property, exc_type_msg

from .exceptions import (ArtifactNotFound,
                         ManifestNotFound,
                         ManifestTooBig,
                         S3MissingConfiguration,
                         S3ObjectNotFound,
                         TooManyArtifacts)
from .types import ImageArtifactManifest, ImageManifest

# Type annotation of S3/boto objects is complicated. These modules use some weird dynamic
# typing where the classes being returned do not exist at the time that type checking happens.
# The boto3-stubs and botocore-stubs packages allow mypy to handle these types, but we do not
# include the stub packages in production, because they are only useful for type checking.
# This is why the TYPE_CHECKING conditional is used here:
if TYPE_CHECKING:
    # Define the types we need to explicitly annotate the S3/boto objects we need
    from mypy_boto3_s3.client import S3Client
    from mypy_boto3_s3.type_defs import GetObjectOutputTypeDef as S3GetObjectOutput
    from mypy_boto3_s3.type_defs import HeadObjectOutputTypeDef as S3HeadObjectOutput
else:
    # To prevent pylint from complaining about undefined annotation names, we
    # include this. It will have no impact at runtime.
    S3Client = object
    S3GetObjectOutput = object
    S3HeadObjectOutput = object

LOGGER = logging.getLogger(__name__)

# CASMCMS-9015: Instantiating the client is not thread-safe.
# This lock is used to serialize it.
boto3_client_lock = threading.Lock()

# Limit the size of manifest files we will attempt to load, in order to avoid
# OOM errors. Any files this big are almost certainly not actually manifest files.
MAX_MANIFEST_SIZE_BYTES = 1048576


class S3Url:
    """
    https://stackoverflow.com/questions/42641315/s3-urls-get-bucket-name-and-path/42641363
    """

    def __init__(self, url: str) -> None:
        self._parsed = urlparse(url, allow_fragments=False)

    @property
    def bucket(self) -> str:
        return self._parsed.netloc

    @cached_property
    def key(self) -> str:
        if self._parsed.query:
            return self._parsed.path.lstrip('/') + '?' + self._parsed.query
        return self._parsed.path.lstrip('/')

    @cached_property
    def url(self) -> str:
        return self._parsed.geturl()

def s3_client(connection_timeout: int=60, read_timeout: int=60) -> S3Client:
    """
    Return an s3 client

    Args:
      connection_timeout -- Number of seconds to wait to time out the connection
                            Default: 60 seconds
      read_timeout -- Number of seconds to wait to time out a read
                            Default: 60 seconds
    Returns:
      Returns an s3 client object
    Raises:
      S3MissingConfiguration -- it cannot contact S3 because it did not have the proper
                                credentials or configuration
    """
    try:
        s3_access_key = os.environ['S3_ACCESS_KEY']
        s3_secret_key = os.environ['S3_SECRET_KEY']
        s3_protocol = os.environ['S3_PROTOCOL']
        s3_gateway = os.environ['S3_GATEWAY']
    except KeyError as error:
        LOGGER.error("Missing needed S3 configuration: %s", error)
        raise S3MissingConfiguration(error) from error

    with boto3_client_lock:
        s3 = boto3.client('s3',
                          endpoint_url=s3_protocol + "://" + s3_gateway,
                          aws_access_key_id=s3_access_key,
                          aws_secret_access_key=s3_secret_key,
                          use_ssl=False,
                          verify=False,
                          config=BotoConfig(connect_timeout=connection_timeout,
                                            read_timeout=read_timeout))
    return s3


class S3Object:
    """
    A generic S3 object. It provides a way to download the object.
    """

    def __init__(self, path: str, etag: str|None=None) -> None:
        """
        Args:
          path (string): S3 path to the S3 object
          etag (string): S3 entity tag
          """
        self.path = path
        self.etag = etag
        self.s3url = S3Url(self.path)

    @cached_property
    def object_header(self) -> S3HeadObjectOutput:
        """
        Get the S3 object's header metadata.


        Return:
          The S3 object headers (dict)

        Raises:
          ClientError
        """

        try:
            s3 = s3_client()
            s3_obj = s3.head_object(Bucket=self.s3url.bucket,
                                    Key=self.s3url.key)
        except ClientError as error:
            msg = f"s3 object {self.path} was not found."
            LOGGER.error(msg)
            LOGGER.debug(exc_type_msg(error))
            raise S3ObjectNotFound(msg) from error

        if self.etag and self.etag != s3_obj["ETag"].strip('\"'):
            LOGGER.warning(
                "s3 object %s was found, but has an etag '%s' that does "
                "not match what BOS has '%s'.", self.path, s3_obj["ETag"],
                self.etag)
        return s3_obj

    @cached_property
    def object(self) -> S3GetObjectOutput:
        """
        The S3 object itself.  If the object was not found, log it and return an error.

        Args:
          path -- path to the S3 key
          etag -- Entity tag

        Return:
          S3 Object

        Raises:
          boto3.exceptions.ClientError -- when it cannot read from S3
        """

        s3 = s3_client()

        LOGGER.info("++ _get_s3_download_url %s with etag %s.", self.path,
                    self.etag)
        try:
            return s3.get_object(Bucket=self.s3url.bucket, Key=self.s3url.key)
        except (ClientError, ParamValidationError) as error:
            msg = f"Unable to download object {self.path}."
            LOGGER.error(msg)
            LOGGER.debug(exc_type_msg(error))
            raise S3ObjectNotFound(msg) from error

class S3BootArtifacts(S3Object):

    def __init__(self, path: str, etag: str|None=None) -> None:
        """
        Args:
          path (string): S3 path to the S3 object
          etag (string): S3 entity tag
          """
        S3Object.__init__(self, path, etag)
        self._manifest_json: ImageManifest | None = None

    @cached_property
    def manifest_json(self) -> ImageManifest:
        """
        Read a manifest.json file from S3. If the object was not found, log it and return an error.

        Args:
          path -- path to the S3 key
          etag -- Entity tag

        Return:
          Manifest file in JSON format

        Raises:
          boto3.exceptions.ClientError -- when it cannot read from S3
        """

        if self._manifest_json:
            return self._manifest_json

        try:
            s3_manifest_obj = self.object
            if s3_manifest_obj["ContentLength"] > MAX_MANIFEST_SIZE_BYTES:
                raise ManifestTooBig(
                    f"{self.path} is supposed to be an image manifest, but "
                    f"{s3_manifest_obj['ContentLength']} bytes is too big for a manifest")
            s3_manifest_data = s3_manifest_obj['Body'].read().decode('utf-8')
        # Typical exceptions are ClientError, ParamValidationError
        except Exception as error:
            msg = f"Unable to read manifest file '{self.path}'."
            LOGGER.error(msg)
            LOGGER.debug(exc_type_msg(error))
            if isinstance(error, ManifestTooBig):
                raise
            raise ManifestNotFound(msg) from error

        manifest_json = json.loads(s3_manifest_data)
        if not isinstance(manifest_json, dict):
            msg = f"Manifest should be dict. Invalid data type: {type(manifest_json).__name__}"
            LOGGER.error(msg)
            raise ManifestNotFound(msg)
        # Cache the manifest.json file
        self._manifest_json = cast(ImageManifest, manifest_json)
        return self._manifest_json

    def _get_artifact(self, artifact_type: str) -> ImageArtifactManifest:
        """
        Get the artifact_type artifact object out of the manifest.

        The artifact object looks like this
        {
            "link": {
              "path": "s3://boot-artifacts/F6C1CC79-9A5B-42B6-AD3F-E7EFCF22CAE8/rootfs",
              "etag": "foo",
              "type": "s3"
            },
            "type": "application/vnd.cray.image.rootfs.squashfs",
            "md5": "cccccckvnfdikecvecdngnljnnhvdlvbkueckgbkelee"
        }

        Return:
          Artifact object

        Raises:
          ValueError -- Manifest file is corrupt or invalid
          ArtifactNotFound -- The requested artifact is missing
          TooManyArtifacts -- There is more than one artifact when only one was expected
        """
        try:
            artifacts = [
                artifact for artifact in self.manifest_json['artifacts']
                if artifact['type'] == artifact_type
            ]
        except ValueError as value_error:
            LOGGER.info("Received ValueError while processing manifest file.")
            LOGGER.debug(value_error)
            raise
        if not artifacts:
            msg = f"No artifact of type {artifact_type} could be found in the image manifest."
            LOGGER.info(msg)
            raise ArtifactNotFound(msg)
        if len(artifacts) > 1:
            msg = f"Multiple {artifact_type} artifacts found in the manifest."
            LOGGER.info(msg)
            raise TooManyArtifacts(msg)
        return artifacts[0]

    @cached_property
    def initrd(self) -> ImageArtifactManifest:
        """
        Get the initrd artifact object out of the manifest.

        Return:
          initrd object
        """
        return self._get_artifact('application/vnd.cray.image.initrd')

    @cached_property
    def kernel(self) -> ImageArtifactManifest:
        """
        Get the kernel artifact object out of the manifest.

        Return:
          Kernel object
        """
        return self._get_artifact('application/vnd.cray.image.kernel')

    @cached_property
    def boot_parameters(self) -> ImageArtifactManifest | None:
        """
        Get the boot parameters artifact object out of the manifest, if one exists.

        Return:
           boot parameters object if one exists, else None
        """
        try:
            return self._get_artifact('application/vnd.cray.image.parameters.boot')
        except ArtifactNotFound:
            return None

    @cached_property
    def rootfs(self) -> ImageArtifactManifest:
        """
        Get the rootfs artifact object out of the manifest.

        Return:
          rootfs object
        """
        return self._get_artifact('application/vnd.cray.image.rootfs.squashfs')
