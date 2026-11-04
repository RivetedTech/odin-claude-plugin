#!/usr/bin/env python3
"""Snapshot registered Odin routes from a clean, local SupportPlatform checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "plugins/odin-api/skills/odin-api/references/route-catalog.md"


def render(platform):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(platform), *args], text=True).strip()

    if git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("Use a clean platform checkout so the source commit is reproducible")
    commit = git("rev-parse", "HEAD")
    version = json.loads((platform / "package.json").read_text())["version"]
    path = platform / "infrastructure/api-codegen/manifest.json"
    routes = json.loads(path.read_text())["routes"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    lines = ["# Registered route snapshot", "",
             f"Source: RivetedTech/SupportPlatform **{version}**, commit `{commit}`.",
             f"Manifest SHA-256: `{digest}`. Registered entries: **{len(routes)}**.", "",
             "Generated with `python3 scripts/update-route-catalog.py --platform-root <clean-checkout>`.",
             "This is a routing inventory, not a PAT-access or request-body specification.",
             "`ANY` and greedy `{proxy+}` resources delegate concrete methods and tails to a handler;",
             "they do not authorize arbitrary requests. Public signing/portal routes, provider",
             "callbacks and agent enrollment/heartbeat routes use their own authentication;",
             "do not send a user PAT to them merely because they appear here. Feature and live",
             "scope checks still apply. Registration in source does not prove runtime deployment.", "",
             "Native work, context, leads, current-context, chat connections and other domain",
             "operations reuse `/{domainEntity}` and `/{domainEntity}/{domainEntityId}`;",
             "read their dedicated references. Monitoring has a separate proxy API and is",
             "described in [monitoring.md](monitoring.md). This inventory alone is not an",
             "exhaustive list of concrete handler operations.", "",
             "| Method | Path | Handler parameter |", "| --- | --- | --- |"]
    for route in sorted(routes, key=lambda route: (route["path"], route["method"])):
        lines.append(f'| `{route["method"]}` | `{route["path"]}` | `{route["lambdaArnParam"]}` |')
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform-root", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = render(args.platform_root)
    if args.check:
        if OUTPUT.read_text() != content:
            raise SystemExit("Route snapshot differs; regenerate and review it")
        print("Route snapshot matches the clean platform checkout")
    else:
        OUTPUT.write_text(content)
        print(f"Updated {OUTPUT}")
