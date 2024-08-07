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
"""
This module is responsible for interacting with BOS in a reliable, authorized
fashion.
"""

import os
import logging
import subprocess
import requests
import time
from functools import partial

from bos.common.utils import requests_retry_session as common_requests_retry_session

from . import PROTOCOL

LOGGER = logging.getLogger('bos.reporter.client')

TOKEN_DIR = "/etc/opt/cray/tokens/"
ACCESS_TOKEN_PATH = os.path.join(TOKEN_DIR, 'access')
REFRESH_TOKEN_PATH = os.path.join(TOKEN_DIR, 'refresh')

# Note: There is not a current process in place for what
# would otherwise update the access token, as stored in the
# ACCESS_TOKEN_PATH. Our assumption is that the token lifetime
# is sufficient for us to use it as part of multi-user.target
# right after a node reboots. The code is written to handle
# both kinds of files, should we ever need to extend this
# code to handle token refresh operations.


def get_auth_token(path='/opt/cray/auth-utils/bin/get-auth-token'):
    """
    Obtain the authorization token. Continually retry until acquired.
    """
    # This environment variable needs to be set because the get-auth-token script utilizes it.
    if not os.getenv('SPIRE_AGENT_PATH'):
        os.environ['SPIRE_AGENT_PATH'] = '/usr/bin/bos-reporter-spire-agent'
    while True:
        try:
            out = subprocess.check_output([path], universal_newlines=True)
            out = out.rstrip('\n')
            return out
        except subprocess.CalledProcessError as e:
            LOGGER.error(
                'get_auth_token failed to retrieve authorization token: code=%d: error=%s',
                e.returncode, e.output)
        except Exception as e:
            LOGGER.exception(f"Unexpected exception: {e}")
        LOGGER.info("Spire Token not yet available; retrying in a few seconds.")
        time.sleep(2)

def authorized_requests_retry_session(*pargs, **kwargs) -> requests.session:
    """
    Returns a session with the authorization token included in the headers of the session's requests.
    """
    if 'protocol' not in kwargs:
        kwargs['protocol'] = PROTOCOL
    session = common_requests_retry_session(*pargs, **kwargs)
    auth_token = get_auth_token()
    headers = {'Authorization': f'Bearer {auth_token}'}
    session.headers.update(headers)
    return session