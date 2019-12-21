#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""see https://setuptools.readthedocs.io/en/latest/setuptools.html."""


from setuptools import setup, find_packages
COPYRIGHT = """
Copyright (c) 2019 Wolfgang Rohdewald <wolfgang@rohdewald.de>
See LICENSE for details.
"""


def readall(path):
    """explicitly close the file again.

    Returns:
        The file content

    """
    with open(path) as in_file:
        return in_file.read()


version_data = readall('restaround/restaround.py')
version_line = [x for x in version_data.split('\n') if 'VERSION' in x][0].strip()
version = version_line.split('"')[1]

setup(
    name='restaround',
    version=version,
    setup_requires=['setuptools_scm'],
    description='A wrapper around restic',
    long_description=readall('README.rst'),
    url='https://github.com/wrohdewald/restaround',
    author='Wolfgang Rohdewald',
    author_email='wolfgang@rohdewald.de',
    license='GPLv2',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Communications',
        'Topic :: Internet :: WWW/HTTP',
    ],
    packages=find_packages(),
    install_requires=['pytest'],
    entry_points = {
        'console_scripts': ['restaround = restaround:exec_main']
    }
)
