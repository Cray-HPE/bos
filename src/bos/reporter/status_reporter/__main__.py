#
# Copyright 2020-2021 Hewlett Packard Enterprise Development LP
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
#
# (MIT License)
import logging
import sys
from time import sleep

from bos.reporter.client import requests_retry_session
from bos.reporter.node_identity import read_identity
from bos.reporter.components.state import report_state, BOSComponentException, UnknownComponent
from bos.reporter.proc_cmdline import get_value_from_proc_cmdline

# Configure Project Level Logging options when invoked through __main__;
# This allows the whole project to log from their source when invoked through
# __main__, but does not populate standard out streaming when the code
# is imported by other tooling.
try:
    LOG_LEVEL = get_value_from_proc_cmdline('bos_log_level')
    LOG_LEVEL = getattr(logging, LOG_LEVEL.upper(), logging.WARN)
except KeyError:
    LOG_LEVEL = logging.WARN
PROJECT_LOGGER = logging.getLogger('BOS')
LOGGER = logging.getLogger('bos.reporter.status_reporter')
LOGGER.setLevel(LOG_LEVEL)
_stream_handler = logging.StreamHandler(sys.stdout)
_stream_handler.setLevel(LOG_LEVEL)
PROJECT_LOGGER.addHandler(_stream_handler)
PROJECT_LOGGER.setLevel(LOG_LEVEL)


def report_state_until_success(component):
    """
    Loop until BOS component information has been registered;
    tells BOS the component's (_this_ node) state.
    """
    backoff_ceiling = 30
    backoff_scalar = 2
    attempt = 0
    while True:
        # Each iteration, wait a bit longer before patching BOS component
        # state until the ceiling is reached.
        time_to_wait = backoff_scalar * attempt
        time_to_wait = min([backoff_ceiling, time_to_wait])
        sleep(time_to_wait)
        attempt += 1
        LOGGER.info("Attempt %s of contacting BOS..." % (attempt))
        session = requests_retry_session()
        try:
            bss_referral_token = get_value_from_proc_cmdline('bss_referral_token')
            state = {'actualState': {'bootArtifacts': {'bssToken': bss_referral_token}}}
            report_state(component, state, session)
        except UnknownComponent:
            LOGGER.warning("BOS has no record of component '%s'; nothing to report." % (component))
            LOGGER.warning("Will re-attempt patch operation as necessary.")
            continue
        except BOSComponentException as cce:
            LOGGER.warning("Unable to contact BOS to report component status: %s" % (cce))
            continue
        except OSError as exc:
            LOGGER.error("BOS client encountered an %s" % (exc))
            continue
        LOGGER.info("Updated the actualState record for BOS component '%s'." % (component))
        return


STATE_UPDATE_FREQUENCY = 86400  # Number of seconds between state updates


def main():
    """
    Read the Boot Artifact ID from the /proc/cmdline and report it to the BOS
    API. This reports the booted 'state' of the node to BOS.
    """
    component = read_identity()
    try:
        sleep_time = get_value_from_proc_cmdline('bos_update_frequency')
    except KeyError:
        sleep_time = STATE_UPDATE_FREQUENCY

    while True:
        LOGGER.info("Attempting to report status for '%s'" % (component))
        try:
            report_state_until_success(component)
        except Exception as exp:
            LOGGER.error("An error occurred: {}".format(exp))
        sleep(sleep_time)


if __name__ == '__main__':
    main()
