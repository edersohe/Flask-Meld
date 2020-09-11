from flask import send_from_directory, jsonify, request
import os

from jinja2 import nodes
from jinja2.ext import Extension

from .component import get_component_class  # , Component


__version__ = '0.0.1'


class Meld(object):
    def __init__(self, app=None):
        self.app = app

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.jinja_env.add_extension(MeldExtension)
        app.jinja_env.add_extension(MeldScriptsExtension)

        # if not app.config.get('SECRET_KEY'):
        #     raise RuntimeError(
        #         "The Flask-Meld requires the 'SECRET_KEY' config "
        #         "variable to be set")

        app.add_url_rule('/_meld/static/js/<path:filename>', None,
                         self.send_static_file)

        @app.route("/message")
        @app.route("/message/<string:component_name>", methods=['GET', 'POST'])
        def message(component_name):
            body = request.get_json()
            meld_id = body.get("id")
            action_queue = body.get("actionQueue")
            Component = get_component_class(component_name)
            component = Component(meld_id)

            if action_queue:
                for action in action_queue:
                    if 'sync' in action["type"]:
                        payload = action["payload"]
                        print(payload)
                        if hasattr(component, payload['name']):
                            setattr(component, payload['name'], payload['value'])

            rendered_component = component.render(component_name)
            print(rendered_component)

            res = {
                "id": meld_id,
                "dom": rendered_component,
            }

            return jsonify(res)

    def send_static_file(self, filename):
        _static_dir = os.path.realpath(
            os.path.join(os.path.dirname(__file__), 'static/js'))
        """Send a static file from the flask-meld static directory."""
        return send_from_directory(_static_dir, filename)


class MeldScriptsExtension(Extension):
    """
    Create a {% meld %} tag.
    Used as {% meld 'component_name' %}
    """

    tags = {'meld_scripts'}

    def parse(self, parser):
        lineno = parser.stream.expect('name:meld_scripts').lineno

        call = self.call_method('_render', lineno=lineno)
        return nodes.Output([nodes.MarkSafe(call)]).set_lineno(lineno)

    def _render(self):
        files = ["morphdom-umd.js", "meld.js"]
        msg_url = "message"
        scripts = ""
        for f in files:
            scripts += f'<script src="_meld/static/js/{f}"></script>'

        scripts += f'<script>var url = "{msg_url}"; Meld.init(url); </script>'

        return scripts


class MeldExtension(Extension):
    """
    Create a {% meld %} tag.
    Used as {% meld 'component_name' %}
    """

    tags = {'meld'}

    def parse(self, parser):
        lineno = parser.stream.expect('name:meld').lineno

        component = parser.parse_expression()

        call = self.call_method('_render', [component], lineno=lineno)
        return nodes.Output([nodes.MarkSafe(call)]).set_lineno(lineno)

    def _render(self, component):
        # return render_template(self.environment.get_template(f'meld/example.html'))
        mn = MeldNode(component)
        return mn.render()


class MeldNode():
    def __init__(self, component):
        self.component_name = component

    def render(self):
        Component = get_component_class(self.component_name)
        component = Component()
        rendered_component = component.render(self.component_name)

        return rendered_component