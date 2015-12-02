from pymongo import MongoClient, DESCENDING, ASCENDING

class MongoStore:
    """ Mongo Data accessor """
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
    def __str__(self):
        return "MongoStore " + str(self.config)

    def close(self):
        pass

    def users(self, start, end):
        coll = self._connect().users.find(skip=start, limit=end-start)
        return [self._format_user(t) for t in coll.sort("created_at", ASCENDING)]

    def followers(self, handle, start, end):
        coll = self._connect().followings.find({'handle': handle})
        return [(res['from'], res['created_at']) for res in coll.sort("created_at", ASCENDING)]

    def followings(self, handle, start, end):
        coll = self._connect().followings.find({'from': handle})
        return [(res['handle'], res['created_at']) for res in coll.sort("created_at", ASCENDING)]

    def create_following(self, followed_handle, handle, created_at):
        self._connect().followings.insert_one({"handle": followed_handle, "from": handle, "created_at": created_at})
        return True

    def delete_following(self, followed_handle, handle):
        self._connect().followings.delete_many({"handle": followed_handle, "from": handle})
        return True

    def get_user_by_handle(self, handle):
        res = self._connect().users.find_one({"handle": handle})
        return self._format_user(res)

    def _format_user(self, res):
        if res is None:
            return None
        return (res['handle'], res['password'], res['token'], res['created_at'])

    def create_user(self, handle, password, token, created_at):
        self._connect().users.insert_one({"handle": handle, "password": password, "token": token, "created_at": created_at})
        return True

    def create_tweet(self, content, handle, created_at):
        self._connect().tweets.insert_one({"handle": handle, "content": content, "created_at": created_at})
        return True

    def reading_list(self, handle, start, end):
        query = self._connect().followings.find({'from': handle})
        followed = [res["handle"] for res in query]
        coll = self._connect().tweets.find({"handle": {"$in": followed}}, skip=start, limit=end-start)
        return [self._format_tweet(t) for t in coll.sort("created_at", DESCENDING)]

    def tweets(self, handle, start, end):
        if handle is None:
            coll = self._connect().tweets.find(skip=start, limit=end-start)
        else:
            coll = self._connect().tweets.find({"handle": handle}, skip=start, limit=end-start)
        return [self._format_tweet(t) for t in coll.sort("created_at", DESCENDING)]

    def _format_tweet(self, res):
        if res is None:
            return None
        return (res['content'], res['handle'], res['created_at'])

    def _connect(self):
        if not hasattr(self, 'connection'):
            self.connection = MongoClient(self.config.get('uri'))[self.config['db']]
        return self.connection
