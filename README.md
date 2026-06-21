# LinkRay Deploy Skill

Codex/Claude skill for deploying and operating a LinkRay-branded 3X-UI setup with one subscription URL, local or remote VPS nodes, and multi-protocol inbounds.

## Covers

- Single-point and multi-node 3X-UI deployment planning
- One stable `subId` across all selected inbounds
- VLESS Reality, Trojan Reality, Hysteria2, VLESS TLS WS, and VLESS XHTTP TLS
- Nginx-terminated 443 paths for WS/XHTTP
- Cloudflare DNS and certificate layout
- Clash/Mihomo subscriptions with strategy groups and rules
- BBR, Fail2Ban, and verification checks

## Install

```bash
cp -R LinkRay-deploy ~/.codex/skills/
cp -R LinkRay-deploy ~/.claude/skills/
```

Then invoke it as:

```text
$LinkRay-deploy
```
