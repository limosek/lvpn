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
from lib.registry import Registry
from lib.session import Session
from lib.service import Service
from lib.sessions import Sessions
from lib.util import Util
from lib.vdp import VDP
from lib.vdpobject import VDPException
from server.wg_service import WGServerService

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
    return make_response(404, "Not found")


def check_authentication():
    if Registry.cfg.manager_bearer_auth:
        bearer = request.headers.get('Authorization')
        if not bearer:
            return make_response(403, "Missing Auth Bearer")
        if len(bearer.split()) != 2:
            return make_response(403, "Missing Auth Bearer")
        token = bearer.split()[1]
        if token != Registry.cfg.manager_bearer_auth:
            return make_response(403, "Bad Auth Bearer")
    return False


@app.route('/api/vdp', methods=['GET'])
@openapi_validated
def get_vdp():
    if "localOnly" in request.args and request.args["localOnly"]:
        jsn = json.loads(Registry.vdp.get_json(my_only=True))
    else:
        jsn = json.loads(Registry.vdp.get_json())
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
    if not Registry.cfg.stripe_api_key or not Registry.cfg.stripe_plink_id:
        return make_response(500, "Server not configured.", {})
    paymentid = request.args["paymentid"]
    wallet = request.args["wallet"]
    if not Util.check_paymentid(paymentid):
        return make_response(400, "Bad paymentid", {})
    if not Util.check_wallet_address(wallet):
        return make_response(400, "Bad wallet", {})
    stripe.api_key = Registry.cfg.stripe_api_key
    if Registry.cfg.lthn_price[0] == "*":
        price1 = Market.get_price_coingecko() * float(Registry.cfg.lthn_price[1:])
    else:
        price1 = float(Registry.cfg.lthn_price)
    if price1:
        amount1 = 1 / price1
        found = None
        for p in Registry.cfg.stripe_plink_id.split(","):
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
                return make_response(502, "Cannot use Stripe now. Please try again later.")
        else:
            logging.getLogger("http").error("No Stripe payment link available")
            return make_response(502, "Cannot use Stripe now. Please try again later.")
    else:
        return make_response(501, "Cannot contact market API")


@app.route('/api/vdp', methods=['POST'])
# @openapi_validated
def post_vdp():
    if "checkOnly" in request.args and request.args["checkOnly"]:
        check = True
    else:
        check = False
    jsn = request.data.decode("utf-8")
    try:
        try:
            new_vdp = VDP(vdpdata=jsn)
        except VDPException as e:
            return make_response(443, "Bad Request data", {"error": str(e)})
        if not check:
            saved = new_vdp.save()
        else:
            saved = None
        return make_response(200, "OK", saved)
    except VDPException as e:
        return make_response(443, "Bad Request data", {"error": str(e)})


@app.route('/api/session', methods=['POST'])
@openapi_validated
def post_session():
    space = Registry.vdp.get_space(request.openapi.body["spaceid"])
    if not space or not space.is_local():
        return make_response(460, "Unknown space or space is not local")
    gate = Registry.vdp.get_gate(request.openapi.body["gateid"])
    if not gate or not gate.is_local():
        return make_response(461, "Unknown gate or space is not local")
    if not gate.is_for_space(space.get_id()):
        return make_response(462, "Gate %s cannot be used with space %s" % (gate.get_id(), space.get_id()))
    sessions = Sessions()
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
        session = Session()
        session.generate(gate.get_id(), space.get_id(), request.openapi.body["days"])
        if session.is_free() and session.days_left() > Registry.cfg.max_free_session_days:
            return make_response(463, "No permission for free service and %s days", "too-many-days-for-free-service: %s" % request.openapi.body["days"])
        if gate.get_type() == "wg":
            if "wg" in request.openapi.body:
                WGServerService.prepare_server_session(session, request.openapi.body["wg"])
            else:
                return make_response(465, "Missing WG endpoint data")
        sessions.add(session)
    if not session.is_active():
        return make_response(402, "Waiting for payment", session.get_dict())
    else:
        return make_response(200, "OK", session.get_dict())


@app.route('/api/session', methods=['GET'])
@openapi_validated
def get_session():
    sessions = Sessions(noload=True)
    if "sessionid" in request.args:
        session = sessions.get(request.args["sessionid"])
        if session:
            if not session.is_active():
                return make_response(402, "Waiting for payment", session.get_dict())
            else:
                return make_response(200, "OK", session.get_dict())
        else:
            return make_response(404, "Session not found", {})
    else:
        return make_response(400, "Missing sessionid", {})


@app.route('/api/session/rekey', methods=['GET'])
@openapi_validated
def rekey_session():
    sessions = Sessions(noload=True)
    if "sessionid" in request.args:
        session = sessions.get(request.args["sessionid"])
        if session:
            if not session.is_active():
                return make_response(402, "Waiting for payment", session.get_dict())
            else:
                if session.get_gate().get_type == "wg":
                    if "wg_public_key" in request.args:
                        WGServerService.prepare_server_session(session, {"public_key": request.args["wg_public_key"], "endpoint": "dynamic"})
                        return make_response(200, "OK", session.get_dict())
                    else:
                        return make_response(400, "Missing wg_public_key", {})
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
    for c in Sessions().find():
        rsessions.append(c.get_dict())
    return rsessions


class Manager(Service):
    p = None
    myname = "server-manager"

    @classmethod
    def refresh_vdp(cls):
        while not cls.exit:
            for i in range(1, 300):
                time.sleep(1)
                if cls.exit:
                    return
            Registry.vdp = VDP()

    @classmethod
    def postinit(cls):
        cls.p = threading.Thread(target=cls.loop)
        cls.p.start()
        cls.vdp = threading.Thread(target=cls.refresh_vdp)
        cls.vdp.start()
        cls.app = app
        cls.app.run(port=Registry.cfg.http_port, host="0.0.0.0", debug=Registry.cfg.l == "DEBUG", use_reloader=False)
        cls.exit = True

    @classmethod
    def stop(cls):
        cls.p.join()
