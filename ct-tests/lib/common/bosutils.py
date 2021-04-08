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

"""
CMS test helper functions that are BOS-related but may involve other services or
otherwise don't fit neatly into the regular common.bos module

This largely was created because the bos limit test and crus integration test
have a lot of opportunity for shared code
"""

from .bos import delete_bos_session_template
from .cfs import create_cfs_config_with_appended_layer, delete_cfs_config
from .helpers import debug, debug_logvar, info, get_str_field_from_obj, log_exception_error
from .hsm import delete_hsm_group
from .utils import create_ansible_motd_repo_branch
from .vcs import delete_vcs_org, delete_vcs_repo, get_vcs_repo_git_url
import re

CLE_BST_RD_RETRY_PARAM_PATTERN = "^.*(rd[.]retry=([0-9][0-9]*))[^0-9].*$"
CLE_BST_RD_RETRY_PARAM_RE_PROG =  re.compile(CLE_BST_RD_RETRY_PARAM_PATTERN)

def logvar(func, varname, varvalue):
    debug_logvar(caller="common.bosutils.%s" % func, varname=varname, varvalue=varvalue)

def get_used_retry_values(template_objects, bss_boot_parameters):
    def _logvar(varname, varvalue):
        logvar(func="get_used_retry_values", varname=varname, varvalue=varvalue)

    used_rd_retry_values = set()
    def parse_params(params):
        results = CLE_BST_RD_RETRY_PARAM_RE_PROG.match(params)
        if results:
            rval = int(results.group(2))
            debug("Found retry value %d" % rval)
            used_rd_retry_values.add(rval)
    for tobject in template_objects.values():
        for bootset in tobject["boot_sets"].values():
            parse_params(bootset["kernel_parameters"])
    # And just to be thorough, let's also grab any that are listed in BSS, since theoretically the
    # nodes could have been booted separately from BOS or have had their session templates changed or
    # deleted since they were booted
    for i, bss_bootparam in enumerate(bss_boot_parameters):
        # We aren't going to worry about verifying BSS data here, so we will just get the parameters
        # if we can
        try:
            params = get_str_field_from_obj(bss_bootparam, "params", null_okay=True)
        except:
            debug("Error parsing 'params' field in BSS boot parameter #%d" % i)
            _logvar("bss_bootparam", bss_bootparam)
            continue
        if params == None:
            continue
        debug("Checking BSS boot params = %s" % params)
        parse_params(params)
    return used_rd_retry_values

def get_unused_retry_values(start_value, howmany, template_objects, bss_boot_parameters):
    def _logvar(varname, varvalue):
        logvar(func="get_unused_retry_values", varname=varname, varvalue=varvalue)

    used_rd_retry_values = get_used_retry_values(template_objects, bss_boot_parameters)
    _logvar("used_rd_retry_values", used_rd_retry_values)
    unused_retry_values = list()
    i=start_value
    while len(unused_retry_values) < howmany:
        if i not in used_rd_retry_values:
            unused_retry_values.append(i)
        i+=1
    return unused_retry_values

def get_retry_string_from_bootset(bootset):
    results = CLE_BST_RD_RETRY_PARAM_RE_PROG.match(bootset["kernel_parameters"])
    if results:
        return results.group(1)
    return None

def clear_bootset_nodes(bootset):
    for f in [ 'node_list', 'node_groups', 'node_roles_groups' ]:
        try:
            del bootset[f]
        except KeyError:
            continue

def set_new_template_cfs_config(use_api, new_test_template_object, new_tname, test_variables):
    def _logvar(varname, varvalue):
        logvar(func="set_new_template_cfs_config", varname=varname, varvalue=varvalue)

    test_vcs_org = test_variables["test_vcs_org"]
    test_vcs_repo = test_variables["test_vcs_repo"]
    vcs_repo_dir = test_variables["vcs_repo_dir"]
    base_cfs_config_name = test_variables["base_cfs_config_name"]
    test_cfs_config_names = test_variables["test_cfs_config_names"]
    playbook_name = "label_motd.yml"

    vcs_repo_clone_url = get_vcs_repo_git_url(test_vcs_org, test_vcs_repo, with_auth=False)
    _logvar("vcs_repo_clone_url", vcs_repo_clone_url)

    info("Creating git branch with motd ansible task for new template %s" % new_tname)
    commit_id = create_ansible_motd_repo_branch(repo_dir=vcs_repo_dir, motd_string="tname=" + new_tname, playbook_name=playbook_name)

    new_config_name = "test-config-for-%s" % new_tname
    info("Creating new CFS configuration %s based on %s but with our new ansible task appended at the end" % (new_config_name, base_cfs_config_name))
    create_cfs_config_with_appended_layer(use_api=use_api, base_config_name=base_cfs_config_name, new_config_name=new_config_name, 
                                          layer_clone_url=vcs_repo_clone_url, layer_commit=commit_id, layer_playbook=playbook_name, 
                                          layer_name="catfood-is-delicious")
    test_cfs_config_names.append(new_config_name)

    new_test_template_object["cfs"]["configuration"] = new_config_name

#
# Test cleanup functions
#

def delete_bos_session_templates(use_api, template_names, error_cleanup=False):
    """
    Delete the specified list of bos session templates (and removes their
    names from the list as they are successfully deleted)
    """
    verify_delete = not error_cleanup
    while template_names:
        tname = template_names[-1]
        try:
            delete_bos_session_template(use_api, tname, verify_delete=verify_delete)
            template_names.pop()
        except Exception as e:
            if error_cleanup:
                # This means we are doing final test cleanup when the test
                # has already failed.
                # In this case, we will record the error, but proceed with our
                # attempts to remove the remaining configs.
                log_exception_error(e, "to delete BOS session template %s" % tname)
                
                # Need to remove the template name from the list, so we don't keep
                # trying to clean it up
                template_names.pop()
                continue
            # Otherwise we re-raise the error
            raise

def delete_cfs_configs(use_api, cfs_config_names, error_cleanup=False):
    """
    Delete all CFS configs, removing them from the list as they are deleted.
    """
    while cfs_config_names:
        cname = cfs_config_names[-1]
        try:
            info("Attempting to delete CFS config %s" % cname)
            delete_cfs_config(use_api, cname)
            cfs_config_names.pop()
        except Exception as e:
            if error_cleanup:
                # This means we are doing final test cleanup when the test
                # has already failed.
                # In this case, we will record the error, but proceed with our
                # attempts to remove the remaining configs.
                log_exception_error(e, "to delete CFS config %s" % cname)

                # Need to remove the config name from the list, so we don't keep
                # trying to clean it up
                cfs_config_names.pop()
                continue
            # Otherwise we re-raise the error
            raise

def delete_hsm_groups(use_api, group_map, error_cleanup=False):
    """
    Delete all HSM groups, removing them from the map as they are deleted.
    """
    key_gname_pairs = list(group_map.items())
    for key, gname in key_gname_pairs:
        try:
            info("Attempting to delete HSM group %s" % gname)
            delete_hsm_group(use_api, gname)
            del group_map[key]
        except Exception as e:
            if error_cleanup:
                # This means we are doing final test cleanup when the test
                # has already failed.
                # In this case, we will record the error, but proceed with our
                # attempts to remove the remaining groups.
                log_exception_error(e, "to delete HSM group %s" % gname)
                continue
            # Otherwise we re-raise the error
            raise

def delete_vcs_repo_and_org(test_variables, error_cleanup=False):
    try:
        orgname = test_variables["test_vcs_org"]
        try:
            reponame = test_variables["test_vcs_repo"]
        except KeyError:
            reponame = None
    except KeyError:
        orgname = None
    if orgname == None:
        return
    query_delete = not error_cleanup
    if reponame != None:
        info("Attempting to delete VCS repo %s in org %s" % (reponame, orgname))
        try:
            delete_vcs_repo(orgname, reponame, query_delete=query_delete)
            test_variables["test_vcs_repo"] = None
        except Exception as e:
            if error_cleanup:
                log_exception_error(e, "to delete VCS repo %s in org %s" % (reponame, orgname))
            else:
                raise
    info("Attempting to delete VCS org %s" % orgname)
    try:
        delete_vcs_org(orgname, query_delete=query_delete)
        test_variables["test_vcs_org"] = None
    except Exception as e:
        if error_cleanup:
            log_exception_error(e, "to delete VCS org %s" % orgname)
        else:
            raise

KERNEL_LINE_STRING = "Kernel command line:"
KERNEL_LINE_GREP = "grep '%s'" % KERNEL_LINE_STRING
SHOW_KERNEL_CMD = "dmesg | %s" % KERNEL_LINE_GREP

def get_boot_verification_command(bootset):
    def _logvar(varname, varvalue):
        logvar(func="get_boot_verification_command", varname=varname, varvalue=varvalue)

    expected_retry_string = get_retry_string_from_bootset(bootset)
    _logvar("expected_retry_string", expected_retry_string)
    if expected_retry_string == None:
        # We end with another kernel line grep to catch the case where the kernel line is not present at all
        return "%s | grep -Ev 'rd[.]retry=[0-9]' | %s" % (SHOW_KERNEL_CMD, KERNEL_LINE_GREP)
    else:
        expected_retry_string = expected_retry_string.replace(".", "[.]")
        return "dmesg | grep -E '%s .*%s($|[^0-9])'" % (KERNEL_LINE_STRING, expected_retry_string)
