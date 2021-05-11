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
import six

from bos.models.base_model_ import Model
from bos.models.generic_metadata import GenericMetadata
from bos.encoder import JSONEncoder


class MetadataEncoder(JSONEncoder):
    include_nulls = False

    def converter_metadata(self, metadata):
        dikt = {}
        if hasattr(metadata, 'start_time'):
            dikt['start_time'] = metadata.start_time
        if hasattr(metadata, 'stop_time'):
            dikt['stop_time'] = metadata.stop_time
        if hasattr(metadata, 'complete'):
            dikt['complete'] = metadata.complete
        if hasattr(metadata, 'in_progress'):
            dikt['in_progress'] = metadata.in_progress
        if hasattr(metadata, 'error_count'):
            dikt['error_count'] = metadata.error_count
        if hasattr(metadata, 'errors'):
            dikt['errors'] = metadata.errors
        return GenericMetadata(**dikt)

    def default(self, o):
        """
        This replaces the GenericMetadata class that is not JSON-serializable
        with a dictionary that is. It takes properties and turns them
        into values in the dictionary.
        """
        if isinstance(o, Model):
            for attr, _type in six.iteritems(o.openapi_types):
                if _type == GenericMetadata:
                    value = getattr(o, attr)
                    attribute = o.attribute_map[attr]
                    setattr(o, attribute, self.converter_metadata(value))
        return super().default(o)
