"""
Wrappers for third-party libs

Usage:

from smoq.wrappers import MongoClient
#
# from here on out it's just pymongo..
#
client = MongoClient()
db = client.some_database
coll = db.some_collection
#
# .. except you can use smoq-style queries:
#
coll.find("beverage = 'beer' and IBU > 20")

"""
__author__ = 'Dan Gunter <dkgunter@lbl.gov>'
__date__ = '9/6/13'

from .query import to_mongo, BadExpression

have_pymongo = False
try:
    import pymongo
    have_pymongo = True
except ImportError:
    pass

if have_pymongo:

    from pymongo.mongo_client import MongoClient as _MongoClient
    from pymongo.database import Database as _Database
    from pymongo.collection import Collection as _Collection

    spec_pos = 1   # which arg

    def smoq_spec(or_id):
        """Run to_mongo() on string or list 'spec' arguments.
        """
        def wrap(fn):
            def wrapped_fn(*args, **kwargs):
                # find spec
                spec, in_args = None, False
                if len(args) > spec_pos:    # 0-th is 'self'
                    spec = args[spec_pos]
                    in_args = True
                elif 'spec' in kwargs:
                    spec = kwargs['spec']
                if spec is not None and (
                        isinstance(spec, str) or isinstance(spec, list)):
                    try:
                        spec = to_mongo(spec)
                        if in_args:
                            args = list(args)
                            args[spec_pos] = spec
                        else:
                            kwargs['spec'] = spec
                    except BadExpression as err:
                        if or_id:
                            pass   # treat as id, so ignore err
                        else:
                            raise pymongo.errors.InvalidOperation(str(err))
                return fn(*args, **kwargs)
            return wrapped_fn
        return wrap

    class Collection(_Collection):
        @smoq_spec(False)
        def find(self, *args, **kwargs):
            return _Collection.find(self, *args, **kwargs)

        @smoq_spec(True)
        def find_one(self, *args, **kwargs):
            return _Collection.find(self, *args, **kwargs)

        @smoq_spec(False)
        def remove(self, *args, **kwargs):
            return _Collection.remove(self, *args, **kwargs)

        @smoq_spec(True)
        def update(self, *args, **kwargs):
            return _Collection.update(self, *args, **kwargs)

    class Database(_Database):
        def __getitem__(self, item):
            return Collection(self, item)
        def __getattr__(self, item):
            return Collection(self, item)

    class MongoClient(_MongoClient):
        """Drop-in replacement for pymongo.MongoClient.

        Three functions are enabled:

        * find
        * update
        * remove

        In each case, the `spec` argument will be transparently
        pre-processed as a smoqe query if it is a string or list.
        """
        def __getitem__(self, item):
            return Database(self, item)
        def __getattr__(self, item):
            return Database(self, item)
