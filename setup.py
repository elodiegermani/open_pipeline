#!/usr/bin/python
# coding: utf-8

"""
Allow the project to be installed as a local package, using :
    python -m pip install .
    or
    python -m pip install -e .
The -e option stands for editable, which allows to change the
source code of the package without having to reinstall it. Using this option
will add the current directory (.) to the system path.
"""

from setuptools import setup, find_packages

requires = [
    'importlib_resources>=5.10.2,<5.11',
    'tomli>=2.0.1,<2.1',
    'networkx>=2.0,<3.0', # a workaround to nipype's bug (issue 3530)
    'nilearn>=0.10.0,<0.11',
    'nipype>=1.8.6,<1.9',
    'pandas>=1.5.2,<1.6',
    'niflow-nipype1-workflows>=0.0.5,<0.1.0'
]
extras_require = {
    'tests': [
        'pathvalidate>=3.2.0,<3.3',
        'pylint>=3.0.3,<3.1',
        'pytest>=7.2.0,<7.3',
        'pytest-cov>=2.10.1,<2.11',
        'pytest-helpers-namespace>=2021.12.29,<2021.13',
        'pytest-mock>=3.12.0,<3.13',
        'checksumdir>=1.2.0,<1.3'
        ]
}

setup(
    name = 'narps_open',
    version = '0.1.0',
    description = 'The NARPS open pipelines project :\
    a codebase reproducing the 70 pipelines of the NARPS study (Botvinik-Nezer et al., 2020).',
    long_description = 'file: README.md',
    long_description_content_type = 'text/markdown',
    author = '',
    author_email = '',
    url = 'https://github.com/Inria-Empenn/narps_open_pipelines',

    include_package_data = True,
    python_requires = '>=3.8,<3.12',
    install_requires = requires,
    extras_require = extras_require,
    classifiers = [
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8'
    ],
    project_urls = {
        'Bug Tracker': 'https://github.com/Inria-Empenn/narps_open_pipelines/issues',
        'Source': 'https://github.com/Inria-Empenn/narps_open_pipelines',
    },
    packages = find_packages(exclude=('tests', 'examples')),
    data_files = [
        ('narps_open/utils/configuration', ['narps_open/utils/configuration/default_config.toml']),
        ('narps_open/utils/configuration', ['narps_open/utils/configuration/testing_config.toml']),
        ('narps_open/data/description', ['narps_open/data/description/analysis_pipelines_comments.tsv']),
        ('narps_open/data/description', ['narps_open/data/description/analysis_pipelines_derived_descriptions.tsv']),
        ('narps_open/data/description', ['narps_open/data/description/analysis_pipelines_full_descriptions.tsv'])
    ],
    entry_points = {
        'console_scripts': [
            'narps_open_runner = narps_open.runner:main',
            'narps_open_exporter = narps_open.utils.export.__main__:main',
            'narps_open_tester = narps_open.tester:main',
            'narps_open_status = narps_open.utils.status:main',
            'narps_open_correlations = narps_open.utils.correlation.__main__:main',
            'narps_description = narps_open.data.description.__main__:main',
            'narps_results = narps_open.data.results.__main__:main'
        ]
    }
)
