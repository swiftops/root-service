from flask import Flask, jsonify, request, session
from flask_cors import CORS
from util import load_autocomplete_data,\
    filter_request, add_data_in_session, insert_on_logout, init
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)
session = {}
init(app)


@app.route("/root", methods=['POST'])
def _auto_complete():
    user_query = request.form.get('query')
    show_more = request.form.get('show_more')
    session_id = request.form.get('session_id')
    if session_id is not None and session_id:
        add_data_in_session(session, str(datetime.now()), session_id, "login_time", False)
    if user_query is not None:
        data = load_autocomplete_data(user_query, show_more)
    return jsonify(data)


@app.route("/filter", methods=['POST'])
def _filter():
    user_query = request.form.get('query')
    username = request.form.get('username')
    session_id = request.form.get('session_id')
    firstreq = request.form.get('loadFirst')
    if session_id is not None and session_id:
        add_data_in_session(session, user_query, session_id, "query", True)
    if user_query is not None and username is not None:
        data = filter_request(user_query, username, firstreq)
    return json.dumps(data)


@app.route("/logout", methods=['POST'])
def _logout():
    session_id = request.json['session_id']
    username = request.json['username']
    session_list = session.get(session_id)
    response = {}
    if session_id is not None and session_id:
        response = insert_on_logout(session, session_list, username, session_id)
    session.pop('session_id', None)
    return jsonify(response)


if __name__ == "__main__":
    app.secret_key = os.urandom(24)
    app.run('0.0.0.0', port=8082, debug=True)


