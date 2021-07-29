#!/usr/bin/env sh

# Copyright 2021 Hewlett Packard Enterprise Development LP
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

# Since this repo uses dynamic versioning, it can be more complicated going
# from a version number back to the source code from which it arose. This
# tool is run at build time to collect information on what is being built.
# It stores its output in gitInfo.txt, and this file is included in Docker
# images and RPMs created by the build. It also appends some annotation
# metadata to the k8s chart being built.

GITINFO_OUTFILE=${GITINFO_OUTFILE:-gitInfo.txt}
GITINFO_NUM_COMMITS=${GITINFO_NUM_COMMITS:-10}
MYNAME=$(basename $0)

function run_cmd
{
    local rc
    echo "# $*"
    "$@"
    rc=$?
    if [ $rc -ne 0 ]; then
        echo "${MYNAME}: ERROR: Command failed with return code $rc: $*" 1>&2
        exit 1
    fi
    return 0
}

function main
{
    run_cmd git rev-parse --abbrev-ref HEAD
    run_cmd git log --decorate=full --source -n ${GITINFO_NUM_COMMITS}
}

GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
read -r GIT_COMMIT_ID GIT_COMMIT_DATE <<< $(git log -n 1 --pretty=tformat:"%H %cI")
echo "${MYNAME}: Appending git metadata to kubernetes/cray-bos/Chart.yaml"
tee -a kubernetes/cray-bos/Chart.yaml << EOF
annotations:
  git/branch: "${GIT_BRANCH}"
  git/commit-date: "${GIT_COMMIT_DATE}"
  git/commit-id: "${GIT_COMMIT_ID}"
EOF

main > ${GITINFO_OUTFILE}
echo "${MYNAME}: Collected build information:"
cat ${GITINFO_OUTFILE}
exit $?


