import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "configure_residential_outbound.py"


def make_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("create table settings (key text primary key, value text)")
    template = {
        "outbounds": [
            {"tag": "direct", "protocol": "freedom"},
            {"tag": "blocked", "protocol": "blackhole"},
        ],
        "routing": {
            "rules": [
                {"type": "field", "inboundTag": ["api"], "outboundTag": "api"},
                {"type": "field", "ip": ["geoip:private"], "outboundTag": "blocked"},
            ]
        },
    }
    conn.execute(
        "insert into settings(key,value) values('xrayTemplateConfig', ?)",
        (json.dumps(template),),
    )
    conn.commit()
    conn.close()


def read_template(path: Path) -> dict:
    conn = sqlite3.connect(path)
    row = conn.execute(
        "select value from settings where key='xrayTemplateConfig'"
    ).fetchone()
    conn.close()
    return json.loads(row[0])


class ConfigureResidentialOutboundTests(unittest.TestCase):
    def run_script(self, db_path: Path, socks_uri: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--db",
                str(db_path),
                "--socks",
                socks_uri,
                "--no-backup",
            ],
            text=True,
            capture_output=True,
        )

    def test_writes_authenticated_residential_outbound(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "x-ui.db"
            make_db(db_path)

            result = self.run_script(
                db_path, "socks5://res-user:res-pass@example.com:443"
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            template = read_template(db_path)
            outbound = next(o for o in template["outbounds"] if o["tag"] == "residential")
            server = outbound["settings"]["servers"][0]
            self.assertEqual(outbound["protocol"], "socks")
            self.assertEqual(server["address"], "example.com")
            self.assertEqual(server["port"], 443)
            self.assertEqual(server["users"], [{"user": "res-user", "pass": "res-pass"}])
            residential_rules = [
                r
                for r in template["routing"]["rules"]
                if r.get("outboundTag") == "residential"
            ]
            self.assertEqual(len(residential_rules), 1)
            self.assertIn("domain:openai.com", residential_rules[0]["domain"])
            self.assertNotIn("res-pass", result.stdout)

    def test_writes_ip_allowlisted_residential_outbound_without_users(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "x-ui.db"
            make_db(db_path)

            result = self.run_script(db_path, "socks5://example.net:1080")

            self.assertEqual(result.returncode, 0, result.stderr)
            template = read_template(db_path)
            outbound = next(o for o in template["outbounds"] if o["tag"] == "residential")
            server = outbound["settings"]["servers"][0]
            self.assertEqual(server["address"], "example.net")
            self.assertEqual(server["port"], 1080)
            self.assertNotIn("users", server)

    def test_rejects_endpoint_without_port(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "x-ui.db"
            make_db(db_path)

            result = self.run_script(db_path, "socks5://example.net")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("port", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
