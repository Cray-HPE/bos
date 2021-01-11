#!/bin/sh
# Copyright 2019, Cray Inc. All Rights Reserved.

set -e
set -o pipefail
cd /app/
flake8 --config /app/setup.cfg /app/lib/server/bos 2>&1 | tee /results/flake8.out
