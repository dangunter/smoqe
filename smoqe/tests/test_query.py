"""
Test expressions
"""
__author__ = "Dan Gunter"
__copyright__ = "Copyright 2013, LBNL"
__email__ = "dkgunter@lbl.gov"

import unittest
import smoqe


class TestCase(unittest.TestCase):

    V = dict(v1='abba', v2='beebs', v3='coco')

    def _q_expect(self, expr, expected):
        mx = smoqe.to_mongo(expr)
        self.assertEqual(mx, expected, "Expression ({e}).to_mongo() = {x}\nbut expected: {y}".format(
            e=expr, x=mx, y=expected))

    def _q_bad(self, expr):
        self.assertRaises(smoqe.BadExpression, smoqe.to_mongo, expr)

    def _q_ok(self, expr):
        try:
            smoqe.to_mongo(expr)
        except smoqe.BadExpression as err:
            self.fail("Unexpected BadExpression for '{e}'".format(e=expr))

    def test_q1(self):
        "Query 1"
        v = self.V
        self._q_expect('{v1} > 12 and {v2} <= 3 or {v3} type int'.format(**v),
                {'$or': [{v['v1']: {'$gt': 12}, v['v2']: {'$lte': 3}},
                         {'$where': 'typeof this.{v3} == "number"'.format(**v)}]})

    def test_q2(self):
        "Query 2"
        v = self.V
        self._q_expect('{v1} > 12 and {v2} <= 3 or {v3} type int or {v1} = "foo" and {v2} exists false'.format(**v),
                {'$or': [{v['v1']: {'$gt': 12}, v['v2']: {'$lte': 3}},
                         {'$where': 'typeof this.{v3} == "number"'.format(**v)},
                         {v['v1']: "foo", v['v2']: {'$exists': False}}]})


    def test_q3(self):
        "Bad ones"
        map(self._q_bad, ["a <>2", "!a", "and or and", ",,,", [{}]])

    def test_q4(self):
        "Simple good ones"
        map(self._q_ok, ["a = 1", "dude_where_is = 'my car'"])

if __name__ == '__main__':
    unittest.main()
