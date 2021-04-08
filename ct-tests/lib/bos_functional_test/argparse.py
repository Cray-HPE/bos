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
Parses command line arguments for BOS functional test.

Usage: bos_functional_test.py [-v] {api|cli}
"""

import argparse
from common.argparse import valid_api_cli, valid_session_template_name

def parse_args(test_variables):
    """
    Parse the command line arguments and sets the test_variables appropriately.
    """
    parser = argparse.ArgumentParser(
        description="Tests basic BOS functions using API or CLI")
    parser.add_argument("-v", dest="verbose", action="store_const", const=True, 
        help="Enables verbose output (default: disabled)")
    parser.add_argument("api_or_cli", type=valid_api_cli, metavar="{api|cli}", 
        help="Specify whether the test should use API or CLI calls")

    args = parser.parse_args()
    test_variables["use_api"] = (args.api_or_cli == 'api')
    test_variables["verbose"] = (args.verbose == True)
