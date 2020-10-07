#!/bin/sh
# Copyright 2019-2020 Cray Inc.
set -e
set -o pipefail

mkdir -p /results

# Fire up etcd because it's needed for the status tests
etcd &

# Remove the nosetest invocation when CASMCMS-5335 is resolved.
# Nosetests
python3 -m pip freeze 2>&1 | tee /results/pip_freeze.out
nosetests -v \
 -w /app/lib/server/bos/test \
 --with-xunit \
 --xunit-file=/results/nosetests.xml \
 --with-coverage \
 --cover-erase \
 --cover-package=bos \
 --cover-branches \
 --cover-inclusive \
 --cover-html \
 --cover-html-dir=/results/coverage \
 --cover-xml \
 --cover-xml-file=/results/coverage.xml \
 2>&1 | tee /results/nosetests.out

# pytest equivalent of the above
# The above nosetests can be removed once pytest duplicates
# all of the needed functionality.
pytest --cov=/app/lib/server/bos -k "not Status" \
 2>&1 | tee /results/pytests.out
 
# Running this test suite separately because it hangs when run with the other tests
# Apparently it is antisocial.
pytest --cov=/app/lib/server/bos /app/lib/server/bos/test/test_status_controller.py \
 2>&1 | tee -a /results/pytests.out