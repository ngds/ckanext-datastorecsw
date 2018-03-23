from setuptools import setup, find_packages
import sys, os

version = '0.0.1'

setup(
    name='ckanext-datastorecsw',
    version=version,
    description="PyCSW interface for CKAN Datastore, ported a lot of code from ckanext-spatial",
    long_description='''
    ''',
    classifiers=[],
    keywords='',
    author='Arizona Geological Survey',
    author_email='adrian.sonnenschein@azgs.az.gov',
    url='http://geothermaldata.org',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.csw'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
    entry_points=\
    """
    [ckan.plugins]
    datastorecsw=ckanext.csw.plugin:DatastoreCSW
    [paste.paster_command]
    datastore-pycsw=ckanext.csw.commands.csw:Pycsw
    """,
)