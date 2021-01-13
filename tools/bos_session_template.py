#!/usr/bin/env python3
# Copyright 2020 Cray Inc.

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
