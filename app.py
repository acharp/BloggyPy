# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, abort, redirect, url_for, flash
from pymongo import MongoClient
from bson import ObjectId
import json
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user
from models import User
from werkzeug.security import generate_password_hash


app = Flask(__name__)
app.debug = True

lm = LoginManager()
lm.init_app(app)
app.config['SECRET_KEY'] = 'itsasecret'

client = MongoClient('localhost', 27017)
db = client.blogdb
users = db.users


# Pour décoder le champ ObjectId. Sinon définir nous même les _id et ne pas utiliser cette classe.
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


@app.route('/')

@app.route('/home')
def hello_world():
    return "Hello World!"


# User registration 
@app.route('/users', methods=['POST'])
def create_user():

    # Retrieve json parameters
    if not request.json :
        abort(400, "JSON expected in the request body.")
    user = request.get_json() # Renvoie un dict
   
    # Hashing user's password
    user['password'] = generate_password_hash(user['password'], method='pbkdf2:sha256', salt_length=6)

    # Checking user unicity before storing in databse
    if (users.find_one({'username' : user['username']}) == None):
        users.insert_one(user) 
        return "User " + str(user) + " successfully created !\n"
    else :
        abort(400, "This user already exists in the database.")


# Retrieving list of all users registered
@app.route('/users')
def return_users():

    list_users=[]
    for user in db.users.find():
        list_users.append(user['username'])

    dict_users = { 'users' : list_users}
    #return JSONEncoder().encode(dict_users);
    return jsonify(dict_users) # Fonctionne si on définit nos propres id et qu'on a pas à décoder ObjectId OU si on ne renvoie pas les id dans ce json


# User authentication/login
@app.route('/sessions', methods=['POST'])
def login():
    
    # Retrieve json parameters
    if not request.json:
        abort(400, "JSON expected in the request body.")
    user_to_login = request.get_json()

    # Check user registration
    user_db = users.find_one({'username': user_to_login['username']})
    if user_db:

        # Check password validation
        if User.validate_login(user_db['password'], user_to_login['password']):
            user_obj = User(user_db['username'], user_db['password'])
            login_user(user_obj)
            return "User : " + user_db['username'] + " logged in successfully !\n"
        else:
            abort(401, "Wrong password !")

    else:
        abort(401, "Wrong username !")


# User logout
@app.route('/logout')
def logout():
    logout_user()
    # return redirect(url_for('login')) # Redirige sur /sessions en GET. A voir si on l'utilise.
    return "Logout OK !"


# Test authentication
@app.route('/protected')
@login_required
def protected():
    user_logged = current_user.get_id()
    print(user_logged + " is logged in \n")
    return "Accés avec login OK !"


# Add a tweet, by the logined user.
@app.route('/:handle/tweets', methods=['POST'])
@login_required


# Method to instanciate an user from database. Used in login().
@lm.user_loader
def load_user(username):
    u = users.find_one({'username': username})
    if not u:
        return None
    return User(u['username'], u['password'])


# Next steps :
# Ajouter le champ follow aux users qui contiendra un dict id users followés : date de following 
# Récupérer les followers et les followings, c'est surtout l'aspect requête à la base qui est à réfléchir ici
# Refactorer(créer fichier de config, et répartir méthodes dans d'autres classes : créer un views.py)  (et cleaner) code.

if __name__ == '__main__':
    app.run()

