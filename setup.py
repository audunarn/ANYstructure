"""A setuptools based setup module.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
    name='ANYstructure',  # Required
    url = 'https://github.com/audunarn/ANYstructure',
    entry_points={'gui_scripts': ['run_me = ANYstructure.__main__:main']},
    version='0.1.17',  # Required
    description='A offshore structure plate field optimization tool',  # Required
    author='Audun Arnesen Nyhus',  # Optional
    author_email='audunarn@gmail.com',  # Optional
    classifiers=[  # Optional
        'Development Status :: 3 - Alpha',
        'Environment :: X11 Applications',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.6',
        'Topic :: Scientific/Engineering'],
    keywords='dnv-gl-os-c101 naval_architecture',  # Optional
    include_package_data=True,
    packages=['ANYstructure'],  # Required
)