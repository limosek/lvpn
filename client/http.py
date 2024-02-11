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
import secrets

from client.connection import Connections
from lib.session import Session
from lib.mngrrpc import ManagerRpcCall
from lib.service import Service
from lib.shared import Messages
from lib.vdp import VDP

app = Flask(__name__)
openapi = OpenAPI.from_file_path(os.path.dirname(__file__) + "/../misc/schemas/client.yaml")
openapi_validated = FlaskOpenAPIViewDecorator(openapi)


def make_response(code, reason, data=None):
    if data is None:
        data = {"code": code, "reason": reason}
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


@app.route('/api/connections', methods=['GET'])
@openapi_validated
def connections():
    conns = []
    for c in Manager.get_value("connections"):
        conns.append(c.get_dict())
    return conns


@app.route('/api/sessions', methods=['GET'])
@openapi_validated
def sessions():
    sessions = []
    for c in Manager.ctrl["cfg"].sessions.find():
        sessions.append(c.get_dict())
    return sessions


@app.route('/api/session', methods=['POST'])
@openapi_validated
def create_session():
    days = request.openapi.body["days"]
    space = Manager.ctrl["cfg"].vdp.get_space(request.openapi.body["spaceid"])
    if not space:
        return make_response(460, "Unknown space")
    gate = Manager.ctrl["cfg"].vdp.get_gate(request.openapi.body["gateid"])
    if not gate:
        return make_response(461, "Unknown gate")
    if not gate.is_for_space(space.get_id()):
        return make_response(416, "Gate cannot be used with this space")
    fresh = Manager.ctrl["cfg"].sessions.find(gateid=gate.get_id(), spaceid=space.get_id(), fresh=True)
    if fresh:
        fresh = fresh[0]
        if fresh.is_paid():
            return make_response(200, "OK", fresh.get_dict())
        else:
            return make_response(402, "Awaiting payment", fresh.get_dict())
    else:
        mngr = ManagerRpcCall(space.get_manager_url())
        session = Session(Manager.ctrl["cfg"], mngr.create_session(gate.get_id(), space.get_id(), days))
        session.save()
        Manager.ctrl["cfg"].sessions.add(session)
        if session.is_paid():
            return make_response(200, "OK", session.get_dict())
        else:
            return make_response(402, "Awaiting payment", session.get_dict())


@app.route('/api/session', methods=['GET'])
@openapi_validated
def get_session():
    if "sessionid" in request.args:
        session = Manager.ctrl["cfg"].sessions.get(request.args["sessionid"])
        if session:
            if not session.is_paid():
                return make_response(402, "Waiting for payment", session.get_dict())
            else:
                return make_response(200, "OK", session.get_dict())
        else:
            return make_response(404, "Session not found", {})


@app.route('/api/connect/<sessionid>', methods=['GET'])
@openapi_validated
def connect(sessionid):
    session = Manager.ctrl["cfg"].sessions.get(sessionid)
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
        elif not session.is_paid():
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
    session = Manager.ctrl["cfg"].sessions.get(sessionid)
    if session:
        if session.is_active():
            return make_response(201, "Already paid")
        elif not session.is_paid():
            Manager.queue.put(session.get_pay_msg())
            waited = 0
            paid = False
            while waited < 30 and not paid:
                session = Manager.ctrl["cfg"].sessions.get(session.get_id())
                if session.is_paid():
                    return make_response(200, "OK", session.get_dict())
                if Manager.myqueue and not Manager.myqueue.empty():
                    try:
                        msg = Manager.myqueue.get(block=False, timeout=0.1)
                        print(msg)
                        if msg.startswith(Messages.PAID):
                            data = Messages.get_msg_data(msg)
                            if data == session.get_pay_msg():
                                return make_response(200, "OK", session.get_dict())
                        elif msg.startswith(Messages.UNPAID):
                            data = Messages.get_msg_data(msg)
                            if data == session.get_pay_msg():
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
        app.run(port=cls.ctrl["cfg"].http_port, host="127.0.0.1")
        cls.exit = True

    @classmethod
    def stop(cls):
        cls.p.join()

    @classmethod
    def loop(cls):
        while True:
            time.sleep(1)
