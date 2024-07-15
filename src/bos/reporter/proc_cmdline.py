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
"""
This module provides a function for parsing the /proc/cmdline special file.
"""


def proc_cmdline():
    """
    This generator yields key value pairs from a node's /proc/cmdline file in
    the order they appear.

    Emits both tuples and strings.

    Raises:
      OSError if it cannot open /proc/cmdline
    """
    with open('/proc/cmdline', 'r') as procfile:
        boot_options = procfile.read().strip().split(' ')
        for entry in boot_options:
            try:
                yield entry.split('=')
            except IndexError:
                yield entry


def get_value_from_proc_cmdline(key):
    """
    Attempts to read the value of a key from /proc/cmdline and return it.
    The key is assumed to have a value associated with it.

    If the key is not found, raise a KeyError exception.
    """
    for entry in proc_cmdline():
        try:
            ekey, value = entry
            if ekey == key:
                return value
        except ValueError:
            # Single string values are not interesting to us
            continue
    raise KeyError(f"Key '{key}' was not discovered on '/proc/cmdline'")
