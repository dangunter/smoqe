smoqe: Simplified MongoDB Query Expressions
============================================

This module translates from a simple human-readable syntax
into a MongoDB query. Currently it does no execution of
the query -- use something like pymongo for that (as shown below).

For sample usage, etc., see the docs.

But here's a teaser, showing how you might use it, standalone..

	import smoqe
    q = smoqe.to_mongo("a > 0 and b > 0 and c type string")
    print(q)
    {'a': {'$gt': 0}, 'b': {'$gt': 0}, '$where': 'typeof this.c == "string"'}


..or with pymongo:

    # use the smoqe replacement for MongoClient
    from smoqe import MongoClient
    # treat just like MongoClient instances
    client = MongoClient()
	coll = client.test.test
    # now you can use the simplified syntax in queries
	coll.find("a > 0 and b > 0 and c type string")


Happy Trails!

-DanG
