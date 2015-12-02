from flask import Flask, session, _app_ctx_stack, request, redirect, url_for, abort, jsonify
from datastore import DataStore
from werkzeug import datastructures
import json
import urllib

DATASTORE = "Mongo"
DATASTORE_CONFIG = {"db": "federated_birds_scratch"}

SESSION_KEY = b'%e3\x87%\xd7\x9a\x8d\x01\x7f\xf5\xec\xca!j{\xdc/\xf3v\xdc+\xab\xa4'
SERVER_NAME = "pybirds"

app = Flask(__name__)
app.secret_key = SESSION_KEY

def get_datastore():
    top = _app_ctx_stack.top
    if not hasattr(top, 'datastore'):
        top.datastore = DataStore(DATASTORE, DATASTORE_CONFIG, app.logger)
    return top.datastore

def format_response(coll, has_more=False):
    resp = jsonify(coll)
    if not has_more and page() == 1:
        return resp
    else:
        url = list(urllib.parse.urlsplit(request.url))
        params = urllib.parse.parse_qs(url[3])
        links = []
        if has_more:
            params['page'] = [page()+1]
            url[3] = urllib.parse.urlencode(params, doseq=True)
            links.append('<%s>; rel="next"' % urllib.parse.urlunsplit(url))
        if page() > 1:
            params['page'] = [page()-1]
            url[3] = urllib.parse.urlencode(params, doseq=True)
            links.append('<%s>; rel="prev"' % urllib.parse.urlunsplit(url))

        return resp, 200, {'Link': ", ".join(links)}



@app.teardown_appcontext
def close_datastore(exception):
    top = _app_ctx_stack.top
    if hasattr(top, 'datastore'):
        top.datastore.close()

def authorized(handle, token):
    if not get_datastore().authenticate_token(handle, token):
        abort(401)
        
        
def page():
    return int(request_form().get('page', 1))

@app.route("/users.json")
def users():
    coll = get_datastore().user_logins(page())
    return format_response({"server": SERVER_NAME, "users": coll}, coll.has_more)

@app.route("/users.json", methods=["POST"])
def create_user():
    handle = request_form().get('handle', '')
    password = request_form().get('password', '')
    if len(handle) < 1 or len(password) < 1:
        return '', 422
    elif get_datastore().get_user_by_handle(handle) is not None:
        return '', 409
    else:
        return format_response(get_datastore().create_user(handle, password))

@app.route("/sessions.json", methods=["POST"])
def signin():
    handle = request_form().get('handle', '')
    password = request_form().get('password', '')
    if len(handle) < 1 or len(password) < 1:
        return '', 401
    tentative_user = get_datastore().authenticate(handle, password)
    if tentative_user is None:
        return '', 401
    else:
        return format_response(tentative_user)

@app.route("/tweets.json")
def tweets():
    return format_response({"tweets": get_datastore().tweets(None, page())})

@app.route("/<handle>/tweets.json")
def personal_tweets(handle):
    return format_response({"tweets": get_datastore().tweets(handle, page())})

@app.route("/<handle>/followers.json")
def followers(handle):
    return format_response({"followers": get_datastore().followers(handle, page())})

@app.route("/<handle>/followings.json")
def followings(handle):
    return format_response({"followings": get_datastore().followings(handle, page())})

@app.route("/<myhandle>/followings.json", methods= ['DELETE'])
def delete_following(myhandle):
    authorized(myhandle, request_form()["token"])
    following = get_datastore().delete_following(request_form()["handle"], myhandle)
    return '', (200 if following else 422)

@app.route("/<myhandle>/followings.json", methods= ['POST'])
def create_following(myhandle):
    authorized(myhandle, request_form()["token"])
    following = get_datastore().create_following(request_form()["handle"], myhandle)
    if following is None:
        return '', 422
    return format_response(following)

@app.route("/<handle>/tweets.json", methods= ['POST'])
def create_tweet(handle):
    authorized(handle, request_form()['token'])
    return format_response(get_datastore().create_tweet(request_form()['content'], handle))

@app.route("/<handle>/reading_list.json")
def reading_list(handle):
    authorized(handle, request_form()['token'])
    return format_response({"tweets": get_datastore().reading_list(handle, page())})

@app.route("/")
def index():
    return redirect(url_for('tweets'))

def request_form():
    ret = request.form
    if request.json is not None:
        ret = request.json
    if request.headers.get('X-Token'):
        ret = datastructures.CombinedMultiDict([ret, {'token': request.headers.get('X-Token')}])
    return ret
    

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, X-Token')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, DELETE')
    response.headers.add('Access-Control-Expose-Headers', 'Link')
    return response

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
