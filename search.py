"""searchkit CLI 入口（skill 形态调它）。

用法：
    python search.py "kimi k3" --engine bing_int --backend bs
    python search.py "kimi k3" --engine baidu
    python search.py "kimi k3" --backend api --api tavily --key tvly-xxx
    python search.py "kimi k3" --backend api --api serper --key xxxx
"""

from __future__ import annotations

import argparse
import sys

from searchkit import search, multi_search, ENGINES


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="searchkit",
        description="通用多引擎搜索（库+skill 双形态，支持 scrape/bs/api 三后端）")
    p.add_argument("query", help="搜索词；高级语法 site:/filetype:/\"\"/-/_OR 直接写")
    p.add_argument("--engine", default="google",
                   choices=list(ENGINES),
                   help="单引擎搜索时指定（scrape/bs 后端用）")
    p.add_argument("--multi", nargs="*", metavar="ENGINE",
                   help="多引擎聚合（不填则用默认 google/bing_int/ddg/brave）")
    p.add_argument("--backend", default="scrape",
                   choices=["scrape", "bs", "api"],
                   help="scrape=正则解析(默认) / bs=BeautifulSoup / api=搜索API")
    p.add_argument("--api", default="tavily",
                   choices=["tavily", "serper"], help="api 后端选提供商")
    p.add_argument("--key", default=None, help="api 后端 key（或环境变量）")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--proxy", default=None,
                   help="HTTP/HTTPS 代理，如 http://127.0.0.1:7897")
    p.add_argument("--list", action="store_true",
                   help="列出所有可用引擎后退出")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--hour",  action="store_const", const="h", dest="tf")
    g.add_argument("--day",   action="store_const", const="d", dest="tf")
    g.add_argument("--week",  action="store_const", const="w", dest="tf")
    g.add_argument("--month", action="store_const", const="m", dest="tf")
    g.add_argument("--year",  action="store_const", const="y", dest="tf")

    if argv is None:
        argv = sys.argv[1:]
    if "--list" in argv:
        for k, e in ENGINES.items():
            flag = "" if e.stable else "  (不稳)"
            print(f"  {k:10s} {e.region:7s}{flag}")
        return 0

    a = p.parse_args(argv)

    if a.backend == "api":
        results = search(a.query, backend="api", api_provider=a.api,
                         api_key=a.key, time_filter=a.tf, limit=a.limit)
    elif a.multi is not None:
        results = multi_search(a.query, engines=a.multi or None,
                               time_filter=a.tf, limit=a.limit,
                               proxy=a.proxy, backend=a.backend)
    else:
        results = search(a.query, engine=a.engine, time_filter=a.tf,
                         limit=a.limit, proxy=a.proxy, backend=a.backend)

    for i, r in enumerate(results, 1):
        snip = f" — {r.snippet[:60]}" if r.snippet else ""
        print(f"{i}. {r.title}{snip}\n   {r.url}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
