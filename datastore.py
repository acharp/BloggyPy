import itertools
import datetime
from werkzeug import generate_password_hash, check_password_hash
import uuid
import sys

from mongostore import MongoStore

class Paginated(list):
    """ A colloction for list that have been paginated"""
    def __init__(self, iterable, per_page):
        v = list(iterable)
        self.has_more = len(v) > per_page
        list.__init__(self, v[0:per_page])

class DataStore:
    """ Data accessor """
    def __init__(self, name, config, logger):
        self.logger = logger
        self.store = getattr(sys.modules[__name__], name + "Store")(config, logger)

    def __str__(self):
        return "Datastore embeding " + str(self.store)
    
    def close(self):
        """Teardown datastore"""
        self.store.close()

    def user_logins(self, page):
        """ Get the users login list"""
        start, end, per_page = self._paginate(page)
        raw =  self.store.users(start, end)
        return Paginated(map(lambda x : x[0], raw), per_page)

    def get_user_by_handle(self, handle):
        """Find a user by its handle"""
        return self.store.get_user_by_handle(handle)

    def create_user(self, handle, password):
        """Signup a new user"""
        password = generate_password_hash(password)
        token = uuid.uuid4().hex
        t = datetime.datetime.now()
        self.store.create_user(handle, password, token, t)
        return {"handle": handle, "token": token}

    def create_tweet(self, content, handle):
        """Post a new tweet"""
        t = datetime.datetime.now()
        if self.store.create_tweet(content, handle, t):
            return self._format_tweet((content, handle, t))
        else:
            return None

    def authenticate_token(self, handle, token):
        """Autenticate handle using token"""
        user = self.get_user_by_handle(handle)
        if user is None:
            return False
        return user[2] == token

    def authenticate(self, handle, password):
        """Autenticate handle using password"""
        user = self.get_user_by_handle(handle)
        if user is None:
            return None
        if check_password_hash(user[1], password):
            return {"handle": handle, "token": user[2]}
    
    def tweets(self, handle, page):
        """ Get the tweets list (can be retricted to those of handle)"""
        start, end, per_page = self._paginate(page)
        raw = self.store.tweets(handle, start, end)
        return Paginated(map(self._format_tweet, raw), per_page)

    def reading_list(self, handle, page):
        """ Get the tweets from account followed"""
        start, end, per_page = self._paginate(page)
        raw = self.store.reading_list(handle, start, end)
        return Paginated(map(self._format_tweet, raw), per_page)

    def _format_tweet(self, tweet):
        return {"content": tweet[0], "by": tweet[1], "at": tweet[2]}

    def followers(self, handle, page):
        """ Get the followers list (who is following handle)"""
        start, end, per_page = self._paginate(page)
        raw = self.store.followers(handle, start, end)
        return Paginated(map(self._format_following, raw), per_page)

    def followings(self, handle, page):
        """ Get the followings list (who handle follows)"""
        start, end, per_page = self._paginate(page)
        raw = self.store.followings(handle, start, end)
        return Paginated(map(self._format_following, raw), per_page)

    def _format_following(self, following):
        return {"user": following[0], "at": following[1]}

    def create_following(self, followed_handle, follower_handle):
        """follow followed_handle by follower_handle"""
        t = datetime.datetime.now()
        res= self.store.create_following(followed_handle, follower_handle, t)
        if res:
            return self._format_following((followed_handle, t))
        else:
            return None

    def delete_following(self, followed_handle, follower_handle):
        """Unfollow followed_handle by follower_handle"""
        res= self.store.delete_following(followed_handle, follower_handle)
        if res:
            return True
        else:
            return False
    
    def _paginate(self, page):
        if page < 1:
            page = 1
        per_page = 30
        return ((page - 1)*per_page, per_page*page + 1, per_page)

