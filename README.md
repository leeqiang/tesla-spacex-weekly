# Tesla & SpaceX 周报

每周一份的 Tesla 与 SpaceX 中文简报，静态网站，托管在 GitHub Pages：
https://leeqiang.github.io/tesla-spacex-weekly/

## 结构

- `content/YYYY-MM-DD.md` — 每期周报的 Markdown 原文（唯一需要编辑的地方）
- `reports/YYYY-MM-DD.html` — 由脚本生成的报告页
- `index.html` — 由脚本生成的首页（最新一期 + 全部往期，按日期倒序）
- `essays/YYYY-MM-DD-slug.md` — 长文精读 Markdown；生成 `essays/<slug>.html` 与 `essays/index.html`
- `assets/style.css` — 共享样式（自动适配浅色/深色模式）
- `build.py` — 生成脚本（仅用 Python 3 标准库，无需安装依赖；同时构建周报与长文）

## 添加新一期

```bash
cp /path/to/2026-10-26.md content/2026-10-26.md   # 文件名必须是 YYYY-MM-DD.md
python3 build.py
git add -A && git commit -m "Weekly report 2026-10-26" && git push origin main
```

推送后 GitHub Pages 会在一两分钟内自动更新。

Markdown 支持范围：`#` 标题、`##` 分节、段落、`- ` 列表、`**粗体**`、`[链接](url)`。
以 `**本周要点**` 开头的段落显示为摘要卡片；以 `**股价**` 开头的段落会额外显示收盘价/周涨跌卡片（数字直接取自该段原文）。
