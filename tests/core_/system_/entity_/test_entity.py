import unittest

from myrrh.provider import IProvider, IShellService, IFileSystemService
from myrrh.provider.registry import ProviderRegistry

from myrrh.core.services.entity import CoreProvider


class CoreProviderTest(unittest.TestCase):
    def test_basic_create(self):
        ProviderRegistry()._new_provider("new", ProviderRegistry().local)
        p_local = ProviderRegistry().get("local")

        p = CoreProvider((p_local(),))

        self.assertEqual(len(p_local().services()), len(p.services()))
        self.assertEqual(set(p_local().catalog()), set(p.catalog()))

    def test_basic_set_default(self):
        class FakeProvider(IProvider):
            class FakeShellServ(IShellService):
                protocol = "fake"

            class FakeFilesystemServ(IFileSystemService):
                protocol = "fake"

            def services(self):
                return (self.FakeShellServ, self.FakeFilesystemServ)

            def catalog(self):
                return tuple()

            def deliver(self, name):
                ...

        ProviderRegistry()._new_provider("fake", FakeProvider)
        p_local = ProviderRegistry().get("local")()
        p_fake = ProviderRegistry().get("fake")()

        p = CoreProvider((p_local, p_fake))
        self.assertEqual(len(p.services()), len(p_fake.services() + p_local.services()))

        p = CoreProvider((p_local, p_fake), patterns=("**/local",))
        self.assertEqual(len(p.services()), len(p_local.services()))
        p = CoreProvider((p_local, p_fake), patterns=("*system*/fake",))
        self.assertEqual(len(p.services()), len(p_fake.services()))


if __name__ == "__main__":
    unittest.main()
