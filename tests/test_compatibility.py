import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('compat', Path(__file__).parents[1] / 'tools/check_compatibility.py')
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)


class ExportTests(unittest.TestCase):
    def parse(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.dll'
            path.write_bytes(data)
            return compat.pe_exports(path)

    def fixture(self):
        data = bytearray(1024)
        data[:2] = b'MZ'
        struct.pack_into('<I', data, 0x3c, 0x80)
        data[0x80:0x84] = b'PE\0\0'
        struct.pack_into('<HH', data, 0x84, 0x8664, 1)
        struct.pack_into('<H', data, 0x94, 240)
        struct.pack_into('<H', data, 0x98, 0x20b)
        struct.pack_into('<I', data, 0x98 + 112, 0x1000)
        struct.pack_into('<IIII', data, 0x98 + 240 + 8, 512, 0x1000, 512, 512)
        struct.pack_into('<I', data, 512 + 24, 1)
        struct.pack_into('<I', data, 512 + 32, 0x1040)
        struct.pack_into('<I', data, 576, 0x1050)
        name = b'il2cpp_domain_get\0'
        data[592:592 + len(name)] = name
        return data

    def test_reads_export_table(self):
        self.assertEqual(self.parse(self.fixture()), ['il2cpp_domain_get'])

    def test_rejects_unmapped_name(self):
        data = self.fixture()
        struct.pack_into('<I', data, 576, 0xffffffff)
        with self.assertRaises(ValueError):
            self.parse(data)

    def test_no_export_directory(self):
        data = self.fixture()
        struct.pack_into('<I', data, 0x98 + 112, 0)
        self.assertEqual(self.parse(data), [])

    def test_rejects_non_pe(self):
        with self.assertRaises(ValueError):
            self.parse(b'not an executable')


if __name__ == '__main__':
    unittest.main()
