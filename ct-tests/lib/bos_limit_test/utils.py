# Copyright 2020-2021 Hewlett Packard Enterprise Development LP

"""
BOS limit test helper functions that involve multiple services
"""

from common.bos import perform_bos_session
from common.bss import get_bss_host_by_nid, \
                       list_bss_bootparameters, \
                       list_bss_bootparameters_nidlist
from common.capmc import get_capmc_node_status
from common.hsm import list_hsm_groups
from common.helpers import any_dict_value, debug, error, info, \
                           raise_test_error, sleep
from common.utils import is_xname_pingable, ssh_command_passes_on_xname
import time

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

def find_node_template(use_api, nid, xname, hsm_groups, template_objects, tnamelist):
    """
    For the specified node, find a bos session template which has a bootset that:
    1) includes the node in its node_groups/node_list/node_role_groups field
    2) has kernel parameters and manifest that match the bss bootparameters for the node
    Return the name of a matching template object.
    """
    my_hsm_groups = { g["label"] for g in hsm_groups if xname in g["members"]["ids"] }

    bss_host = get_bss_host_by_nid(use_api, nid, xname)
    role = bss_host["Role"]

    bss_bootparams = list_bss_bootparameters(use_api, nid, xname)
    params = bss_bootparams["params"]
    manifest = bss_bootparams["kernel"].replace("/kernel","/manifest.json")

    def template_matches_node(tobject):
        for bootset in tobject["boot_sets"].values():
            if not bootset_bss_match(bootset, manifest, params):
                continue
            # Okay, this one looks good, but we need to make sure that this node is
            # specified in the 'node_list', 'node_groups', or 'node_roles_groups' field
            try:
                if role in bootset["node_roles_groups"]:
                    return True
                break
            except KeyError:
                pass
            try:
                if xname in bootset["node_list"]:
                    return True
                break
            except KeyError:
                pass
            # We should not risk a KeyError for this last check, since we previously
            # verified that every bootset in every bos session template had exactly 1
            # of these 3 fields. So if this one lacks the previous two, it must have this one
            for g in bootset["node_groups"]:
                if g in my_hsm_groups:
                    return True

    for tname in tnamelist:
        if template_matches_node(template_objects[tname]):
            return tname

    raise_test_error("Unable to find bos session template that matches current node state for nid %d" % nid)

def record_node_states(use_api, nid_to_xname, template_objects, default_cle_template_name):
    """
    For every target node, record its current bos session template (or best guess) and power state.
    For the template, we always check the slurm template first, then the cle template, since those
    are the ones most commonly used (and so if a node matches one of those, we stop looking for further
    matches).
    """
    tnamelist = list()
    if "slurm" in template_objects:
        tnamelist.append("slurm")
    if default_cle_template_name != None and default_cle_template_name in template_objects:
        tnamelist.append(default_cle_template_name)
    tnamelist.extend([tname for tname in template_objects if tname not in { "slurm", default_cle_template_name }])

    hsm_groups = list_hsm_groups(use_api)
    orig_node_states = dict()
    nid_to_power_status = get_capmc_node_status(use_api, list(nid_to_xname.keys()))
    for nid, xname in nid_to_xname.items():
        pow = nid_to_power_status[nid]
        info("Current power state of nid %d: %s" % (nid, pow))
        tmp = find_node_template(use_api, nid, xname, hsm_groups, template_objects, tnamelist)
        info("Current bos session template of nid %d: %s" % (nid, tmp))
        orig_node_states[nid] = { 
            "motd_template_name": None,
            "power": pow,
            "boot_template_name": tmp }
    return orig_node_states

def verify_node_states(use_api, current_node_states, template_objects, target_nids, xname_to_nid, template_name, test_template_names, operation):
    """
    Given the specified operation that was performed, the specified session template used in the operation, and the specified target nodes of the
    operation, verify that all nodes are in the expected state. 
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
            boot_verification_cmd = "dmesg | grep -q '%s'" % kparams
            show_kernel_cmd = "dmesg | grep 'Kernel command line:'"
            if motd_tname in test_template_names:
                config_verification_cmd = "tail -1 /etc/motd | grep -q 'branch=%s$'" % motd_tname
            else:
                config_verification_cmd = "tail -1 /etc/motd | grep -vq 'branch='"
            show_motd_cmd = "tail -1 /etc/motd"
            while True:
                if is_xname_pingable(xname):
                    if ssh_command_passes_on_xname(xname, connection_cmd):
                        if operation in { "boot", "reboot" }:
                            if ssh_command_passes_on_xname(xname, boot_verification_cmd):
                                debug("Node %d appears to be booted using the expected kernel parameters" % nid)
                            else:
                                error("Node %d is booted but appears to have the wrong kernel parameters")
                                ssh_command_passes_on_xname(xname, show_kernel_cmd)
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