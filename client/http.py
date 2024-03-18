import logging
import os.path
import threading

import _queue
import jsonschema
from flask import Flask, request, Response
import time
import json
from jsonschema.exceptions import ValidationError
from openapi_core import OpenAPI
from openapi_core.contrib.flask.decorators import FlaskOpenAPIViewDecorator
import openapi_schema_validator

from client.connection import Connections
from lib.registry import Registry
from lib.session import Session
from lib.mngrrpc import ManagerRpcCall, ManagerException
from lib.service import Service
from lib.sessions import Sessions
from lib.messages import Messages
from lib.vdp import VDP

app = Flask(__name__)
openapi = OpenAPI.from_file_path(os.path.dirname(__file__) + "/../misc/schemas/client.yaml")
openapi_validated = FlaskOpenAPIViewDecorator(openapi)


def make_response(code, reason, data=None):
    if data is None:
        data = {"code": code, "reason": reason}
    return Response(json.dumps(data, indent=2), "%s %s" % (code, reason), {'content-type': 'application/json'})


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


@app.errorhandler(404)
def error_404(e):
    return make_response(404, "Not found")


@app.route('/api/vdp', methods=['GET'])
@openapi_validated
def get_vdp():
    notauth = check_authentication()
    if notauth:
        return notauth
    jsn = json.loads(Registry.vdp.get_json())
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
    notauth = check_authentication()
    if notauth:
        return notauth
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
            vdp = VDP(Registry.cfg, vdpdata=request.data)
            try:
                vdp.save()
            except Exception as e:
                return make_response(500, "Cannot update VDP", {})
            return make_response(200, "OK", jsn)
    except ValidationError as e:
        return make_response(412, "Bad VDP", { "error": str(e.message) })
    except Exception as e:
        return make_response(444, "Bad Request data", {"error": str(e)})


@app.route('/api/connections', methods=['GET'])
@openapi_validated
def connections():
    notauth = check_authentication()
    if notauth:
        return notauth
    conns = []
    for c in Manager.get_value("connections"):
        conns.append(c.get_dict())
    return conns


@app.route('/api/sessions', methods=['GET'])
@openapi_validated
def sessions():
    notauth = check_authentication()
    if notauth:
        return notauth
    sessions = Sessions()
    rsessions = []
    for c in sessions.find():
        rsessions.append(c.get_dict())
    return rsessions


@app.route('/api/session', methods=['POST'])
@openapi_validated
def create_session():
    notauth = check_authentication()
    if notauth:
        return notauth
    sessions = Sessions()
    days = request.openapi.body["days"]
    space = Registry.vdp.get_space(request.openapi.body["spaceid"])
    if not space:
        return make_response(460, "Unknown space")
    gate = Registry.vdp.get_gate(request.openapi.body["gateid"])
    if not gate:
        return make_response(461, "Unknown gate")
    if not gate.is_for_space(space.get_id()):
        return make_response(416, "Gate cannot be used with this space")
    fresh = sessions.find(gateid=gate.get_id(), spaceid=space.get_id(), fresh=True)
    if fresh:
        fresh = fresh[0]
        if fresh.is_active():
            return make_response(200, "OK", fresh.get_dict())
        else:
            if Registry.cfg.auto_pay_days > days:
                for m in fresh.get_pay_msgs():
                    Manager.queue.put(m)
                return make_response(402, "Payment sent, awaiting server", fresh.get_dict())
            else:
                return make_response(402, "Awaiting payment", fresh.get_dict())
    else:
        try:
            mngr = ManagerRpcCall(space.get_manager_url())
            session = Session(mngr.create_session(gate, space, days))
            session.save()
            sessions.add(session)
        except ManagerException as e:
            return make_response(501, "Manager RPC error", str(e))
        if session.is_active():
            return make_response(200, "OK", session.get_dict())
        else:
            return make_response(402, "Awaiting payment", session.get_dict())


@app.route('/api/session', methods=['GET'])
@openapi_validated
def get_session():
    notauth = check_authentication()
    if notauth:
        return notauth
    if "sessionid" in request.args:
        sessions = Sessions()
        session = sessions.get(request.args["sessionid"])
        if session:
            if not session.is_active():
                return make_response(402, "Waiting for payment", session.get_dict())
            else:
                return make_response(200, "OK", session.get_dict())
        else:
            return make_response(404, "Session not found")
    else:
        return make_response(400, "Missing sessionid")


@app.route('/api/connect/<sessionid>', methods=['GET'])
@openapi_validated
def connect(sessionid):
    notauth = check_authentication()
    if notauth:
        return notauth
    sessions = Sessions()
    session = sessions.get(sessionid)
    if session:
        if session.is_active():
            m = Messages.connect(session)
            Manager.queue.put(m)
            waited = 0
            found = False
            while waited < 10 and not found:
                conn = Connections(Manager.ctrl["connections"]).get_by_sessionid(session.get_id())
                if conn:
                    return make_response(200, "OK", conn.get_dict())
                waited += 1
                time.sleep(1)
            return make_response(500, "Server error")
        elif not session.is_active():
            return make_response(402, "Waiting for payment")
        elif not session.is_fresh():
            return make_response(405, "Session expired")
        else:
            return make_response(404, "Session not found")
    else:
        return make_response(404, "Session not found")


@app.route('/api/disconnect/<connectionid>', methods=['GET'])
@openapi_validated
def disconnect(connectionid):
    notauth = check_authentication()
    if notauth:
        return notauth
    connection = Connections(Manager.ctrl["connections"]).get(connectionid)
    if connection:
        m = Messages.disconnect(connection.get_id())
        Manager.queue.put(m)
        waited = 0
        found = False
        while waited < 10 and not found:
            if not Connections(Manager.ctrl["connections"]).get(connection.get_id()):
                return make_response(200, "OK")
            waited += 1
            time.sleep(1)
        return make_response(500, "Server error")
    else:
        return make_response(404, "Connmection not found")


@app.route('/api/pay/session/<sessionid>', methods=['GET'])
@openapi_validated
def pay_session(sessionid):
    notauth = check_authentication()
    if notauth:
        return notauth
    sessions = Sessions()
    session = sessions.get(sessionid)
    if session:
        if session.is_active():
            return make_response(201, "Already paid")
        elif not session.is_paid():
            for m in session.get_pay_msgs():
                Manager.queue.put(m)
            waited = 0
            paid = []
            while waited < 30:
                session = sessions.get(session.get_id())
                if session.is_paid():
                    return make_response(200, "OK", session.get_dict())
                if len(paid) >= session.get_pay_msgs():
                    return make_response(200, "OK", session.get_dict())
                if Manager.myqueue and not Manager.myqueue.empty():
                    try:
                        msg = Manager.myqueue.get(block=False, timeout=0.1)
                        if msg.startswith(Messages.PAID):
                            data = Messages.get_msg_data(msg)
                            if data not in paid:
                                paid.append(data)
                                return make_response(200, "OK", session.get_dict())
                        elif msg.startswith(Messages.UNPAID):
                            return make_response(500, "Payment error", session.get_dict())
                    except _queue.Empty:
                        pass
                time.sleep(1)
                waited += 1
            return make_response(500, "Error during payment")

        elif not session.is_fresh():
            return make_response(405, "Session expired")
        else:
            return make_response(404, "Session not found")
    else:
        return make_response(404, "Session not found")


class Manager(Service):

    p = None
    myname = "client-manager"

    @classmethod
    def postinit(cls):
        cls.p = threading.Thread(target=cls.loop)
        cls.p.start()
        app.run(port=Registry.cfg.http_port, host=Registry.cfg.manager_local_bind, debug=Registry.cfg.l == "DEBUG", use_reloader=False)
        cls.exit = True

    @classmethod
    def stop(cls):
        cls.p.join()

    @classmethod
    def loop(cls):
        while True:
            time.sleep(1)
