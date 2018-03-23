import sys
import logging
from bin import datastore_pycsw
from paste import script

log = logging.getLogger(__name__)

class Pycsw(script.command.Command):
    """
    Manages the CKAN datastore-pycsw integration

    datastore-pycsw setup [-p]
        Setups the necessary pycsw table on the db.

    datastore-pycsw load [-p] [-u]
        Loads CKAN datasets as records into the pycsw db.

    datastore-pycsw clear [-p]
        Removes all records from the pycsw table.

    All commands require the pycsw configuration file. By default it will try
    to find a file called 'default.cfg' in the same directory, but you'll
    probably need to provide the actual location with the -p option.

    paster datastore-pycsw setup -p /etc/ckan/default/pycsw.cfg

    The load command requires a CKAN URL from where the datasets will be pulled.
    By default it is set to 'http://localhost', but you can define it with the -u
    option:

    paster datastore-pycsw load -p /etc/ckan/default/pycsw.cfg -u http://ckan.instance.org
    """

    parser = script.command.Command.standard_parser(verbose=True)
    parser.add_option('-p', '--pycsw-config', dest='pycsw_config',
            default='default.cfg', help='pycsw config file to use.')
    parser.add_option('-u', '--ckan-url', dest='ckan_url',
            default='http://localhost', help='CKAN instance to import the datasets from.')

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2
    min_args = 0

    def command(self):
        if len(self.args) == 0:
            self.parser.print_usage()
            sys.exit(1)

        config = datastore_pycsw._load_config(self.options.pycsw_config)
        cmd = self.args[0]
        if cmd == 'setup':
            datastore_pycsw.setup_db(config)
        elif cmd == 'load':
            ckan_url = self.options.ckan_url.rstrip('/') + '/'
            datastore_pycsw.load(config, ckan_url)
        elif cmd == 'clear':
            datastore_pycsw.clear_db(config)
        else:
            print 'Command %s not recognized' % cmd