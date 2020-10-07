'''
Copyright 2019, Cray Inc. All Rights Reserved.

   Filename: run_apitests.py
Description: A test runner for BOS API tests.
'''

import pytest
import sys

sys.exit(
    pytest.main([
        '-x',
        '-v',
        '-s',
        '--disable-pytest-warnings',
        '--maxfail=10',
        'api_tests',
    ])
)
