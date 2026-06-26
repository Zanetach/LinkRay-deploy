# LinkRay Deploy

> 已验证的 LinkRay 双节点 3X-UI 部署技能：一个主面板、一个远程节点、一个 Clash/Mihomo 订阅入口。

![LinkRay two-node deployment hero](assets/linkray-hero.png)

![LinkRay Deploy 能力总览](assets/linkray-capabilities.png)

## 项目介绍

LinkRay Deploy 是一个用于复现和维护当前已验证 LinkRay 部署形态的 Codex/agent skill。它不是通用 VPN 面板模板，而是把这次已经跑通的 3X-UI 双 VPS 方案固化成可执行的部署和运维文档。

部署完成后，系统由 VPS-A 和 VPS-B 两台服务器组成：

- VPS-A：主 3X-UI 面板、订阅服务、Nginx HTTPS 入口、本地 node1、Clash/Mihomo profile wrapper。
- VPS-B：远程 3X-UI node2，由 VPS-A 主面板统一管理。
- 用户侧：只导入一个订阅地址，默认使用 wrapper 增强后的 Clash/Mihomo 配置。

```text
用户主订阅：
https://sub.example.com/clash/<subId>
```

上图展示的是当前项目的实际部署关系：用户客户端从一个安全订阅入口进入，VPS-A 负责公开访问、订阅生成和本地 wrapper，最终配置分发到 node1 和 node2。

## 这个项目解决什么

| 问题 | LinkRay Deploy 的处理方式 |
|---|---|
| 多节点订阅分散 | 使用一个稳定 `subId` 聚合 node1/node2 的所有已验证协议 |
| Clash/Mihomo 原生订阅规则不完整 | 用本地 wrapper 输出完整 YAML，包含策略组、rule-providers 和 rules |
| 主面板和远程节点边界不清 | VPS-A 是唯一订阅和管理 authority，VPS-B 只作为远程节点 |
| WS/XHTTP 与 443 端口冲突 | Nginx 占用公网 443，Xray 只监听 localhost 随机路径 |
| Reality/Hysteria2 被错误放到 Cloudflare 小云朵 | Reality/Hysteria2 使用 VPS IP 或 DNS-only 主机名 |
| node2 换 IP 容易漏改 | 文档固定 DNS、节点地址、share_addr、防火墙、Nginx upstream、wrapper rewrite map 同步项 |
| 住宅 IP 被误当成订阅节点 | 住宅出口只作为服务端 Xray 透明 outbound，不暴露 SOCKS 凭据 |

## Deployed Shape

| Layer | Verified deployment |
|---|---|
| Main authority | VPS-A 3X-UI panel |
| Remote node | VPS-B 3X-UI node |
| Public handoff | `https://sub.example.com/clash/<subId>` |
| Native diagnostics | `/sub/<subId>`, `/json/<subId>` |
| Subscription profile | Wrapper-backed Clash/Mihomo YAML |
| Profile count | `12` profiles total |
| Rules output | `23` strategy groups, `20` providers, `41` routing rules |
| Residential routing | Server-side Xray outbound `residential`, not a Clash profile |

## Deployment Prompts

部署前应该先确认这些选项，尤其是住宅 IP。没有住宅 SOCKS 上游时，可以直接选择不启用，核心 12 个协议订阅不受影响。

| 交互问题 | 默认值 | 需要提供 |
|---|---|---|
| 是否启用服务端住宅出口？ | 不启用 | 一个 SOCKS endpoint URI |
| 住宅出口用于哪些域名？ | AI/Copilot 域名 | 只在需要扩展时调整 |
| 是否把住宅出口显示成 Clash 节点？ | 不显示 | 需要另建可见入站并单独验证 |
| `dmit.io` 是否走住宅出口？ | 不走 | 保持 `DIRECT` |

住宅出口是可选增强能力：启用后由 Xray 服务端透明分流，客户端订阅仍然只看到普通 node1/node2 profiles。

可接受的输入格式：

```text
socks5://username:password@host:port
socks5://host:port
host:port
```

## 支持的协议

当前 README 只记录已经通过该 skill 固化的协议集合。每个协议在 node1 和 node2 上各一份，完整订阅共 `12` 个 profiles。

| 协议/Profile | 节点 | 公网入口 | 说明 |
|---|---|---|---|
| VLESS Reality | node1 + node2 | VPS IP 或 DNS-only 域名 | 直连 TCP Reality |
| VLESS Reality Vision | node1 + node2 | VPS IP 或 DNS-only 域名 | Vision flow 的 Reality 直连配置 |
| Trojan Reality | node1 + node2 | VPS IP 或 DNS-only 域名 | Trojan over Reality，独立端口 |
| Hysteria2 | node1 + node2 | VPS IP 或 DNS-only 域名，UDP | Xray `protocol=hysteria`，version `2` |
| VLESS TLS WS 443 | node1 + node2 | Nginx `443/tcp` 随机 WS path | 兼容性 HTTPS fallback |
| VLESS XHTTP TLS 443 | node1 + node2 | Nginx `443/tcp` 随机 XHTTP path | 当前 HTTPS/CDN 路径 |

协议边界：

- Reality、Reality Vision、Trojan Reality、Hysteria2 不走 Cloudflare orange-cloud。
- WS/XHTTP 可以走 Cloudflare HTTP-compatible 路径。
- Xray 不直接绑定公网 `443/tcp`；公网 443 由 Nginx 接管并转发到 localhost-only Xray 入站。

## Domains

| Public name | Role | Cloudflare mode |
|---|---|---|
| `panel.example.com` | 3X-UI admin panel | DNS only during setup |
| `sub.example.com` | Public subscription URL | DNS only or tested proxy mode |
| `direct1.example.com` | node1 direct endpoint | DNS only |
| `direct2.example.com` | node2 direct endpoint | DNS only |
| `node1.example.com` | node1 WS transport | Proxied for WS |
| `node2.example.com` | node2 WS transport | Proxied for WS |
| `xhttp1.example.com` | node1 XHTTP transport | Proxied for XHTTP |
| `xhttp2.example.com` | node2 XHTTP transport | Proxied for XHTTP |

## Verified Profile Set

Each node exposes the same verified profile set:

| Node | Profiles |
|---|---|
| node1 / VPS-A | VLESS Reality, VLESS Reality Vision, Trojan Reality, Hysteria2, VLESS TLS WS 443, VLESS XHTTP TLS 443 |
| node2 / VPS-B | VLESS Reality, VLESS Reality Vision, Trojan Reality, Hysteria2, VLESS TLS WS 443, VLESS XHTTP TLS 443 |

Expected subscription total: `12` profiles.

## Clash/Mihomo Rules

VPS-A 上的本地 wrapper 会读取 3X-UI 原生 `/clash/<subId>` 输出，保留原生 `proxies:`，再替换为完整 Clash/Mihomo profile。订阅流量和到期信息不是单用户补丁：wrapper 会按请求中的 `subId` 查询 3X-UI 数据库，为任意已启用用户动态生成 `subscription-userinfo`。

Wrapper 输出内容：

| 项目 | 数量/行为 |
|---|---|
| 可见策略组 | `23` 个 |
| `meta-rules-dat` providers | `20` 个 |
| 路由规则 | `41` 条 |
| 流量/到期信息 | 按 `subId` 全局计算 `subscription-userinfo`，原生 header 仅兜底 |
| 最后一条规则 | `MATCH,漏网之鱼` |

Visible strategy groups:

```text
自动选择, 故障转移, 负载均衡, 节点选择, 流媒体, 手动切换,
全球代理, DNS_Proxy, Telegram, Google, YouTube, Netflix, Spotify,
HBO, Bing, Microsoft, OpenAI, ClaudeAI, Disney, GitHub,
国内媒体, 本地直连, 漏网之鱼
```

Routing contract:

| Route type | Target |
|---|---|
| DoH domains | `DNS_Proxy` |
| Telegram domain and IP rules | `Telegram` |
| `media-cn` | `国内媒体` |
| China domains and IPs | `本地直连` |
| Overseas geolocation | `全球代理` |
| Final fallback | `MATCH,漏网之鱼` |

`subscription-userinfo` 的来源：

| 字段 | 来源 |
|---|---|
| `upload` / `download` | `client_traffics.up` / `client_traffics.down` 汇总 |
| `total` | `clients.total_gb` |
| `expire` | `clients.expiry_time` |

`expire=0` 表示该用户没有固定到期日期。需要客户端显示具体日期时，先在 3X-UI 用户配置里设置到期时间；wrapper 会自动反映到所有订阅用户。

## Residential Outbound

当前住宅 IP 不是单独的 Clash 订阅节点，也不在客户端暴露 SOCKS 上游地址。它是两台服务器 Xray 配置里的服务端透明 outbound：

| 项目 | 当前设计 |
|---|---|
| Xray outbound tag | `residential` |
| Xray outbound protocol | `socks` |
| 用户订阅中是否显示 | 不显示 |
| 是否计入 12 个 profiles | 不计入 |
| Clash 是否需要住宅策略组 | 当前不需要 |

部署交互点：在安装 3X-UI 和写入 Xray 模板前，先问是否启用该能力。只有在用户提供住宅 SOCKS 上游时才写入 `residential` outbound；没有提供时，不要生成空的 residential 配置。

启用流程是在每台 VPS 上写入 3X-UI 的 `settings.xrayTemplateConfig`，不是只改临时生成的 Xray config。先把 `scripts/configure_residential_outbound.py` 复制到 VPS，或在 VPS 上的 repo checkout 目录中运行。标准流程：

```bash
read -r -s RESIDENTIAL_SOCKS_URL
curl -fsS --connect-timeout 8 --max-time 15 \
  --proxy "$RESIDENTIAL_SOCKS_URL" https://api.ipify.org

python3 scripts/configure_residential_outbound.py \
  --socks "$RESIDENTIAL_SOCKS_URL" \
  --restart
unset RESIDENTIAL_SOCKS_URL
```

这个脚本会备份 `/etc/x-ui/x-ui.db`，写入 `residential` SOCKS outbound 和 AI/Copilot 域名规则，然后重启 `x-ui`。需要在 VPS-A 和 VPS-B 都执行一次。

服务端只把高风控 AI/Copilot 类域名转到 `residential` outbound：

```text
openai.com
chatgpt.com
oaistatic.com
oaiusercontent.com
anthropic.com
claude.ai
console.anthropic.com
cursor.com
githubcopilot.com
copilot.microsoft.com
```

客户端仍然只选择普通 node1/node2 profile。命中上面域名后，Xray 在服务端二次路由到住宅出口。不要把住宅 SOCKS 账号、密码或上游地址写进 Clash/Mihomo 订阅。

`dmit.io` 不走住宅出口，继续保留在客户端订阅规则里的 `DIRECT` 前置规则。

## Install Skill

Fresh clone install:

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/Zanetach/LinkRay-deploy.git \
  ~/.codex/skills/LinkRay-deploy
```

Update an existing install:

```bash
git -C ~/.codex/skills/LinkRay-deploy pull --ff-only
```

Local copy install:

```bash
mkdir -p ~/.codex/skills
cp -R LinkRay-deploy ~/.codex/skills/
```

Invoke it with:

```text
$LinkRay-deploy
```

A fresh clone includes the skill entrypoint, deployment blueprint, wrapper rules, residential outbound deployment script, tests, and visual assets needed to run a new deployment from the documented prompts.

## Handoff Verification

Run these before handing a subscription to a user:

```bash
systemctl is-active x-ui nginx
ss -tlnp | grep -E ':(443|9444|9445|9446|<local-ws-port>|<local-xhttp-port>) '
ss -lunp | grep -E ':(8444) '

curl -fsS 'https://sub.example.com/clash/<subId>' -o /tmp/linkray.yaml
mihomo -t -f /tmp/linkray.yaml
grep -nE '^(proxy-groups|rule-providers|rules):' /tmp/linkray.yaml
grep -nE '^[[:space:]]*- name: (自动选择|故障转移|负载均衡|节点选择|流媒体|手动切换|全球代理|DNS_Proxy|Telegram|Google|YouTube|Netflix|Spotify|HBO|Bing|Microsoft|OpenAI|ClaudeAI|Disney|GitHub|国内媒体|本地直连|漏网之鱼)$' /tmp/linkray.yaml
```

For live checks, run Mihomo controller delay tests against every exact proxy name. A single GUI green check is not enough evidence.

Residential outbound verification is server-side:

```bash
python3 - <<'PY'
import json, pathlib
data=json.loads(pathlib.Path('/usr/local/x-ui/bin/config.json').read_text())
print([(o.get('tag'), o.get('protocol')) for o in data.get('outbounds', [])])
print([r for r in data.get('routing', {}).get('rules', []) if r.get('outboundTag') == 'residential'])
PY
```

## Node2 IP Change Checklist

When VPS-B changes IP, update these together:

```text
Cloudflare DNS for direct2/node2/xhttp2
VPS-A main-panel nodes.address
VPS-B share_addr values
VPS-B firewall allow rules for VPS-A
VPS-A Nginx WS/XHTTP upstreams
Wrapper server rewrite map
```

Then re-fetch `/clash/<subId>`, run `mihomo -t`, and run delay checks for every node2 profile.

## Operational Guardrails

- Keep one subscription authority: VPS-A.
- Do not disable subscriptions.
- Do not expose VPS-B panel/API ports publicly.
- Do not expose residential SOCKS upstream credentials in the public subscription.
- Do not rename `x-ui` services, database paths, API paths, or node sync identifiers for branding.
- Do not point Reality or Hysteria2 at Cloudflare orange-cloud hostnames.
- Do not bind Xray directly to public `443/tcp` for WS/XHTTP when Nginx owns 443.
- Keep the wrapper bound to `127.0.0.1`.

## Repository Layout

| Path | Purpose |
|---|---|
| [SKILL.md](SKILL.md) | Agent entrypoint and deployed workflow rules |
| [references/cluster-blueprint.md](references/cluster-blueprint.md) | Command-level deployment and repair blueprint |
| [scripts/configure_residential_outbound.py](scripts/configure_residential_outbound.py) | Writes the optional server-side residential Xray outbound into 3X-UI |
| [agents/openai.yaml](agents/openai.yaml) | Display metadata for OpenAI/Codex-style agent surfaces |
| [evals/evals.json](evals/evals.json) | Behavioral expectations for this deployed scope |
| [tests/test_configure_residential_outbound.py](tests/test_configure_residential_outbound.py) | Regression tests for residential outbound configuration |

## Local Checks

```bash
python3 ~/.codex/skills/readme-generator/scripts/check_readme_refs.py .
python3 -m unittest tests.test_configure_residential_outbound
git diff --check
```

## License

MIT License. See [LICENSE](LICENSE).

## Scope

This README intentionally describes the deployment already verified through this skill.
