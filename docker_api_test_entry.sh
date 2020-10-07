#!/bin/sh
# Copyright 2019, Cray Inc. All Rights Reserved.

set -e
set -o pipefail

mkdir -p /results
python3 -m pip freeze 2>&1 | tee /results/pip_freeze.out
python3 run_apitests.py 2>&1 | tee /results/pytest.out

