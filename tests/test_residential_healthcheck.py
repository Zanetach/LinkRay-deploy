import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "residential_healthcheck.py"
DEFAULT_DOMAINS = [
    "domain:openai.com",
    "domain:chatgpt.com",
    "domain:oaistatic.com",
    "domain:oaiusercontent.com",
    "domain:anthropic.com",
    "domain:claude.ai",
    "domain:console.anthropic.com",
    "domain:cursor.com",
    "domain:githubcopilot.com",
    "domain:copilot.microsoft.com",
]


def make_db(path: Path, outbound_tag: str = "residential") -> None:
    conn = sqlite3.connect(path)
    conn.execute("create table settings (key text primary key, value text)")
    template = {
        "outbounds": [
            {
                "tag": "residential",
                "protocol": "socks",
                "settings": {
                    "servers": [
                        {
                            "address": "example.com",
                            "port": 443,
                            "users": [{"user": "res-user", "pass": "res-pass"}],
                        }
                    ]
                },
            },
            {"tag": "direct", "protocol": "freedom"},
        ],
        "routing": {
            "rules": [
                {"type": "field", "inboundTag": ["api"], "outboundTag": "api"},
                {
                    "type": "field",
                    "domain": DEFAULT_DOMAINS,
                    "outboundTag": outbound_tag,
                },
            ]
        },
    }
    conn.execute(
        "insert into settings(key,value) values('xrayTemplateConfig', ?)",
        (json.dumps(template),),
    )
    conn.commit()
    conn.close()


def read_ai_outbound(path: Path) -> str:
    conn = sqlite3.connect(path)
    row = conn.execute(
        "select value from settings where key='xrayTemplateConfig'"
    ).fetchone()
    conn.close()
    template = json.loads(row[0])
    for rule in template["routing"]["rules"]:
        if "domain:openai.com" in rule.get("domain", []):
            return rule["outboundTag"]
    raise AssertionError("AI rule not found")


def fake_curl(path: Path, exit_code: int) -> Path:
    script = path / "curl"
    script.write_text(
        textwrap.dedent(
            f"""\
            #!/bin/sh
            exit {exit_code}
            """
        )
    )
    script.chmod(0o755)
    return script


class ResidentialHealthcheckTests(unittest.TestCase):
    def run_script(self, db_path: Path, curl_bin: Path, mode: str = "auto"):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--db",
                str(db_path),
                "--curl-bin",
                str(curl_bin),
                "--mode",
                mode,
                "--no-backup",
            ],
            text=True,
            capture_output=True,
        )

    def test_auto_disables_ai_residential_route_when_probe_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / "x-ui.db"
            make_db(db_path, outbound_tag="residential")

            result = self.run_script(db_path, fake_curl(tmp_path, 7))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(read_ai_outbound(db_path), "direct")
            self.assertIn("disabled", result.stdout)
            self.assertNotIn("res-pass", result.stdout)

    def test_auto_enables_ai_residential_route_when_probe_recovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / "x-ui.db"
            make_db(db_path, outbound_tag="direct")

            result = self.run_script(db_path, fake_curl(tmp_path, 0))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(read_ai_outbound(db_path), "residential")
            self.assertIn("enabled", result.stdout)

    def test_check_mode_does_not_mutate_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / "x-ui.db"
            make_db(db_path, outbound_tag="residential")

            result = self.run_script(db_path, fake_curl(tmp_path, 7), mode="check")

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(read_ai_outbound(db_path), "residential")


if __name__ == "__main__":
    unittest.main()
