"""
Simple example of usage with pymongo, with drop-in MongoClient
"""
__author__ = 'Dan Gunter <dkgunter@lbl.gov>'
__date__ = '9/6/13'

try:
    import pymongo
except ImportError:
    import sys
    sys.stderr.write("Unable to import pymongo, which is required for this example. Skipping..\n")
    sys.exit(1)
import smoqe

client = smoqe.MongoClient()
coll = client.test.test
# create/populate DB
coll.remove()
coll.insert([{'n': 1, 'a': 1, 'b': 2, 'c': 'hello'},
             {'n': 2, 'a': -1, 'b': 3.14, 'c': 3},
             {'n': 3, 'a': 2, 'b': 99, 'c': 4}])
# perform queries
r = coll.find("a > 0 and b > 0 and c type string")
print(r[0]['n'])
# prints: 1
r = coll.find("a < 0 or c = 4")
print("{},{}".format(r[0]['n'], r[1]['n']))
# prints: 2,3
