#!/usr/bin/python
# Copyright 2019, 2021 Hewlett Packard Enterprise Development LP
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
The purpose of this ansible module is to assist in the creation of boss session templates.
"""

from ansible.module_utils.basic import AnsibleModule
from base64 import decodestring
import bos_python_helper
import subprocess
import time
import json

PROTOCOL = 'https'
API_GW_DNSNAME = 'api-gw-service-nmn.local'
TOKEN_URL_DEFAULT = "{}://{}/keycloak/realms/shasta/protocol/openid-connect/token".format(PROTOCOL, API_GW_DNSNAME)
BOS_URL_DEFAULT = "{}://{}/apis/bos/v1".format(PROTOCOL, API_GW_DNSNAME)
OAUTH_CLIENT_ID_DEFAULT = "admin-client"
CERT_PATH_DEFAULT = "/var/opt/cray/certificate_authority/certificate_authority.crt"


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview', 'stableinterface'],
    'supported_by': 'community'
}



DOCUMENTATION = '''
---
module: bos_session_template_create

short_description: This module creates session templates for BOS

version_added: "2.7.10"

description:
    - Creates session templates for BOS


options:
    name:
        required: True
        type: String
    description:
        required: True
        type: String
    cfs-url (deprecated):
        required: False
        type: String
    cfs-branch (deprecated):
        required: False
        type: String
    enable-cfs:
        required: True
        type: Boolean
    cfs:
        required: False
        type: Json
        suboptions:
            commit:
                type: String
            branch:
                type: String
            clone-url:
                type: String
            playbook:
                type: String
    partition:
        required: True
        type: String
    boot-sets:
        required: True
        type: Json
    bos-url
        required: False
        type: String
        default: {BOS_URL_DEFAULT}
    token-url
        required: False
        type: String
        default: {TOKEN_URL_DEFAULT}
    oauth-client-id
        required: False
        type: String
        default: {OAUTH_CLIENT_ID_DEFAULT}
    oauth-client-secret
        required: False
        type: String
        default: ''
    certificate
        required: False
        type: String
        default: {CERT_PATH_DEFAULT}
    max-sleep
        required: False
        type: Integer
        default: 300

author:
    - rbak
'''.format(BOS_URL_DEFAULT=BOS_URL_DEFAULT,
           TOKEN_URL_DEFAULT=TOKEN_URL_DEFAULT,
           OAUTH_CLIENT_ID_DEFAULT=OAUTH_CLIENT_ID_DEFAULT,
           CERT_PATH_DEFAULT=CERT_PATH_DEFAULT)

EXAMPLES = '''
# Create a new session template
  - name: Invoke bos_session_template_create
    bos_session_template_create:
      name: test_template
      description: A test session template
      cfs-url: "https://api-gw-service-nmn.local/vcs/cray/config-management.git"
      cfs-branch: master
      enable-cfs: True
      partition: p1
      boot-sets:
          boot_set1:
            boot_ordinal: 1
            ims_image_id: 06d37efc-7ba2-4ba9-8c22-073a641f2bf3
            kernel_parameters: console=ttyS0,115200n8
              rd.shell rd.retry=10 ip=dhcp rd.neednet=1 crashkernel=256M
              hugepagelist=2m-2g intel_iommu=off bad_page=panic
              iommu=pt ip=dhcp numa_interleave_omit=headless
              numa_zonelist_order=node oops=panic pageblock_order=14
              pcie_ports=native printk.synchronous=y quiet turbo_boost_limit=999
            network: nmn
            node_list:
            - x0c0s28b0n0
            rootfs_provider: 'cps'
            rootfs_provider_passthrough: 'dvs:api-gw-service-nmn.local:eth0'
          boot_set2:
            boot_ordinal: 1
            ims_image_id: 06d37efc-7ba2-4ba9-8c22-073a641f2bf3
            kernel_parameters: console=ttyS0,115200n8
              rd.shell rd.retry=10 ip=dhcp rd.neednet=1 crashkernel=256M
              hugepagelist=2m-2g intel_iommu=off bad_page=panic
              iommu=pt ip=dhcp numa_interleave_omit=headless
              numa_zonelist_order=node oops=panic pageblock_order=14
              pcie_ports=native printk.synchronous=y quiet turbo_boost_limit=999
            network: nmn
            node_roles_groups:
            - Compute
            rootfs_provider: 'cps'
            rootfs_provider_passthrough: 'dvs:api-gw-service-nmn.local:eth0'
'''


RETURN = '''
original_message:
    description: The original name param that was passed in
    type: str
    returned: always
message:
    description: The output message that the sample module generates
    type: str
    returned: always
'''


class BOSSessionTemplateCreate(AnsibleModule):
    def __init__(self, *args, **kwargs):
        super(BOSSessionTemplateCreate, self).__init__(*args, **kwargs)
        self.populate_oauth_client_secret()

        #Create an BOS Helper Object
        self.session = bos_python_helper.create_session(self.params['oauth-client-id'],
                                                        self.params['oauth-client-secret'],
                                                        self.params['certificate'],
                                                        self.params['token-url'],
                                                        2000)
        self.helper = bos_python_helper.BosHelper(self.params['bos-url'],
                                                  self.session)

    def populate_oauth_client_secret(self):
        """
        Talk with kubernetes and obtain the client secret; this only works if the
        remote execution target allows such interactions; otherwise specify the
        oauth-client-secret value in the call to this module.
        """
        if self.params['oauth-client-secret']:
            return
        stdout = subprocess.check_output(['kubectl', 'get', 'secrets', 'admin-client-auth', "-ojsonpath='{.data.client-secret}"])
        self.params['oauth-client-secret'] = decodestring(stdout.strip())

    def api_health_checks(self):
        """
        Blocks and waits for required API endpoints to respond with a known good
        response; this ensures proper ordering of actions during install, which
        can come online asynchronously.
        """
        self.health_check_bos()

    def health_check_bos(self):
        endpoint = '%s/sessiontemplate' % (self.params['bos-url'])
        sleep_count = 0
        while sleep_count < self.params['max-sleep']:
            response = self.session.get(endpoint)
            if response.ok:
                return
            else:
                time.sleep(1)
                sleep_count += 1
        self.fail_json(msg='BOS endpoing {} was not available after {} seconds'.format(
                            endpoint, self.params['max-sleep']))


    def __call__(self):
        # Check Health of APIs before proceeding
        self.api_health_checks()

        try:
            self.helper.bos_create_session_template(
                name = self.params['name'],
                description = self.params['description'],
                cfs_url = self.params.get('cfs-url'),
                cfs_branch = self.params.get('cfs-branch'),
                enable_cfs = self.params['enable-cfs'],
                cfs = self.params.get('cfs'),
                partition = self.params.get('partition'),
                boot_sets = json.loads(self.params['boot-sets']),
                )
        except Exception as e:
            self.fail_json(msg="Exception running module: %s" % e)
        self.exit_json(changed=True)


def main():
    fields = {# Session Template Information
                'name': {'required': True, "type": "str"},
                'description': {'required': True, "type": "str"},
                'cfs-url': {'required': False, "type": "str"},  # DEPRECATED
                'cfs-branch': {'required': False, "type": "str"},  # DEPRECATED
                'enable-cfs': {'required': True, "type": "bool"},
                'cfs': {'required': False, "type": "json", 'options': {
                    'commit': {'required': False, "type": "str"},
                    'branch': {'required': False, "type": "str"},
                    'clone-url': {'required': False, "type": "str"},
                    'playbook': {'required': False, "type": "str"}}},
                'partition': {'required': False, "type": "str"},
                'boot-sets': {'required': True, "type": "json"},

                # Endpoint Information
                'bos-url': {'required': False, "type": 'str', 'default': BOS_URL_DEFAULT},
                'token-url': {'required': False, "type": 'str', 'default': TOKEN_URL_DEFAULT},

                # Authentication Information
                'oauth-client-id': {'required': False, "type": "str", 'default': OAUTH_CLIENT_ID_DEFAULT},
                'oauth-client-secret': {'required': False, "type": 'str', 'default': ''},
                'certificate': {'required': False, "type": "str", "default": CERT_PATH_DEFAULT},

                # Other
                'max-sleep': {'required': False, "type": "int", "default": 300},
                }
    module = BOSSessionTemplateCreate(argument_spec=fields)
    try:
        module()
    except Exception as e:
        module.response['stderr'] = str(e)
        module.fail_json(**module.response)


if __name__ == '__main__':
    main()
