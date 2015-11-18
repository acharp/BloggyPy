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
tweets = db.tweets


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
    return user_logged + " is logged in \n" 


# Add a tweet, by the logined user.
@app.route('/<username>/tweets', methods=['POST'])
@login_required
def add_tweet(username):

    if username != current_user.get_id():
        return "Actual authenticated user doesn't match with " + username 

    if not request.json :
        abort(400, "JSON expected in the request body.")
    tweet = request.get_json()  

    tweet_id = tweets.insert_one(tweet).inserted_id
    
    try:
        user_tweets = users.find_one({'username': username})['tweets']
    # Handle the case when it's the first tweet of the user
    except KeyError:
        user_tweets=[]

    user_tweets.append(tweet_id)
    res = users.update_one({'username': username}, {'$set': {'tweets': user_tweets}})
    if res:
        return username + " tweeted " + tweet['content']
    else:
        return "error occured while tweeting"


# Retrive all the tweets of the user <username>
@app.route('/<username>/tweets')
def return_user_tweets(username):

    #TESTER SI l'USERNAME EXISTE EN BASE

    try:
        user_tweets_id = users.find_one({'username': username})['tweets']
    except KeyError:
        return "This user doesn't have any tweet"
    user_tweets_content = []
    for tweetid in user_tweets_id:
        user_tweets_content.append(tweets.find_one({'_id': tweetid})['content'])
    res = {'username': username, 'tweets': user_tweets_content}
    return jsonify(res)


# Retrive all the tweets in the database
@app.route('/tweets')
def return_tweets():
    list_tweets=[]
    for tweet in db.tweets.find():
        list_tweets.append(tweet['content'])
    dict_tweets = {'tweets' : list_tweets}
    return jsonify(dict_tweets)


# Follow someone
@app.route('/<username>/followings', methods=['POST'])
@login_required
def follow_user(username):
    if username != current_user.get_id():
        return "Actual authenticated user doesn't match with " + username

    # EMPECHER DE POUVOIR SE SUIVRE SOIT-MEME et EMPECHER DE POUVOIR SUIVRE PLUSIEURS FOIS LE MEME USER

    if not request.json :
        abort(400, "JSON expected in the request body.")
    user_to_follow = request.get_json()

    try:
        user_follows = users.find_one({'username': current_user.get_id()})['follow']
    except KeyError:
        user_follows = []

    user_follows.append(user_to_follow['username'])
    res = users.update_one({'username': username}, {'$set': {'follow': user_follows}})
    if res:
        return username + " is now following " + user_to_follow['username']
    else:
        return "error occured while trying to follow " + user_to_follow('username') 


# Unfollow someone
@app.route('/<username>/followings', methods=['DELETE'])
@login_required
def unfollow_user(username):
    if username != current_user.get_id():
        return "Actual authenticated user doesn't match with " + username

    if not request.json :
        abort(400, "JSON expected in the request body.")
    user_to_unfollow = request.get_json()

    try:
        user_follows = users.find_one({'username': current_user.get_id()})['follow']
    except KeyError:
        return "User " + username + " doesn't follow anybody"

    # A CONTINUER




# Retrieve followers of the user <username>
#@app.route('/<username>/followers')


# Retrieve followings of the user <username>
#@app.route('/<username>/followings')


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

