#!/usr/bin/env python3
#
# MIT License
#
# (C) Copyright 2024-2025 Hewlett Packard Enterprise Development LP
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
Starting in CSM 1.6, BOS is enforcing many API restrictions for the first time.
When migrating to this BOS version, this tool will attempt to clean up the BOS
data so that it complies with the spec (like modifying boot sets so that
rootfs_providers mapping to empty strings instead are not included in the boot set).
It will only delete BOS resources in two cases:

1. Cases where ID fields are in violation. For example, if a
session template has an invalid name. The reason this is deleted is because
that template would be inaccessible using the API or CLI, since incoming
requests would be rejected for not following the spec. For session templates
specifically, however, an attempt will be made to modify the name to comply
with the requirements. Only if that fails will the template be deleted.

2. Cases where the ID fields inside the data structure conflicts with the
database key. That is, if generating the DB key based on the fields in the
actual data result in a different database key than the one used to look it up.
This is not something that is likely to happen, but given the lack of spec
enforcement that existed in the past, we can't rule it out. In this case,
for session templates, if the expected database key is not in use, then
the resource will be moved to the expected key. Otherwise, or for
non-session templates, it will be deleted.

The CSM upgrade code for 1.6 has been modified to include a BOS backup
before the BOS service is updated. In addition, this migration tool will
log all data that is deleted. And the migration pod has been modified
so that it stays around for much longer after completing.
"""

import logging
import sys

from bos.common.values import LOG_FORMAT

from .db import COMP_DB, SESS_DB, TEMP_DB, all_db_ready
from .sanitize import sanitize_component, sanitize_session, sanitize_session_template

LOGGER = logging.getLogger(__name__)


def main() -> None:
    if not all_db_ready():
        LOGGER.error("Not all BOS databases are ready")
        sys.exit(1)

    LOGGER.info("Sanitizing session templates")
    for key, data in TEMP_DB.get_all_as_raw_dict().items():
        sanitize_session_template(key, data)
    LOGGER.info("Done sanitizing session templates")

    LOGGER.info("Sanitizing sessions")
    for key, data in SESS_DB.get_all_as_raw_dict().items():
        sanitize_session(key, data)
    LOGGER.info("Done sanitizing sessions")

    LOGGER.info("Sanitizing components")
    for key, data in COMP_DB.get_all_as_raw_dict().items():
        sanitize_component(key, data)
    LOGGER.info("Done sanitizing components")


if __name__ == "__main__":
    log_level = logging.getLevelName('INFO')
    logging.basicConfig(level=log_level, format=LOG_FORMAT)

    LOGGER.info("Beginning post-upgrade BOS data migration")
    main()
    LOGGER.info("Completed post-upgrade BOS data migration")
