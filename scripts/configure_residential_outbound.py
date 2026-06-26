#!/usr/bin/env python3
"""Configure the LinkRay server-side residential Xray outbound in 3X-UI."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse


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


def parse_socks_endpoint(endpoint: str) -> dict:
    if "://" not in endpoint:
        endpoint = f"socks5://{endpoint}"

    parsed = urlparse(endpoint)
    if parsed.scheme not in {"socks", "socks4", "socks4a", "socks5", "socks5h"}:
        raise ValueError("residential endpoint must use a socks/socks5 URL")
    if not parsed.hostname:
        raise ValueError("residential endpoint must include a host")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("residential endpoint port must be a number") from exc
    if not port:
        raise ValueError("residential endpoint must include a port")

    server = {
        "address": parsed.hostname,
        "port": port,
    }
    if parsed.username is not None or parsed.password is not None:
        server["users"] = [
            {
                "user": unquote(parsed.username or ""),
                "pass": unquote(parsed.password or ""),
            }
        ]
    return server


def load_template(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "select value from settings where key='xrayTemplateConfig'"
        ).fetchone()
    finally:
        conn.close()
    if not row or not row[0]:
        raise RuntimeError("settings.xrayTemplateConfig not found in 3X-UI database")
    return json.loads(row[0])


def save_template(db_path: Path, template: dict) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "update settings set value=? where key='xrayTemplateConfig'",
            (json.dumps(template, ensure_ascii=False, separators=(",", ":")),),
        )
        conn.commit()
    finally:
        conn.close()


def build_residential_outbound(server: dict) -> dict:
    return {
        "tag": "residential",
        "protocol": "socks",
        "settings": {
            "servers": [server],
        },
    }


def build_residential_rule(domains: list[str]) -> dict:
    return {
        "type": "field",
        "domain": domains,
        "outboundTag": "residential",
    }


def upsert_residential(template: dict, server: dict, domains: list[str]) -> dict:
    outbounds = template.setdefault("outbounds", [])
    outbounds[:] = [o for o in outbounds if o.get("tag") != "residential"]
    outbounds.insert(0, build_residential_outbound(server))

    routing = template.setdefault("routing", {})
    rules = routing.setdefault("rules", [])
    rules[:] = [r for r in rules if r.get("outboundTag") != "residential"]

    insert_at = 0
    while insert_at < len(rules) and rules[insert_at].get("outboundTag") == "api":
        insert_at += 1
    rules.insert(insert_at, build_residential_rule(domains))
    return template


def backup_db(db_path: Path) -> Path:
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    backup_path = db_path.with_name(f"{db_path.name}.bak-residential-{stamp}")
    shutil.copy2(db_path, backup_path)
    return backup_path


def restart_xui() -> None:
    subprocess.run(["systemctl", "restart", "x-ui"], check=True)
    subprocess.run(["systemctl", "is-active", "--quiet", "x-ui"], check=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Configure server-side residential SOCKS outbound in 3X-UI."
    )
    parser.add_argument(
        "--db",
        default="/etc/x-ui/x-ui.db",
        help="Path to the 3X-UI sqlite database.",
    )
    parser.add_argument(
        "--socks",
        required=True,
        help="Residential SOCKS endpoint, e.g. socks5://user:pass@host:443.",
    )
    parser.add_argument(
        "--domain",
        action="append",
        dest="domains",
        help="Domain rule entry to route through residential. Repeatable.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create a timestamped database backup before writing.",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Restart x-ui after writing the template.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    db_path = Path(args.db)
    domains = args.domains or DEFAULT_DOMAINS

    try:
        server = parse_socks_endpoint(args.socks)
        template = load_template(db_path)
        backup_path = None if args.no_backup else backup_db(db_path)
        save_template(db_path, upsert_residential(template, server, domains))
        if args.restart:
            restart_xui()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    backup_text = f" backup={backup_path}" if backup_path else ""
    print(
        "configured residential outbound "
        f"host={server['address']} port={server['port']} domains={len(domains)}"
        f"{backup_text}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
