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



# To decode ObjectId when needed.
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)



# Classic root and home url
@app.route('/')
@app.route('/home')
def hello_world():
    return "Hello World! Welcome to BloggyPy!"



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
        return "User " + user['username'] + " successfully created !\n"
    else :
        abort(400, "This user already exists in the database.")



# Retrieving list of all users registered
@app.route('/users')
def return_users():

    list_users=[]
    for user in db.users.find():
        list_users.append(user['username'])

    dict_users = { 'users' : list_users}
    return jsonify(dict_users)



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

    # Check if authenticated user match with <username> parameter
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
    users.update_one({'username': username}, {'$set': {'tweets': user_tweets}})
    return username + " tweeted " + tweet['content']



# Retrive all the tweets of the user <username>
@app.route('/<username>/tweets')
def return_user_tweets(username):

    # Check if <username> exists in our database
    if (users.find_one({'username': username}) == None):
        return username + " isn't a registrated user"

    # Check and retrieve <username> tweets id
    try:
        user_tweets_id = users.find_one({'username': username})['tweets']
    except KeyError:
        return "This user doesn't have any tweet"

    # List tweets content
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

    if not request.json :
        abort(400, "JSON expected in the request body.")
    user_to_follow = request.get_json()

    if (users.find_one({'username': user_to_follow['username']}) == None):
        return user_to_follow['username'] + " isn't a registrated user"

    # Forbid following myself 
    if username == user_to_follow['username']:
        return "You're such a self-lover that you want to follow yourself ? Really..."

    # Add followings to actual authenticated user
    try:
        user_followings = users.find_one({'username': username})['followings']
    except KeyError:
        user_followings = []
    user_followings.append(user_to_follow['username'])
    users.update_one({'username': username}, {'$set': {'followings': user_followings}})

    # Add authenticated user as follower of the user past in the json
    try:
        userjson_followers = users.find_one({'username': user_to_follow['username']})['followers']
    except KeyError:
        userjson_followers = []
    userjson_followers.append(username)
    users.update_one({'username': user_to_follow['username']}, {'$set': {'followers': userjson_followers}})

    return username + " is now following " + user_to_follow['username']



# Unfollow someone
@app.route('/<username>/followings', methods=['DELETE'])
@login_required
def unfollow_user(username):

    if username != current_user.get_id():
        return "Actual authenticated user doesn't match with " + username

    if not request.json :
        abort(400, "JSON expected in the request body.")
    user_to_unfollow = request.get_json()

    if (users.find_one({'username': user_to_unfollow['username']}) == None):
        return user_to_unfollow['username'] + " isn't a registrated user"

    try:
        user_followings = users.find_one({'username': username})['followings']
    except KeyError:
        return username + " isn't following anybody"

    # If the follow relation exists, we delete the followings from authenticated user and the followers from the user past in the json
    if user_to_unfollow['username'] in user_followings:
        user_followings.remove(user_to_unfollow['username'])
        userjson_followers = users.find_one({'username': user_to_unfollow['username']})['followers']
        userjson_followers.remove(username)
    else:
        return username + " isn't following " + user_to_unfollow['username']

    # Update the database
    users.update_one({'username': username}, {'$set': {'followings': user_followings}}) 
    users.update_one({'username': user_to_unfollow['username']}, {'$set': {'followers': userjson_followers}})

    return username + " doesn't follow " + user_to_unfollow['username'] + " anymore"



# Retrieve followers of the user <username>
@app.route('/<username>/followers')
def return_followers(username):

    try:
        user_followers = users.find_one({'username': username})['followers']
    except KeyError:
        return username + " hasn't any follower"

    res = {'username': username, 'followers': user_followers}
    return jsonify(res)



# Retrieve followings of the user <username>
@app.route('/<username>/followings')
def return_followings(username):

    try:
        user_followings = users.find_one({'username': username})['followings']
    except KeyError:
        return username + " isn't following anybody"

    res = {'username': username, 'followings': user_followings}
    return jsonify(res)



# Retrive all the tweets of the followings of the authenticated user
@app.route('/<username>/reading_list')
@login_required
def return_readlist(username):

    if username != current_user.get_id():
        return "Actual authenticated user doesn't match with " + username

    try:
        user_followings = users.find_one({'username': username})['followings']
    except KeyError: 
        return username + " isn't following anybody"

    # List all the id tweets we have to add to the reading_list
    tweetid_list=[]
    for following in user_followings:
        try:
            following_tweets = users.find_one({'username': following})['tweets']
            for tweetid in following_tweets:
                tweetid_list.append(tweetid)
        except KeyError:
            # Handle the case when we follow someone who has never posted a tweet
            pass

    # Create the reading_list with the content of the tweets
    tweets_list=[]
    for tweetid in tweetid_list:
        tweets_list.append(tweets.find_one({'_id': tweetid})['content'])

    res = {'username': username, 'reading list': tweets_list}
    return jsonify(res)



# Method to instanciate an user from database. Used in login().
@lm.user_loader
def load_user(username):
    u = users.find_one({'username': username})
    if not u:
        return None
    return User(u['username'], u['password'])



if __name__ == '__main__':
    app.run()

