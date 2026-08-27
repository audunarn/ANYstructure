"""A setuptools based setup module.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import find_namespace_packages, setup
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out...

def readme():
    with open(path.join(here, 'README.md'), encoding='utf-8') as file:
        return file.read()

core_requires = [
    'ANY3dView[gpu]>=0.5.4,<0.6',
    'ANYbuckling>=0.1.1,<0.2',
    'ANYfileio[semantics]>=0.2.1,<0.3',
    'ANYgeometry>=0.4.1,<0.5',
    'ANYmaterial>=0.1.1,<0.2',
    'ANYmesher>=0.3.2,<0.4',
    'ANYsolver>=0.4.0,<0.5',
    'ANYtk3D>=0.5.3,<0.6',
    'matplotlib',
    'meshio',
    'numpy',
    'numpy-stl',
    'Pillow',
    'reportlab',
    'scipy',
]
excel_requires = ['xlwings']
ml_requires = ['scikit-learn']
dev_requires = ['build', 'pytest']

setup(
    name='ANYstructure',  # Required
    url = 'https://github.com/audunarn/ANYstructure',
    entry_points={"console_scripts": ['ANYstructure = anystruct.__main__:main']},
    version='6.3.1',  # Required
    license='GPL-3.0-or-later',
    python_requires='>=3.13',
    description='A plate field optimization tool for offshore structures calculated according to DNV standards',
    long_description = readme(),
    long_description_content_type='text/markdown',
    author='Audun Arnesen Nyhus',  # Optional
    author_email='audunarn@gmail.com',  # Optional
    classifiers=[  # Optional
        'Development Status :: 5 - Production/Stable',
        'Environment :: X11 Applications',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
        'Topic :: Scientific/Engineering'],
    keywords='dnv-gl-os-c101 dnv-rp-c202 dnv-rp-c201 naval_architecture structural_engineering steel buckling fatigue local_scantlings optimization weight',
    include_package_data=True,
    install_requires=core_requires + excel_requires + ml_requires,
    extras_require={
        'core': core_requires,
        'excel': excel_requires,
        'ml': ml_requires,
        'dev': dev_requires,
        'all': core_requires + excel_requires + ml_requires,
    },
    packages=find_namespace_packages(include=['anystruct', 'anystruct.*'], exclude=['anystruct.calc_structure_classes*']),
    py_modules = [],
)
