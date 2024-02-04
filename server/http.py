import os.path
import threading
import jsonschema
from flask import Flask, request, Response
import json
from jsonschema.exceptions import ValidationError
from openapi_core import OpenAPI
from openapi_core.contrib.flask.decorators import FlaskOpenAPIViewDecorator
import openapi_schema_validator
import stripe

from lib.market import Market
from lib.session import Session
from lib.service import Service
from lib.sessions import Sessions
from lib.util import Util
from lib.vdp import VDP

app = Flask(__name__)
openapi = OpenAPI.from_file_path(os.path.dirname(__file__) + "/../misc/schemas/server.yaml")
openapi_validated = FlaskOpenAPIViewDecorator(openapi)


def make_response(code, reason, data=None):
    if data is None:
        data = {}
    if type(data) is str:
        return Response(data, "%s %s" % (code, reason), {'content-type': 'text/plain'})
    else:
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


@app.route('/api/pay/stripe', methods=['GET'])
@openapi_validated
def stripe_payment():
    if not Manager.ctrl["cfg"].stripe_api_key or not Manager.ctrl["cfg"].stripe_price_id or not Manager.ctrl["cfg"].stripe_price_eur:
        return make_response(500, "Server not configured.", {})
    try:
        paymentid = request.args["paymentid"]
        wallet = request.args["wallet"]
        if not Util.check_paymentid(paymentid):
            return make_response(400, "Bad paymentid", {})
        if not Util.check_wallet_address(wallet):
            return make_response(400, "Bad wallet", {})
        stripe.api_key = Manager.ctrl["cfg"].stripe_api_key
        if Manager.ctrl["cfg"].lthn_price[0] == "*":
            price1 = Market.get_price_coingecko() * float(Manager.ctrl["cfg"].lthn_price[1:])
        else:
            price1 = float(Manager.ctrl["cfg"].lthn_price)
        if price1:
            amount = Manager.ctrl["cfg"].stripe_price_eur / price1
            p = stripe.PaymentLink.create(
                line_items=[{'price': Manager.ctrl["cfg"].stripe_price_id, 'quantity': 1}],
                payment_intent_data={
                    'metadata':
                    {
                        'wallet': wallet,
                        'paymentid': paymentid,
                        'amount': int(amount)
                    },
                    'description': "Receive %s VPN credits for %sEUR to wallet %s" % (int(amount), Manager.ctrl["cfg"].stripe_price_eur, Util.shorten_wallet_address(wallet))
                },
                custom_text={
                    "submit": {
                        "message": "Receive %s VPN credits for %sEUR to wallet %s" % (int(amount), Manager.ctrl["cfg"].stripe_price_eur, Util.shorten_wallet_address(wallet))
                    }
                }
            )
            return make_response(200, "OK", p.url)
        else:
            return make_response(500, "Cannot contact market API", {})
    except Exception as e:
        return make_response(400, "Bad request", {"error": str(e)})


@app.route('/api/vdp', methods=['POST'])
# @openapi_validated
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
        return make_response(412, "Bad VDP", {"error": str(e.message)})
    except Exception as e:
        return make_response(444, "Bad Request data", {"error": str(e)})


@app.route('/api/session', methods=['POST'])
@openapi_validated
def post_session():
    space = Manager.ctrl["cfg"].vdp.get_space(request.openapi.body["spaceid"])
    if not space:
        return make_response(460, "Unknown space")
    gate = Manager.ctrl["cfg"].vdp.get_gate(request.openapi.body["gateid"])
    if not gate:
        return make_response(461, "Unknown gate")
    if not gate.is_for_space(space.get_id()):
        return make_response(416, "Gate cannot be used with this space")
    if "sessionid" in request.openapi.body:
        session = Sessions.find_by_id(request.openapi.body["sessionid"])
    else:
        session = Session(Manager.ctrl["cfg"])
        session.generate(gate.get_id(), space.get_id(), request.openapi.body["days"])
        Manager.ctrl["cfg"].sessions.add(session)
        session.save()
    if not session.is_paid():
        return make_response(402, "Waiting for payment", session.get_dict())
    else:
        return make_response(200, "OK", session.get_dict())


@app.route('/api/session', methods=['GET'])
@openapi_validated
def get_session():
    if "sessionid" in request.args:
        session = Manager.ctrl["cfg"].sessions.find_by_id(request.args["sessionid"])
        if session:
            if not session.is_paid():
                return make_response(402, "Waiting for payment", session.get_dict())
            else:
                return make_response(200, "OK", session.get_dict())
        else:
            return make_response(404, "Session not found", {})


class Manager(Service):
    p = None
    myname = "server-manager"

    @classmethod
    def postinit(cls):
        cls.p = threading.Thread(target=cls.loop)
        cls.p.start()
        app.run(port=cls.ctrl["cfg"].http_port, host="0.0.0.0")
        cls.exit = True

    @classmethod
    def stop(cls):
        cls.p.join()
