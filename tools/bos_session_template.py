#!/usr/bin/env python3
#
# MIT License
#
# (C) Copyright 2020-2022 Hewlett Packard Enterprise Development LP
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
import argparse
import base64
import json
import subprocess
import sys

import requests

"""
This script accepts a JSON file containing the contents for a Session Template.
It then gets the needed credentials and contacts the Boot Orchestration Service 
(BOS) to create a Session Template.
"""

def get_token():
    """
    Returns the access token.
    """
    KEYCLOAK_ENDPOINT = "https://api-gw-service-nmn.local/keycloak/realms/shasta/protocol/openid-connect/token"
    
    cmd = "kubectl get secrets admin-client-auth -ojsonpath='{.data.client-secret}'".split()
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    admin_secret = base64.b64decode(result.stdout)
    resp = requests.post(KEYCLOAK_ENDPOINT, data = {'grant_type':'client_credentials', 'client_id': 'admin-client', 'client_secret': admin_secret})
    return resp.json()["access_token"]    
    

def main():
    parser = argparse.ArgumentParser(description='Create a BOS Session Template from a JSON file.')
    parser.add_argument('fp', metavar='input_file',
                        type=argparse.FileType('r', encoding='UTF-8'),
                        help='A JSON file containing a BOS Session Template')
    args = parser.parse_args()

    BOS_ENDPOINT = "https://api-gw-service-nmn.local/apis/bos/v1/sessiontemplate"
    try:
        body_check = json.load(args.fp)
        if not isinstance(body_check, dict):
            print("ERROR: Session Template must be formatted as a dictionary.")
            sys.exit(1)
        body = json.dumps(body_check)
    except json.decoder.JSONDecodeError as err:
        print("ERROR: File '%s' was not proper JSON: %s" % (args.fp.name, err))
        sys.exit(1)
    try:
        headers = {"Authorization": "Bearer %s" % get_token(), "Content-Type": "application/json"}
    except Exception as err:
        print("ERROR: Unable to get TOKEN to access the Boot Orchestration Service: %s" % err)
        sys.exit(1)            
    try:
        resp = requests.post(BOS_ENDPOINT, data=body, headers=headers)
        resp.raise_for_status()
    except requests.RequestException as err:
        print("ERROR: Problem contacting the Boot Orchestration Service (BOS): %s" % err)
        sys.exit(1)

if __name__ == "__main__":
  main()
