import unittest

from myrrh.core.services.groups import MyrrhGroup, myrrh_group


class TestGroup(unittest.TestCase):
    def test_basic(self):
        g = MyrrhGroup("a", "b")
        self.assertIsInstance(g, MyrrhGroup)

    def test_basic_attr(self):
        g = MyrrhGroup(",", ";")

        gs = g.join("abc")
        gas = g._as_.join("abc")

        self.assertEqual(gs._t_, gas._t_)

    def test_basic_func(self):
        def replace1(s):
            return s.replace("1", "[one]")

        g = MyrrhGroup("2354891251478", "2354891251478", keys=("a", "b"))

        gs = myrrh_group(replace1)(g)
        gas = myrrh_group(replace1)._as_(g)

        self.assertEqual(gs._t_, gas._t_)

    def test_basic_iter(self):
        g = MyrrhGroup("012345678", "abcdefghi", keys=("num", "string"))
        i0, i1 = iter("012345678"), iter("abcdefghi")

        for v in g:
            self.assertEqual(v._t_, (next(i0), next(i1)))

        g = MyrrhGroup(0, 1, keys=("a", "b"))
        self.assertRaises(TypeError, iter, g)

    def test_basic_subscript(self):
        g = MyrrhGroup(list("012345678"), list("abcdefghi"), keys=("num", "string"))
        self.assertEqual(g[0]._t_, ("0", "a"))

        g[0] = "x"
        self.assertEqual(g[0]._t_, ("x", "x"))

        g = MyrrhGroup(1, 2, keys=("num", "string"))
        self.assertRaises(TypeError, lambda: g[0])


if __name__ == "__main__":
    unittest.main()
