"""Run Kodi Omega's unmodified comparator, not a Python approximation."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'compatibility/managed-updates/kodi-omega'


class KodiManagedVersionOrder(unittest.TestCase):
    def test_native_comparator_retains_managed_and_updates_ordinary_addons(self):
        compiler = shutil.which('c++')
        self.assertIsNotNone(compiler, 'A C++ compiler is required for the Kodi version-order regression')
        provenance = json.loads((SOURCE / 'provenance.json').read_text())
        for name, evidence in provenance.items():
            self.assertEqual(hashlib.sha256((SOURCE / name).read_bytes()).hexdigest(), evidence['sha256'])
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory); (d / 'utils').mkdir()
            # Only unrelated logging/formatting adapters are stubbed. The exact
            # constructor and comparison implementation remain unchanged.
            (d / 'utils/StringUtils.h').write_text('''#include <string>
#include <algorithm>
#include <cctype>
struct StringUtils {
 static void ToLower(std::string& s) { std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return std::tolower(c); }); }
 static std::string Format(const char*, int n) { return std::to_string(n) + ":"; }
};
''')
            (d / 'utils/log.h').write_text('enum { LOGERROR }; struct CLog { template<typename... T> static void Log(int, const char*, T...) {} };')
            (d / 'main.cpp').write_text('''#include "AddonVersion.h"
using ADDON::CAddonVersion;
int main() {
 if (!(CAddonVersion("6.17.9") < CAddonVersion("6.18.1"))) return 1;
 if (!(CAddonVersion("1.0.0") < CAddonVersion("2.0.0"))) return 2;
 if (!(CAddonVersion("100.0.0") < CAddonVersion("1:6.17.9+blacklanturn.1"))) return 3;
 if (!(CAddonVersion("1:6.17.9+blacklanturn.1") < CAddonVersion("1:6.17.9+blacklanturn.2"))) return 4;
 if (!(CAddonVersion("1:6.17.9+blacklanturn.2") < CAddonVersion("1:6.18.1+blacklanturn.1"))) return 5;
 if (CAddonVersion("1:6.17.9+blacklanturn.1").asString() != "1:6.17.9+blacklanturn.1") return 6;
}
''')
            subprocess.run([compiler, '-std=c++17', '-I' + str(d), '-I' + str(SOURCE), str(SOURCE / 'AddonVersion.cpp'), str(d / 'main.cpp'), '-o', str(d / 'compare')], check=True, capture_output=True)
            subprocess.run([str(d / 'compare')], check=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
