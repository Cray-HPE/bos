#
# MIT License
#
# (C) Copyright 2021-2022, 2024 Hewlett Packard Enterprise Development LP
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
import logging

from .base import BaseBosEndpoint
from .options import options

LOGGER = logging.getLogger('bos.operators.utils.clients.bos.components')


class ComponentEndpoint(BaseBosEndpoint):
    ENDPOINT = __name__.lower().rsplit('.', maxsplit=1)[-1]

    def get_component(self, component_id):
        return self.get_item(component_id)

    def get_components(self, **kwargs):
        page_size=options.max_component_batch_size
        next_page=self.get_items(page_size=page_size, **kwargs)
        results=next_page
        while next_page:
            last_id=next_page[-1]["id"]
            next_page=self.get_items(page_size=page_size, start_after_id=last_id, **kwargs)
            results.extend(next_page)
        return results

    def update_component(self, component_id, data):
        return self.update_item(component_id, data)

    def update_components(self, data):
        return self.update_items(data)

    def put_components(self, data):
        return self.put_items(data)
