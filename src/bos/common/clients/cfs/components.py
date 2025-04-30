#
# MIT License
#
# (C) Copyright 2021-2025 Hewlett Packard Enterprise Development LP
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
from collections import defaultdict
import logging
from typing import cast

from bos.common.clients.endpoints import BaseEndpoint
from bos.common.types.components import ComponentRecord as BosComponentRecord
from bos.common.types.general import JsonDict
from bos.common.utils import PROTOCOL

from .types import CfsComponentData, CfsGetComponentsPagedResponse, CfsComponentsUpdate

LOGGER = logging.getLogger(__name__)

SERVICE_NAME = 'cray-cfs-api'
BASE_CFS_ENDPOINT = f"{PROTOCOL}://{SERVICE_NAME}/v3"

GET_BATCH_SIZE = 200
PATCH_BATCH_SIZE = 1000

class ComponentEndpoint(BaseEndpoint):
    """
    This class provides access to the CFS API for the /v3/components endpoint, for GET and PATCH.
    Because it is limited to a single endpoint, no CFS base classes are implemented.
    """
    BASE_ENDPOINT = BASE_CFS_ENDPOINT
    ENDPOINT = 'components'

    def get_components(self, ids: str|None=None) -> list[CfsComponentData]:
        """
        If 'ids' is not specified, query CFS for all components.
        Otherwise, only query for the specified components.
        """
        kwargs: JsonDict | None = {} if ids is None else { "ids": ids }
        item_list: list[CfsComponentData] = []
        while kwargs is not None:
            response_json = cast(CfsGetComponentsPagedResponse, super().get(params=kwargs))
            new_items = cast(list[CfsComponentData], response_json.get("components", []))
            LOGGER.debug("Query returned %d components", len(new_items))
            item_list.extend(new_items)
            kwargs = response_json.get("next")
        LOGGER.debug("Returning %d components from CFS", len(item_list))
        return item_list

    def get_components_from_id_list(self, id_list: list[str]) -> list[CfsComponentData]:
        if not id_list:
            LOGGER.warning(
                "get_components_from_id_list called without IDs; returning without action."
            )
            return []
        LOGGER.debug("get_components_from_id_list called with %d IDs",
                     len(id_list))
        component_list = []
        while id_list:
            next_batch = id_list[:GET_BATCH_SIZE]
            next_comps = self.get_components(ids=','.join(next_batch))
            component_list.extend(next_comps)
            id_list = id_list[GET_BATCH_SIZE:]
        LOGGER.debug(
            "get_components_from_id_list returning a total of %d components from CFS",
            len(component_list))
        return component_list

    def patch_desired_config(self,
                             node_ids: list[str],
                             desired_config: str,
                             enabled: bool = False,
                             tags: dict[str, str]|None = None,
                             clear_state: bool = False) -> None:
        if not node_ids:
            LOGGER.warning(
                "patch_desired_config called without IDs; returning without action."
            )
            return
        LOGGER.debug(
            "patch_desired_config called on %d IDs with desired_config=%s enabled=%s tags=%s"
            " clear_state=%s", len(node_ids), desired_config, enabled, tags,
            clear_state)
        node_patch: CfsComponentData = {
            'enabled': enabled,
            'desired_config': desired_config,
            'tags': tags if tags else {}
        }
        if clear_state:
            node_patch['state'] = []
        data: CfsComponentsUpdate = {"patch": node_patch, "filters": {}}
        while node_ids:
            data["filters"]["ids"] = ','.join(node_ids[:PATCH_BATCH_SIZE])
            self.patch(json=data)
            node_ids = node_ids[PATCH_BATCH_SIZE:]

    def set_cfs(self, components: list[BosComponentRecord], enabled: bool,
                clear_state: bool = False) -> None:
        if not components:
            LOGGER.warning(
                "set_cfs called without components; returning without action.")
            return
        LOGGER.debug(
            "set_cfs called on %d components with enabled=%s clear_state=%s",
            len(components), enabled, clear_state)
        configurations = defaultdict(list)
        for component in components:
            config_name = component.get('desired_state',
                                        {}).get('configuration', '')
            bos_session = component.get('session', '')
            key = (config_name, bos_session)
            configurations[key].append(component['id'])
        for key, ids in configurations.items():
            config_name, bos_session = key
            self.patch_desired_config(ids,
                                      config_name,
                                      enabled=enabled,
                                      tags={'bos_session': bos_session},
                                      clear_state=clear_state)
