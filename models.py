# -*- coding: utf-8 -*-

from werkzeug.security import check_password_hash 


class User():

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.tweets = []
        self.followings = []
        self.followers = []
        #self.email =
        #self.avatar =

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.username

    @staticmethod
    def validate_login(bdd_pwd, given_pwd):
        return check_password_hash(bdd_pwd, given_pwd)


class Tweet():

    def __init__(self, content):
        self.content = content
        #self.date =
        #self.location =
