#!/usr/bin/env python3
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
See bos_functional_test/argparse.py for command line usage.

Eventually this test will also cover BOS sessions, but the most urgent need
is for a test which covers BOS session template operations without requiring
node operations also (as BOS limit does).

Steps (for all supported API versions):
- Create new BOS session template
- Describe new session template
- List all BOS session templates and verify the new one is there
- Delete it
- Verify describe now fails
- List all BOS session templates and verify the new one is no longer there
"""

from bos_functional_test.argparse import parse_args
from bos_functional_test.helpers import generate_session_template, verify_template_list
from common.bos import create_bos_session_template, delete_bos_session_template, \
                       describe_bos_session_template, list_bos_session_templates
from common.helpers import CMSTestError, debug, error_exit, exit_test, \
                           init_logger, info, log_exception_error, raise_test_exception_error, \
                           section, subtest, warn
import sys

TEST_NAME = "bos_functional_test"

def do_subtest(subtest_name, subtest_func, **subtest_kwargs):
    """
    Log that we are about to run a subtest with the specified name, then call the specified function
    with the specified arguments. Raise exception in case of an error.
    """
    subtest(subtest_name)
    try:
        return subtest_func(**subtest_kwargs)
    except CMSTestError:
        raise
    except Exception as e:
        raise_test_exception_error(e, "%s subtest" % subtest_name)

def do_test(test_variables):
    """
    Main test body. Execute each subtest in turn.
    """
    use_api = test_variables["use_api"]

    if use_api:
        info("Using API")
    else:
        info("Using CLI")

    new_session_template = do_subtest("Generate BOS session template to be created", generate_session_template)
    template_name = new_session_template["name"]
    test_variables["test_template_name"] = template_name

    do_subtest("Create BOS session template", create_bos_session_template, use_api=use_api, template_object=new_session_template)

    do_subtest("Describe BOS session template", describe_bos_session_template, use_api=use_api, template_name=template_name)

    all_templates = do_subtest("List all BOS session templates", list_bos_session_templates, use_api=use_api)
    
    do_subtest("Verify new BOS session template is listed", verify_template_list, template_map=all_templates, 
               template_name=template_name, should_exist=True)

    do_subtest("Delete new BOS session template", delete_bos_session_template, use_api=use_api, template_name=template_name, 
                                         verify_delete=False)
    test_variables["test_template_name"] = None

    do_subtest("Verify describe of template now fails", describe_bos_session_template, use_api=use_api, template_name=template_name,
               expect_to_pass=False)

    all_templates = do_subtest("List all BOS session templates", list_bos_session_templates, use_api=use_api)
    
    do_subtest("Verify template is no longer listed", verify_template_list, template_map=all_templates, 
               template_name=template_name, should_exist=False)

    section("Test passed")

def test_wrapper():
    test_variables = { "test_template_name": None }
    parse_args(test_variables)
    init_logger(test_name=TEST_NAME, verbose=test_variables["verbose"])
    info("Starting test")
    debug("Arguments: %s" % sys.argv[1:])
    debug("test_variables: %s" % str(test_variables))
    try:
        do_test(test_variables=test_variables)
    except Exception as e:
        # Adding this here to do cleanup when unexpected errors are hit (and to log those errors)
        msg = log_exception_error(e)
        if test_variables["test_template_name"]:
            info("Attempting to clean up test BOS session template before exiting")
            delete_bos_session_template(use_api=test_variables["use_api"], template_name=test_variables["test_template_name"], 
                                         verify_delete=False)
        error_exit(msg)

if __name__ == '__main__':
    test_wrapper()
    exit_test()
