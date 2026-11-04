"""Offline packaging checks; no Odin account or credential is needed."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("builder", ROOT / "scripts/build-skill.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class Packages(unittest.TestCase):
    def test_reproducible_safe_packages(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            one, two = Path(first), Path(second)
            manifest = builder.build(one)
            self.assertEqual(manifest, builder.build(two))
            for name, digest in manifest["packages"].items():
                self.assertEqual((one / name).read_bytes(), (two / name).read_bytes())
                self.assertEqual(hashlib.sha256((one / name).read_bytes()).hexdigest(), digest)
                with zipfile.ZipFile(one / name) as package:
                    names = package.namelist()
                    self.assertIn("odin-api/SKILL.md", names)
                    for entry in names:
                        self.assertTrue(entry.endswith(".md") or entry == "odin-api/scripts/odin", entry)
                        self.assertNotIn("..", Path(entry).parts)
                    if name.startswith("chatgpt"):
                        self.assertTrue(all(entry.endswith(".md") for entry in names))
                        self.assertIn(b"documentation only", package.read("odin-api/SKILL.md"))
                    else:
                        self.assertTrue(package.getinfo("odin-api/scripts/odin").external_attr >> 16 & 0o111)

    def test_manifests_and_references(self):
        plugin = json.loads((ROOT / "plugins/odin-api/.claude-plugin/plugin.json").read_text())
        marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())["plugins"][0]
        self.assertEqual(plugin["version"], marketplace["version"])
        with tempfile.TemporaryDirectory() as directory:
            builder.build(Path(directory))
            for archive in Path(directory).glob("*.zip"):
                with zipfile.ZipFile(archive) as package:
                    names = set(package.namelist())
                    for name in names:
                        if not name.endswith(".md"):
                            continue
                        content = package.read(name).decode()
                        for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", content):
                            if "://" in target or target.startswith("/"):
                                continue
                            self.assertIn((Path(name).parent / target).as_posix(), names, (name, target))


if __name__ == "__main__":
    unittest.main()
