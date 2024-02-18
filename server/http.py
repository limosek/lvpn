import logging
import os.path
import threading
import time
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
        data = {"code": code, "reason": reason}
    if type(data) is str:
        return Response(data, "%s %s" % (code, reason), {'content-type': 'text/plain'})
    else:
        return Response(json.dumps(data, indent=2), "%s %s" % (code, reason), {'content-type': 'application/json'})


@app.errorhandler(404)
def error_404(e):
    return make_response(404, "Not found", str(e))


def check_authentication():
    if Manager.ctrl["cfg"].manager_bearer_auth:
        bearer = request.headers.get('Authorization')
        if not bearer:
            return make_response(403, "Missing Auth Bearer")
        if len(bearer.split()) != 2:
            return make_response(403, "Missing Auth Bearer")
        token = bearer.split()[1]
        if token != Manager.ctrl["cfg"].manager_bearer_auth:
            return make_response(403, "Bad Auth Bearer")
    return False


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
    if not Manager.ctrl["cfg"].stripe_api_key or not Manager.ctrl["cfg"].stripe_plink_id:
        return make_response(500, "Server not configured.", {})
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
        amount1 = 1 / price1
        found = None
        for p in Manager.ctrl["cfg"].stripe_plink_id.split(","):
            try:
                pl = stripe.PaymentLink.retrieve(p)
            except Exception as e:
                logging.getLogger("http").error("Cannot retrieve payment link %s:%s" % (p, e))
                break
            try:
                updated = float(pl.to_dict()["payment_intent_data"]["metadata"]["updated"])
            except Exception as e:
                found = p
                foundpl = pl
                logging.getLogger("http").warning("Payment link without metadata:%s - will update" % p)
                break
            if not bool(pl["active"]):
                found = p
                foundpl = pl
                logging.getLogger("http").warning("Using free paymentlink:%s" % p)
                break
            elif int(updated) + 600 < time.time():
                try:
                    stripe.PaymentLink.modify(p, active=False)
                except Exception as e:
                    logging.getLogger("http").error("Cannot disable payment link %s:%s" % (p, e))
                    break
        if found and foundpl:
            try:
                stripe.PaymentLink.modify(
                    found,
                    active=True,
                    custom_text={
                        "submit": {
                            "message": "Receive %s VPN credits per 1EUR to wallet %s" % (int(amount1), Util.shorten_wallet_address(wallet))
                        }
                    },
                    payment_intent_data={
                        'metadata': {
                            'updated': time.time(),
                            'wallet': wallet,
                            'paymentid': paymentid,
                            'amount1': int(amount1)
                        }
                    }
                )
                return make_response(200, "OK", foundpl.url)
            except Exception as e:
                logging.getLogger("http").error("Cannot modify payment link %s:%s" % (found, e))
                return make_response(502, "Cannot use Stripe now. Please try again later.", {})
        else:
            logging.getLogger("http").error("No Stripe payment link available")
            return make_response(502, "Cannot use Stripe now. Please try again later.", {})
    else:
        return make_response(501, "Cannot contact market API", {})


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
        return make_response(462, "Gate cannot be used with this space")
    sessions = Sessions(Manager.ctrl["cfg"])
    if "like_sessionid" in request.openapi.body:
        session = sessions.find_by_id(request.openapi.body["like_sessionid"])
        if session:
            if session.is_free():
                return make_response(404, "Unknown sessionid to reuse", request.openapi.body["reuse_sessionid"])
            elif session.get_gate().get_id() != request.openapi.body["gateid"] or session.get_get_space().get_id() != request.openapi.body["spaceid"]:
                return make_response(464, "Cannot reuse with different gate or space")
            elif session.is_paid() and session.is_fresh():
                session.reuse(request.openapi.body["days"])
                return make_response(402, "Waiting for payment", session.get_dict())
            else:
                return make_response(404, "Bad sessionid to reuse", request.openapi.body["reuse_sessionid"])
        else:
            return make_response(463, "No permission to reuse session", request.openapi.body["reuse_sessionid"])
    else:
        session = Session(Manager.ctrl["cfg"])
        session.generate(gate.get_id(), space.get_id(), request.openapi.body["days"])
        sessions.add(session)
    if not session.is_paid():
        return make_response(402, "Waiting for payment", session.get_dict())
    else:
        return make_response(200, "OK", session.get_dict())


@app.route('/api/session', methods=['GET'])
@openapi_validated
def get_session():
    sessions = Sessions(Manager.ctrl["cfg"], noload=True)
    if "sessionid" in request.args:
        session = sessions.get(request.args["sessionid"])
        if session:
            if not session.is_paid():
                return make_response(402, "Waiting for payment", session.get_dict())
            else:
                return make_response(200, "OK", session.get_dict())
        else:
            return make_response(404, "Session not found", {})
    else:
        return make_response(400, "Missing sessionid", {})


@app.route('/api/sessions', methods=['GET'])
@openapi_validated
def sessions():
    notauth = check_authentication()
    if notauth:
        return notauth
    rsessions = []
    for c in Sessions(Manager.ctrl["cfg"]).find():
        rsessions.append(c.get_dict())
    return rsessions


class Manager(Service):
    p = None
    myname = "server-manager"

    @classmethod
    def postinit(cls):
        cls.p = threading.Thread(target=cls.loop)
        cls.p.start()
        cls.app = app
        cls.app.run(port=cls.ctrl["cfg"].http_port, host="0.0.0.0")
        cls.exit = True

    @classmethod
    def stop(cls):
        cls.p.join()
