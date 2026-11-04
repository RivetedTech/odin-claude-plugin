#!/usr/bin/env python3
"""Build reproducible terminal and documentation-only Odin skill archives."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins/odin-api/skills/odin-api"


def archive(path, files):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as output:
        for name, content, executable in sorted(files):
            info = zipfile.ZipInfo("odin-api/" + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | (0o755 if executable else 0o644)) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(info, content)


def build(destination):
    destination.mkdir(parents=True, exist_ok=True)
    # Explicit allowlist: never package .env, tokens or machine-local files.
    references = [(p.relative_to(SKILL).as_posix(), p.read_bytes(), False)
                  for p in sorted((SKILL / "references").glob("*.md"))]
    terminal = [("SKILL.md", (SKILL / "SKILL.md").read_bytes(), False),
                ("scripts/odin", (SKILL / "scripts/odin").read_bytes(), True), *references]
    guide = (SKILL / "SKILL.md").read_text()
    guide = re.sub(r"\]\(references/([^)]+)\)", r"](\1)", guide)
    documentation = [("SKILL.md", (ROOT / "scripts/templates/chatgpt-SKILL.md").read_bytes(), False),
                     ("references/terminal-guide.md", guide.encode(), False),
                     *references]
    archive(destination / "odin-api.zip", terminal)
    archive(destination / "chatgpt-odin-api.zip", documentation)
    manifest = {"version": json.loads((ROOT / "plugins/odin-api/.claude-plugin/plugin.json").read_text())["version"],
                "packages": {name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
                             for name in ("odin-api.zip", "chatgpt-odin-api.zip")}}
    (destination / "verification.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    print(json.dumps(build(args.output_dir), indent=2))
