# setuptools-based installation module for bos_session_template
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

from os import path
from setuptools import setup, find_packages


here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

with open(path.join(here, 'requirements_bos_session_template.txt'), encoding='utf-8') as f:
    install_requires = []
    for line in f.readlines():
        commentless_line = line.split('#', 1)[0].strip()
        if commentless_line:
            install_requires.append(commentless_line)

version = 1.0

setup(
    name='bos_session_template',
    version=version,
    description="BOS Session Template creation script",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://stash.us.cray.com/projects/SCMS/repos/bos',
    author='Cray, Inc.',
    license='Cray Proprietary',
    package_dir = {'': 'tools'},
    py_modules=['bos_session_template'],
    python_requires='>=3, <4',
    # Top-level dependencies are parsed from requirements.txt
    install_requires=install_requires,
    #scripts=['tools/bos_session_template.py'],
    # This makes setuptools generate our executable script automatically for us.
    entry_points={
        'console_scripts': [
#            'bos_session_template = bos_session_template.py:main'
            'bos_session_template = bos_session_template:main'
        ]
    },
)