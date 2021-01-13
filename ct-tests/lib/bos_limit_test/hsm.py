# Copyright 2020 Hewlett Packard Enterprise Development LP

"""
HSM-related BOS limit test helper functions
"""

from common.hsm import create_hsm_group, delete_hsm_group

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

def delete_hsm_groups(use_api, nid_to_hsm_group):
    """
    Delete all HSM groups, removing them from the map as they are deleted.
    """
    key_gname_pairs = list(nid_to_hsm_group.items())
    for key, gname in key_gname_pairs:
        delete_hsm_group(use_api, gname)
        del nid_to_hsm_group[key]
