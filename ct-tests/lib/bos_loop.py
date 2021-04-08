#! /usr/bin/env python3
# Copyright 2020-2021 Hewlett Packard Enterprise Development LP
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

"""
This script will continuously call the Boot Orchestration Service (BOS) and
ask it to perform the specified operation (reboot, configure, shutdown, or
boot).
It is useful for testing purposes.
"""

import argparse
import datetime
import json
import logging
import os
import re
import requests
import subprocess
from subprocess import run
import sys
import time
import urllib3

ENDPOINT = "https://api-gw-service-nmn.local/apis/bos"
VERSION = "v1"
URL_SESSION = "{}/{}/session".format(ENDPOINT, VERSION)
URL_STATUS = "%s/{}/status" % (URL_SESSION)

# Authentication
TOKEN_PATH = "/root/.config/cray/tokens/api_gw_service_nmn_local.vers"

# Logging
LOGGER = logging.getLogger(__name__)


def get_token(token_file):
    """
    Read the authentication token
    """
    with open(token_file, 'r') as fi:
        token_info = json.load(fi)
    return token_info['access_token']


def create_bos_session(template, operation, limit=[]):
    """
    Returns the session response and status.
    """
    body = {"templateUuid": template,
            "operation": operation}
    if limit:
        body["limit"] = ','.join(limit)
    headers = {"Authorization": "Bearer {}".format(get_token(TOKEN_PATH))}
    response = requests.post(URL_SESSION, json=body,
                             headers=headers, verify=False)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        LOGGER.error("Failed to create the BOS session "
                     "for template %s", template)
        LOGGER.error(response.text)
        raise
    return response


def get_session_status(session_id):
    """
    Returns the session status
    """
    headers = {"Authorization": "Bearer {}".format(get_token(TOKEN_PATH))}
    response = requests.get(URL_STATUS.format(session_id),
                             headers=headers, verify=False)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        LOGGER.warn("Failed to get status for BOS session %s", session_id)
    return response


def arguments(args):
    """
    Handle command line arguments
    """
    todays_date = datetime.date.today()
    parser = argparse.ArgumentParser(
        description="Launch the designated BOS operation in a continuous loop")
    parser.add_argument('template', type=str,
                        help='BOS Session Template')
    parser.add_argument('operation', type=str,
                        choices=['shutdown', 'boot', 'reboot', 'configure'],
                        help='Operation to perform on the nodes')
    parser.add_argument('-l', '--limit', action="append",
                        help='Nodes to limit the operation to')
    parser.add_argument('-t', '--timeout', type=int,
                        default=30,
                        help='How long to wait (in minutes) for a BOS session to finish before timing out; Default=30')
    parser.add_argument('-s', '--sessions', type=int,
                        default=9999,
                        help='Number of BOS sessions to launch; Default=9999')
    parser.add_argument('--sessions_file', type=argparse.FileType('a'),
                        default='bos_sessions_{}'.format(str(todays_date)),
                        help='Output file containing a list of the BOS Sessions; Default=bos_sessions_<date>')
    parser.add_argument('--completed_file', type=argparse.FileType('a'),
                        default='bos_completed_{}'.format(str(todays_date)),
                        help='Output file containing a list of the BOS Sessions that completed; Default=bos_completed_<date>')
    parser.add_argument('--timed_out_file', type=argparse.FileType('a'),
                        default='bos_timed_out_{}'.format(str(todays_date)),
                        help='Output file containing a list of the BOS Sessions that timed-out; Default=bos_timed_out_<date>')

    return parser.parse_args(args)


def logs():
    """
    Set up logging.
    """
    _log_level = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
    _stream_handler = logging.StreamHandler()
    _stream_handler.setLevel(_log_level)
    _stream_handler.setFormatter(logging.Formatter("%(asctime)-15s - %(levelname)-7s - %(name)s - %(message)s"))
    LOGGER.addHandler(_stream_handler)
    LOGGER.setLevel(_log_level)


def handle_time_out(session_id):
    """
    When a time out occurs, find all of the pods associated with the BOS
    session. There is likely only one pod associated with the session,
    but we will loop through any that are found.
    Capture the log of any timed out pod to a log file. We do this because
    the next step is to delete the BOA job which deletes the associated log.
    We delete the job because we do not want a failing or hung job to exist
    because it could interfere with the next job we are about to launch on
    the same set of nodes.
    """
    cmd = "kubectl -n services get pods"
    # Get all the Kubernetes pods
    all_pods = run(cmd.split(), check=True, stdout=subprocess.PIPE).stdout.decode('utf-8', 'strict')
    # Filter down to the ones matching the session ID. There can be multiple pods associated with a
    # single session ID.
    session_pods = re.findall('boa-{}-[a-z0-9]*\s'.format(session_id), all_pods)
    session_pods = [x.strip() for x in session_pods]
    for pod in session_pods:
        cmd = "kubectl -n services logs -c boa {0}".format(pod)
        with open('{}/{}.log'.format(os.getcwd(), pod), 'w') as fout:
            run(cmd.split(), check=True, stdout=fout)
    cmd = "kubectl -n services delete job boa-{}".format(session_id)
    run(cmd.split(), check=True)


def main(in_args):
    LOGGER = logs()
    args = arguments(in_args)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # List out the starting arguments
    args.sessions_file.write("\nBOS Session Template: {}\tOperation: {}\n".format(args.template,
                                                                                args.operation))

    count = 0
    while count < args.sessions:
        count += 1
        # Create BOS session
        try:
            response = create_bos_session(args.template, args.operation, args.limit)
        except:
            # Failed to create the session; start again from the top
            continue
        """
        Extract the session ID from the creation response.
        This is a work-around. The session ID should be more easily accessible
        part of the response. It should not be buried under links.
        """
        session_id = str(os.path.basename(response.json()['links'][0]['href']))
        args.sessions_file.write("Session: {}\n".format(session_id))
        args.sessions_file.write("Arguments:\n".format(session_id))
        for arg in vars(args):
            args.sessions_file.write('{}: {}\n'.format(arg, getattr(args, arg) or ''))
        args.sessions_file.write("Session: {}\tStart:{}\t".format(session_id,
                                 datetime.datetime.now().isoformat(timespec='minutes')))
        args.sessions_file.flush()

        # Give BOA time to create the status
        time.sleep(30)
        # Convert minutes to seconds
        timeout_window = 60 * args.timeout
        end_time = time.time() + timeout_window
        complete = False
        while time.time() < end_time:
            response = get_session_status(session_id)
            if response.ok:
                # Is the session complete?
                if str(response.json()['metadata']['complete']).lower() == 'true':
                        complete = True
                        args.completed_file.write("{}\n".format(session_id))
                        args.completed_file.flush()
                        print("Session: {} completed.".format(session_id))
                        break
            time.sleep(10)

        if not complete:
            args.timed_out_file.write("{}\n".format(session_id))
            args.timed_out_file.flush()
            print("Session: {} timed-out.".format(session_id))
            handle_time_out(session_id)

        # Record the stop time
        args.sessions_file.write("Stop:{}\n".format(datetime.datetime.now().isoformat(timespec='minutes')))
        args.sessions_file.flush()

    # Clean up
    args.sessions_file.close()
    args.completed_file.close()
    args.timed_out_file.close()


if '__main__' == __name__ :
    main(sys.argv[1:])
