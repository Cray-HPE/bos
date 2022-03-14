#!/usr/bin/env sh
#
# MIT License
#
# (C) Copyright 2019-2022 Hewlett Packard Enterprise Development LP
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
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