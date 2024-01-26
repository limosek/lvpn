import logging
import os.path
import threading
import jsonschema
from flask import Flask, request, Response
import time
import json
from jsonschema.exceptions import ValidationError
from openapi_core import OpenAPI
from openapi_core.contrib.flask.decorators import FlaskOpenAPIViewDecorator
import openapi_schema_validator
import secrets

from lib.session import Session
from lib.mngrrpc import ManagerRpcCall
from lib.service import Service
from lib.signverify import Sign, Verify
from lib.vdp import VDP

app = Flask(__name__)
openapi = OpenAPI.from_file_path(os.path.dirname(__file__) + "/../misc/schemas/client.yaml")
openapi_validated = FlaskOpenAPIViewDecorator(openapi)


def make_response(code, reason, data=None):
    if data is None:
        data = {}
    return Response(json.dumps(data, indent=2), "%s %s" % (code, reason), {'content-type': 'application/json'})


@app.route('/api/vdp', methods=['GET'])
@openapi_validated
def get_vdp():
    jsn = json.loads(Manager.ctrl["cfg"].vdp.get_json())
    spc = openapi.spec.contents()
    resolver = jsonschema.validators.RefResolver.from_schema(spc)
    validator = openapi_schema_validator.OAS31Validator(spc["components"]["schemas"]["Vdp"], resolver=resolver)
    try:
        validator.validate(jsn)
        return make_response(200, "OK", jsn)
    except ValidationError as e:
        return make_response(500, "Bad VDP", {"error": str(e.message)})


@app.route('/api/vdp', methods=['POST'])
def post_vdp():
    spc = openapi.spec.contents()
    resolver = jsonschema.validators.RefResolver.from_schema(spc)
    validator = openapi_schema_validator.OAS31Validator(spc["components"]["schemas"]["Vdp"], resolver=resolver)
    if "checkOnly" in request.args and request.args["checkOnly"]:
        check = True
    else:
        check = False
    try:
        jsn = json.loads(request.data.decode("utf-8"))
        validator.validate(jsn)
        if check:
            return make_response(200, "OK", jsn)
        else:
            vdp = VDP(Manager.ctrl["cfg"], vdpdata=request.data)
            try:
                vdp.save()
            except Exception as e:
                return make_response(500, "Cannot update VDP", {})
            return make_response(200, "OK", jsn)
    except ValidationError as e:
        return make_response(412, "Bad VDP", { "error": str(e.message) })
    except Exception as e:
        return make_response(444, "Bad Request data", {"error": str(e)})


@app.route('/api/connect', methods=['GET'])
@openapi_validated
def connect():
    pass


@app.route('/api/session/prepare', methods=['POST'])
@openapi_validated
def prepare_session():
    space = request.openapi.body["space"]
    gate = request.openapi.body["gate"]
    mngr = ManagerRpcCall("http://localhost:8123")
    data = mngr.preconnect(
        {
            "spaceid": space.get_id(),
            "gateid": gate.get_id(),
            "days": instance._days
        })


@app.route('/api/connections', methods=['GET'])
@openapi_validated
def connections():
    conns = []
    for c in Manager.get_value("connections"):
        if c["port"] != "NA":
            port = c["port"]
        else:
            port = 0
        ci = {
            "gate": c["gate"].get_dict(),
            "space": c["space"].get_dict(),
            "local_port": port,
            "connectionid": c["connectionid"]
        }
        conns.append(ci)
    return conns


class Manager(Service):

    p = None
    myname = "client-manager"

    @classmethod
    def postinit(cls):
        cls.p = threading.Thread(target=cls.loop)
        cls.p.start()
        app.run(port=cls.ctrl["cfg"].http_port, host="127.0.0.1")
        cls.exit = True

    @classmethod
    def stop(cls):
        cls.p.join()
