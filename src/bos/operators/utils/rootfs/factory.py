#
# MIT License
#
# (C) Copyright 2022, 2024 Hewlett Packard Enterprise Development LP
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
import importlib
import logging

from . import ProviderNotImplemented

LOGGER = logging.getLogger(__name__)

class ProviderFactory:
    """
    Conditionally creates new instances of rootfilesystem providers based on
    a given agent instance.
    """
    def __init__(self, boot_set, artifact_info):
        """
        Inputs:
            boot_set: A boot set from the session template data
            artifact_info: The artifact summary from the boot_set.
                           This is a dictionary containing keys which are boot artifacts (kernel, initrd, roots, and kernel boot parameters)
                           the values are the paths to those boot artifacts in S3. It also contains the etags for the rootfs and kerenl boot parameters.
        """
        self.boot_set = boot_set
        self.artifact_info = artifact_info

    def __call__(self):
        provider_name = self.boot_set.get('rootfs_provider', '').lower()

        if provider_name:
            # When a provisioning protocol is specified...
            provider_module = 'bos.operators.utils.rootfs.{}'.format(provider_name)
            provider_classname = '{}Provider'.format(provider_name.upper())
        else:
            # none specified or blank
            provider_module = 'bos.operators.utils.rootfs'
            provider_classname = 'RootfsProvider'

        # Import the Provider's provisioning model
        try:
            module = importlib.import_module(provider_module)
        except ModuleNotFoundError as mnfe:
            # This is pretty much unrecoverable at this stage of development; make note and raise
            LOGGER.error("Provider provisioning mechanism '{}' not yet implemented or not found.".format(provider_name))
            raise ProviderNotImplemented(mnfe) from mnfe

        class_def = getattr(module, provider_classname)
        return class_def(self.boot_set, self.artifact_info)
