import os, sys, re, io
import argparse
import requests
import logging
import datetime
import pycsw.config
import pycsw.admin
from lxml import etree
from pycsw import util, repository, metadata
from ConfigParser import SafeConfigParser

logging.basicConfig(format='%(message)s', level=logging.INFO)
log = logging.getLogger(__name__)

def setup_db(pycsw_config):
    """
    Lifted from ckanext-spatial/bin/ckan_pycsw.py
    Initializes a PyCSW database in an empty database.

    @param pycsw_config: pycsw.cfg file that should have been configured upon installing
    PyCSW.  Should contain auth information about the database to connect to.
    """
    from sqlalchemy import Column, Text
    database = pycsw_config.get('repository', 'database')
    table_name = pycsw_config.get('repository', 'table', 'records')
    ckan_columns = [
        Column('ckan_id', Text, index=True),
        Column('ckan_modified', Text),
    ]
    pycsw.admin.setup_db(database,
        table_name, '',
        create_plpythonu_functions=False,
        extra_columns=ckan_columns)

def clear_db(pycsw_config):
    """
    Lifted from ckanext-spatial/bin/ckan_pycsw.py
    Clears a PyCSW database, but does not delete the database itself.

    @param pycsw_config: pycsw.cfg file that should have been configured upon installing
    PyCSW.  Should contain auth information about the database to connect to.
    """
    from sqlalchemy import create_engine, MetaData, Table
    database = pycsw_config.get('repository', 'database')
    table_name = pycsw_config.get('repository', 'table', 'record')
    log.debug('Creating engine')
    engine = create_engine(database)
    records = Table(table_name, MetaData(engine))
    records.delete().execute()
    log.info('Table cleared')

def load(pycsw_config, ckan_url):
    """
    Take ISO 19139 XML data from a CKAN package and insert it into the PyCSW database.  This function
    runs selectively, meaning that it will only return packages for resources in the CKAN datastore
    database.  It builds a URL for querying the datastore, returns a list of the datastore resource IDs,
    builds URLs for querying the resources, runs a regular expression to determine what the
    package ID of a datastored resource is, builds a URL to scrape each package's ISO XML record and then
    inserts the XML as a record in the PyCSW database.

    @param pycsw_config: pycsw.cfg file that should have been configured upon installing
    PyCSW.  Should contain auth information about the database to connect to.
    @param ckan_url: e.g http://127.0.0.1:5000
    """

    def parse_datastore(ckan_url):
        """
        Scrape and return every resource ID in the datastore database, accessing the information through
        CKAN's REST API.

        @param ckan_url: e.g. http://127.0.0.1:5000
        @return: a list of datastored resource object IDs
        """
        api_query = 'api/3/action/datastore_search?resource_id=_table_metadata'
        ignore_names = ['_table_metadata', 'geography_columns', 'geometry_columns', 'spatial_ref_sys']
        url = ckan_url + api_query
        response = requests.get(url)
        listing = response.json()
        if not isinstance(listing, dict):
            raise RuntimeError, 'Wrong API response: %s' % listing
        results = listing['result']['records']
        resource_names = []
        # Should use a list/dict comprehension here
        for result in results:
            if not result['name'] in ignore_names:
                resource_names.append(result['name'])
        return resource_names

    def parse_resource(resource_id, ckan_url):
        """
        CKAN's search API doesn't allow querying packages by their resources.  Thankfully,
        each resource is returned with a URL which contains the package id between the
        paths "dataset" and "resource", (at least for datastore items) so we can use a RegEx
        to figure out what the package of a resource is.  This is not an ideal solution, but
        it's the cleanest way to solve the problem until the CKAN team decides to organize
        their data in a less authoritative manner.

        @param resource_id: the id of a datastored resource object
        @param ckan_url: http://127.0.0.1:5000
        """
        api_query = 'api/3/action/resource_show?id=%s' % resource_id
        url = ckan_url + api_query
        response = requests.get(url)
        listing = response.json()
        if not isinstance(listing, dict):
            raise RuntimeError, 'Wrong API response: %s' % listing
        # skip Authorization Error, most likely due to deleted packages.
        if 'error' in listing:
            if ("Not Found Error" == listing['error']['__type']) or ("Authorization Error" == listing['error']['__type']):
                return None
        log.info('listing is %r' % listing )
        if listing['result']:
            package_url = listing['result']['url']
        else:
            return None

        # Here's that RegEx.  Ugh.
        package_id = re.findall('dataset/(.*?)/resource', package_url, re.DOTALL)
        if package_id:
            return package_id[0]
        else:
            return None

    def get_record(context, repo, ckan_url, ckan_id, ckan_info):
        """
        Hit the CKAN REST API for an ISO 19139 XML representation of a package with data
        uploaded into the datastore.

        @param context: Vanilla-CKAN auth noise
        @param repo: PyCSW repository (database)
        @param ckan_url: e.g. http://127.0.0.1:5000
        @param ckan_id: Package ID
        @param ckan_info: Package data
        @return: ISO 19139 XML data
        """
        query = ckan_url + 'package_iso/object/%s'
        url = query % ckan_info['id']
        response = requests.get(url)
        try:
            xml = etree.parse(io.BytesIO(response.content))
        except Exception, err:
            log.error('Could not pass xml doc from %s, Error: %s' % (ckan_id, err))
            return
        try:
            record = metadata.parse_record(context, xml, repo)[0]
        except Exception, err:
            log.error('Could not extract metadata from %s, Error: %s' % (ckan_id, err))
            return
        return record


    # Now that we've defined the local functions, let's actually run the parent function
    database = pycsw_config.get('repository', 'database')
    table_name = pycsw_config.get('repository', 'table', 'records')

    context = pycsw.config.StaticContext()
    repo = repository.Repository(database, context, table=table_name)

    log.info('Started gathering CKAN datasets identifiers: {0}'.format(str(datetime.datetime.now())))

    gathered_records = {}

    results = parse_datastore(ckan_url)
    package_ids = []
    for result in results:
        package_id = parse_resource(result, ckan_url)
        if not package_id in package_ids:
            package_ids.append(package_id)

    for id in package_ids:
        api_query = 'api/3/action/package_show?id=%s' % id
        url = ckan_url + api_query
        response = requests.get(url)
        listing = response.json()
        if not isinstance(listing, dict):
            raise RuntimeError, 'Wrong API response: %s' % listing
        # skip Not Found Error, most likely due to deleted packages.
        if 'error' in listing \
            and "Not Found Error" == listing['error']['__type']:
            continue
        result = listing['result']
        gathered_records[result['id']] = {
            'metadata_modified': result['metadata_modified'],
            'id': result['id'],
        }


    log.info('Gather finished ({0} datasets): {1}'.format(
        len(gathered_records.keys()),
        str(datetime.datetime.now())
    ))

    existing_records = {}
    skipped_records = {}

    query = repo.session.query(repo.dataset.ckan_id, repo.dataset.ckan_modified, repo.dataset.type)
    for row in query:
        existing_records[row[0]] = row[1]
        # skip records loaded by pycsw
        # TODO is empty type an valid criteria?
        if row[2]:
            skipped_records[row[0]] = row[1]
    repo.session.close()

    new = set(gathered_records) - set(existing_records)
    deleted = set(existing_records) - set(skipped_records) - set(gathered_records)
    changed = set()

    for key in set(gathered_records) & (set(existing_records) - set(skipped_records)):
        if gathered_records[key]['metadata_modified'] > existing_records[key]:
            changed.add(key)

    for ckan_id in deleted:
        try:
            repo.session.begin()
            repo.session.query(repo.dataset.ckan_id).filter_by(
                ckan_id = ckan_id
            ).delete()
            log.info('Deleted %s' % ckan_id)
            repo.session.commit()
        except Exception, err:
            repo.session.rollback()
            raise

    for ckan_id in new:
        ckan_info = gathered_records[ckan_id]
        record = get_record(context, repo, ckan_url, ckan_id, ckan_info)
        if not record:
            log.info('Skipped record %s' % ckan_id)
            continue
        try:
            repo.insert(record, 'local', util.get_today_and_now())
            log.info('Inserted %s' % ckan_id)
        except Exception, err:
            log.error('ERROR: not inserted %s Error:%s' % (ckan_id, err))

    for ckan_id in changed:
        ckan_info = gathered_records[ckan_id]
        record = get_record(context, repo, ckan_url, ckan_id, ckan_info)
        if not record:
            continue
        update_dict = dict([(getattr(repo.dataset, key), getattr(record, key))
                            for key in record.__dict__.keys() if key != '_sa_instance_state'])

        try:
            repo.session.begin()
            repo.session.query(repo.dataset).filter_by(
                ckan_id = ckan_id
            ).update(update_dict)
            repo.session.commit()
            log.info('Changed %s' % ckan_id)
        except Exception, err:
            repo.session.rollback()
            raise RuntimeError, 'ERROR: %s' % str(err)

def _load_config(file_path):
    """
    Lifted from ckanext-spatial/bin/ckan_pycsw.py
    Loads the PyCSW configuration file.

    @param file_path: location of configuration file in the file system
    @return: configuration object
    """
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        raise AssertionError('pycsw config file {0} does not exist.'.format(abs_path))
    config = SafeConfigParser()
    config.read(abs_path)
    return config


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-p', '--pycsw_config',
                        action = 'store', default = 'default.cfg',
                        help = 'pycsw config file to use.')

    parser.add_argument('-u', '--ckan_url',
                        action = 'store',
                        help = 'CKAN instance to import the datasets from.')

    if len(sys.argv) <= 1:
        parser.print_usage()
        sys.exit(1)

    arg = parser.parse_args()
    pycsw_config = _load_config(arg.pycsw_config)

    if arg.command == 'setup':
        setup_db(pycsw_config)
    elif arg.command == 'load':
        load(pycsw_config, ckan_url)
    elif arg.command == 'clear':
        clear_db(pycsw_config)
    else:
        print 'Unknown command {0}'.format(arg.command)
        sys.exit(1)
