# -*- coding: utf-8 -*-

import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = (
    open(os.path.join(here, 'README.md')).read()
)

install_requires = [
    "bashcolor",
    "Jinja2",
]

setup_requires = [
]

tests_require = install_requires + [
]

setup(
    name="metatask",
    version="1.0.1",
    description="A tool and library to run task or moves on many files",
    long_description=README,
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    author="Stéphane Brunner",
    author_email="stephane.brunner@gmail.com",
    url="https://github.com/sbrunner/metatask/",
    packages=find_packages(exclude=["*.tests", "*.tests.*"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    entry_points={
        "console_scripts": [
            "metatask = metatask:main",
        ],
    }
)
