# -*- coding: utf-8 -*-

# Première version sans hash, on va faire avec le pwd en clair pour le moment
#from werkzeug.security import check_password_hash 

class User():

   #str userid 

   #str server
   #avatar =
   #email =
   #list tweets
   #dict follow

    def __init__(self, username, password):
        self.username = username
        self.password = password

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
        if bdd_pwd == given_pwd:
            return True
        return False
