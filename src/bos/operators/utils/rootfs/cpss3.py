#
# MIT License
#
# (C) Copyright 2022 Hewlett Packard Enterprise Development LP
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
Provisioning mechanism unique to the ContentProjectionService; this is software
that is often installed as part of Cray CME images in both standard, enhanced
and premium offerings; the underlying implementation of CPS may be handled by
another protocol (iSCSI or DVS) depending on the product.
'''

from requests.exceptions import HTTPError
import logging
import os

from . import RootfsProvider
from .. import PROTOCOL, ServiceNotReady, requests_retry_session

LOGGER = logging.getLogger(__name__)
SERVICE_NAME = 'cray-cps'
VERSION = 'v1'
ENDPOINT = '%s://%s/%s' % (PROTOCOL, SERVICE_NAME, VERSION)


class CPSS3Provider(RootfsProvider):
    PROTOCOL = 'craycps-s3'

    @property
    def provider_field(self):
        return self.artifact_info['rootfs']

    @property
    def provider_field_id(self):
        return self.artifact_info['rootfs_etag']

    @property
    def nmd_field(self):
        """
        The value to add to the kernel boot parameters for Node Memory Dump (NMD)
        parameter.
        """
        fields = []
        if self.provider_field:
            fields.append("url=%s" % self.provider_field)
        if self.provider_field_id:
            fields.append("etag=%s" % self.provider_field_id)
        if fields:
            return "nmd_data={}".format(",".join(fields))
        else:
            return ''


def check_cpss3(session=None):
    """
    A call to check on the health of the CPS microservice.
    """
    session = session or requests_retry_session()
    uri = os.path.join(ENDPOINT, 'contents')
    try:
        response = session.get(uri)
        response.raise_for_status()
    except HTTPError as he:
        raise ServiceNotReady(he) from he
