#!/usr/bin/env python3
"""Tesla & SpaceX 周报 static site generator.

Converts every content/YYYY-MM-DD.md into reports/YYYY-MM-DD.html and
regenerates index.html. Pure standard library: no dependencies.
Usage: python3 build.py
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
REPORTS = ROOT / "reports"
SITE_TITLE = "Tesla & SpaceX 周报"
DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def inline(text):
    s = html.escape(text, quote=False)
    s = LINK_RE.sub(
        lambda m: '<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>'
        % (m.group(2).replace('"', "&quot;"), m.group(1)),
        s,
    )
    s = BOLD_RE.sub(r"<strong>\1</strong>", s)
    return s


def plain(text):
    """Markdown inline -> plain text (for titles / excerpts)."""
    text = LINK_RE.sub(r"\1", text)
    return BOLD_RE.sub(r"\1", text)


def section_class(title):
    t = title.lower()
    if "反方" in title:
        return "sec-bear"
    if t.startswith("tesla"):
        return "sec-tesla"
    if t.startswith("spacex"):
        return "sec-spacex"
    return "sec-other"


def stock_card(text):
    """Small card built ONLY from numbers present in the markdown line."""
    close = re.search(r"收盘\s*\$([\d,]+(?:\.\d+)?)", text)
    prev = re.search(r"前一周五[^$]*?收\s*\$([\d,]+(?:\.\d+)?)", text)
    chg = re.search(r"周(跌|涨)约?\s*([\d.]+)%", text)
    if not (close and chg):
        return ""
    down = chg.group(1) == "跌"
    arrow = "▼" if down else "▲"
    cls = "down" if down else "up"
    prev_html = (
        '<div class="stat"><span class="label">前一周五收盘</span>'
        '<span class="value small">$%s</span></div>' % prev.group(1)
        if prev else ""
    )
    return (
        '<div class="stock-card">'
        '<div class="stat"><span class="label">周五收盘</span>'
        '<span class="value">$%s</span></div>'
        '<div class="stat"><span class="label">周%s幅</span>'
        '<span class="value %s">%s %s%%</span></div>%s</div>'
        % (close.group(1), chg.group(1), cls, arrow, chg.group(2), prev_html)
    )


def convert(md):
    """Minimal converter for the weekly-report subset of Markdown:
    # / ## headings, paragraphs, '- ' lists, **bold**, [links](url)."""
    title, summary = None, ""
    out, para, items = [], [], []
    in_section = False

    def flush_para():
        if not para:
            return
        text = " ".join(para)
        para.clear()
        if text.startswith("**本周要点**"):
            out.append('<aside class="callout"><p>%s</p></aside>' % inline(text))
        elif text.startswith("**股价**"):
            out.append(stock_card(text))
            out.append('<p class="stock-line">%s</p>' % inline(text))
        else:
            out.append("<p>%s</p>" % inline(text))

    def flush_list():
        if not items:
            return
        out.append("<ul>" + "".join("<li>%s</li>" % inline(i) for i in items) + "</ul>")
        items.clear()

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_para(); flush_list()
            continue
        if line.startswith("# "):
            flush_para(); flush_list()
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            flush_para(); flush_list()
            if in_section:
                out.append("</section>")
            h = line[3:].strip()
            out.append('<section class="%s"><h2>%s</h2>' % (section_class(h), inline(h)))
            in_section = True
            continue
        if re.match(r"^\s*[-*] ", line):
            flush_para()
            items.append(re.sub(r"^\s*[-*] ", "", line))
            continue
        if items:  # continuation of a list item
            items[-1] += " " + line.strip()
            continue
        if line.startswith("**本周要点**"):
            summary = plain(line)
        para.append(line.strip())
    flush_para(); flush_list()
    if in_section:
        out.append("</section>")
    return title, summary, "\n".join(out)


def page(title, body, css_href, home_href=None):
    nav = (
        '<a class="back" href="%s">← 全部周报</a>' % home_href if home_href else ""
    )
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{title}</title>
<link rel="stylesheet" href="{css}">
</head>
<body>
<header class="site-header"><div class="wrap">
<a class="brand" href="{home}">{site}</a>{nav}
</div></header>
<main class="wrap">
{body}
</main>
<footer class="site-footer"><div class="wrap">{site} · 每周更新</div></footer>
</body>
</html>
""".format(title=html.escape(title), css=css_href, body=body, nav=nav,
           home=home_href or "./", site=html.escape(SITE_TITLE))


def cn_date(d):
    y, m, dd = d.split("-")
    return "%s年%d月%d日" % (y, int(m), int(dd))


def build():
    REPORTS.mkdir(exist_ok=True)
    reports = []
    for md_path in sorted(CONTENT.glob("*.md")):
        date = md_path.stem
        if not DATE_RE.match(date):
            print("skip (name is not YYYY-MM-DD):", md_path.name)
            continue
        title, summary, body = convert(md_path.read_text(encoding="utf-8"))
        title = title or "%s · %s" % (SITE_TITLE, cn_date(date))
        article = (
            '<article class="report">'
            '<p class="date"><time datetime="%s">%s</time></p>'
            "<h1>%s</h1>\n%s</article>" % (date, cn_date(date), inline(title), body)
        )
        (REPORTS / ("%s.html" % date)).write_text(
            page(plain(title), article, "../assets/style.css", "../"), encoding="utf-8")
        reports.append((date, plain(title), summary))
        print("built reports/%s.html" % date)

    reports.sort(key=lambda r: r[0], reverse=True)
    parts = ['<h1 class="site-title">%s</h1>' % html.escape(SITE_TITLE),
             '<p class="tagline">每周一份的 Tesla 与 SpaceX 中文简报</p>']
    if reports:
        d, t, s = reports[0]
        parts.append(
            '<a class="latest" href="reports/%s.html">'
            '<span class="badge">最新一期</span>'
            '<time datetime="%s">%s</time><h2>%s</h2>%s'
            '<span class="read">阅读全文 →</span></a>'
            % (d, d, cn_date(d), html.escape(t),
               '<p class="excerpt">%s</p>' % html.escape(s) if s else ""))
        parts.append('<h2 class="list-title">全部周报</h2><ul class="report-list">')
        for d, t, _ in reports:
            parts.append('<li><a href="reports/%s.html"><time datetime="%s">%s</time>'
                         '<span>%s</span></a></li>' % (d, d, d, html.escape(t)))
        parts.append("</ul>")
    else:
        parts.append("<p>暂无周报。</p>")
    (ROOT / "index.html").write_text(
        page(SITE_TITLE, "\n".join(parts), "assets/style.css"), encoding="utf-8")
    print("built index.html (%d reports)" % len(reports))


if __name__ == "__main__":
    build()
