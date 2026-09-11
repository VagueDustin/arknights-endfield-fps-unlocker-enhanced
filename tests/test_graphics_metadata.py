from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
from inspect_graphics_metadata import inspect


class MetadataTests(unittest.TestCase):
    def fixture(self, stride=88):
        data = bytearray(2048)
        struct.pack_into('<II', data, 0, 0xFAB11BAF, 29)
        strings = b'Sample\0Example\0value\0SetValue\0Example.dll\0'
        data[264:264 + len(strings)] = strings
        for table, offset, size in ((2, 264, len(strings)), (5, 544, 32),
                                    (11, 512, 12), (19, 640, stride), (20, 1024, 40)):
            struct.pack_into('<II', data, 8 + table * 8, offset, size)
        struct.pack_into('<III', data, 512, 15, 123, 0x04000001)
        struct.pack_into('<IIIIIIHHHH', data, 544, 21, 0, 123, 0, 0xffffffff, 0x06000001, 16, 0, 0, 1)
        struct.pack_into('<II', data, 640, 0, 7)
        struct.pack_into('<ii', data, 672, 0, 0)
        struct.pack_into('<HHH', data, 640 + stride - 24, 1, 0, 1)
        struct.pack_into('<I', data, 640 + stride - 4, 0x02000001)
        struct.pack_into('<IIiI', data, 1024, 30, 0, 0, 1)
        return data

    def parse(self, data):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'metadata.dat'
            path.write_bytes(data)
            return inspect(path, {'Sample'})

    def test_standard_and_endfield_record_sizes(self):
        for stride in (88, 92):
            with self.subTest(stride=stride):
                result = self.parse(self.fixture(stride))
                self.assertEqual(result['type_record_bytes'], stride)
                record = result['types'][0]
                self.assertEqual(record['namespace'], 'Example')
                self.assertEqual(record['image'], 'Example.dll')
                self.assertEqual(record['fields'][0]['name'], 'value')
                self.assertEqual(record['methods'][0]['name'], 'SetValue')
                self.assertTrue(record['methods'][0]['static'])

    def test_unknown_version_rejected(self):
        data = self.fixture()
        struct.pack_into('<I', data, 4, 31)
        with self.assertRaisesRegex(ValueError, 'version 29'):
            self.parse(data)

    def test_unknown_stride_rejected(self):
        with self.assertRaisesRegex(ValueError, 'record size'):
            self.parse(self.fixture(96))

    def test_out_of_bounds_table_rejected(self):
        data = self.fixture()
        struct.pack_into('<II', data, 8 + 19 * 8, 2000, 88)
        with self.assertRaisesRegex(ValueError, 'table extent'):
            self.parse(data)

    def test_wrong_method_owner_rejected(self):
        data = self.fixture(92)
        struct.pack_into('<I', data, 548, 7)
        with self.assertRaisesRegex(ValueError, 'ownership'):
            self.parse(data)

    def test_wrong_type_token_rejected(self):
        data = self.fixture(92)
        struct.pack_into('<I', data, 640 + 92 - 4, 0x06000001)
        with self.assertRaisesRegex(ValueError, 'type token'):
            self.parse(data)


if __name__ == '__main__':
    unittest.main()
