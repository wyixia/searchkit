---
name: searchkit
description: |
  通用多引擎搜索工具。集成 16 个搜索引擎（7 国内 + 9 国际），支持
  site:/filetype:/""/-/_OR 高级语法与 tbs=qdr: 时间过滤，无需 API key。
  三种后端：scrape(默认,正则解析) / bs(BeautifulSoup 按引擎 DOM 精准解析) /
  api(Tavily/Serper 搜索 API,量产稳定)。既可当 Python 库 import，也可 CLI 调用。
  触发词：搜索、多引擎搜索、搜一下、搜资讯、site:、qdr:w、web_fetch 替代。
version: 1.1.0
---

# searchkit — 通用多引擎搜索

## 何时用
用户要搜网页 / 资讯，且不指定必须用某付费搜索 API（如 Tavily/Serper）时。
等价于"multi-search-engine"能力，但是纯代码实现、可移植、可当库。

## 三种后端
- **scrape**（默认）：requests + html2text + 正则/base64 解码。零额外依赖，反爬弱。
- **bs**：requests + BeautifulSoup 按引擎 DOM 选择器精准解析。稳过正则，需 `beautifulsoup4`。
- **api**：Tavily / Serper 搜索 API。量产稳定、绕开反爬、返回清洗 JSON，需 key。

## 两种调用方式（二选一）

### A. 当库
```python
from searchkit import search, multi_search
# bs 后端（精准 DOM 解析）
for r in search("kimi k3", engine="bing_int", backend="bs"):
    print(r.title, r.url, r.snippet)
# api 后端（量产稳定，需 key）
for r in search("kimi k3", backend="api", api_provider="tavily", api_key="tvly-xxx"):
    print(r.title, r.url)
# 多引擎聚合（单引擎失败跳过）
for r in multi_search("kimi k3", engines=["google","bing_int","ddg"], backend="bs"):
    print(r.url)
```

### B. 当 CLI
```bash
python search.py "kimi k3" --engine bing_int --backend bs
python search.py "kimi k3" --backend api --api tavily --key tvly-xxx
python search.py "kimi k3" --backend api --api serper --key xxxx
python search.py "kimi k3" --engine baidu --week --proxy http://127.0.0.1:7897
```

## 参数映射
- --engine : baidu|bing_cn|bing_int|360|sogou|wechat|shenma|
             google|google_hk|ddg|yahoo|startpage|brave|ecosia|qwant|wolfram
- --backend : scrape | bs | api
- --api : tavily | serper（仅 api 后端）
- --key : API key（或用环境变量 TAVILY_API_KEY / SERPER_API_KEY）
- --multi ENGINE ... : 多引擎聚合
- --week/--day/--month/--year/--hour : 时间过滤 → tbs=qdr:w/d/m/y/h
- --limit N / --proxy URL / --list

## 引擎选择建议
- 中文 → baidu / bing_cn / sogou；英文 → google / ddg / brave
- 微信 → wechat（常验证码，不稳）
- 量产稳定 → 直接用 api 后端（Tavily/Serper）

## 依赖
```
pip install requests html2text beautifulsoup4
pip install tavily-python        # 仅 api 后端用 tavily
# serper 后端用 requests 即可，无需额外包
```

## 限制
- scrape/bs 后端：Google/DuckDuckGo/百度等常反爬（验证码/403），靠代理+重试缓解。
- api 后端：需 key，有调用额度/费用，但最稳。
- 微信(wx.sogou.com)基本要验证码，默认不建议用。

## 与 WorkBuddy 内置能力的关系
- WebFetch ≈ fetch_markdown()（requests + html2text）
- multi-search-engine skill ≈ 本工具 scrape 后端（16 引擎 + 时间过滤）
- bs/api 后端是本工具在 WorkBuddy 方案上的增强
