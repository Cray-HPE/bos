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
#
# (MIT License)

"""
BOS-related CMS test helper functions
"""

from .api import API_URL_BASE, requests_delete, requests_get, requests_post
from .cli import run_cli_cmd
from .helpers import CMSTestError, debug, error, get_bool_field_from_obj, \
                     get_dict_field_from_obj, get_field_from_obj, \
                     get_int_field_from_obj, get_str_field_from_obj, \
                     info, raise_test_error, raise_test_exception_error, \
                     sleep, validate_list
import json
import os
import tempfile
import time

BOS_URL_BASE = "%s/bos/v1" % API_URL_BASE
BOS_SESSION_URL_BASE = "%s/session" % BOS_URL_BASE
BOS_SESSIONTEMPLATE_URL_BASE = "%s/sessiontemplate" % BOS_URL_BASE

BOS_SESSION_HREF_PREFIX = "/v1/session/"

def bos_session_url(id=None):
    """
    Returns the BOS API endpoint for either BOS sessions generally, or the
    specified BOS session
    """
    if id == None:
        return BOS_SESSION_URL_BASE
    return "%s/%s" % (BOS_SESSION_URL_BASE, id)

def bos_session_status_url(id, bootset=None):
    """
    Returns the BOS API endpoint for either BOS sessions generally, or the
    specified BOS session
    """
    if bootset == None:
        return "%s/status" % bos_session_url(id)
    return "%s/status/%s" % (bos_session_url(id), bootset)

def bos_sessiontemplate_url(id=None):
    """
    Returns the BOS API endpoint for either BOS session templates generally, or the
    specified BOS session template
    """
    if id == None:
        return BOS_SESSIONTEMPLATE_URL_BASE
    return "%s/%s" % (BOS_SESSIONTEMPLATE_URL_BASE, id)

def bos_status_link(bos_session_object, session_uuid):
    """
    Extracts, verifies, and then returns the status_link field from a BOS session
    object (obtained from a session describe request). The verification is mainly that the
    link begins with the prefix that we expect.
    """
    status_link_prefix = ''.join([BOS_SESSION_HREF_PREFIX, session_uuid, "/"])
    return get_str_field_from_obj(bos_session_object, "status_link", 
                                  noun="BOS session response", null_okay=False,
                                  min_length=len(status_link_prefix)+1, 
                                  prefix=status_link_prefix)

def bos_session_template_name(bst):
    """
    Extracts and returns the name field from the specified session template object.
    Raises an error if there are problems.
    """
    return get_str_field_from_obj(bst, "name", noun="session template", min_length=1)

def validate_bos_session_template(bst):
    """
    Validates that the specified BOS session template has a non-empty name specified
    """
    bos_session_template_name(bst)

def bos_session_template_validate_cfs(bst):
    """
    Validates that the specified BOS session template:
    1) Has enable_cfs set to True
    2) Has cfs[configuration] set to a non-empty string
    Returns cfs[configuration] string
    """
    get_bool_field_from_obj(bst, "enable_cfs", noun="session template", exact_value=True)
    cfs = get_dict_field_from_obj(bst, "cfs", noun="session template", key_type=str, null_okay=False)
    return get_str_field_from_obj(cfs, "configuration", noun="session template cfs object", min_length=1)

def describe_bos_session_template(use_api, template_name, expect_to_pass=True):
    """
    Calls an API GET or CLI describe on the specified BOS session template
    If we are expecting it to pass, the BOS session template is extracted from the response, 
    it is validated (for the things we care about, anyway), and then it is returned.
    Otherwise we just validate that the request failed.
    """
    info("Describing BOS session template %s" % template_name)
    if use_api:
        url = bos_sessiontemplate_url(template_name)
        if expect_to_pass:
            response_object = requests_get(url)
        else:
            requests_get(url, expected_sc=404)
            return
    else:
        cmd_list = ["bos","v1","sessiontemplate","describe",template_name]
        if expect_to_pass:
            response_object = run_cli_cmd(cmd_list)
        else:
            cmdresp = run_cli_cmd(cmd_list, return_rc=True, parse_json_output=False)
            if cmdresp["rc"] == 0:
                raise_test_error("We expected this BOS query to fail but the return code was 0")
            return

    validate_bos_session_template(response_object)
    return response_object

def list_bos_session_templates(use_api):
    """
    Uses the API or CLI to list all BOS session templates. 
    The response is validated and the list of BOS session templates is returned.
    """
    info("Listing BOS session templates")
    if use_api:
        response_object = requests_get(bos_sessiontemplate_url())
    else:
        response_object = run_cli_cmd("bos v1 sessiontemplate list".split())

    if not isinstance(response_object, list):
        raise_test_error("Response should be a list but it is %s" % str(type(response_object)))
    elif len(response_object) < 1:
        raise_test_error("No BOS session templates found")

    for bst in response_object:
        validate_bos_session_template(bst)

    return { bst["name"]: bst for bst in response_object }

def create_bos_session_template(use_api, template_object):
    """
    Creates the specified BOS session template
    """
    info("Creating BOS session template %s" % template_object["name"])
    if use_api:
        requests_post(bos_sessiontemplate_url(), json=template_object)
    else:
        # Even though the name field is specified in the file we are going to create,
        # the CLI requires it to be specified on the command line
        name = bos_session_template_name(template_object)
        bst_tempfile = tempfile.mkstemp(prefix="bos-sessiontemplate-tmpfile")[1]
        with open(bst_tempfile, "wt") as bstfile:
            json.dump(template_object, bstfile)
        cli_cmd_list = [ "bos", "v1", "sessiontemplate", "create", "--name", name, "--file", bst_tempfile ]
        run_cli_cmd(cli_cmd_list, parse_json_output=False)
        os.remove(bst_tempfile)

def delete_bos_session_template(use_api, template_name, verify_delete=True):
    """
    Delete the specified BOS session template
    """
    info("Deleting BOS session template %s" % template_name)
    if use_api:
        url = bos_sessiontemplate_url(template_name)
        requests_delete(url)
    else:
        cli_cmd_list = [ "bos", "v1", "sessiontemplate", "delete", template_name ]
        run_cli_cmd(cli_cmd_list, parse_json_output=False)
    if not verify_delete:
        return

    # Now try to describe it, to make sure it is actually gone
    info("Validate that BOS session template %s no longer exists" % template_name)
    describe_bos_session_template(use_api=use_api, template_name=template_name, expect_to_pass=False)

def get_session_link_uuid(links, rel):
    """
    From the BOS session href link, extract the uuid string and return it
    """
    uuid = None
    for link in links:
        try:
            if link["rel"] != rel:
                continue
        except KeyError:
            error_exit("link has no 'rel' field: %s" % str(link))
        if uuid:
            raise_test_error("Multiple links with 'rel' = %s" % rel)
        try:
            href = link["href"]
        except KeyError:
            raise_test_error("link has no 'href' field: %s" % str(link))
        if not isinstance(href, str):
            raise_test_error("link 'href' field should be string but is type %s: %s" % (str(type(href)), str(href)))
        try:
            if href.index(BOS_SESSION_HREF_PREFIX) != 0:
                raise_test_error("We expect link 'href' field to begin with '%s' but it does not: %s" % (BOS_SESSION_HREF_PREFIX, href))
        except ValueError:
            raise_test_error("We expect link 'href' field to begin with '%s' but it does not even contain that substring: %s" % (BOS_SESSION_HREF_PREFIX, href))
        uuid = href.replace(BOS_SESSION_HREF_PREFIX,"")
        if len(uuid) < 1:
            raise_test_error("link 'href' field should consist of more than just '%s'" % BOS_SESSION_HREF_PREFIX)
    if not uuid:
        raise_test_error("No link found with 'rel' field of '%s'" % rel)
    return uuid

def create_bos_session(use_api, template_name, operation, limit_params=None, validate_response=True, return_uuid=True):
    """
    Create the specified BOS session, optionally validate its response, and return either the
    response object or the session UUID
    """
    info("Creating BOS session")
    operation = operation.lower()
    if operation not in { 'boot', 'configure', 'reboot', 'shutdown' }:
        raise_test_error("Invalid operation specified to create_bos_session function: %s" % operation)
    if limit_params != None:
        limit_arg = ','.join(limit_params)
    if use_api:
        data = { 'templateUuid': template_name, 'operation': operation }
        if limit_params != None:
            data['limit'] = limit_arg
        response_object = requests_post(bos_session_url(), json=data)
    else:
        cli_cmd_list = [ "bos", "v1", "session", "create", "--template-uuid", template_name, "--operation", operation ]
        if limit_params != None:
            cli_cmd_list.extend(["--limit", limit_arg])
        response_object = run_cli_cmd(cli_cmd_list)
    if validate_response or return_uuid:
        if not isinstance(response_object, dict):
            raise_test_error("response object from session creation should be dict but this is type %s" % str(type(response_object)))
        try:
            links = response_object["links"]
        except KeyError:
            raise_test_error("response object from session creation is missing 'links' field")
        if not isinstance(links, list):
            raise_test_error("links field should be a list but it is type %s" % str(type(links)))
        elif len(links) < 1:
            raise_test_error("We expect the links field to contain at least 1 entry")
        session_uuid = get_session_link_uuid(links, "session")
        if return_uuid:
            return session_uuid
    return response_object

def list_bos_sessions(use_api):
    """
    Returns a list of all current BOS session IDs
    """
    info("Listing BOS sessions")
    if use_api:
        url = bos_session_url()
        response_object = requests_get(url)
    else:        
        response_object = run_cli_cmd("bos v1 session list".split())
    validate_list(val=response_object, noun="BOS session list response object", member_type=str, 
                  show_val_on_error=True)
    return response_object

def describe_bos_session(use_api, session_uuid, expect_to_pass=True):
    """
    Calls an API GET or CLI describe on the specified BOS session.
    If we are expecting it to pass, the BOS session is extracted from the response and returned.
    Otherwise we just validate that the request failed.
    """
    info("Describing BOS session %s" % session_uuid)
    if use_api:
        url = bos_session_url(session_uuid)
        if expect_to_pass:
            return requests_get(url)
        else:
            requests_get(url, expected_sc=404)
    else:        
        cli_cmd_list = [ "bos", "v1", "session", "describe", session_uuid ]
        if expect_to_pass:
            return run_cli_cmd(cli_cmd_list)
        else:
            cmdresp = run_cli_cmd(cli_cmd_list, return_rc=True, parse_json_output=False)
            if cmdresp["rc"] == 0:
                raise_test_error("We expected this BOS query to fail but the return code was 0")
    return

def delete_bos_session(use_api, session_uuid, verify_delete=True):
    """
    Delete the specified BOS session
    """
    info("Deleting BOS session %s" % session_uuid)
    if use_api:
        url = bos_session_url(session_uuid)
        requests_delete(url)
    else:
        cli_cmd_list = [ "bos", "v1", "session", "delete", session_uuid ]
        run_cli_cmd(cli_cmd_list, parse_json_output=False)
    if not verify_delete:
        return

    # Now try to describe it, to make sure it is actually gone
    info("Validate that BOS session %s no longer exists" % session_uuid)
    describe_bos_session(use_api=use_api, session_uuid=session_uuid, expect_to_pass=False)

def describe_bos_session_status(use_api, session_uuid, bootset=None):
    """
    Return the overall BOS session status, or the status for the specified bootset.
    """
    if bootset == None:
        info("Getting status for BOS session %s" % session_uuid)
    else:
        info("Getting status for BOS session %s, bootset %s" % (session_uuid, bootset))
    if use_api:
        url = bos_session_status_url(session_uuid, bootset)
        # Workaround for CASMCMS-3544, wherein getting the session status of
        # a bootset returns status code 201
        if bootset == None:
            return requests_get(url)
        else:
            return requests_get(url, expected_sc=201)
    else:
        if bootset == None:
            cli_cmd_list = [ "bos", "v1", "session", "status", "list", session_uuid ]
        else:
            # This is a hacky way to work around the fact that there is no CLI equivalent to
            # querying the bootset endpoint directly. In the CLI you can either query the
            # session status itself, or you have to query a specific bootset/phase/category
            # combination.
            cli_cmd_list = [ "bos", "v1", "session", "describe", session_uuid+"/status/"+ bootset ]
        return run_cli_cmd(cli_cmd_list)

def wait_until_bos_session_complete(use_api, session_uuid, timeout=45*60, sleeptime=30):
    """
    Wait until the specified BOS session has complete set to True, or until
    we time out. The sleeptime is how long between checks of the BOS session status.
    Units for both timeout and sleeptime is seconds.
    If it completes, validate that no errors seem to have happened.
    """
    info("Waiting for BOS session %s to complete" % session_uuid)
    stoptime = time.time() + timeout
    errors_found = False
    noun = "BOS session response"
    myargs = { "noun": noun, "null_okay": True }
    while True:
        response_object = describe_bos_session(use_api, session_uuid)
        try:
            # Workaround for CASMCMS-5740
            #complete = get_bool_field_from_obj(response_object, "complete", **myargs)
            complete = get_field_from_obj(response_object, "complete", **myargs)
        except CMSTestError:
            errors_found=True
            complete = None
            break
        if complete == True:
            break
        timeleft = stoptime - time.time()
        if timeleft <= 0:
            error("Timeout: BOS session not complete after %d seconds" % timeout)
            errors_found = True
            break
        sleep(min(timeleft,sleeptime))

    try:
        # Workaround for CASMCMS-5740
        #in_progress = get_bool_field_from_obj(response_object, "in_progress", **myargs)
        #if complete and in_progress:
        in_progress = get_field_from_obj(response_object, "in_progress", **myargs)
        if complete == True and in_progress == True:
            error("%s reports it is both complete and in progress" % noun)
            errors_found = True
    except CMSTestError:
        errors_found = True

    try:
        # Workaround for CASMCMS-5740
        #error_count = get_int_field_from_obj(response_object, "error_count", **myargs)
        #if error_count == None:
            #error("%s has null error count field" % noun)
            #errors_found = True
        #elif error_count != 0:
            #error("%s reports %d error(s)" % (noun, error_count))
            #errors_found = True
        #else:
            #info("%s reports no errors" % noun)

        error_count = get_field_from_obj(response_object, "error_count", **myargs)
        if error_count == None:
            error("%s has null error count field" % noun)
            errors_found = True
        elif isinstance(error_count, int):
            if error_count != 0:
                error("%s reports %d error(s)" % (noun, error_count))
                errors_found = True
            else:
                info("%s reports no errors" % noun)
        else:
            error("error_count field should be integer but type is %s: %s" % (str(type(error_count)), str(error_count)))
            errors_found = True
    except CMSTestError:
        errors_found = True

    try:
        start_time = get_str_field_from_obj(response_object, "start_time", **myargs)
        if start_time == None:
            error("%s has null start_time field" % noun)
            errors_found = True
        elif len(start_time) == 0:
            error("%s has 0 length start_time field" % noun)
            errors_found = True
        else:
            debug("%s reports start time of %s" % (noun, start_time))
    except CMSTestError:
        errors_found = True

    try:
        stop_time = get_field_from_obj(response_object, "stop_time", **myargs)
        if stop_time == None:
            if complete == True:
                error("%s has null stop_time field" % noun)
                errors_found = True
            else:
                debug("%s has null stop_time field" % noun)
        elif len(stop_time) == 0:
            if complete == True:
                error("%s has 0 length stop_time field" % noun)
                errors_found = True
            else:
                debug("%s has 0 length stop_time field" % noun)
        else:
            debug("%s reports stop time of %s" % (noun, stop_time))
    except CMSTestError:
        errors_found = True

    try:
        status_link = bos_status_link(response_object, session_uuid)
        info("Status link for %s is %s" % (noun, status_link))
    except CMSTestError:
        errors_found = True

    if errors_found:
        raise_test_error("BOS session did not complete successfully")
    info("BOS session completed with no errors")

def perform_bos_session(use_api, template_name, operation, limit_params=None):
    """
    Create the specified bos session, wait for it to complete, validate that it reports success,
    and then delete the bos session.
    """
    session_uuid = create_bos_session(use_api=use_api, \
                                      template_name=template_name, \
                                      operation=operation, \
                                      limit_params=limit_params)

    wait_until_bos_session_complete(use_api, session_uuid)

    delete_bos_session(use_api=use_api, session_uuid=session_uuid)