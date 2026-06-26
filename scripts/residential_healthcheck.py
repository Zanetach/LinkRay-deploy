#!/usr/bin/env python3
"""Health-check LinkRay residential outbound and fail over AI routes."""

from __future__ import annotations

import argparse
import json
import shlex
import sqlite3
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from configure_residential_outbound import (
    DEFAULT_DOMAINS,
    backup_db,
    build_residential_rule,
    load_template,
    restart_xui,
    save_template,
)


DEFAULT_PROBE_URLS = ["https://api.ipify.org"]


def residential_rule(rule: dict) -> bool:
    domains = set(rule.get("domain") or [])
    return bool(domains.intersection(DEFAULT_DOMAINS)) and rule.get("outboundTag") in {
        "residential",
        "direct",
    }


def find_residential_server(template: dict) -> dict:
    for outbound in template.get("outbounds", []):
        if outbound.get("tag") != "residential":
            continue
        if outbound.get("protocol") != "socks":
            raise RuntimeError("residential outbound exists but is not protocol=socks")
        servers = (outbound.get("settings") or {}).get("servers") or []
        if not servers:
            raise RuntimeError("residential outbound has no SOCKS server")
        return servers[0]
    raise RuntimeError("residential outbound not configured")


def proxy_url(server: dict) -> str:
    host = server.get("address")
    port = server.get("port")
    if not host or not port:
        raise RuntimeError("residential SOCKS server must include address and port")

    users = server.get("users") or []
    auth = ""
    if users:
        user = quote(str(users[0].get("user", "")), safe="")
        password = quote(str(users[0].get("pass", "")), safe="")
        auth = f"{user}:{password}@"
    if ":" in str(host) and not str(host).startswith("["):
        host = f"[{host}]"
    return f"socks5h://{auth}{host}:{port}"


def probe(curl_bin: str, proxy: str, urls: list[str]) -> bool:
    for url in urls:
        result = subprocess.run(
            [
                curl_bin,
                "-fsS",
                "--connect-timeout",
                "8",
                "--max-time",
                "15",
                "--proxy",
                proxy,
                url,
            ],
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            return False
    return True


def set_ai_route(template: dict, outbound_tag: str) -> tuple[dict, bool]:
    routing = template.setdefault("routing", {})
    rules = routing.setdefault("rules", [])
    changed = False
    matched = False

    for rule in rules:
        if residential_rule(rule):
            matched = True
            if rule.get("outboundTag") != outbound_tag:
                rule["outboundTag"] = outbound_tag
                changed = True

    if not matched:
        rules.insert(0, build_residential_rule(DEFAULT_DOMAINS))
        rules[0]["outboundTag"] = outbound_tag
        changed = True

    return template, changed


def write_route(db_path: Path, template: dict, outbound_tag: str, backup: bool) -> bool:
    updated, changed = set_ai_route(template, outbound_tag)
    if not changed:
        return False
    if backup:
        backup_db(db_path)
    save_template(db_path, updated)
    return True


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check residential SOCKS health and route AI domains to residential/direct."
    )
    parser.add_argument("--db", default="/etc/x-ui/x-ui.db")
    parser.add_argument(
        "--mode",
        choices=["check", "auto", "enable", "disable"],
        default="check",
        help="check only, auto failover, force enable, or force disable.",
    )
    parser.add_argument(
        "--probe-url",
        action="append",
        dest="probe_urls",
        help="URL to fetch through the residential SOCKS proxy. Repeatable.",
    )
    parser.add_argument("--curl-bin", default="curl")
    parser.add_argument("--no-backup", action="store_true")
    parser.add_argument("--restart", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    db_path = Path(args.db)
    urls = args.probe_urls or DEFAULT_PROBE_URLS

    try:
        template = load_template(db_path)
        server = find_residential_server(template)
        proxy = proxy_url(server)

        if args.mode == "disable":
            changed = write_route(db_path, template, "direct", not args.no_backup)
            if args.restart and changed:
                restart_xui()
            print("residential route disabled; AI/Copilot domains use direct")
            return 0

        healthy = probe(args.curl_bin, proxy, urls)

        if args.mode == "check":
            if healthy:
                print(
                    "residential route healthy "
                    f"host={server.get('address')} port={server.get('port')} urls={len(urls)}"
                )
                return 0
            print(
                "residential route unhealthy "
                f"host={server.get('address')} port={server.get('port')} urls={len(urls)}",
                file=sys.stderr,
            )
            return 1

        target = "residential" if args.mode == "enable" or healthy else "direct"
        changed = write_route(db_path, template, target, not args.no_backup)
        if args.restart and changed:
            restart_xui()

        action = "enabled" if target == "residential" else "disabled"
        state = "healthy" if healthy else "unhealthy"
        print(
            f"residential route {action}; health={state}; "
            f"host={server.get('address')} port={server.get('port')}"
        )
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
