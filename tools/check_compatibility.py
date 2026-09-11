"""Read-only inspection of the on-disk runtime; never loads game DLLs."""
import argparse
import hashlib
import json
import mmap
from pathlib import Path
import struct

REQUIRED_EXPORTS = (
    'il2cpp_domain_get', 'il2cpp_thread_attach', 'il2cpp_thread_detach',
    'il2cpp_domain_get_assemblies', 'il2cpp_class_from_name',
    'il2cpp_class_get_method_from_name', 'il2cpp_runtime_invoke',
    'il2cpp_assembly_get_image',
)


def pe_exports(path):
    with path.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
        def read(fmt, offset):
            return struct.unpack_from(fmt, data, offset)

        if data[:2] != b'MZ':
            raise ValueError('Not a PE file')
        pe, = read('<I', 0x3c)
        if data[pe:pe + 4] != b'PE\0\0':
            raise ValueError('Invalid PE signature')
        machine, count = read('<HH', pe + 4)
        optional_size, = read('<H', pe + 20)
        optional = pe + 24
        magic, = read('<H', optional)
        if magic != 0x20b or machine != 0x8664:
            raise ValueError('Expected an x64 PE32+ runtime')
        sections = []
        for index in range(count):
            section = optional + optional_size + index * 40
            virtual_size, rva, raw_size, raw = read('<IIII', section + 8)
            sections.append((rva, raw_size, raw))

        def offset(rva):
            for start, size, raw in sections:
                if start <= rva < start + size:
                    result = raw + rva - start
                    if result < len(data):
                        return result
            raise ValueError(f'Unmapped RVA: {rva:#x}')

        export_rva, = read('<I', optional + 112)
        if not export_rva:
            return []
        directory = offset(export_rva)
        name_count, = read('<I', directory + 24)
        names_rva, = read('<I', directory + 32)
        if name_count > len(data) // 4:
            raise ValueError('Invalid export count')
        names = offset(names_rva) if name_count else 0
        result = []
        for index in range(name_count):
            name_rva, = read('<I', names + index * 4)
            start = offset(name_rva)
            end = data.find(b'\0', start, min(start + 4096, len(data)))
            if end == -1:
                raise ValueError('Unterminated export name')
            result.append(data[start:end].decode('ascii'))
        return result


def inspect(game):
    runtime = game / 'GameAssembly.dll'
    if not (game / 'Endfield.exe').is_file() or not runtime.is_file():
        raise ValueError('Select the folder containing Endfield.exe and GameAssembly.dll')
    exports = pe_exports(runtime)
    missing = sorted(set(REQUIRED_EXPORTS) - set(exports))
    with runtime.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {
        'runtime_sha256': digest,
        'runtime_bytes': runtime.stat().st_size,
        'export_count': len(exports),
        'il2cpp_export_count': sum(name.startswith('il2cpp_') for name in exports),
        'missing_required_exports': missing,
        'legacy_loader_files_present': [name for name in
            ('ace_inject.dll', 'ace_inject-1.dll', 'vulkan-1.dll')
            if (game / name).is_file()],
        'd3dcompiler_present': (game / 'd3dcompiler_47.dll').is_file(),
        'status': 'legacy_api_unavailable' if missing else 'runtime_testing_required',
        'note': 'Export presence alone does not establish working FPS unlock or graphics compatibility. Do not overwrite the game-owned d3dcompiler_47.dll.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game_directory', type=Path)
    args = parser.parse_args()
    try:
        report = inspect(args.game_directory)
    except (OSError, ValueError, struct.error) as exc:
        parser.exit(2, f'Inspection failed: {exc}\n')
    print(json.dumps(report, indent=2))
    return 1 if report['missing_required_exports'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
