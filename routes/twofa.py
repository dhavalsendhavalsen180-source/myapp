from flask import Blueprint, request, make_response, jsonify
import secure_login

twofa_bp = Blueprint("twofa", __name__)

@twofa_bp.route("/enable_2fa", methods=["POST"])
def enable_2fa():
    resp, code, headers = secure_login.enable_2fa(dict(request.headers))
    r = make_response(jsonify(resp), code)
    for k, v in headers.items(): r.headers[k] = v
    return r

@twofa_bp.route("/verify_2fa", methods=["POST"])
def verify_2fa():
    body = request.get_data(as_text=True)
    resp, code, headers = secure_login.verify_2fa(body, dict(request.headers))
    r = make_response(jsonify(resp), code)
    for k, v in headers.items(): r.headers[k] = v
    return r
