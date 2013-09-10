"""
Test expressions
"""
__author__ = 'dang'

import unittest
import smoqe


class TestCase(unittest.TestCase):

    V = dict(v1='abba', v2='beebs', v3='coco')

    def _q(self, expr, expected):
        mx = smoqe.to_mongo(expr)
        self.assertEqual(mx, expected, "Expression ({e}).to_mongo() = {x}\nbut expected: {y}".format(
            e=expr, x=mx, y=expected))

    def test_q1(self):
        "Query 1"
        v = self.V
        self._q('{v1} > 12 and {v2} <= 3 or {v3} type int'.format(**v),
                {'$or': [{v['v1']: {'$gt': 12}, v['v2']: {'$lte': 3}},
                         {'$where': 'typeof this.{v3} == "number"'.format(**v)}]})

    def test_q2(self):
        "Query 2"
        v = self.V
        self._q('{v1} > 12 and {v2} <= 3 or {v3} type int or {v1} = "foo" and {v2} exists false'.format(**v),
                {'$or': [{v['v1']: {'$gt': 12}, v['v2']: {'$lte': 3}},
                         {'$where': 'typeof this.{v3} == "number"'.format(**v)},
                         {v['v1']: "foo", v['v2']: {'$exists': False}}]})


if __name__ == '__main__':
    unittest.main()
