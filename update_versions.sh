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

function do_update_version
{
    if ! ./cms_meta_tools/latest_version/latest_version.sh \
                --docker \
                --major "${BOA_X}" \
                --minor "${BOA_Y}" \
                --outfile boa.version \
                --overwrite \
                cray-boa ; then
        echo "ERROR: Unable to determine latest cray-boa version with major.minor of ${BOA_X}.${BOA_Y}" 1>&2
        return 1
    fi

    if ! cat boa.version ; then
        echo "ERROR: Unable to cat boa.version file" 1>&2
        return 1
    fi
    
    ./cms_meta_tools/update_versions/update_versions.sh && return 0
    echo "ERROR: cms_meta_tools update_version.sh failed" 1>&2
    return 1
}

# First we need to find the latest stable boa version with the
# desired major/minor numbers (found in boa.x and boa.y)
BOA_X=$(head -1 boa.x)
if [ $? -ne 0 ]; then
    echo "ERROR: failed reading boa.x" 1>&2
    exit 1
fi
echo "boa.x = ${BOA_X}"
BOA_Y=$(head -1 boa.y)
if [ $? -ne 0 ]; then
    echo "ERROR: failed reading boa.y" 1>&2
    exit 1
fi
echo "boa.y = ${BOA_Y}"

./install_cms_meta_tools.sh || exit 1
RC=0
do_update_version || RC=1
rm -rf ./cms_meta_tools boa.version
exit $RC
