#!/usr/bin/env python
"""
Setup file for installing GC3Pie.
"""

import sys


# see http://peak.telecommunity.com/DevCenter/setuptools
# for an explanation of the keywords and syntax of this file.
#
from ez_setup import use_setuptools
use_setuptools()

import setuptools
import setuptools.dist
# avoid setuptools including `.svn` directories into the PyPI package
from setuptools.command import sdist
if hasattr(sdist, 'finders'):
    del sdist.finders[:]


## auxiliary functions
#
def read_whole_file(path):
    with open(path, 'r') as stream:
        return stream.read()


## test runner setup
#
# See http://tox.readthedocs.org/en/latest/example/basic.html#integration-with-setuptools-distribute-test-commands # noqa
# on how to run tox when python setup.py test is run
#
from setuptools.command.test import test as TestCommand

class Tox(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import tox
        errno = tox.cmdline(self.test_args)
        sys.exit(errno)


## real setup description begins here
#
setuptools.setup(
    name="gc3pie",
    version="2.3.dev",  # see PEP 440

    packages=setuptools.find_packages(exclude=['ez_setup']),
    # metadata for upload to PyPI
    description=(
        "A Python library and simple command-line frontend for"
        " computational job submission to multiple resources."
    ),
    long_description=read_whole_file('README.txt'),
    author="S3IT, Zentrale Informatik, University of Zurich",
    author_email="gc3pie-dev@googlegroups.com",
    license="LGPL",
    keywords="grid arc globus sge gridengine ssh gamess rosetta batch job",
    url="http://gc3pie.googlecode.com/",  # project home page

    # see http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU Library or"
        " Lesser General Public License (LGPL)",
        "License :: DFSG approved",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: System :: Distributed Computing",
        ],

    entry_points={
        'console_scripts': [
            # the generic, catch-all script:
            'gc3utils = gc3utils.frontend:main',
            # entry points to specific subcommands:
            'gclean = gc3utils.frontend:main',
            'gget = gc3utils.frontend:main',
            'ginfo = gc3utils.frontend:main',
            'gkill = gc3utils.frontend:main',
            'gservers = gc3utils.frontend:main',
            'gresub = gc3utils.frontend:main',
            'gstat = gc3utils.frontend:main',
            'gsub = gc3utils.frontend:main',
            'gtail = gc3utils.frontend:main',
            'gsession = gc3utils.frontend:main',
            'gselect = gc3utils.frontend:main',
            'gcloud = gc3utils.frontend:main',
            ],
    },

    # run-time dependencies
    install_requires=[
        # paramiko and pycrypto are required for SSH operations
        'paramiko',
        'pycrypto',
        # prettytable -- format tabular text output
        'prettytable',
        # pyCLI -- object-oriented command-line app programming
        'pyCLI',
        # Needed by SqlStore
        # 0.7.9 is the latest version with Python2.4 support
        'sqlalchemy',
        # Needed for parsing human-readable dates (gselect uses it).
        'parsedatetime',
        # needed by DependentTaskCollection
        # (but incompatible with Py 2.6, so we include a patched copy)
        #'toposort==1.0',
        ],
    extras_require = {
        'openstack': [
            'python-novaclient',
        ],
        'ec2': [
            'boto',
        ],
        'optimizer': [
            # needed by Benjamin's DE optimizer code
            'numpy',
        ],
    },
    # Apparently, this list is read from right to left...
    tests_require=[
        'tox'
    ],
    cmdclass={'test': Tox},
    # additional non-Python files to be bundled in the package
    package_data={
        'gc3libs': [
            'etc/codeml.pl',
            'etc/gc3pie.conf.example',
            'etc/geotop_wrap.sh',
            'etc/logging.conf.example',
            'etc/rosetta.sh',
            ],
    },
    data_files=[
        ('gc3apps', [
            'gc3apps/gc3.uzh.ch/gridrun.py',
            'gc3apps/zods/gzods.py',
            'gc3apps/geotop/ggeotop.py',
            'gc3apps/geotop/ggeotop_utils.py',
            'gc3apps/geotop/gtsub_control.py',
            'gc3apps/ieu.uzh.ch/gmhc_coev.py',
            'gc3apps/ieu.uzh.ch/gbiointeract.py',
            'gc3apps/turbomole/gricomp.py',
            'gc3apps/rosetta/gdocking.py',
            'gc3apps/rosetta/grosetta.py',
            'gc3apps/lacal.epfl.ch/gcrypto.py',
            'gc3apps/codeml/gcodeml.py',
            'gc3apps/gamess/grundb.py',
            'gc3apps/gamess/ggamess.py',
            ]),
    ],
    # `zip_safe` can ease deployment, but is only allowed if the package
    # do *not* do any __file__/__path__ magic nor do they access package data
    # files by file name (use `pkg_resources` instead).
    zip_safe=True,
)
