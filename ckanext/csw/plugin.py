import ckan.plugins as p
import ckan.model as model
import ckanext.csw.logic.action as action


class DatastoreCSW(p.SingletonPlugin):
    """
    Entry point to the 'datastorecsw' extension.  All of the PyCSW logic is done
    through a CLI, so this object is not aware of those commands.  This object solely
    exists for generating ISO 19139 XML records out of CKAN packages and routing them
    through CKAN's REST API.
    """
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IResourceUrlChange)

    # Program crashes without this empty function...
    def configure(self, config):
        return

    # Tell the object where we keep our Jinja templates
    def update_config(self, config):
        templates = 'templates'
        p.toolkit.add_template_directory(config, templates)

    # Set a controller/route for generating ISO XML pages
    def before_map(self, map):
        controller = 'ckanext.csw.controllers.view:ViewController'
        map.connect('datastore_package_show', '/package_iso/object/:id',
                    controller=controller, action='show_object')
        return map

    # Add this extension's actions to the CKAN Action API
    def get_actions(self):
        return {
            'iso_metadata': action.iso_metadata,
        }

    # We don't really need auth functions for actions because we want everyone to
    # be able to view the ISO records
    def get_auth_functions(self):
        return {}

    # Lifted this function from ckan/ckanext/datastore.  We need it for testing purposes
    # because we need to create data to use in the tests
    def notify(self, entity, operation=None):
        if not isinstance(entity, model.Package):
            return
        if operation == model.domain_object.DomainObjectOperation.changed:
            context = {'model': model, 'ignore_auth': True}
            if entity.private:
                func = p.toolkit.get_action('datastore_make_private')
            else:
                func = p.toolkit.get_action('datastore_make_public')
            for resource in entity.resources:
                try:
                    func(context, {
                        'connection_url': self.write_url,
                        'resource_id': resource.id})
                except p.toolkit.ObjectNotFound:
                    pass