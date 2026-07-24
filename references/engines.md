# searchkit 引擎清单（references/engines.md）

| key | 引擎 | 区域 | URL 模板 | stable |
|-----|------|------|----------|--------|
| baidu | 百度 | cn | `https://www.baidu.com/s?wd={q}` | ✓ |
| bing_cn | Bing CN | cn | `https://cn.bing.com/search?q={q}&ensearch=0` | ✓ |
| bing_int | Bing INT | cn | `https://cn.bing.com/search?q={q}&ensearch=1` | ✓ |
| 360 | 360 | cn | `https://www.so.com/s?q={q}` | ✓ |
| sogou | 搜狗 | cn | `https://sogou.com/web?query={q}` | ✓ |
| wechat | 微信 | cn | `https://wx.sogou.com/weixin?type=2&query={q}` | ✗ 常验证码 |
| shenma | 神马 | cn | `https://m.sm.cn/s?q={q}` | ✓ |
| google | Google | global | `https://www.google.com/search?q={q}` | ✓ |
| google_hk | Google HK | global | `https://www.google.com.hk/search?q={q}` | ✓ |
| ddg | DuckDuckGo | global | `https://duckduckgo.com/html/?q={q}` | ✓ |
| yahoo | Yahoo | global | `https://search.yahoo.com/search?p={q}` | ✓ |
| startpage | Startpage | global | `https://www.startpage.com/sp/search?query={q}` | ✓ |
| brave | Brave | global | `https://search.brave.com/search?q={q}` | ✓ |
| ecosia | Ecosia | global | `https://www.ecosia.org/search?q={q}` | ✓ |
| qwant | Qwant | global | `https://www.qwant.com/?q={q}` | ✓ |
| wolfram | WolframAlpha | global | `https://www.wolframalpha.com/input?i={q}` | ✓ (无 tbs) |

## 时间过滤参数

| 参数 | tbs 值 | 含义 |
|------|--------|------|
| --hour | qdr:h | 过去 1 小时 |
| --day | qdr:d | 过去 1 天 |
| --week | qdr:w | 过去 1 周 |
| --month | qdr:m | 过去 1 月 |
| --year | qdr:y | 过去 1 年 |

## 高级语法（直接写进查询，透传）

- `site:github.com python` — 站内限定
- `machine learning filetype:pdf` — 文件类型
- `"exact phrase"` — 精确匹配
- `python -snake` — 排除
- `cat OR dog` — 任一
