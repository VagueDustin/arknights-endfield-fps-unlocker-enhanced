"""The version shipped by the installer, the runtime log, and the package manifest must agree."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProductMetadataTests(unittest.TestCase):
    def setUp(self):
        self.product = json.loads((ROOT / 'assets/identity/product.json').read_text(encoding='utf-8-sig'))

    def test_version_is_semantic(self):
        self.assertRegex(self.product['version'], r'^\d+\.\d+\.\d+$')

    def test_cmake_reads_the_product_version_instead_of_hardcoding_one(self):
        cmake = (ROOT / 'CMakeLists.txt').read_text(encoding='utf-8')
        self.assertIn('string(JSON product_version GET', cmake)
        self.assertNotRegex(cmake, r'project\(\s*FateEngine\s+VERSION\s+\d')
        self.assertIn('FATE_ENGINE_VERSION', cmake)

    def test_runtime_logs_the_build_version_not_a_literal(self):
        runtime = (ROOT / 'src/modern/runtime.cpp').read_text(encoding='utf-8')
        self.assertIn('FATE_ENGINE_VERSION', runtime)
        self.assertNotRegex(runtime, r'Starting runtime \d+\.\d+\.\d+')

    def test_installer_derives_its_name_and_version_from_the_generated_include(self):
        script = (ROOT / 'installer/EndfieldEnhancer.iss').read_text(encoding='utf-8')
        self.assertIn('{#ProductVersion}', script)
        self.assertNotRegex(script, r'AppVersion=\d')
        # The unbundled CI build must not masquerade as the bundled release download.
        self.assertIn('-unbundled', script)

    def test_release_download_link_points_at_a_tagged_release(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        match = re.search(r'\[Download Fate Engine (\d+\.\d+\.\d+) for Windows\]\([^)]*releases/tag/v(\d+\.\d+\.\d+)\)', readme)
        self.assertIsNotNone(match, 'README must link the published release download')
        self.assertEqual(match[1], match[2])


if __name__ == '__main__':
    unittest.main()
