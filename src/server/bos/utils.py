# Copyright 2019, Cray Inc.  All Rights Reserved.
import re


def _canonize_xname(xname):
    """Ensure the xname is canonical.
    * Its components should be lowercase.
    * Any leading zeros should be stripped off.

    :param xname: xname to canonize
    :type xname: string

    :return: canonized xname
    :rtype: string
    """
    return re.sub(r'x0*(\d+)c0*(\d+)s0*(\d+)b0*(\d+)n0*(\d+)', r'x\1c\2s\3b\4n\5', xname.lower())
