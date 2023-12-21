import unittest
import myrrh.warehouse.registry
import myrrh.warehouse.item


class GenericBasicTests(unittest.TestCase):
    def test_basic_item_dom_set(self):
        import datetime

        dom = datetime.datetime.now() + datetime.timedelta(days=4)
        self.assertRaises(ValueError, myrrh.warehouse.registry.GenericItem, type_="new_kind", DOM=dom)

        dom = datetime.datetime.now() + datetime.timedelta(days=-4)
        c = myrrh.warehouse.registry.GenericItem(type_="new_kind", DOM=dom)
        self.assertEqual(dom, c.DOM)

    def test_basic_item_sll_set(self):
        import datetime

        c = myrrh.warehouse.registry.GenericItem(type_="new_kind", SLL=datetime.timedelta(days=4))

        self.assertEqual(c.UBD, c.DOM + datetime.timedelta(days=4))
        self.assertEqual(c.SLL, datetime.timedelta(days=4))

    def test_basic_item_udb_set(self):
        import datetime

        UBD = datetime.datetime.now() + datetime.timedelta(days=4)
        c = myrrh.warehouse.registry.GenericItem(type_="new_kind", UBD=UBD)

        self.assertEqual(c.UBD, UBD)
        self.assertEqual(c.SLL, None)

    def test_basic_item_sll_and_udb_set(self):
        import datetime

        now = datetime.datetime.now()
        c = myrrh.warehouse.registry.GenericItem(type_="new_kind", UBD=now, SLL=datetime.timedelta(days=4))

        self.assertEqual(c.UBD, now)
        self.assertEqual(c.SLL, datetime.timedelta(days=4))

    def test_basic_item_validity_unset(self):
        c = myrrh.warehouse.registry.GenericItem(type_="new_kind")

        self.assertEqual(c.UBD, None)
        self.assertEqual(c.SLL, None)
        self.assertEqual(c.UBD, None)

    def test_basic_item_sll_negative(self):
        import datetime

        self.assertRaises(
            ValueError,
            myrrh.warehouse.registry.GenericItem,
            type_="new_kind",
            SLL=datetime.timedelta(-5),
        )

    def test_basic_json_dump(self):
        import json

        c = myrrh.warehouse.registry.GenericItem(type_="new_kind")
        j = c.model_dump_json()

        c_from_j = json.loads(j)

        self.assertIn("type_", c_from_j)
        self.assertNotIn("DOM", c_from_j)
        self.assertNotIn("SLL", c_from_j)
        self.assertNotIn("UBD", c_from_j)

    def test_basic_items(self):
        for cls in myrrh.warehouse.registry.ItemRegistry().items.values():
            item = cls()

            self.assertEqual(item.type_, cls._type_())


class SystemBasicTests(unittest.TestCase):
    def test_basic_create(self):
        c = myrrh.warehouse.System()

        self.assertEqual(c.type_, "system")

    def test_basic_set_propreties(self):
        c = myrrh.warehouse.System(cwd="/root")

        c.model_json_schema()
        c.model_dump()

        self.assertEqual(c.cwd, "/root")

    def test_basic_parse(self):
        c = myrrh.warehouse.System.model_validate({"cwd": "/root"})
        self.assertEqual(c.type_, "system")
        self.assertEqual(c.cwd, "/root")


class CredentialBasicTests(unittest.TestCase):
    def test_basic_create(self):
        c = myrrh.warehouse.Credentials()

        self.assertEqual(c.type_, "credentials")

    def test_basic_cred(self):
        c = myrrh.warehouse.Credentials(credentials=[{"login": "root", "password": "pAssworD"}])

        c.model_json_schema()
        c.model_dump()

        self.assertTrue(c.credentials[0].password.startswith("fernet"))


class NoneItemBasicTests(unittest.TestCase):
    def test_basic(self):
        self.assertFalse(myrrh.warehouse.item.NoneItem)
        self.assertIs(myrrh.warehouse.item.NoneItem.a.b.c, myrrh.warehouse.item.NoneItem)


if __name__ == "__main__":
    unittest.main()
