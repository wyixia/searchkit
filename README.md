# searchkit

通用多引擎搜索工具，**库 + skill 双形态**，纯 Python、零平台依赖。

把 WorkBuddy 的 `WebFetch` + `multi-search-engine` 能力复刻成可移植代码：
同样 16 个搜索引擎、同样时间过滤，只是底层从"平台工具 + 提示词"换成了
`requests + html2text + BeautifulSoup` 的纯实现，并额外提供一个搜索 API 后端用于量产。

---

## 特性

- **16 个搜索引擎**：7 国内（百度/Bing CN/Bing INT/360/搜狗/微信/神马）+ 9 国际（Google/Google HK/DuckDuckGo/Yahoo/Startpage/Brave/Ecosia/Qwant/WolframAlpha）
- **三种后端**：
  - `scrape`（默认）：`requests + html2text` + 正则/base64 解码，零额外依赖
  - `bs`：`requests + BeautifulSoup` 按引擎 DOM 选择器精准解析，带摘要
  - `api`：Tavily / Serper 搜索 API，量产稳定、绕开反爬
- **高级语法**：`site:` / `filetype:` / `""` / `-` / `OR` 直接写进查询透传
- **时间过滤**：`--hour/--day/--week/--month/--year` → `tbs=qdr:h/d/w/m/y`
- **多引擎聚合**：`multi_search()` 单引擎失败自动跳过，冗余抗失败
- **双形态**：既能 `import searchkit` 当库，也能作为 skill 被智能体加载

---

## 安装

```bash
# 基础（scrape 后端）
pip install requests html2text

# + bs 后端
pip install beautifulsoup4

# + api 后端（Tavily）
pip install tavily-python
# Serper 后端用 requests 即可，无需额外包

# 作为可编辑库安装
pip install -e .
```

---

## 当库用

```python
from searchkit import search, multi_search

# scrape 后端（默认）
for r in search("kimi k3", engine="google", time_filter="w"):
    print(r.title, r.url)

# bs 后端（BeautifulSoup 精准解析，带摘要）
for r in search("kimi k3", engine="bing_int", backend="bs"):
    print(r.title, r.url, r.snippet)

# api 后端（量产稳定，需 key；或用环境变量 TAVILY_API_KEY / SERPER_API_KEY）
for r in search("kimi k3", backend="api", api_provider="tavily", api_key="tvly-xxx"):
    print(r.title, r.url)

# 多引擎聚合（单引擎失败自动跳过）
for r in multi_search("kimi k3", engines=["google", "bing_int", "ddg"], backend="bs"):
    print(r.url)
```

`Result` 数据类：`title: str`, `url: str`, `snippet: str`。

---

## 当 skill 用

把整个 `searchkit/` 目录放到智能体技能目录（如 `~/.workbuddy/skills/`），
智能体加载 `SKILL.md` 后通过 CLI 调用：

```bash
# scrape 后端（默认）
python search.py "kimi k3" --engine baidu --week --proxy http://127.0.0.1:7897

# bs 后端
python search.py "kimi k3" --engine bing_int --backend bs

# api 后端
python search.py "kimi k3" --backend api --api tavily --key tvly-xxx
python search.py "kimi k3" --backend api --api serper --key xxxx

# 多引擎聚合
python search.py "kimi k3" --multi google bing_int ddg --backend bs

# 列出所有引擎
python search.py --list
```

### CLI 参数

| 参数 | 说明 |
|------|------|
| `query` | 搜索词（必填）；`site:`/`filetype:`/`""`/`-`/`OR` 直接写 |
| `--engine` | 单引擎：baidu/bing_cn/bing_int/360/sogou/wechat/shenma/google/google_hk/ddg/yahoo/startpage/brave/ecosia/qwant/wolfram |
| `--backend` | `scrape`(默认) / `bs` / `api` |
| `--api` | `tavily` / `serper`（仅 api 后端） |
| `--key` | API key（或环境变量 `TAVILY_API_KEY` / `SERPER_API_KEY`） |
| `--multi` | 多引擎聚合，后跟引擎名列表 |
| `--limit N` | 返回条数 |
| `--proxy URL` | HTTP/HTTPS 代理，如 `http://127.0.0.1:7897` |
| `--hour/--day/--week/--month/--year` | 时间过滤 |
| `--list` | 列出所有可用引擎 |

---

## 引擎选择建议

- 中文查询 → `baidu` / `bing_cn` / `sogou`
- 英文查询 → `google` / `ddg` / `brave`
- 微信内容 → `wechat`（常验证码，不稳，已标记 `stable=False`）
- 量产稳定 → 直接用 `api` 后端（Tavily/Serper）

---

## 已知限制

1. **反爬**：`scrape`/`bs` 后端直接抓 Google/DuckDuckGo/百度 HTML 常被 403/验证码；
   靠代理 + 重试缓解，不根除。要稳定量产请用 `api` 后端。
2. **微信**：`wx.sogou.com` 基本要验证码，默认不建议用。
3. **解析启发式**：`scrape` 后端正则抽链接对改版敏感；`bs` 后端选择器按主流页面结构写，
   引擎改版可能需更新 `SearchEngine.bs_*` 字段。
4. **代理对国内站**：测试中发现代理 `127.0.0.1:7897` 对百度等国内站反而拦截，国内引擎宜直连。

---

## 与 WorkBuddy 内置能力的关系

| WorkBuddy | searchkit 等价 |
|-----------|----------------|
| `WebFetch` 工具 | `fetch_markdown()` / `fetch_html()`（requests + html2text） |
| `multi-search-engine` skill | `scrape` 后端（16 引擎 + 时间过滤） |
| — | `bs` / `api` 后端是增强 |

---

## 项目结构

```
searchkit/
├── searchkit/
│   ├── __init__.py     # 核心：引擎注册表 + 3 后端 + fetch + parse
│   └── parse_md.py     # scrape 后端解析（正则 + base64 跳转解码）
├── search.py           # CLI 入口
├── SKILL.md            # skill 描述（智能体加载用）
├── references/
│   └── engines.md      # 引擎清单 + 时间过滤 + 高级语法
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## License

MIT
