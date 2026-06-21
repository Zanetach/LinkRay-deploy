# LinkRay Deploy

Codex/Claude skill for deploying and operating a LinkRay-branded 3X-UI control plane with one user subscription URL and multiple Xray inbounds.

This skill is subscription-centered: 3X-UI remains the user, quota, traffic, and subscription authority. Extra Nginx paths, local wrappers, and protocol adapters are presentation or transport layers around that authority.

## What It Covers

- Single-point and two-VPS 3X-UI layouts
- One stable `subId` across all selected inbounds
- VLESS Reality, VLESS Reality Vision, Trojan Reality, Hysteria2
- VLESS TLS WS on `443/tcp` through Nginx
- VLESS XHTTP TLS on `443/tcp` through Nginx and optional Cloudflare orange-cloud
- Clash/Mihomo profile wrapper with strategy groups and `meta-rules-dat`
- BBR, Fail2Ban, certificate renewal, and verification checks

## Recommended Current Shape

```text
sub.example.com
  -> 3X-UI subscription server

direct.example.com or VPS IP
  -> VLESS Reality / Trojan Reality / Hysteria2

ws.example.com:443 /ws-<random>
  -> Nginx
  -> 127.0.0.1:<local-ws-port>
  -> VLESS WS, security none on Xray, TLS terminated by Nginx

xhttp.example.com:443 /xh-<random>
  -> Nginx
  -> 127.0.0.1:<local-xhttp-port>
  -> VLESS XHTTP, security none on Xray, TLS terminated by Nginx
```

Use Cloudflare orange-cloud only for HTTP-compatible transports such as XHTTP or WS. Do not point Reality or Hysteria2 at orange-cloud hostnames.

## Protocol Boundary

| Protocol profile | Xray native | Good public endpoint | Notes |
|---|---:|---|---|
| VLESS Reality | Yes | VPS IP or DNS-only hostname | Good direct anti-probe profile |
| VLESS Reality Vision | Yes | VPS IP or DNS-only hostname | Same direct path, with Vision flow |
| Trojan Reality | Yes | VPS IP or DNS-only hostname | Can coexist with Trojan TLS |
| Hysteria2 | Yes | VPS IP or DNS-only hostname, UDP | Do not route through Cloudflare HTTP proxy |
| VLESS TLS WS 443 | Yes | Nginx `443/tcp` path | Compatibility fallback |
| VLESS XHTTP TLS 443 | Yes | Nginx `443/tcp` path, optional Cloudflare | Preferred CDN/HTTPS profile |
| TUIC v5 | No | Separate sing-box or tuic-server | Keep outside this native 3X-UI/Xray skill unless explicitly adding a sidecar |

## Install

```bash
cp -R LinkRay-deploy ~/.codex/skills/
cp -R LinkRay-deploy ~/.claude/skills/
```

Then invoke it as:

```text
$LinkRay-deploy
```

## Main Files

- `SKILL.md`: routing rules and operator checklist
- `references/cluster-blueprint.md`: command-level deployment and repair workflow
- `agents/openai.yaml`: agent metadata
- `evals/evals.json`: basic skill expectations

## Verification Pattern

Before handing over a user subscription, verify both the server and the actual client-facing subscription:

```bash
systemctl is-active x-ui nginx
ss -tlnp | grep -E ':(443|9444|9445|9446|<local-ws-port>|<local-xhttp-port>) '
ss -lunp | grep -E ':(8444) ' || true

curl -fsS 'https://sub.example.com/clash/<subId>' -o /tmp/linkray.yaml
mihomo -t -f /tmp/linkray.yaml
```

For live protocol testing, run Mihomo's delay API against each new proxy name, not just the first green button in a GUI client.
