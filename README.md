# 微信公众号宏观研究公开索引

这是 `wechat-research-corpus` 的公开、元数据专用版本。它提供可检索、可下载、可审计的文章目录，但不复制第三方文章全文、图表、原始网页、私有归档包或个人阅读数据。

## 数据文件

- `data/articles.jsonl`：适合流式处理和模型读取，一篇一行。
- `data/articles.json`：适合浏览器或静态应用直接读取。
- `data/articles.csv`：适合 Excel、R、Python 和数据库导入。
- `data/articles.sqlite`：可直接使用 SQLite 或 DuckDB 查询，已为日期、研究流、公众号和质量状态建立索引。
- `data/stats.json`：记录数量、覆盖期、研究流分布和生成版本。
- `schema/article.schema.json`：公开字段的 JSON Schema。
- [搜索页面](https://chuanchenge-ship-it.github.io/wechat-research-corpus-public/)：按标题、研究流和质量状态检索。

## 稳定访问

```text
https://raw.githubusercontent.com/chuanchenge-ship-it/wechat-research-corpus-public/main/data/articles.jsonl
https://raw.githubusercontent.com/chuanchenge-ship-it/wechat-research-corpus-public/main/data/articles.csv
```

SQLite 示例：

```sql
SELECT published_date, publisher_account, title, source_url
FROM articles
WHERE research_stream = '美国宏观'
ORDER BY published_date DESC
LIMIT 20;
```

Python示例：

```python
import pandas as pd

url = "https://raw.githubusercontent.com/chuanchenge-ship-it/wechat-research-corpus-public/main/data/articles.csv"
df = pd.read_csv(url)
print(df.groupby("research_stream").size())
```

## 数据边界

- `content_status` 描述私有证据库中的恢复状态，不代表公开库提供全文。
- `quality_status` 与 `quality_flags` 用于揭示重复、缺图或来源验证问题。
- `source_url` 指向公开来源；目标网页可能移动、失效或调整访问条件。
- 公开库不包含 `discovered_url`，避免发布临时搜索令牌和追踪参数。

## 许可与权利

数据库的事实性元数据按 [ODC Attribution License 1.0](LICENSE-DATA) 提供；程序代码按 [MIT License](LICENSE-CODE) 提供。文章正文、图表、商标及其他第三方内容的权利仍归原权利人所有。本项目与微信及相关研究机构无隶属关系。
