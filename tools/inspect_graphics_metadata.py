"""Inspect selected IL2CPP v29 type declarations without loading or modifying the game.

Format reference: https://github.com/Perfare/Il2CppDumper/blob/master/Il2CppDumper/Il2Cpp/MetadataClass.cs
This reads declarations, not runtime offsets or instantiated generic types.
"""
import argparse
import json
import mmap
from pathlib import Path
import struct

DEFAULT_TYPES = {'HGSettingParameters', 'HGRenderPipeline', 'HGSMAA',
                 'HGAdditionalCameraData', 'RenderPipelineManager', 'Application',
                 'QualitySettings', 'Texture'}


def inspect(path, names=DEFAULT_TYPES):
    with path.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
        def unpack(fmt, offset):
            if offset < 0 or offset + struct.calcsize(fmt) > len(data):
                raise ValueError('Metadata record exceeds file bounds')
            return struct.unpack_from(fmt, data, offset)

        magic, version = unpack('<II', 0)
        if magic != 0xFAB11BAF or version != 29:
            raise ValueError('Only standard IL2CPP metadata version 29 is supported')

        def table(index, stride):
            start, size = unpack('<II', 8 + 8 * index)
            if start < 184 or start + size > len(data) or size % stride:
                raise ValueError('Invalid metadata table extent or record size')
            return start, size // stride

        strings, string_bytes = table(2, 1)
        types, type_bytes = table(19, 1)
        fields, field_count = table(11, 12)
        methods, method_count = table(5, 32)
        images, image_count = table(20, 40)

        def string(index):
            if index >= string_bytes:
                raise ValueError('String index exceeds metadata string table')
            end = data.find(b'\0', strings + index, strings + string_bytes)
            if end < 0:
                raise ValueError('Unterminated metadata string')
            return data[strings + index:end].decode('utf-8')

        image_ranges = []
        type_count = 0
        for index in range(image_count):
            name, _, first, count = unpack('<IIiI', images + index * 40)
            if count and first < 0:
                raise ValueError('Invalid image type range')
            type_count = max(type_count, first + count if count else 0)
            image_ranges.append((first, first + count, string(name)))
        if not type_count or type_bytes % type_count:
            raise ValueError('Image ranges do not describe a whole type table')
        type_stride = type_bytes // type_count
        if type_stride not in (88, 92):
            raise ValueError(f'Unsupported v29 type record size: {type_stride}')

        result = []
        for index in range(type_count):
            position = types + index * type_stride
            name_index, namespace_index = unpack('<II', position)
            name = string(name_index)
            field_start, method_start = unpack('<ii', position + 32)
            methods_size, _, fields_size = unpack('<HHH', position + type_stride - 24)
            if (fields_size and (field_start < 0 or field_start + fields_size > field_count)) or \
               (methods_size and (method_start < 0 or method_start + methods_size > method_count)):
                raise ValueError('Type member range exceeds its table')
            token, = unpack('<I', position + type_stride - 4)
            if token >> 24 != 2:
                raise ValueError('Unexpected type token; type layout is not recognized')
            # Validate method ownership for every type, even those not selected.
            for method in range(method_start, method_start + methods_size):
                owner, = unpack('<i', methods + method * 32 + 4)
                if owner != index:
                    raise ValueError('Method ownership does not validate this type layout')
            if name not in names:
                continue
            type_fields = []
            for field in range(field_start, field_start + fields_size):
                name_offset, type_index, token = unpack('<IiI', fields + field * 12)
                type_fields.append({'name': string(name_offset), 'type_index': type_index,
                                    'token': f'{token:08x}'})
            type_methods = []
            for method in range(method_start, method_start + methods_size):
                position_method = methods + method * 32
                name_offset, declaring, return_type = unpack('<Iii', position_method)
                flags, _, _, parameters = unpack('<HHHH', position_method + 24)
                if declaring != index:
                    raise ValueError('Method declaration does not match its owning type')
                type_methods.append({'name': string(name_offset), 'parameters': parameters,
                                     'static': bool(flags & 0x10), 'return_type_index': return_type})
            result.append({'image': next((name for first, last, name in image_ranges if first <= index < last), None),
                           'namespace': string(namespace_index), 'name': name,
                           'fields': type_fields, 'methods': type_methods})
        return {'metadata_version': version, 'type_record_bytes': type_stride,
                'type_count': type_count, 'types': result,
                'missing_types': sorted(set(names) - {item['name'] for item in result}),
                'status': 'declarations_only_not_runtime_validated'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('metadata', type=Path)
    parser.add_argument('--type', action='append', dest='types')
    args = parser.parse_args()
    try:
        report = inspect(args.metadata, set(args.types) if args.types else DEFAULT_TYPES)
    except (OSError, ValueError, struct.error) as error:
        parser.exit(2, f'Metadata inspection failed: {error}\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
