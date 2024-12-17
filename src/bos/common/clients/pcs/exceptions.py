#
# MIT License
#
# (C) Copyright 2023-2024 Hewlett Packard Enterprise Development LP
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


class PowerControlException(Exception):
    """
    Interaction with PCS resulted in a known failure.
    """


class PowerControlSyntaxException(Exception):
    """
    A class of error raised when interacting with PCS in an unsupported way.
    """


class PowerControlTimeoutException(PowerControlException):
    """
    Raised when a call to PowerControl exceeded total time to complete.
    """


class PowerControlComponentsEmptyException(Exception):
    """
    Raised when one of the PCS utility functions that requires a non-empty
    list of components is passed an empty component list. This will only
    happen in the case of a programming bug.

    This exception is not raised for functions that require a node list
    but that are able to return a sensible object to the caller that
    indicates nothing has been done. For example, the status function.
    This exception is instead used for functions that will fail if they run
    with an empty node list, but which cannot return an appropriate
    "no-op" value to the caller.
    """
