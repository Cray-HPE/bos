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
Parses command line arguments for BOS limit test.

Usage: bos_limit_test.py [--nids { <A>[-<B>][,<C>[-<D>]]... } ] [--template <bos_session_template_name>] [-v] {api|cli}

Examples of legal --nids arguments:
--nids 1,5
--nids 1-3
--nids 1,3,5-10
If nodes are specified, at least two must be specified. If no nodes are specified, it will use all compute nodes.

If no BOS session template is specified, the most recent default cle template is identified and used.
"""

import argparse
from common.argparse import valid_api_cli, valid_nid_list, \
                            valid_session_template_name

def bos_limit_test_valid_nid_list(s):
    """
    Wrapper for common.argparse.valid_nid_list function, calling it with the
    minimum nid count (2) for the BOS limit test
    """
    return valid_nid_list(s, min_nid_count=2)

def parse_args(test_variables):
    """
    Parse the command line arguments and return the specified nids, template, use_api, and verbose 
    parameters (or their default values)
    """
    parser = argparse.ArgumentParser(
        description="Tests the BOS limit function by using it to configure, boot, reboot, and power off nodes")
    parser.add_argument("--nids", dest="nids", type=bos_limit_test_valid_nid_list, 
        help="List or range of at least two nids to use for test (default: all compute nodes)", 
        metavar="a[-b][,c[-d]]...")
    parser.add_argument("--template", dest="template", type=valid_session_template_name, 
        help="Name of BOS session template to copy for test (by default latest CLE template is used)",
        metavar="bos_session_template_name")
    parser.add_argument("-v", dest="verbose", action="store_const", const=True, 
        help="Enables verbose output (default: disabled)")
    parser.add_argument("api_or_cli", type=valid_api_cli, metavar="{api|cli}", 
        help="Specify whether the test should use API or CLI calls")

    args = parser.parse_args()
    test_variables["use_api"] = (args.api_or_cli == 'api')
    test_variables["nids"] = args.nids
    test_variables["template"] = args.template if args.template else None
    test_variables["verbose"] = (args.verbose == True)
