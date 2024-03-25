import typing
import unittest

import myrrh.warehouse.registry
import myrrh.warehouse.items


class GenericBasicTests(unittest.TestCase):
    def test_basic_item_dom_set(self):
        import datetime

        dom = datetime.datetime.now() + datetime.timedelta(days=4)
        self.assertRaises(ValueError, myrrh.warehouse.registry.GenericItem, DOM=dom)

        dom = datetime.datetime.now() + datetime.timedelta(days=-4)
        c = myrrh.warehouse.registry.GenericItem(DOM=dom)
        self.assertEqual(dom, c.DOM)

    def test_basic_item_sll_set(self):
        import datetime

        c = myrrh.warehouse.registry.GenericItem(SLL=datetime.timedelta(days=4))

        self.assertEqual(c.UBD, c.DOM + datetime.timedelta(days=4))
        self.assertEqual(c.SLL, datetime.timedelta(days=4))

    def test_basic_item_udb_set(self):
        import datetime

        UBD = datetime.datetime.now() + datetime.timedelta(days=4)
        c = myrrh.warehouse.registry.GenericItem(UBD=UBD)

        self.assertEqual(c.UBD, UBD)
        self.assertEqual(c.SLL, None)

    def test_basic_item_sll_and_udb_set(self):
        import datetime

        now = datetime.datetime.now()
        c = myrrh.warehouse.registry.GenericItem(UBD=now, SLL=datetime.timedelta(days=4))

        self.assertEqual(c.UBD, now)
        self.assertEqual(c.SLL, datetime.timedelta(days=4))

    def test_basic_item_validity_unset(self):
        c = myrrh.warehouse.registry.GenericItem()

        self.assertEqual(c.UBD, None)
        self.assertEqual(c.SLL, None)
        self.assertEqual(c.UBD, None)

    def test_basic_item_sll_negative(self):
        import datetime

        self.assertRaises(
            ValueError,
            myrrh.warehouse.registry.GenericItem,
            SLL=datetime.timedelta(-5),
        )

    def test_basic_json_dump(self):
        import json

        c = myrrh.warehouse.registry.GenericItem()
        j = c.model_dump_json()

        c_from_j = json.loads(j)

        self.assertIn("type_", c_from_j)
        self.assertNotIn("DOM", c_from_j)
        self.assertNotIn("SLL", c_from_j)
        self.assertNotIn("UBD", c_from_j)

    def test_basic_encoding(self):
        class DecodedItem(myrrh.warehouse.registry.BaseItem[typing.Literal["decoded"]]):
            mystring: myrrh.warehouse.item.DecodedStr
            mydict: myrrh.warehouse.item.DecodedDict
            mylist: myrrh.warehouse.item.DecodedList
            mystringb: myrrh.warehouse.item.DecodedStr
            mydictb: myrrh.warehouse.item.DecodedDict
            mylistb: myrrh.warehouse.item.DecodedList

        item = DecodedItem(
            encoding="utf16",
            encerrors="ignore",
            mystring="myvalue",
            mydict={"mykey": "myvalue"},
            mylist=["myvalue0", "myvalue1"],
            mystringb=b"myvalueb",
            mydictb={b"mykeyb": b"myvalueb"},
            mylistb=[b"myvalue0b", b"myvalue1b"],
        )

        item.model_dump()
        item.model_json_schema()
        item.model_dump_json()

        self.assertEqual(item.encoding, "utf16")
        self.assertEqual(item.encerrors, "ignore")

        for v in (item.mystring, item.mydict, item.mylist):
            self.assertEqual(item.mystring._encodings, (item.encoding, item.encerrors))

        self.assertEqual(item.mystring.e, "myvalue".encode("utf16"))
        self.assertEqual(item.mydict.e, {"mykey".encode("utf16"): "myvalue".encode("utf16")})
        self.assertEqual(item.mylist.e, ["myvalue0".encode("utf16"), "myvalue1".encode("utf16")])

        item.mydictb.d
        self.assertEqual(item.mystringb, b"myvalueb".decode("utf16", errors="ignore"))
        self.assertEqual(item.mydictb, {b"mykeyb".decode("utf16", errors="ignore"): b"myvalueb".decode("utf16", errors="ignore")})
        self.assertEqual(item.mylistb, [b"myvalue0b".decode("utf16", errors="ignore"), b"myvalue1b".decode("utf16", errors="ignore")])

    def test_basic_delete(self):
        class Item(myrrh.warehouse.registry.GenericItem):
            mystring: str = "this is a string"
            mydict: dict = {"a": "b", "c": {"d": "e"}, "f": ["g", "h"]}
            mylist: list[str] = ["l0", "l1", "l2"]

        item = Item()

        item.delete("mydict.c.d")
        self.assertEqual(item.mydict["c"], {})
        item.delete("mystring")
        self.assertEqual(
            item.model_dump(),
            {
                "type_": "generic",
                "DOM": None,
                "SLL": None,
                "UBD": None,
                "UTC": None,
                "label": "",
                "tags": "",
                "description": "",
                "encoding": "utf8",
                "encerrors": "strict",
                "mydict": {"a": "b", "c": {}, "f": ["g", "h"]},
                "mylist": ["l0", "l1", "l2"],
            },
        )

        item["mystring"] = "new string"
        self.assertIn("mystring", item.model_fields_set)
        item.delete("mystring")
        self.assertNotIn("mystring", item.model_fields_set)

        item.delete("mydict.a")
        self.assertIn("mydict", item.model_fields_set)
        self.assertEqual(item.mydict, {"c": {}, "f": ["g", "h"]})

        item.delete("mydict.f.1")
        self.assertEqual(item.mydict, {"c": {}, "f": ["g"]})
        self.assertIn("mydict", item.model_fields_set)

        item.delete("mylist.1")
        self.assertIn("mylist", item.model_fields_set)
        self.assertEqual(item.mylist, ["l0", "l2"])

    def test_basic_update(self):
        class Item(myrrh.warehouse.registry.GenericItem):
            mystring: str = "this is a string"
            mydict: dict = {"a": "b", "c": {"d": "e"}, "f": ["g", "h"]}
            mylist: list[str] = ["l0"]
            mydecoded: myrrh.warehouse.item.DecodedList = ["d0", "d1"]

        item = Item()

        item.update("mystring", "this is a new string")
        self.assertIn("mystring", item.model_fields_set)
        self.assertEqual(item.mystring, "this is a new string")

        item.update("mydict.a", "i")
        self.assertEqual(item.mydict["a"], "i")
        self.assertIn("mydict", item.model_fields_set)

        item.model_fields_set.remove("mydict")
        item.update("mydict.c.d", "j")
        self.assertIn("mydict", item.model_fields_set)
        self.assertEqual(item.mydict["c"]["d"], "j")

        item.model_fields_set.remove("mydict")
        item.update("mydict.f.1", "l1")
        self.assertIn("mydict", item.model_fields_set)
        self.assertEqual(item.mydict["f"][1], "l1")

        item.update("mylist.0", "c0")
        self.assertEqual(item.mylist[0], "c0")
        self.assertIn("mylist", item.model_fields_set)

        item.update("mylist", ["l1", "l2"])
        self.assertEqual(item.mylist, ["c0", "l1", "l2"])
        item.update("mydict", {"l": "another string"})
        self.assertEqual(item.mydict, {"a": "i", "c": {"d": "j"}, "f": ["g", "l1"], "l": "another string"})
        item.update("mydict.", {"l": "another string"})
        self.assertEqual(item.mydict, {"l": "another string"})

        item.update("", {"myadded": "string"})

        self.assertEqual(item.model_fields_set, {"mystring", "mydict", "mylist", "type_", "myadded"})
        self.assertEqual(
            item.model_dump(),
            {
                "type_": "generic",
                "DOM": None,
                "SLL": None,
                "UBD": None,
                "UTC": None,
                "label": "",
                "tags": "",
                "description": "",
                "encoding": "utf8",
                "encerrors": "strict",
                "mystring": "this is a new string",
                "mydict": {"l": "another string"},
                "mylist": ["c0", "l1", "l2"],
                "myadded": "string",
                "mydecoded": ["d0", "d1"],
            },
        )
        self.assertRaises(TypeError, item.update, "mylist.1", 1)

        item["mydecoded.+"] = "d2"
        self.assertEqual(item.mydecoded, ["d0", "d1", "d2"])
        item["mydecoded.+2"] = "d2.5"
        self.assertEqual(item.mydecoded, ["d0", "d1", "d2.5", "d2"])

        item["mydecoded"] = ["dN"]
        self.assertTrue(isinstance(item.mydecoded, myrrh.warehouse.items.DecodedList))


class SystemBasicTests(unittest.TestCase):
    def test_basic_create(self):
        c = myrrh.warehouse.items.System()

        self.assertEqual(c.type_, "system")

    def test_basic_set_propreties(self):
        c = myrrh.warehouse.items.System(machine="i386")

        c.model_json_schema()
        c.model_dump()

        self.assertEqual(c.machine, "i386")

    def test_basic_parse(self):
        c = myrrh.warehouse.items.System.model_validate({"machine": "msx2"})
        self.assertEqual(c.type_, "system")
        self.assertEqual(c.machine, "msx2")


class CredentialBasicTests(unittest.TestCase):
    def test_basic_create(self):
        c = myrrh.warehouse.items.Credentials()

        self.assertEqual(c.type_, "credentials")

    def test_basic_cred(self):
        c = myrrh.warehouse.items.Credentials(credentials=[{"login": "root", "password": "pAssworD"}])

        c.model_json_schema()
        c.model_dump()

        self.assertTrue(c.credentials[0].password.startswith("fernet"))


class NoneItemBasicTests(unittest.TestCase):
    def test_basic(self):
        self.assertFalse(myrrh.warehouse.items.NoneItem)
        self.assertIs(myrrh.warehouse.items.NoneItem.a.b.c, myrrh.warehouse.items.NoneItem)


if __name__ == "__main__":
    unittest.main()
