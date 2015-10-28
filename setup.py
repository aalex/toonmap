#!/usr/bin/env python
"""
installation script
"""
from distutils.core import setup
from toonloopwizard import __version__

setup(
    name="toonloopwizard",
    version=__version__,
    description="Assistant for launching Toonloop",
    author="Alexandre Quessy",
    author_email="alexandre@quessy.net",
    url="http://www.quessy.net",
    packages=["toonloopwizard"],
    scripts=["scripts/toonloop-wizard"]
    )

