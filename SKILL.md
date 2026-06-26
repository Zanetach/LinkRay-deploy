---
name: LinkRay-deploy
description: Use when deploying or operating the verified LinkRay two-node 3X-UI cluster with one wrapper-backed Clash/Mihomo subscription, node1/node2 protocol parity, and the documented routing rules.
---

# LinkRay Deploy

## Overview

Deploy and operate the current LinkRay-branded 3X-UI cluster that has been verified through this skill. Keep the scope narrow: VPS-A is the main panel and subscription authority, VPS-B is the remote node, and the public user subscription is the wrapper-backed Clash/Mihomo URL.

Keep all answers and deployment steps inside the verified deployed set.

## Deployed Shape

| Role | Host | Public names |
|---|---|---|
| Main panel + subscription + local node + wrapper | VPS-A | `panel.example.com`, `sub.example.com`, `direct1.example.com`, `node1.example.com`, `xhttp1.example.com` |
| Remote node | VPS-B | `direct2.example.com`, `node2.example.com`, `xhttp2.example.com` |

## Workflow

1. Collect deployment inputs before SSH:
   - VPS-A: IP, SSH user/port/auth, panel domain, subscription domain.
   - VPS-B: IP, SSH user/port/auth, node domains, management API endpoint.
   - Root domain and DNS provider credentials.
   - Users: email/remark, quota, expiry, IP limit, and `subId` policy.
   - Security choice for node API reachability: private network preferred; otherwise firewall allow only VPS-A.

2. Read `references/cluster-blueprint.md` before executing commands or changing a server.

3. Deploy in this order:
   - Install 3X-UI on VPS-A and VPS-B.
   - Configure DNS and TLS for `panel`, `sub`, `direct1`, `direct2`, `node1`, `node2`, `xhttp1`, and `xhttp2`.
   - Enable BBR on both VPS nodes before traffic testing.
   - Configure the VPS-A subscription server and Nginx reverse proxy.
   - Configure VPS-B node API access so only VPS-A can reach it.
   - Register VPS-B in the VPS-A main panel and verify heartbeat.
   - Create the verified profile set on both nodes: VLESS Reality, VLESS Reality Vision, Trojan Reality, Hysteria2, VLESS TLS WS 443, and VLESS XHTTP TLS 443.
   - Create clients once on VPS-A and attach the same client identity/subId to every selected inbound on node1 and node2.
   - For WS/XHTTP on 443, keep Xray localhost-only and advertise the public TLS host through `externalProxy`.
   - Deploy the localhost Clash/Mihomo wrapper in front of `/clash/<subId>`.
   - Configure UFW and Fail2Ban after SSH and node API reachability are verified.
   - Verify certificate renewal, subscription decoding, node parity, wrapper-generated strategy groups/rules, and remote-node API access.
   - Output subscription URLs and admin notes.

## Architecture

```text
Clients
  -> https://sub.example.com/clash/<subId>
      -> Nginx on VPS-A
      -> localhost Clash/Mihomo wrapper
      -> native 3X-UI /clash/<subId> source
      -> node1 and node2 inbounds
```

## Hard Requirements

- Keep one subscription authority: VPS-A.
- Enable the subscription server on VPS-A.
- VPS-B panel/API ports must not be open to the world.
- Use one stable `subId` per user across all deployed inbounds.
- Use unique remarks/tags per node/protocol so subscriptions are readable.
- Keep 3X-UI client names unique after lowercasing on every node.
- Use DNS-01 certificates for Cloudflare-managed domains when possible.
- Keep subscription service behind Nginx and set `subDomain`.
- Keep `subPath=/sub/` and `subClashPath=/clash/`; do not set `subPath=/clash/`.
- Publish `https://sub.example.com/clash/<subId>` through the native wrapper.
- The wrapper must read native 3X-UI `/clash/<subId>`, preserve `proxies:`, replace minimal groups/rules with the standard full profile, and forward `subscription-userinfo`.
- The wrapper must expose the 23 visible strategy groups, 20 providers, and 41 routing rules from the blueprint.
- Do not leave visible strategy groups as dead UI.
- Route DoH domains to `DNS_Proxy`, Telegram domain/IP rules to `Telegram`, `media-cn` to `国内媒体`, and the final fallback to `MATCH,漏网之鱼`.
- Keep Reality and Hysteria2 on VPS IPs or DNS-only hostnames.
- Use Cloudflare orange-cloud only for WS/XHTTP.
- Do not let Xray bind public `443/tcp` for WS/XHTTP; Nginx owns 443 and forwards random paths to localhost Xray ports.
- When VPS-B IP changes, update Cloudflare DNS, `nodes.address`, VPS-B `share_addr`, firewall allow rules, Nginx upstreams, and wrapper server rewrite maps together.
- Persist BBR as `net.core.default_qdisc=fq` and `net.ipv4.tcp_congestion_control=bbr` where supported.
- Configure Fail2Ban's `sshd` jail for the actual SSH port.

## Subscription Output

For each user, output:

```text
Clash/Mihomo:
https://sub.example.com/clash/<subId>

Generic diagnostic:
https://sub.example.com/sub/<subId>

JSON diagnostic:
https://sub.example.com/json/<subId>
```

Do not present panel-exported internal links as the primary deliverable.

## Common Mistakes

| Mistake | Correct action |
|---|---|
| Creating separate users per protocol | Create one user/subId and attach it to every deployed inbound |
| Exposing VPS-B panel/API ports publicly | Use private networking or firewall allow only VPS-A |
| Making users manually edit `/sub/` to `/clash/` | Configure displayed `subURI` to `/clash/` while leaving `subPath=/sub/` |
| Returning only `proxies:` and the client shows no nodes | Return a full wrapper-backed profile with `proxy-groups`, `rule-providers`, and `rules` |
| Returning rules but no visible strategy groups | Add the standard 23 strategy groups and map every `RULE-SET` |
| Wrapper-backed profile shows no traffic quota or expiry | Forward `subscription-userinfo` from native 3X-UI |
| Provider/admin/payment pages fail after importing the subscription | Keep front-loaded `DIRECT` overrides before `geolocation-!cn` |
| Binding Xray directly to public 443 for WS/XHTTP | Keep Xray on localhost and forward Nginx paths |
| Reusing one 443 path for WS and XHTTP | Use separate random paths |
| Pointing Reality/Hysteria2 at Cloudflare orange-cloud names | Use DNS-only hostnames or VPS IPs |
| Creating Hysteria2 as TCP+TLS | Set `protocol=hysteria`, version `2`, and verify UDP listening |
| Renaming 3X-UI internals to a brand | Only rewrite presentation text; do not rename services, DBs, API paths, or tags |

## References

- `references/cluster-blueprint.md`: command-level deployment and repair blueprint for the verified two-node LinkRay cluster.
