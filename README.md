smoq
====

`smoq` stands for "Simple MongoDB Query interface".

This module translates from a simple human-readable syntax
into a MongoDB query. Currently it does no execution of
the query -- use something like pymongo for that.

For sample usage, etc., see the 'docs' directory.
But here's a teaser, showing how you might use it with
pymongo:

	import pymongo
	import smoq
	client = pymongo.MongoClient()
	coll = client.test.test
	# create/populate DB
	coll.remove()
	coll.insert([{'n': 1, 'a': 1,  'b': 2,    'c': 'hello'},
	             {'n': 2, 'a': -1, 'b': 3.14, 'c': 3},
	             {'n': 3, 'a': 2,  'b': 99,   'c': 4}])
	# perform queries
	q = smoq.to_mongo("a > 0 and b > 0 and c type string")
	r = coll.find(q)
	print(r[0]['n'])
	# prints: 1
	q = smoq.to_mongo("a < 0 or c = 4")
	r = coll.find(q)
	print("{},{}".format(r[0]['n'], r[1]['n']))
	# prints: 2,3


Happy Trails!

-DanG