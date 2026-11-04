"""Exercise the real Bash wrapper with synthetic curl responses, offline."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "plugins/odin-api/skills/odin-api/scripts/odin"
TOKEN = "synthetic-token-never-a-live-credential"


class Wrapper(unittest.TestCase):
    def fixture(self, args, pages=None, status=200, overrides=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pages.json").write_text(json.dumps(pages or [{"success": True, "data": {}}]))
            curl = root / "curl"
            curl.write_text(f"#!{sys.executable}\n" + '''import json, pathlib, sys
root = pathlib.Path(__file__).parent
calls = root / 'calls.jsonl'
count = len(calls.read_text().splitlines()) if calls.exists() else 0
with calls.open('a') as output:
    output.write(json.dumps(sys.argv[1:]) + '\\n')
pages = json.loads((root / 'pages.json').read_text())
if count >= len(pages):
    sys.exit('fixture exhausted: unexpected request')
body = pages[count]
if body is not None:
    print(json.dumps(body), end='')
''' + f"\nprint('\\n{status}', end='')\n")
            curl.chmod(0o755)
            environment = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}",
                               ODIN_API_TOKEN=TOKEN, ODIN_API_BASE_URL="https://api.odinhelp.net",
                               ODIN_TENANT_ID="synthetic-tenant")
            result = subprocess.run(["bash", str(WRAPPER), *args], env=environment | (overrides or {}),
                                    capture_output=True, text=True, timeout=10)
            self.assertNotIn(TOKEN, result.stdout + result.stderr)
            calls = root / "calls.jsonl"
            return result, [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []

    def test_preflight_identity_and_denials(self):
        result, calls = self.fixture(["preflight"], [{"success": True, "data": {
            "userEmail": "demo@example.invalid", "tenantId": "synthetic-tenant", "daysRemaining": 20}}])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("demo@example.invalid", result.stdout)
        self.assertIn("Authorization: Bearer " + TOKEN, calls[0])
        self.assertIn("X-Active-Tenant-Id: synthetic-tenant", calls[0])
        result, _ = self.fixture(["preflight"], status=401)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("INVALID", result.stderr)
        result, _ = self.fixture(["preflight"], status=403)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("expired", result.stderr)

    def test_help_needs_no_connection(self):
        result, calls = self.fixture(["--help"], overrides={"ODIN_API_TOKEN": "", "ODIN_API_BASE_URL": ""})
        self.assertEqual(result.returncode, 0)
        self.assertIn("--body-file", result.stdout)
        self.assertEqual(calls, [])

    def test_pagination_shapes_empty_pages_and_encoded_cursor(self):
        for field in ("items", "data"):
            with self.subTest(field=field):
                result, calls = self.fixture(["--all", "GET", "/api/work-records?search=demo"], [
                    {"success": True, "data": {field: [], "nextCursor": "opaque+/=&?", "partial": True}},
                    {"success": True, "data": {field: [{"recordId": "late-item"}], "partial": False}},
                ])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), {"recordId": "late-item"})
                self.assertEqual(len(calls), 2)
                self.assertIn("https://api.odinhelp.net/api/work-records?search=demo&cursor=opaque%2B%2F%3D%26%3F", calls[1])
        result, _ = self.fixture(["--all", "GET", "/api/customers"], [{"success": True, "data": [{"id": "one"}]}])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"id": "one"})
        result, _ = self.fixture(["--all", "GET", "/api/customers"], [{"success": True, "data": {"data": []}}])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_incomplete_malformed_and_looping_pages_fail(self):
        for page in ({"data": {"items": [], "partial": True}}, {"data": {"items": [], "truncated": True}},
                     {"data": {}}, None):
            with self.subTest(page=page):
                result, _ = self.fixture(["--all", "GET", "/api/work-records"], [page])
                self.assertNotEqual(result.returncode, 0)
        page = {"data": {"items": [], "nextCursor": "repeated"}}
        result, calls = self.fixture(["--all", "GET", "/api/work-records"], [page, page])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repeated continuation", result.stderr)
        self.assertEqual(len(calls), 2)

    def test_history_routing_hint_and_real_authorization_denial(self):
        result, calls = self.fixture(["GET", "/api/native-context/demo/history"],
                                     [{"message": "Missing Authentication Token"}], status=403)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("?operation=history", result.stderr)
        self.assertIn("does not establish permission", result.stderr)
        self.assertEqual(len(calls), 1)
        denial = {"success": False, "error": {"message": "Missing required permission: tickets:read"}}
        result, calls = self.fixture(["GET", "/api/native-context/demo?operation=history"], [denial], status=403)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Unregistered", result.stderr)
        self.assertIn("Missing required permission", result.stdout)
        self.assertEqual(len(calls), 1)
        result, calls = self.fixture(["--all", "GET", "/api/native-context/demo?operation=history"], [
            {"data": {"items": [{"version": 1}], "nextCursor": "next"}},
            {"data": {"items": [{"version": 2}]}}
        ])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([json.loads(line)["version"] for line in result.stdout.splitlines()], [1, 2])
        self.assertIn("https://api.odinhelp.net/api/native-context/demo?operation=history&cursor=next", calls[1])

    def test_write_headers_and_secret_body_file(self):
        with tempfile.TemporaryDirectory() as directory:
            body = Path(directory) / "request.json"
            body.write_text('{"secret":"synthetic-signing-secret"}')
            body.chmod(0o600)
            result, calls = self.fixture(["--body-file", str(body), "--idempotency-key", "demo-write-v1",
                                          "--if-match", "2", "PATCH", "/api/notification-webhooks/demo"])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Idempotency-Key: demo-write-v1", calls[0])
            self.assertIn("If-Match: 2", calls[0])
            self.assertIn("--data-binary", calls[0])
            self.assertIn("@" + str(body), calls[0])
            self.assertNotIn("synthetic-signing-secret", str(calls) + result.stdout + result.stderr)
            for args in (["--body-file", str(body), "GET", "/api/tickets"],
                         ["--body-file", str(body), "POST", "/api/tickets", "{}"]):
                result, calls = self.fixture(args)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls, [])

    def test_unsafe_or_invalid_inputs_never_reach_curl(self):
        cases = [(["GET", "/api/tickets"], {"ODIN_API_BASE_URL": "http://api.odinhelp.com"}),
                 (["GET", "/api/tickets"], {"ODIN_API_BASE_URL": "https://example.invalid"}),
                 (["GET", "/api/tickets"], {"ODIN_API_TOKEN": ""}),
                 (["GET", "/api/tickets"], {"ODIN_TENANT_ID": "demo\nX-Evil: yes"}),
                 (["GET", "https://example.invalid"], {}),
                 (["--idempotency-key", "bad\rheader", "POST", "/api/work-records"], {}),
                 (["--all", "GET", "/api/work-records?cursor=already"], {}),
                 (["--all", "POST", "/api/work-records"], {})]
        for args, overrides in cases:
            with self.subTest(args=args, overrides=overrides):
                result, calls = self.fixture(args, overrides=overrides)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
