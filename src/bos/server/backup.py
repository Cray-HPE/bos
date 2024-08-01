#
# MIT License
#
# (C) Copyright 2023-2024 Hewlett Packard Enterprise Development LP
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

from contextlib import contextmanager
import datetime
import hashlib
import json
import logging
import os
import tarfile
import tempfile
import time

import botocore

from bos.operators.utils.clients.s3 import s3_client
import bos.server.redis_db_utils as dbutils

LOGGER = logging.getLogger('bos.server.backup')
BOS_S3_BUCKET = 'bos-data'

# https://dev.to/teckert/changing-directory-with-a-python-context-manager-2bj8
@contextmanager
def set_directory(path: str):
    """Sets the cwd within the context

    Args:
        path (Path): The path to the cwd

    Yields:
        None
    """

    origin = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(origin)


def remove_file(filepath):
    try:
        os.remove(filepath)
    except OSError as exc:
        LOGGER.warning("Error deleting temporary file '%s': %s", filepath, exc)


def remove_dir(dirpath):
    try:
        os.rmdir(dirpath)
    except OSError as exc:
        LOGGER.warning("Error deleting temporary directory '%s': %s", dirpath, exc)


def create_tarfile(bos_data: dict, bos_data_basename: str, tmpdir_path: str) -> str:
    jsonfile_name = f"{bos_data_basename}.json"
    jsonfile_path = os.path.join(tmpdir_path, jsonfile_name)
    LOGGER.debug("Writing BOS data as JSON data to '%s'", jsonfile_path)
    with open(jsonfile_path, "wt") as outfile:
        json.dump(bos_data, outfile)
    tarfile_name = f"{bos_data_basename}.tar.gz"
    tarfile_path = os.path.join(tmpdir_path, tarfile_name)
    LOGGER.debug("Creating compressed tar archive of BOS data: '%s'", tarfile_path)
    with set_directory(tmpdir_path):
        with tarfile.open(tarfile_path, mode='w:gz') as tfile:
            tfile.add(jsonfile_name)
    remove_file(jsonfile_path)
    return tarfile_name


def md5sum(filepath: str):
    """
    Utility for efficient md5sum of a file.
    Borrowed from ims-python-helper
    """
    hashmd5 = hashlib.md5()
    with open(filepath, "rb") as afile:
        for chunk in iter(lambda: afile.read(4096), b""):
            hashmd5.update(chunk)
    return hashmd5.hexdigest()


def upload_to_s3(filename: str, filedir: str) -> None:
    s3_key = filename
    s3_path = f"s3://{BOS_S3_BUCKET}/{s3_key}"
    filepath = os.path.join(filedir, filename)
    extra_args = {'Metadata': {'md5sum': md5sum(filepath)}}
    attempt=0
    client = s3_client()
    LOGGER.info("Creating/retrieving S3 bucket '%s'", BOS_S3_BUCKET)
    try:
        response = client.create_bucket(ACL='authenticated-read', Bucket=BOS_S3_BUCKET)
    except Exception as err:  # pylint: disable=bare-except, broad-except
        LOGGER.error("Error creating S3 bucket '%s': %s", BOS_S3_BUCKET, err)
        raise
    LOGGER.debug("create_bucket response = %s", response)
    LOGGER.info("Uploading %s", s3_path)
    while True:
        attempt+=1
        try:
            client.upload_file(filepath, BOS_S3_BUCKET, s3_key, ExtraArgs=extra_args)
            break
        except Exception as err:  # pylint: disable=bare-except, broad-except
            if attempt <= 60:
                LOGGER.warning("Error uploading %s: %s; Re-attempting in %s seconds...",
                               s3_path, err, attempt)
                time.sleep(attempt)
                continue
            LOGGER.error("Error uploading %s: %s; Giving up", s3_path, err)
            raise
    LOGGER.debug("%s upload completed successfully", s3_path)


def backup_bos_data(label: str):
    LOGGER.info("Performing backup of BOS data (context: %s)", label)
    bos_data = { dblabel: dbutils.get_wrapper(db=dblabel).get_all_as_dict()
                 for dblabel in dbutils.DATABASES }
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S.%f")
    bos_data_basename = f"bos_data_{label}_{timestamp}"
    tmpdir_path = tempfile.mkdtemp(prefix=f"{bos_data_basename}-", dir="/tmp")
    tarfile_name = create_tarfile(bos_data, bos_data_basename, tmpdir_path)
    upload_to_s3(tarfile_name, tmpdir_path)
    remove_file(os.path.join(tmpdir_path, tarfile_name))
    remove_dir(tmpdir_path)
    LOGGER.debug("BOS data backup completed (context: %s)", label)
