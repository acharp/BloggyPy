# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, abort, redirect, url_for, flash
from pymongo import MongoClient
from bson import ObjectId
import json
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user
from models import User
# Pour le moment on ne hash pas le password, on fera ça dans une seconde version
#from werkzeug.security import generate_password_hash


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


@app.route('/users', methods=['POST'])
def create_user():
# Récupération des paramètres depuis un query string
#    user={}
#    user['name'] = request.args.get('name')
#    user['age'] = request.args.get('age')

# Récupération des paramètres depuis un json
    if not request.json :
        abort(400)
    user = request.get_json() # Renvoie un dict
   
    # Quand on voudra implémenter le hash du password
   #password = user['password']
   #pass_hash = generate_password_hash(password, method='pbkdf2:sha256') 

    # VERIF QUE L'USER N'EXISTE PAS DEJA (test sur le username)
    user_id = users.insert_one(user).inserted_id # Renvoit l'id de l'user inséré, on peut aussi faire un insert sans récupérer l'id
    print("User " + user + "successfully created !\n")

    return str(user_id);


@app.route('/users')
def return_users():
    #one_user = db.users.find_one({"name":"Miguel"}) # Renvoie un user
    list_users=[]
    for user in db.users.find():
        list_users.append(user)
    print(list_users)
    dict_users = { 'users' : list_users}
    return JSONEncoder().encode(dict_users);
    #return jsonify(dict_users) # Fonctionne si on définit nos propres id et qu'on a pas à décoder ObjectId


@app.route('/sessions', methods=['POST'])
def login():
    
    if not request.json:
        abort(400)
    user_to_login = request.get_json()

    user_db = users.find_one({'username': user_to_login['username']})
    if user_db and User.validate_login(user_db['password'], user_to_login['password']):
        user_obj = User(user_db['username'], user_db['password'])
        login_user(user_obj)
        print("User : " + user_db['username'] + " logged in successfully !\n")
        #flash("User : " + user_db['username'] + " logged in successfully !", category='success')
        return "OK le login c'est cool" # A remplacer par un redirect dans une version future 
    print("Wrong username or password ! \n") #flash("Wrong username or password !", category='error')
    return "NON le login c'est pas cool"


@app.route('/logout')
def logout():
    logout_user()
    # return redirect(url_for('login')) # Redirige sur /sessions en GET. A voir si on l'utilise.
    return "Logout OK !"


@app.route('/protected')
@login_required
def protected():
    user_logged = current_user.get_id()
    print(user_logged + " is logged in \n")
    return "Accés avec login OK !"


@lm.user_loader
def load_user(username):
    u = users.find_one({'username': username})
    if not u:
        return None
    return User(u['username'], u['password'])


# Next steps :
# Voir pour l'authentification https://flask-login.readthedocs.org/en/latest/
# Ajouter le champ follow aux users qui contiendra un dict id users followés : date de following 
# Récupérer les followers et les followings, c'est surtout l'aspect requête à la base qui est à réfléchir ici

if __name__ == '__main__':
    app.run()

