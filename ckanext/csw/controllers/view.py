import ckan.plugins as p
from ckan import model
from ckan.lib.base import BaseController, c, abort, response
from pylons.i18n import _

class ViewController(BaseController):
    """
    Controller object for rendering an ISO 19139 XML representation of a CKAN package.
    @param BaseController: Vanilla CKAN object for extending controllers (The 'C' in MVC)
    """
    def show_object(self, id):
        """
        Given a CKAN package ID: scrape the package data, parse data in the 'iso_metadata'
        function, set response parameters and return an ISO 19139 XML representation of
        the CKAN package.  On error, return an appropriate HTTP error status code.

        @param id: The ID of a CKAN package
        @return: ISO 19139 XML representation of CKAN package
        """
        try:
            context = {'model': model, 'user': c.user}
            obj = p.toolkit.get_action('iso_metadata')(context, {'id': id})
            response.content_type = 'application/xml; charset=utf-8'
            response.headers['Content-Length'] = len(obj)
            return obj.encode('utf-8')

        except p.toolkit.ObjectNotFound, e:
            abort(404, _(str(e)))
        except p.toolkit.NotAuthorized:
            abort(401, self.not_auth_message)
        except Exception, e:
            msg = 'An error ocurred: [%s]' % str(e)
            abort(500, msg)