#!/usr/bin/env python3
"""Tesla & SpaceX 周报 static site generator.

Converts every content/YYYY-MM-DD.md into reports/YYYY-MM-DD.html,
every essays/*.md into essays/<slug>.html, and regenerates index pages.
Pure standard library: no dependencies.
Usage: python3 build.py
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
REPORTS = ROOT / "reports"
ESSAYS = ROOT / "essays"
SITE_TITLE = "Tesla & SpaceX 周报"
DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
ESSAY_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:-.*)?$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
OL_RE = re.compile(r"^\s*\d+\.\s+")


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
    if "长文精读" in title:
        return "sec-essay"
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


def convert(md, wrap_sections=True):
    """Minimal converter for weekly-report / essay Markdown:
    # / ## / ### headings, paragraphs, '- ' and '1. ' lists,
    > blockquotes, **bold**, [links](url)."""
    title, summary = None, ""
    out, para, items = [], [], []
    list_tag = None  # "ul" or "ol"
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
        elif text.startswith("**说明**"):
            out.append('<aside class="callout"><p>%s</p></aside>' % inline(text))
        else:
            out.append("<p>%s</p>" % inline(text))

    def flush_list():
        nonlocal list_tag
        if not items:
            return
        tag = list_tag or "ul"
        out.append("<%s>" % tag + "".join("<li>%s</li>" % inline(i) for i in items) + "</%s>" % tag)
        items.clear()
        list_tag = None

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
            if wrap_sections:
                if in_section:
                    out.append("</section>")
                h = line[3:].strip()
                out.append('<section class="%s"><h2>%s</h2>' % (section_class(h), inline(h)))
                in_section = True
            else:
                out.append("<h2>%s</h2>" % inline(line[3:].strip()))
            continue
        if line.startswith("### "):
            flush_para(); flush_list()
            out.append("<h3>%s</h3>" % inline(line[4:].strip()))
            continue
        if line.startswith("> "):
            flush_para(); flush_list()
            out.append("<blockquote><p>%s</p></blockquote>" % inline(line[2:].strip()))
            continue
        if re.match(r"^\s*[-*] ", line):
            flush_para()
            if list_tag and list_tag != "ul":
                flush_list()
            list_tag = "ul"
            items.append(re.sub(r"^\s*[-*] ", "", line))
            continue
        if OL_RE.match(line):
            flush_para()
            if list_tag and list_tag != "ol":
                flush_list()
            list_tag = "ol"
            items.append(OL_RE.sub("", line))
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


def page(title, body, css_href, home_href="./", essays_href="essays/", back_href=None, back_label="← 返回"):
    nav_links = (
        '<nav class="site-nav">'
        '<a href="%s">周报</a>'
        '<a href="%s">长文精读</a>'
        "</nav>" % (home_href, essays_href)
    )
    back = (
        '<a class="back" href="%s">%s</a>' % (back_href, html.escape(back_label))
        if back_href else ""
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
<a class="brand" href="{home}">{site}</a>{nav}{back}
</div></header>
<main class="wrap">
{body}
</main>
<footer class="site-footer"><div class="wrap">{site} · 每周更新</div></footer>
</body>
</html>
""".format(title=html.escape(title), css=css_href, body=body, nav=nav_links,
           back=back, home=home_href, site=html.escape(SITE_TITLE))


def cn_date(d):
    y, m, dd = d.split("-")
    return "%s年%d月%d日" % (y, int(m), int(dd))


def essay_date(stem):
    m = ESSAY_DATE_RE.match(stem)
    return m.group(1) if m else None


def build_reports():
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
            page(plain(title), article, "../assets/style.css",
                 home_href="../", essays_href="../essays/",
                 back_href="../", back_label="← 全部周报"),
            encoding="utf-8")
        reports.append((date, plain(title), summary))
        print("built reports/%s.html" % date)
    return reports


def build_essays():
    ESSAYS.mkdir(exist_ok=True)
    essays = []
    for md_path in sorted(ESSAYS.glob("*.md")):
        stem = md_path.stem
        date = essay_date(stem)
        title, summary, body = convert(md_path.read_text(encoding="utf-8"))
        title = title or stem
        date_html = (
            '<p class="date"><time datetime="%s">%s</time></p>' % (date, cn_date(date))
            if date else ""
        )
        article = (
            '<article class="report essay">'
            "%s<h1>%s</h1>\n%s</article>" % (date_html, inline(title), body)
        )
        (ESSAYS / ("%s.html" % stem)).write_text(
            page(plain(title), article, "../assets/style.css",
                 home_href="../", essays_href="./",
                 back_href="./", back_label="← 全部长文"),
            encoding="utf-8")
        essays.append((date or "0000-00-00", stem, plain(title), summary))
        print("built essays/%s.html" % stem)

    essays.sort(key=lambda e: (e[0], e[1]), reverse=True)
    parts = [
        '<h1 class="site-title">长文精读</h1>',
        '<p class="tagline">长文与人生 / 认知类文章的精读摘要（非全文翻译）</p>',
    ]
    if essays:
        parts.append('<ul class="report-list">')
        for date, stem, title, _ in essays:
            label = date if date != "0000-00-00" else stem
            parts.append(
                '<li><a href="%s.html"><time datetime="%s">%s</time>'
                '<span>%s</span></a></li>'
                % (stem, date if date != "0000-00-00" else "", label, html.escape(title))
            )
        parts.append("</ul>")
    else:
        parts.append("<p>暂无长文。</p>")
    (ESSAYS / "index.html").write_text(
        page("长文精读 · " + SITE_TITLE, "\n".join(parts), "../assets/style.css",
             home_href="../", essays_href="./"),
        encoding="utf-8")
    print("built essays/index.html (%d essays)" % len(essays))
    return essays


def build_home(reports):
    parts = [
        '<h1 class="site-title">%s</h1>' % html.escape(SITE_TITLE),
        '<p class="tagline">每周一份的 Tesla 与 SpaceX 中文简报 · '
        '<a href="essays/">长文精读</a></p>',
    ]
    reports = sorted(reports, key=lambda r: r[0], reverse=True)
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
        page(SITE_TITLE, "\n".join(parts), "assets/style.css",
             home_href="./", essays_href="essays/"),
        encoding="utf-8")
    print("built index.html (%d reports)" % len(reports))


def build():
    reports = build_reports()
    build_essays()
    build_home(reports)


if __name__ == "__main__":
    build()
