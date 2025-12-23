from setuptools import setup, find_packages

setup(
    name='pylode',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'rdflib',
        'jinja2',
        'markdown'
    ],
    entry_points='''
        [console_scripts]
        pylode=pylode.cli:main
    ''',
)
