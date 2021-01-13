#!/usr/bin/env python3
# Copyright 2020 Hewlett Packard Enterprise Development LP

"""
See bos_limit_test/argparse.py for command line usage.

- Generate map of xnames, nids, and hostnames for target nodes (by default, 
  all computes)
- Generate list of all BOS session templates
- Identify cle session template, if not specified
- Create hsm groups and add xnames to them
- Make several copies of the cle session template, modifying it to use
  hsm groups, to use custom vcs branches, and to slightly modify the kernel
  parameters.
- Save current session template (or best guess) for target nodes
- Perform various BOS session operations to verify they are carried out as expected
- Reboot target nodes using originally saved session templates
- Delete new templates
- Delete custom vcs branches
- Delete new hsm groups
"""

from bos_limit_test.argparse import parse_args
from bos_limit_test.bos import create_bos_session_templates, find_default_cle_template
from bos_limit_test.hsm import create_hsm_groups, delete_hsm_groups
from bos_limit_test.utils import boot_nodes, config_nodes, power_off_nodes, \
                                 reboot_nodes, record_node_states
from common.bos import delete_bos_session_templates, list_bos_session_templates, \
                       bos_session_template_validate_cfs
from common.helpers import CMSTestError, create_tmpdir, debug, error_exit, exit_test, \
                           init_logger, info, log_exception_error, raise_test_exception_error, \
                           remove_tmpdir, section, subtest, warn
from common.utils import get_compute_nids_xnames, validate_node_hostnames
from common.vcs import clone_vcs_repo, remove_vcs_test_branches
import copy
import random
import sys

TEST_NAME = "bos_limit_test"

def do_subtest(subtest_name, subtest_func, **subtest_kwargs):
    """
    Log that we are about to run a subtest with the specified name, then call the specified function
    with the specified arguments. Raise exception in case of an error.
    """
    subtest(subtest_name)
    try:
        return subtest_func(**subtest_kwargs)
    except CMSTestError:
        raise
    except Exception as e:
        raise_test_exception_error(e, "%s subtest" % subtest_name)

def do_test(test_variables):
    """
    Main test body. Execute each subtest in turn.
    """
    use_api = test_variables["use_api"]

    if use_api:
        info("Using API")
    else:
        info("Using CLI")

    nid_to_xname, xname_to_nid = do_subtest("Find compute nids & xnames", 
                                            get_compute_nids_xnames, use_api=use_api, 
                                            nids=test_variables["nids"], min_required=2)
    if test_variables["nids"] == None:
        test_variables["nids"] = sorted(list(nid_to_xname.keys()))
    nids = test_variables["nids"]
    info("nids: %s" % str(nids))

    do_subtest("Validate node hostnames", validate_node_hostnames, nid_to_xname=nid_to_xname)

    template_objects = do_subtest("List all BOS session templates", list_bos_session_templates, 
                                  use_api=use_api)
    if test_variables["template"]:
        info("BOS session template: %s" % test_variables["template"])
        if test_variables["template"] not in template_objects:
            error_exit("No BOS session template found with name %s" % test_variables["template"])
        else:
            cle_template_name = test_variables["template"]
            default_cle_template_name = None
    else:
        default_cle_template_name = do_subtest("Find default CLE BOS session template", 
                                       find_default_cle_template, 
                                       template_objects=template_objects)
        cle_template_name = default_cle_template_name
        info("BOS session template: %s" % cle_template_name)

    do_subtest("Validate CFS settings in %s BOS session template" % cle_template_name, 
               bos_session_template_validate_cfs, bst=template_objects[cle_template_name])

    nid_to_hsm_group = test_variables["nid_to_hsm_group"]
    do_subtest("Create hsm groups", create_hsm_groups, use_api=use_api, 
                                  nid_to_xname=nid_to_xname, nid_to_hsm_group=nid_to_hsm_group)

    orig_node_states = do_subtest("Record current node states and templates", record_node_states, 
                                  use_api=use_api, nid_to_xname=nid_to_xname, 
                                  default_cle_template_name=default_cle_template_name,
                                  template_objects=template_objects)
    current_node_states = copy.deepcopy(orig_node_states)

    tmpdir = do_subtest("Create temporary directory", create_tmpdir)
    test_variables["tmpdir"] = tmpdir

    # Always want to make sure that we have a template which does not match any of the others
    # for both cfs branch and kernel parameters.
    num_test_templates = 6

    vcs_repo_dir = do_subtest("Clone vcs repo", clone_vcs_repo, tmpdir=tmpdir)
    test_variables["vcs_repo_dir"] = vcs_repo_dir

    test_template_names, test_vcs_branches = test_variables["test_template_names"], test_variables["test_vcs_branches"]
    do_subtest("Create modified BOS session templates", 
               create_bos_session_templates, 
               num_to_create=num_test_templates, 
               use_api=use_api, 
               template_objects=template_objects, 
               base_template_name=cle_template_name, 
               nid_to_hsm_group=nid_to_hsm_group,
               xnames=list(nid_to_xname.values()),
               test_template_names=test_template_names,
               test_vcs_branches=test_vcs_branches,
               vcs_repo_dir=vcs_repo_dir)

    bos_func_args = { "use_api": use_api, "current_node_states": current_node_states, 
                      "test_template_names": test_template_names, 
                      "template_objects": template_objects, "xname_to_nid": xname_to_nid }

    orig_template_names = list( { ostate["boot_template_name"] for ostate in orig_node_states.values() } )
    for tname in orig_template_names:
        nids_using_tname = sorted([ nid for nid, ostate in orig_node_states.items() if ostate["boot_template_name"] == tname ])
        xnames_using_tname = [ nid_to_xname[nid] for nid in nids_using_tname ]
        # Order should not matter
        random.shuffle(xnames_using_tname)
        do_subtest("Shutdown nodes %s" % ", ".join([ str(n) for n in nids_using_tname]), power_off_nodes, template_name=tname, 
               limit_params=xnames_using_tname, target_nids=list(nids_using_tname), **bos_func_args)

    def unused_test_template_name():
        currently_used_templates = { cns["boot_template_name"] for cns in current_node_states.values() }
        currently_used_templates.update( { cns["motd_template_name"] for cns in current_node_states.values() } )
        unused_templates = [ tn for tn in test_template_names if tn not in currently_used_templates]
        if unused_templates:
            return random.choice(unused_templates)
        warn("All test templates in used, which should not happen")
        return random.choice(test_template_names)

    # Boot all w/limit xname union
    limit_params = list(nid_to_xname.values())
    # Order should not matter with union
    random.shuffle(limit_params)
    do_subtest("Boot all nids with --limit xname union", boot_nodes, template_name=unused_test_template_name(), 
               limit_params=limit_params, target_nids=list(nids), **bos_func_args)

    this_nid = random.choice(nids)
    # Configure 1 with limit xname
    limit_params = [ nid_to_xname[this_nid] ]
    do_subtest("Configure nid %s with --limit xname" % this_nid, config_nodes, 
               template_name=unused_test_template_name(), limit_params=limit_params, 
               target_nids=[this_nid], **bos_func_args)
    
    # Configure same 1 with limit group intersection
    limit_params = [ nid_to_hsm_group["all"], "&%s" % nid_to_hsm_group[this_nid] ]
    do_subtest("Configure nid %s with --limit group intersection" % this_nid, config_nodes, 
               template_name=unused_test_template_name(), limit_params=limit_params, 
               target_nids=[this_nid], **bos_func_args)

    # Reboot same 1 with limit group
    limit_params = [ nid_to_hsm_group[this_nid] ]
    do_subtest("Reboot nid %s with --limit group" % this_nid, reboot_nodes, 
               template_name=unused_test_template_name(), limit_params=limit_params, 
               target_nids=[this_nid], **bos_func_args)

    # Config rest with limit group except xname
    limit_params = [ nid_to_hsm_group["all"], "!%s" % nid_to_xname[this_nid] ]
    target_nids = [ n for n in nids if n != this_nid ]
    do_subtest("Config all nids except %s with --limit group except xname" % this_nid, config_nodes, 
               template_name=unused_test_template_name(), limit_params=limit_params, target_nids=target_nids, 
               **bos_func_args)

    # Configure rest with limit group except group
    limit_params = [ nid_to_hsm_group["all"], "!%s" % nid_to_hsm_group[this_nid] ]
    do_subtest("Configure all nids except %s with --limit group except group" % this_nid, config_nodes, 
               template_name=unused_test_template_name(), limit_params=limit_params, target_nids=target_nids, 
               **bos_func_args)

    # Configure rest w/limit group union
    limit_params = [ nid_to_hsm_group[n] for n in target_nids ]
    # Order should not matter with union
    random.shuffle(limit_params)
    do_subtest("Configure all nids except %s with --limit group union" % this_nid, config_nodes, 
               template_name=unused_test_template_name(), 
               limit_params=limit_params, target_nids=target_nids, **bos_func_args)

    # Shutdown all w/limit all intersect hsm group
    limit_params = [ "all", "&%s" % nid_to_hsm_group["all"] ]
    do_subtest("Shutdown all nodes with --limit all intersect hsm group", power_off_nodes, 
               template_name=unused_test_template_name(), limit_params=limit_params, target_nids=list(nids), 
               **bos_func_args)

    orig_tn_to_nidlist = dict()
    for this_nid in nids:
        boot_tn = orig_node_states[this_nid]["boot_template_name"]
        try:
            orig_tn_to_nidlist[boot_tn].append(this_nid)
        except KeyError:
            orig_tn_to_nidlist[boot_tn] = [ this_nid ]
    
    for tn, this_nidlist in orig_tn_to_nidlist.items():
        limit_params = [ nid_to_xname[nid] for nid in this_nidlist ]
        # Order should not matter with union
        random.shuffle(limit_params)

        do_subtest("Power on nids %s with --limit xname union" % ', '.join([str(n) for n in this_nidlist]), boot_nodes, template_name=tn, 
                   limit_params=limit_params, target_nids=this_nidlist, **bos_func_args)

    do_subtest("Delete modified BOS session templates", delete_bos_session_templates, use_api=use_api, 
               template_names=test_template_names)
    
    do_subtest("Delete vcs test branches", remove_vcs_test_branches, repo_dir=vcs_repo_dir, test_vcs_branches=test_vcs_branches)
    
    do_subtest("Delete hsm groups", delete_hsm_groups, use_api=use_api, nid_to_hsm_group=nid_to_hsm_group)

    do_subtest("Remove temporary directory", remove_tmpdir, tmpdir=tmpdir)
    test_variables["tmpdir"] = None

    section("Test passed")

def test_wrapper():
    test_variables = { 
        "test_vcs_branches": list(),
        "test_template_names": list(),
        "nid_to_hsm_group": dict(),
        "tmpdir": None,
        "vcs_repo_dir": None }
    parse_args(test_variables)
    init_logger(test_name=TEST_NAME, verbose=test_variables["verbose"])
    info("Starting test")
    debug("Arguments: %s" % sys.argv[1:])
    debug("test_variables: %s" % str(test_variables))
    try:
        do_test(test_variables=test_variables)
    except Exception as e:
        # Adding this here to do cleanup when unexpected errors are hit (and to log those errors)
        msg = log_exception_error(e)
        if test_variables["test_template_names"]:
            info("Attempting to clean up test BOS session templates before exiting")
            delete_bos_session_templates(use_api=test_variables["use_api"], template_names=test_variables["test_template_names"])
        if test_variables["test_vcs_branches"] and test_variables["vcs_repo_dir"]:
            info("Attempting to clean up vcs test branches before exiting")
            remove_vcs_test_branches(test_variables["vcs_repo_dir"], test_variables["test_vcs_branches"])
        if test_variables["nid_to_hsm_group"]:
            info("Attempting to clean up test HSM groups before exiting")
            delete_hsm_groups(use_api=test_variables["use_api"], nid_to_hsm_group=test_variables["nid_to_hsm_group"])
        if test_variables["tmpdir"] != None:
            remove_tmpdir(test_variables["tmpdir"])
            test_variables["tmpdir"] = None
        error_exit(msg)

if __name__ == '__main__':
    test_wrapper()
    exit_test()