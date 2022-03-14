#
# MIT License
#
# (C) Copyright 2020-2022 Hewlett Packard Enterprise Development LP
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
"""
HSM-related BOS limit test helper functions
"""

from common.hsm import create_hsm_group

def create_hsm_groups(use_api, nid_to_xname, nid_to_hsm_group):
    """
    Create one HSM group for each xname, plus one that contains all xnames.
    """
    test_name="CMS BOS limit test"
    nid_to_hsm_group["all"] = create_hsm_group(use_api, xname_list=list(nid_to_xname.values()), 
                                               test_name=test_name)
    for nid, xname in nid_to_xname.items():
        nid_to_hsm_group[nid] = create_hsm_group(use_api, xname_list=[xname], 
                                                 test_name=test_name)
