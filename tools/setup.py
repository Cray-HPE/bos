# setuptools-based installation module for bos_session_template
# Copyright 2020 Cray Inc. All Rights Reserved

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