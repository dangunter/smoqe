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

    from smoqe.wrappers import MongoClient
	client = MongoClient()
	coll = client.test.test
    #
	# create/populate DB
    #
	coll.remove()
	coll.insert([{'n': 1, 'a': 1,  'b': 2,    'c': 'hello'},
	             {'n': 2, 'a': -1, 'b': 3.14, 'c': 3},
	             {'n': 3, 'a': 2,  'b': 99,   'c': 4}])
    #
	# perform queries
    #
	r = coll.find("a > 0 and b > 0 and c type string")
	print(r[0]['n'])
	# prints: 1
	r = coll.find("a < 0 or c = 4")
	print("{},{}".format(r[0]['n'], r[1]['n']))
	# prints: 2,3


Happy Trails!

-DanG
