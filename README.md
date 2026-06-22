# LinkRay Deploy

Operational skill for deploying and maintaining a LinkRay-branded 3X-UI setup with one subscription URL, one main panel, and one or more Xray nodes.

This repository packages an agent skill, not a standalone VPN panel. The skill keeps 3X-UI as the authority for users, quotas, traffic, nodes, and subscriptions, then documents the surrounding deployment pieces: DNS, TLS, Nginx paths, protocol boundaries, Clash/Mihomo profile shaping, and server hardening.

## When To Use

Use this skill when the task is about:

- one VPS or two-VPS 3X-UI deployment
- one subscription URL across multiple nodes and protocols
- LinkRay presentation branding on top of 3X-UI
- VLESS Reality, VLESS Reality Vision, Trojan Reality, Hysteria2, VLESS TLS WS, or VLESS XHTTP TLS
- Cloudflare DNS and DNS-01 certificates
- Clash/Mihomo subscriptions with visible strategy groups and `meta-rules-dat`
- BBR, Fail2Ban, certificate renewal, and protocol verification

Trigger examples:

```text
$LinkRay-deploy 单 VPS，创建用户和订阅地址
$LinkRay-deploy 两个 VPS，用 3X-UI 汇聚成一个订阅
$LinkRay-deploy node2 换 IP，协议和 node1 保持一致
$LinkRay-deploy Reality / Hysteria2 / XHTTP 全部配置并验证
```

## Target Architecture

```text
User clients
  -> https://sub.example.com/clash/<subId>
      -> main 3X-UI subscription server
      -> optional local Clash/Mihomo profile wrapper
      -> node1 inbounds
      -> node2 inbounds
```

Recommended domain split:

| Public name | Role | Cloudflare mode | Protocols |
|---|---|---|---|
| `panel.example.com` | 3X-UI admin panel | DNS only during setup | HTTPS panel |
| `sub.example.com` | public subscription URL | DNS only or tested proxy mode | `/sub/`, `/clash/`, `/json/` |
| `direct1.example.com` | node1 direct endpoint | DNS only | Reality, Hysteria2 |
| `direct2.example.com` | node2 direct endpoint | DNS only | Reality, Hysteria2 |
| `node1.example.com` | node1 HTTPS transport | proxied when needed | VLESS TLS WS |
| `node2.example.com` | node2 HTTPS transport | proxied when needed | VLESS TLS WS |
| `xhttp1.example.com` | node1 XHTTP transport | proxied when needed | VLESS XHTTP TLS |
| `xhttp2.example.com` | node2 XHTTP transport | proxied when needed | VLESS XHTTP TLS |

Cloudflare orange-cloud is only for HTTP-compatible transports such as WS and XHTTP. Reality and Hysteria2 should use VPS IPs or DNS-only hostnames.

## Deployment Modes

| Mode | Shape | Use when |
|---|---|---|
| Single-point | One VPS hosts panel, subscription, and local inbounds | A compact personal deployment still needs users and one subscription URL |
| Cluster | VPS-A hosts the main panel and subscription; VPS-B/N are remote nodes | Multiple VPS nodes should appear under one subscription |
| Direct anti-block | DNS-only endpoints expose Reality and Hysteria2 directly | The goal is simple direct VPS transport without Cloudflare proxying |
| Mixed | Direct protocols plus 443 WS/XHTTP fallbacks | Clients need both direct profiles and HTTPS/CDN-compatible profiles |

## Protocol Matrix

| Profile | Native to 3X-UI/Xray | Public endpoint | Notes |
|---|---:|---|---|
| VLESS Reality | Yes | VPS IP or DNS-only hostname | Direct anti-probe profile |
| VLESS Reality Vision | Yes | VPS IP or DNS-only hostname | Same direct path, Vision-capable client required |
| Trojan Reality | Yes | VPS IP or DNS-only hostname | Separate from Trojan TLS |
| Hysteria2 | Yes | VPS IP or DNS-only hostname, UDP | Must be `protocol=hysteria`, version 2 |
| VLESS TLS WS 443 | Yes | Nginx `443/tcp` path | Compatibility fallback |
| VLESS XHTTP TLS 443 | Yes | Nginx `443/tcp` path | Preferred HTTPS/CDN profile |
| TUIC v5 | No | Separate sidecar | Requires `sing-box` or `tuic-server`, not native 3X-UI |

Reality is not a universal wrapper. Use it with TCP VLESS/Trojan profiles. Do not force Reality onto Hysteria2 or Shadowsocks.

## Subscription Output

The operator-facing result should be subscription URLs, not a pile of separate node links:

```text
Generic:
https://sub.example.com/sub/<subId>

Clash/Mihomo:
https://sub.example.com/clash/<subId>

JSON:
https://sub.example.com/json/<subId>
```

When the native 3X-UI Clash output imports but needs richer rules, use the documented local wrapper to keep 3X-UI as the user and traffic authority while returning a complete Clash/Mihomo profile.

The current wrapper shape documents 23 visible strategy groups:

```text
自动选择, 故障转移, 负载均衡, 节点选择, 流媒体, 手动切换,
全球代理, DNS_Proxy, Telegram, Google, YouTube, Netflix, Spotify,
HBO, Bing, Microsoft, OpenAI, ClaudeAI, Disney, GitHub,
国内媒体, 本地直连, 漏网之鱼
```

It also documents `meta-rules-dat` providers, private IP direct rules, Telegram domain and IP rules, and front-loaded `DIRECT` overrides for provider/admin/payment sites that fail through VPS egress.

## Install

Install into Codex:

```bash
mkdir -p ~/.codex/skills
cp -R LinkRay-deploy ~/.codex/skills/
```

Install into Claude-style skill directories when needed:

```bash
mkdir -p ~/.claude/skills
cp -R LinkRay-deploy ~/.claude/skills/
```

Then invoke:

```text
$LinkRay-deploy
```

## Repository Layout

| Path | Purpose |
|---|---|
| [SKILL.md](SKILL.md) | Agent entrypoint, trigger scope, workflow, hard requirements, common mistakes |
| [references/cluster-blueprint.md](references/cluster-blueprint.md) | Command-level deployment and repair blueprint |
| [agents/openai.yaml](agents/openai.yaml) | Display metadata for OpenAI/Codex-style agent surfaces |
| [evals/evals.json](evals/evals.json) | Basic behavioral expectations for skill regression checks |

## Verification Checklist

Before handing over a user subscription:

```bash
systemctl is-active x-ui nginx
ss -tlnp | grep -E ':(443|9444|9445|9446|<local-ws-port>|<local-xhttp-port>) '
ss -lunp | grep -E ':(8444) ' || true

curl -fsS 'https://sub.example.com/clash/<subId>' -o /tmp/linkray.yaml
mihomo -t -f /tmp/linkray.yaml
```

For live protocol testing, run Mihomo's controller delay API against each exact proxy name. A GUI green check on one profile is not enough.

Reality-specific timeout triage:

1. Confirm the TCP port is reachable.
2. Confirm Xray is actually listening, not just the `x-ui` web service.
3. Check for duplicate client identities after lowercasing, such as `alice` and `Alice`.
4. Verify `target`, `serverNames`, public key, short ID, and SNI.
5. If Mihomo still reports timeout, build a temporary Xray client on another VPS and request `https://www.gstatic.com/generate_204` through the inbound. HTTP 204 proves the server-side Reality profile is valid.

## Operational Guardrails

- Keep one subscription authority: the main panel.
- Do not disable subscriptions in single-point mode.
- Do not expose remote node API ports publicly; use private networking or firewall allowlisting.
- Do not rename `x-ui` services, database paths, API paths, or node sync identifiers for branding.
- Do not point Reality or Hysteria2 at Cloudflare orange-cloud hostnames.
- Do not bind Xray directly to public `443/tcp` for WS/XHTTP when Nginx owns 443.
- When a remote node IP changes, update DNS, `nodes.address`, `share_addr`, firewall rules, Nginx upstreams, and wrapper server rewrite maps together.
- Use Sub-Store only for format conversion, external subscription sources, or Sub-Store-specific rewriting. Do not install it on every remote node.

## Local README Checks

This repository has no package build. Validate documentation changes with:

```bash
python3 ~/.codex/skills/readme-generator/scripts/check_readme_refs.py .
git diff --check
```

## License

No license file is declared in this repository.
