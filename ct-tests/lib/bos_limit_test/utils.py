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
BOS limit test helper functions that involve multiple services
"""

from common.bos import create_bos_session_template, describe_bos_session_template, \
                       perform_bos_session
from common.bosutils import clear_bootset_nodes, get_boot_verification_command, \
                            get_retry_string_from_bootset, \
                            get_unused_retry_values, set_new_template_cfs_config, \
                            SHOW_KERNEL_CMD
from common.bss import list_bss_bootparameters_nidlist
from common.capmc import get_capmc_node_status
from common.hsm import list_hsm_groups
from common.helpers import any_dict_value, debug, debug_logvar, error, info, \
                           raise_test_error, sleep
from common.utils import is_xname_pingable, ssh_command_passes_on_xname
import copy
import datetime
import random
import time

def logvar(func, varname, varvalue):
    debug_logvar(caller="bos_limit_test.utils.%s" % func, varname=varname, varvalue=varvalue)

def get_bootset_node_types(howmany):
    bootset_node_type_options = [ "node_list", "node_groups_single_all_group", "node_groups_all_single_groups", "node_groups_single_all_group_plus_extra" ]
    num_options = len(bootset_node_type_options)
    i = howmany // num_options
    bootset_node_types = bootset_node_type_options*i
    j = howmany % num_options
    bootset_node_types.extend(random.sample(bootset_node_type_options, j))
    return bootset_node_types

def set_nodes_in_bootset(bootset_node_type, bootset, xnames, nid_to_hsm_group=None):
    if bootset_node_type == "node_list":
        xlist = list(xnames)
        random.shuffle(xlist)
        bootset["node_list"] = xlist
        return

    if nid_to_hsm_group == None:
        error("bootset_node_type is %s but nid_to_hsm_group == None" % bootset_node_type)
        raise_test_error("PROGRAMMING_LOGIC_ERROR: set_nodes_in_bootset: nid_to_hsm_group should not be None if bootset_node_type is %s" % bootset_node_type)

    all_hsm_groups = list(nid_to_hsm_group.values())
    hsm_all_group = nid_to_hsm_group["all"]
    hsm_groups_except_all = [ nid_to_hsm_group[n] for n in nid_to_hsm_group.keys() if n != "all" ]

    if bootset_node_type == "node_groups_single_all_group":
        glist = [ hsm_all_group ]
    elif bootset_node_type == "node_groups_all_single_groups":
        glist = list(hsm_groups_except_all)
    elif bootset_node_type == "node_groups_single_all_group_plus_extra":
        num_extra = random.randint(1, len(xnames))
        if num_extra == len(xnames):
            glist = list(all_hsm_groups)
        else:
            glist = [ hsm_all_group ]
            glist.extend(random.sample(hsm_groups_except_all, num_extra))
    else:
        raise_test_error("Programming error: Invalid bootset_node_type specified: %s" % str(bootset_node_type))

    random.shuffle(glist)
    bootset["node_groups"] = glist
    return

def set_new_template_bootset(new_test_template_object, retry_val, bootset_node_type, xnames, test_variables):
    def _logvar(varname, varvalue):
        logvar(func="set_new_template_bootset", varname=varname, varvalue=varvalue)

    nid_to_hsm_group = test_variables["nid_to_hsm_group"]

    # We have previously verified that base_template_object has just 1 boot set
    bootset = any_dict_value(new_test_template_object["boot_sets"])

    # Remove any previous node_list, node_groups, or node_roles_groups fields in this bootset
    clear_bootset_nodes(bootset)

    # At this point, the new_test_template_object will still have the same bootset parameters as the base template
    base_template_retry_string = get_retry_string_from_bootset(bootset)
    _logvar("base_template_retry_string", base_template_retry_string)
    
    new_retry_string = "rd.retry=%d" % retry_val
        
    if base_template_retry_string:
        bootset["kernel_parameters"] = bootset["kernel_parameters"].replace(base_template_retry_string, new_retry_string)
    else:
        bootset["kernel_parameters"] = "%s %s" % (bootset["kernel_parameters"], new_retry_string)

    set_nodes_in_bootset(bootset_node_type=bootset_node_type, bootset=bootset, xnames=xnames, nid_to_hsm_group=nid_to_hsm_group)

def create_template(use_api, template_objects, retry_val, bootset_node_type, xnames, test_variables):
    def _logvar(varname, varvalue):
        logvar(func="create_template", varname=varname, varvalue=varvalue)

    base_template_name = test_variables["template"]
    test_template_names = test_variables["test_template_names"]

    _logvar("retry_val", retry_val)
    _logvar("bootset_node_type", bootset_node_type)
    
    base_template_object = template_objects[base_template_name]
    new_test_template_object = copy.deepcopy(base_template_object)
    new_test_template_object['description'] = "Template for bos-limit integration test, based on %s template" % base_template_name

    new_tname = "bos-test-r%d-%s" % (retry_val, datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S.%f"))
    _logvar("new_tname", new_tname)
    new_test_template_object["name"] = new_tname

    set_new_template_cfs_config(use_api=use_api, new_test_template_object=new_test_template_object, 
                                new_tname=new_tname, test_variables=test_variables)

    set_new_template_bootset(new_test_template_object=new_test_template_object, retry_val=retry_val, 
                             bootset_node_type=bootset_node_type, xnames=xnames, test_variables=test_variables)

    create_bos_session_template(use_api, new_test_template_object)
    test_template_names.append(new_tname)

    # retrieve our new template to verify it was created successfully
    template_objects[new_tname] = describe_bos_session_template(use_api, new_tname)

def create_base_template_for_test_nodes(use_api, template_objects, test_variables, xnames):
    def _logvar(varname, varvalue):
        logvar(func="create_base_template_for_test_nodes", varname=varname, varvalue=varvalue)

    base_template_name = test_variables["template"]
    
    base_template_object = template_objects[base_template_name]
    new_test_template_object = copy.deepcopy(base_template_object)
    new_test_template_object['description'] = "Template for bos-limit integration test, copy of %s template but limited to test nodes" % base_template_name

    new_tname = "bos-test-base-%s" % datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S.%f")
    _logvar("new_tname", new_tname)
    new_test_template_object["name"] = new_tname
    
    # We have previously verified that base_template_object has just 1 boot set
    bootset = any_dict_value(new_test_template_object["boot_sets"])

    # Remove any previous node_list, node_groups, or node_roles_groups fields in this bootset
    clear_bootset_nodes(bootset)

    set_nodes_in_bootset(bootset_node_type="node_list", bootset=bootset, xnames=xnames)

    create_bos_session_template(use_api, new_test_template_object)
    test_variables["test_nodes_base_template"] = new_tname

    # retrieve our new template to verify it was created successfully
    template_objects[new_tname] = describe_bos_session_template(use_api, new_tname)

def create_bos_session_templates(use_api, template_objects, test_variables, num_to_create, xname_to_nid):
    """
    Creates one template which is identical to the base template, but whose bootset includes exactly the 
    list of xnames used by the test. The name of this template will be stored in test_variables["test_nodes_base_template"]
    
    Then:
    
    Create the specified number of new bos session templates, which are clones of test_variables["template"]
    with the following changes:
    1) The kernel parameters are changed to have a different rd.retry value
    2) The template name is based on that value
    3) A new VCS branch is created with an ansible playbook that appends a line to /etc/motd with the new template name
    4) A new CFS configuration is created which uses this playbook
    5) The node_list, node_groups, or node_roles_groups fields in the bootset are replaced with
       a node_groups field that specifies one or more hsm groups that, combined, encompass all of
       our target nodes (and no others)
    The test_template_names list is populated with the new template names.
    The test_cfs_config_names list is populated with the new CFS configuration names.
    The template_objects map is updated to include the new templates.
    """

    def _logvar(varname, varvalue):
        logvar(func="create_bos_session_templates", varname=varname, varvalue=varvalue)

    xnames = xname_to_nid.keys()
    create_base_template_for_test_nodes(use_api, template_objects, test_variables, xnames)

    info("Get list of BSS boot parameters for all enabled compute nodes")
    bss_boot_parameters = list_bss_bootparameters_nidlist(use_api=use_api, xname_to_nid=xname_to_nid)

    unused_rd_retry_values = get_unused_retry_values(start_value=10, howmany=num_to_create, template_objects=template_objects, 
                                                     bss_boot_parameters=bss_boot_parameters)
    _logvar("unused_rd_retry_values", unused_rd_retry_values)

    bootset_node_types = get_bootset_node_types(num_to_create)
    _logvar("bootset_node_types", bootset_node_types)

    for retry_val, bootset_node_type in zip(unused_rd_retry_values, bootset_node_types):
        create_template(use_api=use_api, template_objects=template_objects, retry_val=retry_val, 
                                    bootset_node_type=bootset_node_type, xnames=xnames, test_variables=test_variables)

def bootset_bss_match(bootset, manifest, params):
    """
    Validate that the bos session template bootset matches
    the specified kernel parameters and manifest
    """
    try:
        bootset_type = bootset["type"]
    except KeyError:
        return False
    if bootset_type != "s3":
        return False
    try:
        bootset_path = bootset["path"]
    except KeyError:
        return False
    if bootset_path != manifest:
        return False
    try:
        bootset_params = bootset["kernel_parameters"]
    except KeyError:
        return False
    try:
        bp_index = params.index(bootset_params)
    except ValueError:
        return False
    if bp_index != 0:
        return False
    return True

def init_node_states(nids, base_template):
    """
    Initializes and returns the node state structure to the state the test
    nodes will be in after we reboot them into the base template
    """
    return { nid: { 
                    "motd_template_name": None,
                    "power": "off",
                    "boot_template_name": base_template } 
             for nid in nids }

def verify_node_states(use_api, current_node_states, template_objects, target_nids, xname_to_nid, template_name, test_template_names, operation):
    """
    Given the specified operation that was performed, the specified session template used in the operation, and the specified target nodes of the
    operation, verify that all test nodes are in the expected state. 
    For non-target nodes, nothing should be changed. 
    For target nodes:
    - If the operation was a boot or reboot, then we expect them to be powered on, we expect their kernel parameters to match the session template,
    and we expect their motd to match the vcs branch from the session template.
    - If the operation was config, we expect them to be powered on, we expect their kernel parameters to be unchanged, and we expect their motd
    to match the vcs branch from the session template.
    - If the operation was shutdown, we expect them to be powered off, and ignore their motd and kernel parameters.
    When checking kernel parameters, we both check bss AND we look at them using dmesg on the running system.
    """
    def get_expected_power_state(nid):
        if operation == "configure" or nid not in target_nids:
            return current_node_states[nid]["power"]
        elif operation == "shutdown":
            return "off"
        elif operation in { "boot", "reboot" }:
            return "on"
        else:
            raise_test_error("Programming logic error: Invalid value for operation variable: %s" % str(operation))

    def expected_boot_tname(nid):
        if nid in target_nids and operation in { "boot", "reboot" }:
            return template_name
        else:
            return current_node_states[nid]["boot_template_name"]

    def expected_motd_tname(nid):
        if nid in target_nids and operation != "shutdown":
            return template_name
        else:
            return current_node_states[nid]["motd_template_name"]

    def get_bootset(tname):
        # Get manifest and params values from our template
        # We have previously verified that it has only one boot set specified
        tobj = template_objects[tname]
        return any_dict_value(tobj["boot_sets"])

    wait_time = 600
    end_time = time.time()+wait_time
    bootparams = list_bss_bootparameters_nidlist(use_api, xname_to_nid)
    nid_to_power_status = get_capmc_node_status(use_api, list(xname_to_nid.values()))

    errors_found = False
    for xname, nid in xname_to_nid.items():
        debug("Checking nid %d (xname %s)" % (nid, xname))
        expected_power_state = get_expected_power_state(nid)
        actual_power_state = nid_to_power_status[nid]
        previous_power_state = current_node_states[nid]["power"]
        debug("previous_power_state = %s, expected_power_state = %s, actual_power_state = %s" % (
              previous_power_state, expected_power_state, actual_power_state))
        boot_tname = expected_boot_tname(nid)
        motd_tname = expected_motd_tname(nid)
        bootset = get_bootset(boot_tname)
        debug("Expected boot template name: %s, expected config template name: %s" % (boot_tname, motd_tname))

        kernel, params = None, None
        for bp in bootparams:
            if xname in bp["hosts"]:
                params = bp["params"]
                kernel = bp["kernel"]
                break
        if kernel == None or params == None:
            errors_found=True
            error("Unexpected error -- did not find boot parameters for nid/xname %d/%s" % (nid, xname))
        else:
            manifest = kernel.replace("/kernel","/manifest.json")
            if not bootset_bss_match(bootset, manifest, params):
                info("Expected template name: %s" % str(boot_tname))
                info("Expected bootset: %s" % str(bootset))
                info("Actual params: %s" % params)
                info("Actual kernel: %s" % kernel)
                error("Boot parameters for nid/xname %d/%s do not match what we expect" % (nid, xname))
                errors_found=True
            else:
                debug("Expected template name: %s" % str(boot_tname))
                debug("Expected bootset: %s" % str(bootset))
                debug("Actual params: %s" % params)
                debug("Actual kernel: %s" % kernel)
                if boot_tname != current_node_states[nid]["boot_template_name"]:
                    # Update the current node state to reflect the new template
                    current_node_states[nid]["boot_template_name"] = boot_tname

        if expected_power_state != actual_power_state:
            if expected_power_state == previous_power_state:
                error("Node power state for nid/xname %d/%s should not have changed, but it changed from %s to %s" % (nid, xname, previous_power_state, actual_power_state))
            elif actual_power_state == previous_power_state:
                error("Node power state for nid/xname %d/%s should have changed from %s to %s, but it did not change" % (nid, xname, previous_power_state, expected_power_state))
            else:
                error("Node power state for nid/xname %d/%s should have changed from %s to %s, but it changed to %s" % (nid, xname, previous_power_state, expected_power_state, actual_power_state))
            errors_found=True
        elif actual_power_state != previous_power_state:
            # Update the current node power status to reflect the new status
            current_node_states[nid]["power"] = actual_power_state

        if actual_power_state == "on" and expected_power_state == "on":
            kparams = bootset["kernel_parameters"]
            
            connection_cmd = "date"
            boot_verification_cmd = get_boot_verification_command(bootset)
            if motd_tname in test_template_names:
                config_verification_cmd = "tail -1 /etc/motd | grep -q 'tname=%s$'" % motd_tname
            else:
                config_verification_cmd = "tail -1 /etc/motd | grep -vq 'tname='"
            show_motd_cmd = "tail -1 /etc/motd"
            while True:
                if is_xname_pingable(xname):
                    if ssh_command_passes_on_xname(xname, connection_cmd):
                        if operation in { "boot", "reboot" }:
                            if ssh_command_passes_on_xname(xname, boot_verification_cmd):
                                debug("Node %d appears to be booted using the expected kernel parameters" % nid)
                            else:
                                error("Node %d is booted but appears to have the wrong kernel parameters")
                                ssh_command_passes_on_xname(xname, SHOW_KERNEL_CMD)
                                errors_found = True
                        if ssh_command_passes_on_xname(xname, config_verification_cmd):
                            debug("Node %d appears to be configured as we expect" % nid)
                            current_node_states[nid]["motd_template_name"] = motd_tname
                        else:
                            error("Node %d is booted but appears to have the wrong motd")
                            ssh_command_passes_on_xname(xname, show_motd_cmd)
                            errors_found = True
                        break
                if nid not in target_nids:
                    error("Node %d should not have changed in this operation, it should be booted, but ping or ssh verification failed" % nid)
                    errors_found = True
                    break
                now = time.time()
                if now >= end_time:
                    error("Node %d should be booted, but even after waiting %d seconds, ping or ssh verification still fails" % (nid, wait_time))
                    errors_found = True
                    break
                timeleft = int(round(end_time-now))
                sleep_time = min(15, max(1, timeleft))
                debug("Waiting %d second(s) before retrying" % sleep_time)
                sleep(sleep_time)

    if errors_found:
        raise_test_error("Errors verifying that current node boot parameters and power states match what we expect")

def config_nodes(use_api, current_node_states, template_objects, template_name, target_nids, xname_to_nid, test_template_names, limit_params=None):
    """
    Perform a bos session configure operation on the target nodes and verify that this results in the state we expect.
    """
    perform_bos_session(use_api, template_name, "configure", limit_params)
    verify_node_states(use_api, current_node_states, template_objects, target_nids, xname_to_nid, template_name, test_template_names, "configure")
    info("Target node(s) have been configured as requested")

def boot_nodes(use_api, current_node_states, template_objects, template_name, target_nids, xname_to_nid, test_template_names, limit_params=None):
    """
    Perform a bos session boot operation on the target nodes and verify that this results in the state we expect.
    """
    perform_bos_session(use_api, template_name, "boot", limit_params)
    verify_node_states(use_api, current_node_states, template_objects, target_nids, xname_to_nid, template_name, test_template_names, "boot")
    info("Target node(s) have been booted as requested")
    
def reboot_nodes(use_api, current_node_states, template_objects, template_name, target_nids, xname_to_nid, test_template_names, limit_params=None):
    """
    Perform a bos session reboot operation on the target nodes and verify that this results in the state we expect.
    """
    perform_bos_session(use_api, template_name, "reboot", limit_params)
    verify_node_states(use_api, current_node_states, template_objects, target_nids, xname_to_nid, template_name, test_template_names, "reboot")
    info("Target node(s) have been rebooted as requested")
    
def power_off_nodes(use_api, current_node_states, template_objects, template_name, target_nids, xname_to_nid, test_template_names, limit_params=None):
    """
    Perform a bos session shutdown operation on the target nodes and verify that this results in the state we expect.
    """
    perform_bos_session(use_api, template_name, "shutdown", limit_params)
    verify_node_states(use_api, current_node_states, template_objects, target_nids, xname_to_nid, template_name, test_template_names, "shutdown")
    info("Target node(s) have been powered off as requested")