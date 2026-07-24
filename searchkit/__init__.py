"""
searchkit — 通用多引擎搜索（库 + skill 双形态）

三种后端：
  - "scrape"  : requests + html2text + 正则/base64 解析（默认，等价 WebFetch）
  - "bs"      : requests + BeautifulSoup 按引擎 DOM 选择器精准解析
  - "api"     : Tavily / Serper 搜索 API（量产稳定，绕开反爬，需 key）

当作库：
    from searchkit import search
    for r in search("kimi k3", engine="bing_int", backend="bs"):
        print(r.title, r.url)
    # API 后端
    for r in search("kimi k3", backend="api", api_provider="tavily",
                    api_key="tvly-xxx"):
        print(r.title, r.url)

当作 skill：
    python search.py "kimi k3" --engine bing_int --backend bs
    python search.py "kimi k3" --backend api --api tavily --key tvly-xxx

依赖：
    pip install requests html2text beautifulsoup4
    # API 后端额外：pip install tavily-python   (Serper 用 requests 即可)
"""

from __future__ import annotations

import base64
import html
import os
import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote

import requests
import html2text


# ----------------------------- 数据模型 -----------------------------

@dataclass
class Result:
    title: str
    url: str
    snippet: str = ""


@dataclass
class SearchEngine:
    name: str
    url_template: str            # 含 {q} 占位
    region: str = "global"       # cn / global
    supports_tbs: bool = True    # 是否支持 tbs=qdr: 时间过滤
    stable: bool = True          # 是否通常可稳定访问
    # BeautifulSoup 后端用的结果容器选择器（引擎专属）
    bs_result_sel: str = ""      # 每个结果块的选择器
    bs_title_sel: str = "a"      # 结果块内标题/链接选择器
    bs_snippet_sel: str = ""     # 结果块内摘要选择器（可选）

    def build_url(self, query: str, time_filter: Optional[str] = None) -> str:
        url = self.url_template.format(q=quote(query))
        if time_filter and self.supports_tbs:
            sep = "&" if "?" in url else "?"
            url += f"{sep}tbs=qdr:{time_filter}"
        return url


# ----------------------------- 引擎注册表（16 个）-----------------------------

ENGINES: dict[str, SearchEngine] = {
    # 国内 7
    "baidu":    SearchEngine("baidu",    "https://www.baidu.com/s?wd={q}",
                             region="cn", stable=True,
                             bs_result_sel="div.result, div.c-container",
                             bs_title_sel="h3 a", bs_snippet_sel="div.c-abstract, span.content-right_8Zs40"),
    "bing_cn":  SearchEngine("bing_cn",  "https://cn.bing.com/search?q={q}&ensearch=0",
                             region="cn", stable=True,
                             bs_result_sel="li.b_algo", bs_title_sel="h2 a",
                             bs_snippet_sel="div.b_caption p, p.b_lineclamp2"),
    "bing_int": SearchEngine("bing_int", "https://cn.bing.com/search?q={q}&ensearch=1",
                             region="cn", stable=True,
                             bs_result_sel="li.b_algo", bs_title_sel="h2 a",
                             bs_snippet_sel="div.b_caption p, p.b_lineclamp2"),
    "360":      SearchEngine("360",      "https://www.so.com/s?q={q}",
                             region="cn", stable=True,
                             bs_result_sel="li.res-list", bs_title_sel="h3 a",
                             bs_snippet_sel="div.res-desc, p.res-abs"),
    "sogou":    SearchEngine("sogou",    "https://sogou.com/web?query={q}",
                             region="cn", stable=True,
                             bs_result_sel="div.rb, div.vrwrap", bs_title_sel="h3 a",
                             bs_snippet_sel="div.fz-mid, div.text-layout"),
    "wechat":   SearchEngine("wechat",   "https://wx.sogou.com/weixin?type=2&query={q}",
                             region="cn", stable=False,
                             bs_result_sel="div.news-box", bs_title_sel="a",
                             bs_snippet_sel="p.txt-info, div.s-p"),
    "shenma":   SearchEngine("shenma",   "https://m.sm.cn/s?q={q}",
                             region="cn", stable=True,
                             bs_result_sel="div.result", bs_title_sel="a",
                             bs_snippet_sel="div.abs"),
    # 国际 9
    "google":    SearchEngine("google",    "https://www.google.com/search?q={q}",
                             region="global", stable=True,
                             bs_result_sel="div.g, div.MjjYud", bs_title_sel="h3 a",
                             bs_snippet_sel="div.VwiC3b, div.IsZvec"),
    "google_hk": SearchEngine("google_hk", "https://www.google.com.hk/search?q={q}",
                             region="global", stable=True,
                             bs_result_sel="div.g, div.MjjYud", bs_title_sel="h3 a",
                             bs_snippet_sel="div.VwiC3b, div.IsZvec"),
    "ddg":       SearchEngine("ddg",       "https://duckduckgo.com/html/?q={q}",
                             region="global", stable=True,
                             bs_result_sel="div.result, div.web-result", bs_title_sel="a.result__a",
                             bs_snippet_sel="a.result__snippet, div.result__snippet"),
    "yahoo":     SearchEngine("yahoo",     "https://search.yahoo.com/search?p={q}",
                             region="global", stable=True,
                             bs_result_sel="div.compTitle, div.algo", bs_title_sel="h3 a",
                             bs_snippet_sel="div.compText, div.algo-snippet"),
    "startpage": SearchEngine("startpage", "https://www.startpage.com/sp/search?query={q}",
                             region="global", stable=True,
                             bs_result_sel="div.w-cnresult, div.search_result", bs_title_sel="a",
                             bs_snippet_sel="div.w-cnresult-snippet, p"),
    "brave":     SearchEngine("brave",     "https://search.brave.com/search?q={q}",
                             region="global", stable=True,
                             bs_result_sel="div.snippet, div.snippet-fb", bs_title_sel="a",
                             bs_snippet_sel="p.snippet-description, div.snippet-desc"),
    "ecosia":    SearchEngine("ecosia",    "https://www.ecosia.org/search?q={q}",
                             region="global", stable=True,
                             bs_result_sel="div.result", bs_title_sel="a.result-link",
                             bs_snippet_sel="div.abstract, p.abstract"),
    "qwant":     SearchEngine("qwant",     "https://www.qwant.com/?q={q}",
                             region="global", stable=True,
                             bs_result_sel="div.results a, div.result", bs_title_sel="a",
                             bs_snippet_sel="div.result-snippet, p"),
    "wolfram":   SearchEngine("wolfram",   "https://www.wolframalpha.com/input?i={q}",
                             region="global", supports_tbs=False, stable=True),
}

# 结果页里要过滤掉的引擎自身/导航域名
NOISE_DOMAINS = {
    "google.com", "google.com.hk", "bing.com", "baidu.com", "so.com",
    "sogou.com", "sm.cn", "duckduckgo.com", "yahoo.com", "startpage.com",
    "brave.com", "ecosia.org", "qwant.com", "wolframalpha.com",
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


# ----------------------------- web_fetch 等价：fetch_html / fetch_markdown -----------------------------

def fetch_html(url: str,
               *,
               timeout: int = 15,
               retries: int = 2,
               proxy: Optional[str] = None,
               ua: str = UA) -> str:
    """抓取 URL 返回原始 HTML。"""
    proxies = {"http": proxy, "https": proxy} if proxy else None
    last_err: Optional[Exception] = None
    for _ in range(retries + 1):
        try:
            r = requests.get(url, headers={"User-Agent": ua},
                             timeout=timeout, proxies=proxies)
            r.raise_for_status()
            return r.text
        except Exception as e:
            last_err = e
            time.sleep(2)
    raise last_err or RuntimeError("fetch_html failed")


def fetch_markdown(url: str, **kwargs) -> str:
    """抓取 URL 的 HTML 并转成 markdown，等价 WorkBuddy 的 WebFetch 工具。"""
    html_text = fetch_html(url, **kwargs)
    h = html2text.HTML2Text()
    h.ignore_images = True
    h.ignore_links = False
    h.body_width = 0
    return h.handle(html_text)


# ----------------------------- 解析后端 -----------------------------

def _is_noise(url: str) -> bool:
    return any(d in url for d in NOISE_DOMAINS)


def _clean(url: str) -> str:
    return url.split("?")[0].split("#")[0]


def _decode_bing_ck(md: str) -> list[str]:
    """解码 Bing/Google 结果页里 bing.com/ck/a?u=a1<base64> 的跳转链接。"""
    out: list[str] = []
    for chunk in re.findall(r'u=a1([A-Za-z0-9_\-]+)', md):
        try:
            pad = chunk + "=" * (-len(chunk) % 4)
            raw = base64.urlsafe_b64decode(pad).decode("utf-8", "ignore")
        except Exception:
            continue
        for m in re.finditer(r'https?://[^\s&"\\)]+', raw):
            u = m.group(0)
            if not _is_noise(u):
                out.append(u)
    return out


def parse_markdown(md: str, limit: int = 10) -> list[Result]:
    """scrape 后端：正则 + base64 双通道（适合无 bs4 环境）。"""
    from .parse_md import parse_markdown as _pm  # 复用下方逻辑
    return _pm(md, limit)


def _resolve_url(url: str) -> str:
    """若链接是 Bing/Google 的 ck/a 跳转，解码出真实 URL；否则原样返回。"""
    if "bing.com/ck/a" in url or "google.com/url" in url:
        for chunk in re.findall(r'u=a1([A-Za-z0-9_\-]+)', url):
            try:
                pad = chunk + "=" * (-len(chunk) % 4)
                raw = base64.urlsafe_b64decode(pad).decode("utf-8", "ignore")
                m = re.search(r'https?://[^\s&"\\)]+', raw)
                if m and not _is_noise(m.group(0)):
                    return _clean(m.group(0))
            except Exception:
                continue
    return _clean(url)


def parse_bs(html_text: str, engine: SearchEngine, limit: int = 10) -> list[Result]:
    """bs 后端：BeautifulSoup 按引擎 DOM 选择器精准解析。"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_text, "html.parser")
    seen: set[str] = set()
    out: list[Result] = []
    blocks = soup.select(engine.bs_result_sel) if engine.bs_result_sel else []
    for blk in blocks:
        title_a = blk.select_one(engine.bs_title_sel)
        if not title_a:
            continue
        raw_url = title_a.get("href", "")
        if not raw_url or not raw_url.startswith("http"):
            continue
        url = _resolve_url(raw_url)          # 处理 bing/google 跳转解码
        if not url.startswith("http") or _is_noise(url):
            continue
        if url in seen:
            continue
        seen.add(url)
        title = html.unescape(title_a.get_text(strip=True) or url.split("/")[2])
        snippet = ""
        if engine.bs_snippet_sel:
            sn = blk.select_one(engine.bs_snippet_sel)
            if sn:
                snippet = sn.get_text(strip=True)
        out.append(Result(title=title, url=url, snippet=snippet))
        if len(out) >= limit:
            break
    return out


# ----------------------------- API 后端（Tavily / Serper）-----------------------------

def search_api(query: str,
                provider: str = "tavily",
                api_key: Optional[str] = None,
                time_filter: Optional[str] = None,
                limit: int = 10) -> list[Result]:
    """量产稳定后端：调搜索 API，绕开反爬。需要 key（环境变量或参数）。"""
    api_key = api_key or os.getenv("TAVILY_API_KEY" if provider == "tavily"
                                   else "SERPER_API_KEY")
    if not api_key:
        raise RuntimeError(f"{provider} api_key 未提供（参数或环境变量）")

    if provider == "tavily":
        # pip install tavily-python
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        kwargs = {"query": query, "max_results": limit, "topic": "general"}
        if time_filter:
            days_map = {"h": 1, "d": 1, "w": 7, "m": 30, "y": 365}
            kwargs["days"] = days_map.get(time_filter, 7)
        resp = client.search(**kwargs)
        items = resp.get("results", [])
        return [Result(title=i.get("title", ""), url=i.get("url", ""),
                       snippet=i.get("content", "")) for i in items]

    elif provider == "serper":
        tf_map = {"h": "h", "d": "d", "w": "w", "m": "m", "y": "y"}
        params = {"q": query, "num": limit}
        if time_filter:
            params["tbs"] = f"qdr:{time_filter}"
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json=params, timeout=20)
        r.raise_for_status()
        items = r.json().get("organic", [])
        return [Result(title=i.get("title", ""), url=i.get("link", ""),
                       snippet=i.get("snippet", "")) for i in items]

    raise ValueError(f"unknown api provider '{provider}'")


# ----------------------------- 对外 API -----------------------------

def search(query: str,
           engine: str = "google",
           time_filter: Optional[str] = None,
           limit: int = 10,
           proxy: Optional[str] = None,
           backend: str = "scrape",
           api_provider: str = "tavily",
           api_key: Optional[str] = None) -> list[Result]:
    """统一搜索入口。

    backend:
      "scrape" (默认) → requests+html2text+正则/base64
      "bs"           → requests+BeautifulSoup 按引擎 DOM 解析
      "api"          → Tavily/Serper（需 api_key）
    高级语法(site:/filetype:/""/-/OR)直接写进 query 透传。
    """
    if backend == "api":
        return search_api(query, provider=api_provider, api_key=api_key,
                          time_filter=time_filter, limit=limit)

    if engine not in ENGINES:
        raise KeyError(f"unknown engine '{engine}'. available: {', '.join(ENGINES)}")
    eng = ENGINES[engine]
    url = eng.build_url(query, time_filter)
    html_text = fetch_html(url, proxy=proxy)

    if backend == "bs":
        return parse_bs(html_text, eng, limit)
    # 默认 scrape
    md = fetch_markdown(url, proxy=proxy)
    return parse_markdown(md, limit)


def multi_search(query: str,
                 engines: Optional[list[str]] = None,
                 time_filter: Optional[str] = None,
                 limit: int = 10,
                 proxy: Optional[str] = None,
                 backend: str = "scrape") -> list[Result]:
    """多引擎聚合：单引擎失败不影响整体，模拟 WorkBuddy 的冗余抗失败。"""
    if engines is None:
        engines = ["google", "bing_int", "ddg", "brave"]
    results: list[Result] = []
    for e in engines:
        try:
            results += search(query, engine=e, time_filter=time_filter,
                              limit=limit, proxy=proxy, backend=backend)
        except Exception:
            continue
    seen: set[str] = set()
    deduped: list[Result] = []
    for r in results:
        if r.url in seen:
            continue
        seen.add(r.url)
        deduped.append(r)
    return deduped[:limit]


__all__ = ["search", "multi_search", "search_api", "ENGINES", "SearchEngine",
           "Result", "fetch_html", "fetch_markdown", "parse_markdown",
           "parse_bs"]
