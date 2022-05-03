# -*- coding: utf-8 -*-
import glob
import os
import shutil
from os.path import abspath, dirname, join, normpath

from setuptools import Command, find_packages, setup

here = normpath(abspath(dirname(__file__)))


class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""

    CLEAN_FILES = "./build ./dist ./*.pyc ./*.tgz ./*.egg-info ./__pycache__ ./*/__pycache__ */*/__pycache__".split(
        " "
    )

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        global here

        for path_spec in self.CLEAN_FILES:
            # Make paths absolute and relative to this path
            abs_paths = glob.glob(normpath(join(here, path_spec)))
            for path in [str(p) for p in abs_paths]:
                if not path.startswith(here):
                    # Die if path in CLEAN_FILES is absolute + outside this directory
                    raise ValueError("%s is not a path inside %s" % (path, here))
                print("removing %s" % os.path.relpath(path))
                shutil.rmtree(path)


cmdclass = {"clean": CleanCommand}

with open(os.path.join(os.path.dirname(__file__), "VERSION")) as version_file:
    version = version_file.read().strip()

setup(
    name="tcc_kiola_medication",
    version=version,
    author="AIT Austrian Institute of Technology GmbH",
    author_email="ehealth@ait.ac.at",
    packages=find_packages(),
    include_package_data=True,
    scripts=[],
    url="http://www.ait.ac.at/",
    license="LICENSE.txt",
    description="Class and functions for tcc_kiola_medication",
    long_description=open("README.txt").read(),
    install_requires=[],
    cmdclass=cmdclass,
)
