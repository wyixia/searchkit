"""scrape 后端解析：markdown 正则 + Bing/Google 跳转 base64 解码双通道。"""

import base64
import html
import re

from .__init__ import NOISE_DOMAINS


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
            if not any(d in u for d in NOISE_DOMAINS):
                out.append(u)
    return out


def parse_markdown(md: str, limit: int = 10):
    from .__init__ import Result

    # 通道1：markdown 标准链接 [title](url)
    std = re.findall(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', md)
    # 通道2：Bing/Google 跳转链接 base64 解码出的真实 URL
    decoded = _decode_bing_ck(md)

    seen: set[str] = set()
    out: list = []

    for url in decoded:
        url = url.split("?")[0].split("#")[0]
        if url in seen:
            continue
        seen.add(url)
        out.append(Result(title=url.split("/")[2], url=url))
        if len(out) >= limit:
            return out

    for title, url in std:
        url = url.split("?")[0].split("#")[0]
        host = url.split("/")[2] if len(url.split("/")) > 2 else ""
        if any(d in host for d in NOISE_DOMAINS):
            continue
        if url in seen or url.startswith(("javascript:", "data:", "mailto:")):
            continue
        seen.add(url)
        out.append(Result(title=html.unescape(title).strip(), url=url))
        if len(out) >= limit:
            break
    return out
