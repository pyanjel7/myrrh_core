import typing
import unittest

from myrrh.factory import Assembly

from myrrh.provider.registry import ProviderRegistry
from myrrh.warehouse.registry import ItemRegistry


class AssemblyTest(unittest.TestCase):
    def test_basic_build_local(self):
        p_local = ProviderRegistry().get("local")()

        f = Assembly.fromProvider(p_local)
        e = f.build()
        f_from_e = f.fromEntity(e, only_predefined=False)

        self.assertEqual(f.supply, f_from_e.supply)
        self.assertEqual(e.cfg.system, f_from_e.get_item("system"))
        self.assertEqual(e.cfg.id, f_from_e.get_item("id"))

    def test_basic_build_local_with_predefined(self):
        f = Assembly(
            supply={"paths": ["**/local"]},
            warehouse=[{"type_": "system", "label": "mylabel"}],
        )
        e = f.build()
        f_from_e = f.fromEntity(e, only_predefined=False)

        self.assertEqual(f.supply, f_from_e.supply)
        self.assertEqual(e.cfg.system, f_from_e.get_item("system"))
        self.assertEqual(e.cfg.system.label, "mylabel")
        self.assertEqual(e.cfg.id, f_from_e.get_item("id"))

    def test_basic_settings_raw(self):
        c = Assembly.fromRaw(
            """{
            "supply" : { "paths" : ["**/local"]},
            "warehouse" : [
                { "type_" : "system"},
                { "type_" : "credentials"},
                { "type_" : "id"},
                { "type_" : "host"},
                { "type_" : "new_kind"}
            ]
        }"""
        )

        self.assertIsInstance(c.supply, ItemRegistry().FactorySupply)
        self.assertIsInstance(c.warehouse[0], ItemRegistry().system)
        self.assertIsInstance(c.warehouse[1], ItemRegistry().credentials)
        self.assertIsInstance(c.warehouse[2], ItemRegistry().id)
        self.assertIsInstance(c.warehouse[3], ItemRegistry().host)
        self.assertIsInstance(c.warehouse[4], ItemRegistry().generic)

    def test_basic_settings_init(self):
        c = Assembly(
            supply={"paths": ["**/local"]},
            warehouse=[
                {"type_": "system"},
                {"type_": "credentials"},
                {"type_": "id"},
                {"type_": "host"},
                {"type_": "new_kind"},
            ],
        )

        self.assertIsInstance(c.supply, ItemRegistry().FactorySupply)
        self.assertIsInstance(c.warehouse[0], ItemRegistry().system)
        self.assertIsInstance(c.warehouse[1], ItemRegistry().credentials)
        self.assertIsInstance(c.warehouse[2], ItemRegistry().id)
        self.assertIsInstance(c.warehouse[3], ItemRegistry().host)
        self.assertIsInstance(c.warehouse[4], ItemRegistry().generic)

    def test_basic_settings_obj(self):
        c = Assembly.fromObj(
            {
                "supply": {"paths": ["**/local"]},
                "warehouse": [
                    {"type_": "system"},
                    {"type_": "credentials"},
                    {"type_": "id"},
                    {"type_": "host"},
                    {"type_": "new_kind"},
                ],
            }
        )
        self.assertIsInstance(c.supply, ItemRegistry().FactorySupply)
        self.assertIsInstance(c.warehouse[0], ItemRegistry().system)
        self.assertIsInstance(c.warehouse[1], ItemRegistry().credentials)
        self.assertIsInstance(c.warehouse[2], ItemRegistry().id)
        self.assertIsInstance(c.warehouse[3], ItemRegistry().host)
        self.assertIsInstance(c.warehouse[4], ItemRegistry().generic)


class ItemsBasicTests(unittest.TestCase):
    def test_basic_create_item(self):
        c = ItemRegistry().warehouse_model_validate({"type_": "system"})
        self.assertEqual(c.type_, "system")
        c = ItemRegistry().warehouse_model_validate({"type_": "new_kind", "key": "value"})
        self.assertEqual(c.type_, "new_kind")
        self.assertEqual(c.key, "value")


class RegisterBasicTests(unittest.TestCase):
    def test_basic_register_item(self):
        from myrrh.warehouse.item import BaseItem

        class PluginItem(BaseItem[typing.Literal["plugin"]]):
            type_: typing.Literal["plugin"]
            val: str

        ItemRegistry().register_warehouse(PluginItem)
        c = ItemRegistry().warehouse_model_validate({"type_": "plugin", "val": "value"})

        self.assertIsInstance(c, PluginItem)
        self.assertEqual(c.type_, "plugin")
        self.assertEqual(c.val, "value")
        self.assertIn("plugin", ItemRegistry().items)

    def test_basic_register_provider_model(self):
        import myrrh.warehouse

        class NewProviderModel(myrrh.warehouse.Settings):
            name: typing.Literal["new_provider"]
            usable: bool = False

        ItemRegistry().register_provider_model(NewProviderModel)

        c = ItemRegistry().provider_model_validate({"name": "new_provider", "usable": True})

        self.assertIsInstance(c, NewProviderModel)
        self.assertEqual(c.name, "new_provider")
        self.assertEqual(c.usable, True)


if __name__ == "__main__":
    unittest.main()
