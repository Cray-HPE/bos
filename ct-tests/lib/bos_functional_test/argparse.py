# Copyright 2020 Hewlett Packard Enterprise Development LP

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
