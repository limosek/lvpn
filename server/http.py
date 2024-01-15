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

from lib.authid import AuthID
from lib.service import Service
from lib.signverify import Sign, Verify
from lib.vdp import VDP

app = Flask(__name__)
openapi = OpenAPI.from_file_path(os.path.dirname(__file__) + "/../config/api.yaml")
openapi_validated = FlaskOpenAPIViewDecorator(openapi)


def make_response(code, reason, data=None):
    if data is None:
        data = {}
    return Response(json.dumps(data, indent=2), "%s %s" % (code, reason), {'content-type': 'application/json'})


# Define your API endpoints based on the OpenAPI JSON
@app.route('/api/gates', methods=['GET'])
@openapi_validated
def get_gates():
    return json.loads(Manager.ctrl["cfg"].vdp.gates(as_json=True))


@app.route('/api/spaces', methods=['GET'])
@openapi_validated
def get_spaces():
    return json.loads(Manager.ctrl["cfg"].vdp.spaces(as_json=True))


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
#@openapi_validated
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


@app.route('/api/connect', methods=['POST'])
@openapi_validated
def connect():
    space = Manager.ctrl["cfg"].vdp.get_space(request.openapi.body["spaceid"])
    if not space:
        return make_response(460, "Unknown space")
    gate = Manager.ctrl["cfg"].vdp.get_gate(request.openapi.body["gateid"])
    if not gate:
        return make_response(461, "Unknown gate")
    if not gate.is_for_space(space.get_id()):
        return make_response(416, "Gate cannot be used with this space")
    if "sessionid" in request.openapi.body:
        data = request.openapi.body
        try:
            sessionid = data["sessionid"]
            signedmsg = "%s:%s:%s:%s:%s:%s:%s" % (data["time"], data["paymentid"], data["price"], data["expires"], data["bearer"], data["username"], data["password"])
            if Verify(Manager.ctrl["cfg"].provider_public_key).verify(signedmsg, sessionid):
                return make_response(402, "Waiting for payment", data)
            else:
                return make_response(422, "Bad session data")
        except Exception as e:
            logging.getLogger().error(e)
            return make_response(422, "Bad session data")

    else:
        wallet = gate.get_wallet()
        price_1d = gate.get_price() + space.get_price()
        price = price_1d * request.openapi.body["days"]
        tme = int(time.time())
        authid = AuthID(time=tme, spaceid=request.openapi.body["spaceid"], gateid=request.openapi.body["gateid"], days=request.openapi.body["days"])
        data = {
            "paymentid": str(authid),
            "time": tme,
            "wallet": wallet,
            "price": price,
            "expires": int(tme + request.openapi.body["days"] * 3600 * 24),
            "bearer": secrets.token_urlsafe(16),
            "username": "usr_" + secrets.token_urlsafe(6).lower(),
            "password": secrets.token_urlsafe(8),
            "spaceid": space.get_id(),
            "gateid": gate.get_id(),
            "days": request.openapi.body["days"]
        }
        signedmsg = "%s:%s:%s:%s:%s:%s:%s" % (data["time"], data["paymentid"], data["price"], data["expires"], data["bearer"], data["username"], data["password"])
        signed = Sign(Manager.ctrl["cfg"].provider_private_key).sign(signedmsg)
        data["sessionid"] = signed
        return make_response(402, "Waiting for payment", data)


class Manager(Service):

    p = None
    myname = "manager"

    @classmethod
    def postinit(cls):
        cls.p = threading.Thread(target=cls.loop)
        cls.p.start()
        app.run(port=cls.ctrl["cfg"].http_port, host="0.0.0.0", debug=(cls.ctrl["cfg"].l == "DEBUGa"))
        cls.exit = True

    @classmethod
    def stop(cls):
        cls.p.join()
