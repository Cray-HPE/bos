#
# MIT License
#
# (C) Copyright 2019-2023  Hewlett Packard Enterprise Development LP
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
import os
from time import sleep
from etcd3.client import Etcd3Client
from etcd3.exceptions import ConnectionFailedError, ConnectionTimeoutError

LOGGER = logging.getLogger(__name__)
DB_HOST = os.getenv('ETCD_HOST', 'cray-bos-bitnami-etcd')
DB_PORT = int(os.getenv('ETCD_PORT', 2379))


class BosEtcdClient(Etcd3Client):
    """
    A BOS-specific client to its underlying etcd3 database. This class
    extends the opensource Etcd3Client implementation by making it resilient to
    initial database availability, as well, some nature of static read/get operations.

    Please note: Even though this extends the Etcd3Client implementation, the underlying
    watch and lock implementation pieces that are provided by the underlying etcd client
    code are not expected to be resilient to connection failures. We do not use these
    in the BOS API, so it isn't an issue.
    """

    def __init__(self, host=DB_HOST, port=DB_PORT, timeout=2000):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.initialize_connection()

    def initialize_connection(self):
        """
        Creates a connection to the etcd cluster in question; blocks until
        completion.

        This function may need to be called multiple times if the connection
        is ever lost (like the etcd cluster being taken down temporarily).
        """
        while True:
            try:
                super().__init__(self.host, self.port, timeout=self.timeout)
                return
            except Exception as e:
                # CASMCMS-5513: The method above does not throw any
                # exception if the k8s host (service object) is missing.
                # The generic exception  will catch anything thrown
                # and the repr will ensure the exception type is printed
                # in the event the message string is empty.
                LOGGER.warn("Unable to establish connection to %s",
                            self.host)
                LOGGER.warn("Exception was %s; retrying...", repr(e))
                sleep(2)

    def put(self, *args, **kwargs):
        while True:
            try:
                return super().put(*args, **kwargs)
            except Exception as e:
                # Methods on the super class will throw an exception if the
                # connection to etcd is not valid.
                # Warn if the connection has failed, print the exception type
                # with message (if any) and log out the host we are trying to
                # contact (this will usually be the cray-bos-etcd-client
                # k8s service).
                LOGGER.warn("Connect failed to %s.  Caught %s", self.host, repr(e))
                self.initialize_connection()

    def delete(self, *args, **kwargs):
        while True:
            try:
                return super().delete(*args, **kwargs)
            except Exception as e:
                LOGGER.warn("Connect failed to %s.  Caught %s", self.host, repr(e))
                self.initialize_connection()

    def delete_prefix(self, *args, **kwargs):
        while True:
            try:
                return super().delete_prefix(*args, **kwargs)
            except Exception as e:
                LOGGER.warn("Connect failed to %s.  Caught %s", self.host, repr(e))
                self.initialize_connection()

    def get(self, *args, **kwargs):
        while True:
            try:
                return super().get(*args, **kwargs)
            except Exception as e:
                LOGGER.warn("Connect failed to %s.  Caught %s", self.host, repr(e))
                self.initialize_connection()

    def get_prefix_response(self, *args, **kwargs):
        while True:
            try:
                return super().get_prefix_response(*args, **kwargs)
            except Exception as e:
                LOGGER.warn("Connect failed to %s.  Caught %s", self.host, repr(e))
                self.initialize_connection()

