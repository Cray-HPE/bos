#!/usr/bin/env python3
# Copyright 2020-2021 Hewlett Packard Enterprise Development LP
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

"""
See bos_limit_test/argparse.py for command line usage.

- Generate map of xnames, nids, and hostnames for target nodes (by default, 
  all computes)
- Generate list of all BOS session templates
- Create hsm groups and add xnames to them
- Make several copies of the session template, modifying it to use
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
from bos_limit_test.hsm import create_hsm_groups
from bos_limit_test.utils import boot_nodes, config_nodes, create_bos_session_templates, \
                                 init_node_states, power_off_nodes, reboot_nodes
from common.bos import list_bos_session_templates, \
                       bos_session_template_validate_cfs
from common.bosutils import delete_bos_session_templates, \
                            delete_cfs_configs, \
                            delete_hsm_groups, \
                            delete_vcs_repo_and_org
from common.bss import get_bss_compute_nodes
from common.cfs import describe_cfs_config
from common.helpers import CMSTestError, create_tmpdir, debug, error_exit, exit_test, \
                           init_logger, info, log_exception_error, raise_test_exception_error, \
                           remove_tmpdir, section, subtest, warn
from common.k8s import get_csm_private_key
from common.utils import get_compute_nids_xnames, validate_node_hostnames
from common.vcs import create_and_clone_vcs_repo
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

    # We don't need the CSM private key until it comes time to ssh into the compute nodes, but we'd
    # rather know up front if this fails, to save time
    do_subtest("Get CSM private key (for later use to ssh to computes)", get_csm_private_key)

    bss_hosts = do_subtest("Get list of enabled compute nodes from BSS", get_bss_compute_nodes, use_api=use_api)

    nid_to_xname, xname_to_nid = do_subtest("Find compute nids & xnames", 
                                            get_compute_nids_xnames, use_api=use_api, bss_hosts=bss_hosts,
                                            nids=test_variables["nids"], min_required=2)
    if test_variables["nids"] == None:
        test_variables["nids"] = sorted(list(nid_to_xname.keys()))
    nids = test_variables["nids"]
    info("nids: %s" % str(nids))

    do_subtest("Validate node hostnames", validate_node_hostnames, nid_to_xname=nid_to_xname)

    template_objects = do_subtest("List all BOS session templates", list_bos_session_templates, 
                                  use_api=use_api)
    info("BOS session template: %s" % test_variables["template"])
    if test_variables["template"] not in template_objects:
        error_exit("No BOS session template found with name %s" % test_variables["template"])
    cle_template_name = test_variables["template"]

    cle_cfs_config_name = do_subtest("Get CFS configuration name from %s BOS session template" % cle_template_name, 
               bos_session_template_validate_cfs, bst=template_objects[cle_template_name])
    info("CFS configuration name in %s is %s" % (cle_template_name, cle_cfs_config_name))
    test_variables["base_cfs_config_name"] = cle_cfs_config_name

    do_subtest("Validate CFS configuration %s" % cle_cfs_config_name, 
               describe_cfs_config, use_api=use_api, name=cle_cfs_config_name)

    nid_to_hsm_group = test_variables["nid_to_hsm_group"]
    do_subtest("Create hsm groups", create_hsm_groups, use_api=use_api, 
                                  nid_to_xname=nid_to_xname, nid_to_hsm_group=nid_to_hsm_group)

    tmpdir = do_subtest("Create temporary directory", create_tmpdir)
    test_variables["tmpdir"] = tmpdir

    # Always want to make sure that we have a template which does not match any of the others
    # for both cfs config and kernel parameters.
    num_test_templates = 6

    test_vcs_org = "bos-limit-test-org-%d" % random.randint(0,9999999)
    test_vcs_repo = "bos-limit-test-repo-%d" % random.randint(0,9999999)
    test_variables["test_vcs_org"] = test_vcs_org
    test_variables["test_vcs_repo"] = test_vcs_repo
    
    vcs_repo_dir = do_subtest("Create and clone VCS repo %s in org %s" % (test_vcs_repo, test_vcs_org),
                              create_and_clone_vcs_repo, orgname=test_vcs_org, reponame=test_vcs_repo, 
                              testname=TEST_NAME, tmpdir=tmpdir)
    test_variables["vcs_repo_dir"] = vcs_repo_dir

    do_subtest("Create modified BOS session templates", 
               create_bos_session_templates, 
               num_to_create=num_test_templates, 
               use_api=use_api, 
               template_objects=template_objects, 
               xname_to_nid=xname_to_nid,
               test_variables=test_variables)
    test_nodes_base_template = test_variables["test_nodes_base_template"]
    test_template_names = test_variables["test_template_names"]
    
    current_node_states = init_node_states(nids=nids, base_template=cle_template_name)
    bos_func_args = { "use_api": use_api, "current_node_states": current_node_states, 
                      "test_template_names": test_template_names, 
                      "template_objects": template_objects, "xname_to_nid": xname_to_nid }

    do_subtest("Reboot all test nodes to base template %s" % test_nodes_base_template, reboot_nodes,
               template_name=test_nodes_base_template, target_nids=nids, **bos_func_args)

    do_subtest("Shutdown all test nodes using base template %s" % test_nodes_base_template, power_off_nodes,
               template_name=test_nodes_base_template, target_nids=nids, **bos_func_args)

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

    # Reboot all w/limit all intersect hsm group
    limit_params = [ "all", "&%s" % nid_to_hsm_group["all"] ]
    do_subtest("Reboot all nodes to original template %s with --limit all intersect hsm group" % cle_template_name, 
               power_off_nodes, 
               template_name=cle_template_name, limit_params=limit_params, target_nids=list(nids), 
               **bos_func_args)

    section("Cleaning up")

    # For the purposes of deletion, we will just append the test_nodes_base_template template to the test_template_names list
    test_template_names.append(test_nodes_base_template)
    test_variables["test_nodes_base_template"] = None
    do_subtest("Delete modified BOS session templates", delete_bos_session_templates, use_api=use_api, 
               template_names=test_template_names)

    do_subtest("Delete VCS repo and org", delete_vcs_repo_and_org, test_variables=test_variables)

    do_subtest("Delete CFS configurations", delete_cfs_configs, use_api=use_api, cfs_config_names=test_variables["test_cfs_config_names"])

    do_subtest("Delete hsm groups", delete_hsm_groups, use_api=use_api, group_map=nid_to_hsm_group)

    do_subtest("Remove temporary directory", remove_tmpdir, tmpdir=tmpdir)
    test_variables["tmpdir"] = None

    section("Test passed")

def test_wrapper():
    test_variables = { 
        "test_nodes_base_template": None,
        "test_template_names": list(),
        "test_cfs_config_names": list(),
        "nid_to_hsm_group": dict(),
        "tmpdir": None,
        "test_vcs_org": None,
        "test_vcs_repo": None,
        "vcs_repo_dir": None }
    parse_args(test_variables)
    init_logger(test_name=TEST_NAME, verbose=test_variables["verbose"])
    info("Starting test")
    debug("Arguments: %s" % sys.argv[1:])
    debug("test_variables: %s" % str(test_variables))
    use_api = test_variables["use_api"]
    try:
        do_test(test_variables=test_variables)
    except Exception as e:
        # Adding this here to do cleanup when unexpected errors are hit (and to log those errors)
        msg = log_exception_error(e)
        section("Attempting cleanup before exiting in failure")
        try:
            test_template_names = test_variables["test_template_names"]
        except KeyError:
            test_template_names = None
        try:
            test_nodes_base_template = test_variables["test_nodes_base_template"]
        except KeyError:
            test_nodes_base_template = None
        try:
            test_cfs_config_names = test_variables["test_cfs_config_names"]
        except KeyError:
            test_cfs_config_names = None
        try:
            nid_to_hsm_group = test_variables["nid_to_hsm_group"]
        except KeyError:
            nid_to_hsm_group = None
        try:
            tmpdir = test_variables["tmpdir"]
        except KeyError:
            tmpdir = None

        if test_template_names:
            templates_to_clean = test_template_names
        else:
            templates_to_clean = list()
        if test_nodes_base_template:
            templates_to_clean.append(test_nodes_base_template)
        if templates_to_clean:
            info("Attempting to clean up test BOS session templates before exiting")
            delete_bos_session_templates(use_api=use_api, template_names=templates_to_clean, error_cleanup=True)

        if test_cfs_config_names:
            delete_cfs_configs(use_api=use_api, cfs_config_names=test_cfs_config_names, error_cleanup=True)

        delete_vcs_repo_and_org(test_variables=test_variables, error_cleanup=True)

        if nid_to_hsm_group:
            info("Attempting to clean up test HSM groups before exiting")
            delete_hsm_groups(use_api=use_api, group_map=nid_to_hsm_group, error_cleanup=True)

        if tmpdir != None:
            remove_tmpdir(tmpdir)

        section("Cleanup complete")
        error_exit(msg)

if __name__ == '__main__':
    test_wrapper()
    exit_test()