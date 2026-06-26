# LinkRay Verified Cluster Blueprint

This blueprint documents only the LinkRay deployment that has been verified through this skill: a two-node 3X-UI cluster, one main subscription authority, one wrapper-backed Clash/Mihomo subscription, and the deployed routing rules.

## Target State

```text
VPS-A
  3X-UI main panel
  subscription server on 127.0.0.1
  Nginx public HTTPS entrypoint
  localhost Clash/Mihomo wrapper
  node1 inbounds

VPS-B
  3X-UI remote node
  node2 inbounds

User imports:
  https://sub.example.com/clash/<subId>
```

DNS:

```text
panel.example.com   A/AAAA  VPS-A
sub.example.com     A/AAAA  VPS-A
direct1.example.com A/AAAA  VPS-A
direct2.example.com A/AAAA  VPS-B
node1.example.com   A/AAAA  VPS-A
node2.example.com   A/AAAA  VPS-B
xhttp1.example.com  A/AAAA  VPS-A
xhttp2.example.com  A/AAAA  VPS-B
```

Cloudflare orange-cloud is used only for HTTP-compatible WS/XHTTP hosts. Reality and Hysteria2 use VPS IPs or DNS-only hostnames.

## Main Panel Settings

On VPS-A, configure 3X-UI as the control plane:

```text
Web domain: panel.example.com
Subscription enabled: true
Subscription listen: 127.0.0.1
Subscription port: 10882
Subscription domain: sub.example.com
Sub path: /sub/
JSON path: /json/
Clash path: /clash/
Clash enable: true
```

Displayed subscription URI:

```text
subPath=/sub/
subURI=https://sub.example.com/clash/
subJsonPath=/json/
subJsonURI=https://sub.example.com/json/
subClashPath=/clash/
subClashURI=https://sub.example.com/clash/
```

Do not set `subPath=/clash/`. 3X-UI already registers `/clash/<subId>`, and duplicate routes can crash the panel at startup.

The public Clash handoff path is always wrapper-backed. Keep native `/sub/<subId>` and native 3X-UI `/clash/<subId>` reachable locally for source and diagnostics, but publish `https://sub.example.com/clash/<subId>` through the enhanced wrapper.

## Deployment Discovery Prompts

Before SSH or server changes, ask these questions and record the answers:

```text
Enable server-side residential outbound for AI/Copilot domains? yes/no
If yes: one residential SOCKS endpoint URI, for example socks5://user:pass@host:port
Keep residential hidden from Clash/Mihomo subscriptions? yes/no
Route dmit.io through residential? no
```

Defaults:

- Residential outbound is optional and disabled unless upstream credentials are provided.
- Accepted endpoint formats are `socks5://username:password@host:port`, `socks5://host:port`, or `host:port`.
- Keep residential hidden from subscriptions in the verified design.
- Keep `dmit.io` as `DIRECT`.
- Do not create an empty `residential` outbound without a working upstream.

## Remote Node API

VPS-B must be reachable from VPS-A by private network or firewall allowlisting only VPS-A.

Minimum firewall rule shape on VPS-B:

```bash
ufw allow from <VPS-A-IP> to any port <panel-port> proto tcp
ufw deny <panel-port>/tcp
```

Verification from VPS-A:

```bash
curl -fsS -H "Authorization: Bearer <NODE_API_TOKEN>" \
  https://<node-management-host>:<panel-port>/<base-path>/panel/api/server/status
```

Do not leave the VPS-B panel/API port open to the world.

## Deployed Profiles

Create the same verified profile set on node1 and node2:

```text
node1-vless-reality
node1-vless-reality-vision
node1-trojan-reality
node1-hysteria2
node1-vless-ws-tls
node1-vless-xhttp-tls

node2-vless-reality
node2-vless-reality-vision
node2-trojan-reality
node2-hysteria2
node2-vless-ws-tls
node2-vless-xhttp-tls
```

Expected full subscription count: `12` profiles.

Direct profiles:

- Reality and Reality Vision: TCP direct on VPS IP or DNS-only hostname.
- Trojan Reality: TCP direct on VPS IP or DNS-only hostname.
- Hysteria2: UDP direct, Xray `protocol=hysteria`, version `2`, `streamSettings.network=hysteria`.

443 profiles:

- VLESS TLS WS: Nginx owns public `443/tcp` and forwards a random WS path to a localhost-only Xray port.
- VLESS XHTTP TLS: Nginx owns public `443/tcp` and forwards a separate random XHTTP path to a localhost-only Xray port.

Do not bind Xray directly to public `443/tcp` for WS/XHTTP.

## Users And Aggregation

The aggregation key is `subId`.

Create one client identity per user:

```text
email/remark: user001
subId: user001_<random>
totalGB: quota bytes or 0 for unlimited
expiryTime: unix ms or 0 for unlimited
limitIp: concurrent IP cap or 0
enable: true
```

Attach that same user identity to all 12 deployed inbounds. Do not create one user per protocol.

If a subscription is empty, inspect both normalized tables:

```bash
sqlite3 /etc/x-ui/x-ui.db \
  "select id,email,sub_id,enable from clients;"
sqlite3 /etc/x-ui/x-ui.db \
  "select client_id,inbound_id from client_inbounds;"
```

## Residential Outbound

The verified residential IP setup is a server-side Xray outbound, not a user-visible Clash node.

This capability must be surfaced during deployment discovery. Do not wait until after the profile is built to ask about it.

When enabled, take the SOCKS endpoint from deployment discovery and configure it on both VPS-A and VPS-B.

Current contract:

```text
outbound tag: residential
protocol: socks
scope: server-side transparent routing only
subscription exposure: none
profile count impact: none; the subscription remains 12 profiles
```

Do not publish the residential SOCKS upstream address, username, or password in Clash/Mihomo subscriptions. Users keep selecting normal node1/node2 profiles; Xray performs the residential hop only after a service-side routing rule matches.

Required service-side domains:

```text
domain:openai.com
domain:chatgpt.com
domain:oaistatic.com
domain:oaiusercontent.com
domain:anthropic.com
domain:claude.ai
domain:console.anthropic.com
domain:cursor.com
domain:githubcopilot.com
domain:copilot.microsoft.com
```

Do not route `dmit.io` through the residential outbound in this verified deployment. Keep `DOMAIN-SUFFIX,dmit.io,DIRECT` in the Clash/Mihomo wrapper rules.

Deployment flow on each VPS after copying `scripts/configure_residential_outbound.py` there, or from a repo checkout on that VPS:

```bash
read -r -s RESIDENTIAL_SOCKS_URL
curl -fsS --connect-timeout 8 --max-time 15 \
  --proxy "$RESIDENTIAL_SOCKS_URL" https://api.ipify.org

python3 scripts/configure_residential_outbound.py \
  --socks "$RESIDENTIAL_SOCKS_URL" \
  --restart
unset RESIDENTIAL_SOCKS_URL
```

The script must update `/etc/x-ui/x-ui.db` `settings.xrayTemplateConfig`, create a timestamped backup, restart `x-ui`, and avoid printing credentials. Do not only edit `/usr/local/x-ui/bin/config.json`; 3X-UI can regenerate that file from the database.

Minimal Xray shape:

```json
{
  "outbounds": [
    {
      "tag": "residential",
      "protocol": "socks",
      "settings": {
        "servers": [
          {
            "address": "<residential-socks-host>",
            "port": 443,
            "users": [
              {
                "user": "<username>",
                "pass": "<password>"
              }
            ]
          }
        ]
      }
    }
  ],
  "routing": {
    "rules": [
      {
        "type": "field",
        "domain": [
          "domain:openai.com",
          "domain:chatgpt.com",
          "domain:oaistatic.com",
          "domain:oaiusercontent.com",
          "domain:anthropic.com",
          "domain:claude.ai",
          "domain:console.anthropic.com",
          "domain:cursor.com",
          "domain:githubcopilot.com",
          "domain:copilot.microsoft.com"
        ],
        "outboundTag": "residential"
      }
    ]
  }
}
```

Verification:

```bash
python3 - <<'PY'
import json, pathlib
data=json.loads(pathlib.Path('/usr/local/x-ui/bin/config.json').read_text())
print([(o.get('tag'), o.get('protocol')) for o in data.get('outbounds', [])])
print([r for r in data.get('routing', {}).get('rules', []) if r.get('outboundTag') == 'residential'])
PY
```

The output must include `('residential', 'socks')` and the AI/Copilot domain rule above.

## Clash/Mihomo Wrapper

Shape:

```text
client -> https://sub.example.com/clash/<subId>
  -> Nginx /clash/<subId>
    -> localhost wrapper 127.0.0.1:3012/clash/<subId>
      -> reads native 3X-UI source http://127.0.0.1:<sub-port>/clash/<subId>
      -> returns enhanced Clash/Mihomo YAML
```

The wrapper must:

- read the native 3X-UI `/clash/<subId>` YAML as source
- preserve native `proxies:`
- replace minimal native `proxy-groups` and `rules`
- compute `subscription-userinfo` globally by `subId` from the 3X-UI database, using native `subscription-userinfo` only as fallback
- calculate `upload`/`download` from `client_traffics`, `total` from `clients.total_gb`, and `expire` from `clients.expiry_time` for every enabled user
- forward `profile-title`, `profile-update-interval`, and `profile-web-page-url`
- stay bound to `127.0.0.1`
- rewrite direct node `server` values from DNS names to VPS IPs when clients use fake-IP DNS, while preserving Reality `sni`/`servername` and Hysteria2 `sni`

Do not repair this by inserting rows for one user only. The wrapper must work for every future user created in 3X-UI. `expire=0` means no fixed expiry date; set a user expiry time in 3X-UI when clients must display a concrete date.

Nginx route:

```nginx
location ~ ^/clash/([A-Za-z0-9_-]+)/?$ {
    set $linkray_subid $1;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
    proxy_buffering off;
    proxy_pass http://127.0.0.1:3012/clash/$linkray_subid;
}
```

## Strategy Groups

Required `23` visible strategy groups:

```text
自动选择
故障转移
负载均衡
节点选择
流媒体
手动切换
全球代理
DNS_Proxy
Telegram
Google
YouTube
Netflix
Spotify
HBO
Bing
Microsoft
OpenAI
ClaudeAI
Disney
GitHub
国内媒体
本地直连
漏网之鱼
```

Do not add duplicate English `AUTO`.

## Rule Providers

Required `20` providers:

```text
private
category-ads-all
private-ip
cn
geolocation-!cn
openai
github
google
youtube
netflix
spotify
hbo
bing
microsoft
disney
anthropic
telegram-domain
telegram
media-cn
cn-ip
```

All providers use `format: mrs` from MetaCubeX `meta-rules-dat`.

## Routing Rules

Required `41` rules, in order:

```yaml
rules:
  - IP-CIDR,127.0.0.0/8,DIRECT,no-resolve
  - IP-CIDR,10.0.0.0/8,DIRECT,no-resolve
  - IP-CIDR,172.16.0.0/12,DIRECT,no-resolve
  - IP-CIDR,192.168.0.0/16,DIRECT,no-resolve
  - IP-CIDR,169.254.0.0/16,DIRECT,no-resolve
  - IP-CIDR,224.0.0.0/4,DIRECT,no-resolve
  - IP-CIDR6,::1/128,DIRECT,no-resolve
  - IP-CIDR6,fc00::/7,DIRECT,no-resolve
  - IP-CIDR6,fe80::/10,DIRECT,no-resolve
  - RULE-SET,private,DIRECT
  - RULE-SET,private-ip,DIRECT,no-resolve
  - RULE-SET,category-ads-all,REJECT
  - DOMAIN,dns.google,DNS_Proxy
  - DOMAIN,dns64.dns.google,DNS_Proxy
  - DOMAIN,dns.cloudflare.com,DNS_Proxy
  - DOMAIN,cloudflare-dns.com,DNS_Proxy
  - DOMAIN,dns.quad9.net,DNS_Proxy
  - DOMAIN,doh.opendns.com,DNS_Proxy
  - DOMAIN,dns.alidns.com,DNS_Proxy
  - DOMAIN,doh.pub,DNS_Proxy
  - DOMAIN-SUFFIX,dmit.io,DIRECT
  - DOMAIN,challenges.cloudflare.com,DIRECT
  - DOMAIN-SUFFIX,cloudflare.com,DIRECT
  - RULE-SET,telegram-domain,Telegram
  - RULE-SET,telegram,Telegram,no-resolve
  - RULE-SET,openai,OpenAI
  - RULE-SET,github,GitHub
  - RULE-SET,google,Google
  - RULE-SET,youtube,YouTube
  - RULE-SET,netflix,Netflix
  - RULE-SET,spotify,Spotify
  - RULE-SET,hbo,HBO
  - RULE-SET,bing,Bing
  - RULE-SET,microsoft,Microsoft
  - RULE-SET,disney,Disney
  - RULE-SET,anthropic,ClaudeAI
  - RULE-SET,media-cn,国内媒体
  - RULE-SET,geolocation-!cn,全球代理
  - RULE-SET,cn,本地直连
  - RULE-SET,cn-ip,本地直连,no-resolve
  - MATCH,漏网之鱼
```

## Server Hardening

Enable BBR on both VPS nodes:

```bash
modprobe tcp_bbr 2>/dev/null || true
cat >/etc/sysctl.d/99-linkray-bbr.conf <<'EOF'
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
EOF
sysctl --system
sysctl net.ipv4.tcp_congestion_control net.core.default_qdisc
```

Configure UFW after SSH is confirmed:

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow <ssh-port>/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 9444/tcp
ufw allow 9445/tcp
ufw allow 8444/udp
ufw --force enable
ufw status verbose
```

On VPS-B, add the VPS-A-only API allow rule before the deny rule:

```bash
ufw allow from <VPS-A-IP> to any port <panel-port> proto tcp
ufw deny <panel-port>/tcp
```

Configure Fail2Ban for the actual SSH port:

```bash
cat >/etc/fail2ban/jail.d/linkray-sshd.local <<'EOF'
[sshd]
enabled = true
port = <ssh-port>
backend = systemd
maxretry = 5
findtime = 10m
bantime = 1h
EOF

fail2ban-server -t
systemctl enable --now fail2ban
systemctl restart fail2ban
fail2ban-client status sshd
```

## Verification

Before handoff:

```bash
# Services and ports
systemctl is-active x-ui nginx
ss -tlnp | grep -E ':(443|10882|<panel-port>|9444|9445|<local-ws-port>|<local-xhttp-port>) '
ss -lunp | grep -E ':(8444) '

# VPS-A can reach VPS-B management API
curl -fsS -H "Authorization: Bearer <NODE_API_TOKEN>" \
  https://<node-management-host>:<panel-port>/<base-path>/panel/api/server/status

# Public subscriptions
curl -I https://sub.example.com/sub/<subId>
curl -I https://sub.example.com/clash/<subId>
curl -I https://sub.example.com/json/<subId>

# Native source contains expected schemes
curl -fsS https://sub.example.com/sub/<subId> | base64 -d | \
  grep -E 'security=reality|hysteria2://|type=ws|type=xhttp'

# Wrapper output is the enhanced profile
curl -fsS https://sub.example.com/clash/<subId> -o /tmp/linkray-clash.yaml
mihomo -t -f /tmp/linkray-clash.yaml
grep -nE '^(proxy-groups|rule-providers|rules):' /tmp/linkray-clash.yaml
grep -nE '^[[:space:]]*- name: (自动选择|故障转移|负载均衡|节点选择|流媒体|手动切换|全球代理|DNS_Proxy|Telegram|Google|YouTube|Netflix|Spotify|HBO|Bing|Microsoft|OpenAI|ClaudeAI|Disney|GitHub|国内媒体|本地直连|漏网之鱼)$' /tmp/linkray-clash.yaml

# System hardening
sysctl net.ipv4.tcp_congestion_control net.core.default_qdisc
fail2ban-client status sshd
```

Then import `https://sub.example.com/clash/<subId>` in a Clash/Mihomo client and verify all `12` expected profiles appear once.

## Node2 IP Change Checklist

When VPS-B IP changes, update these together:

```text
Cloudflare DNS for direct2/node2/xhttp2
VPS-A main-panel nodes.address
VPS-B share_addr values
VPS-B firewall allow rules for VPS-A
VPS-A Nginx WS/XHTTP upstreams
wrapper server rewrite map
```

Then re-fetch `/clash/<subId>`, run `mihomo -t`, and run delay checks for every node2 profile.

## Output Format

Return:

```text
Main panel: https://panel.example.com/<basePath>
Nodes: node1 online, node2 online
User: user001
Clash/Mihomo: https://sub.example.com/clash/<subId>
Generic diagnostic: https://sub.example.com/sub/<subId>
JSON diagnostic: https://sub.example.com/json/<subId>
Included profiles: 12
Security:
  - VPS-B API reachable only from VPS-A/private network
  - Subscription public over HTTPS
  - Panel admin access restricted
  - BBR and Fail2Ban enabled
```
