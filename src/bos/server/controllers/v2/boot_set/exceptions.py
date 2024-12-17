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


class BootSetError(Exception):
    """
    Generic error class for fatal problems found during boot set validation
    """


class BootSetWarning(Exception):
    """
    Generic error class for non-fatal problems found during boot set validation
    """


class NonImsImage(BootSetWarning):
    """
    Raised to indicate the boot set boot image is not from IMS
    """


class BootSetArchMismatch(BootSetError):

    def __init__(self, bs_arch: str, expected_ims_arch: str,
                 actual_ims_arch: str):
        super().__init__(
            f"Boot set arch '{bs_arch}' means IMS image arch should be "
            f"'{expected_ims_arch}', but actual IMS image arch is '{actual_ims_arch}'"
        )


class CannotValidateBootSetArch(BootSetWarning):

    def __init__(self, msg: str):
        super().__init__(f"Can't validate boot image arch: {msg}")
