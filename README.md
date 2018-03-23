ckanext-datastorecsw
====================
PyCSW support for resources uploaded into the CKAN datastore.

The [ckanext-spatial](https://github.com/ckan/ckanext-spatial/) extension has support for transferring metadata records
harvested from an external CSW into a local PyCSW database, but lacks support for transferring metadata created within
CKAN into a local PyCSW database.  This extension does two main things:

1. Generates ISO 19139 XML metadata records for CKAN packages which contain resources uploaded into the CKAN datastore 
and makes them available through CKAN's REST API.
2. Interfaces with PyCSW through a command line interface to create/delete/load ISO XML generated from CKAN packages 
which contain datastored resources into the PyCSW database.

Note - The REST API extension will generate ISO 19139 XML metadata records for all CKAN packages.  This ensures that 
all CKAN packages have a service point where users can access ISO 19139 XML records for every piece of data in the 
system.  The command line interface will only load CKAN packages which contain datastore objects into the PyCSW 
database.  Developers looking to load harvested metadata into PyCSW should use 
[ckanext-spatial](https://github.com/ckan/ckanext-spatial/).

####Dependencies
* CKAN >= v2.0 with datastore extension enabled
* PyCSW >= v1.8.0

Although it's not required, you should probably also have either the `datapusher` or `datastorer` extension installed
and enabled.  These extensions are used for uploading data into the datastore.

####Installation
```
# Download extension and enter directory
git clone https://github.com/ngds/ckanext-datastorecsw.git
cd ckanext-datastorecsw
pip install -r requirements.txt

# If you're installing for production
python setup.py build
python setup.py install

# If you're installing for development
python setup.py develop

# Enable extension by adding plugin to ckan.plugins
nano ../path/to/ckan/configuration.ini
ckan.plugins = ... ... datastore datastorecsw
```

####REST API
ISO 19139 metadata for a CKAN package can be found here:
```
http://ckan.instance.org/package_iso/object/:id
```
Where `:id` is the alpha-numeric id of a CKAN package.

####Command Line Interface
```
Usage: paster datastore-pycsw [options]

# Setup PyCSW table in the database
datastore-pycsw setup [-p]
ex: paster datastore-pycsw setup -p src/ckan/pycsw.cfg

# Remove all records from the PyCSW table
datastore-pycsw clear [-p]
ex: paster datastore-pycsw setup -p src/ckan/pycsw.cfg

# Load datasets into the PyCSW database
datastore-pycsw load [-p] [-u]
ex: paster datastore-pycsw load -p src/ckan/pycsw.cfg -u http://ckan.instance.org
```

####Tests
Make sure to update the `ckanext-datastorecsw/test.ini` configuration before running any tests.  Either point it to
inherit your main CKAN configuration file or create a new one.  Note that the CKAN and datastore databases will be 
wiped clean if the tests are run with the main CKAN configuration file.
```
# Run tests
cd ckanext-datastorecsw
nosetests --ckan --with-pylons=test.ini tests
```
