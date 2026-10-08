#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 content/ 里的页面片段 + posts/ 里的文章，组装成一个纯静态站点。

用法：
    python build.py

加一篇文章：往 posts/ 里丢一个 .md 文件，开头写三行元信息，再跑一次本脚本。
    ---
    title: 文章标题
    date: 2026-10-09
    summary: 一句话摘要
    ---
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
POSTS = ROOT / "posts"

# ===================== 站点信息 =====================
# 想改站名 / 导航 / 页脚，只改这一段就够了
SITE = {
    "title": "曾荣琪",
    "tagline": "一个存放生活记忆的地方",
    "welcome": "欢迎你来到这个网站，很高兴你能看到我内心隐藏最深的部分，你对我一定很重要！",
    "nav": [
        ("index.html", "首页"),
        ("memory.html", "记忆"),
        ("writing.html", "文字"),
        ("timeline.html", "时间线"),
        ("resume.html", "简历"),
        ("collection.html", "收藏"),
    ],
    "footer": "欢迎留下打卡留言 · 想联系我：这里填你的邮箱 / 知乎 / 公众号",
}
# ====================================================


def esc(s):
    """转义成安全的 HTML 文本。"""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def inline(text):
    """处理行内标记：链接、粗体、斜体、代码。"""
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def md2html(text):
    """一个够用的极简 Markdown 转换：标题、段落、列表、引用、图片、原始 HTML。"""
    out = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # 原始 HTML 块（照片、图注这些直接写标签）
        if line.strip().startswith("<"):
            out.append(line.rstrip())
            i += 1
            continue

        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            tag = "h1" if level == 1 else f"h{level}"
            out.append(f"<{tag}>{inline(m.group(2))}</{tag}>")
            i += 1
            continue

        # 分隔线
        if line.strip() in ("---", "***"):
            out.append("<hr />")
            i += 1
            continue

        # 无序列表
        if re.match(r"^\s*[-*]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(inline(re.sub(r"^\s*[-*]\s+", "", lines[i])))
                i += 1
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>")
            continue

        # 引用
        if line.strip().startswith(">"):
            out.append(f"<blockquote><p>{inline(line.strip().lstrip('> '))}</p></blockquote>")
            i += 1
            continue

        # 空行
        if not line.strip():
            i += 1
            continue

        # 普通段落
        out.append(f"<p>{inline(line.strip())}</p>")
        i += 1

    return "\n".join(out)


def split_frontmatter(text):
    """读取 --- 包裹的元信息。"""
    meta, body = {}, text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for row in parts[1].strip().split("\n"):
                if ":" in row:
                    k, v = row.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = parts[2]
    return meta, body


def page(title, body_html, current=""):
    """把内容套进整站的骨架里。"""
    nav_html = "\n".join(
        f'<li><a href="{href}"'
        + (' aria-current="page"' if href == current else "")
        + f">{label}</a></li>"
        for href, label in SITE["nav"]
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{esc(title)} · {esc(SITE['title'])}</title>
<meta name="description" content="{esc(SITE['tagline'])}" />
<link rel="stylesheet" href="tufte.css" />
<link rel="stylesheet" href="site.css" />
</head>
<body>
<header class="masthead">
  <a class="brand" href="index.html">{esc(SITE['title'])}</a>
  <nav><ul>
{nav_html}
  </ul></nav>
</header>

<article>
{body_html}
</article>

<footer class="colophon">
  <p>{esc(SITE['footer'])}</p>
</footer>
</body>
</html>
"""


def main():
    built = []
    CONTENT.mkdir(exist_ok=True)
    POSTS.mkdir(exist_ok=True)

    # ---------- 主页面 ----------
    for md_file in sorted(CONTENT.glob("*.md")):
        page_name = md_file.stem + ".html"
        raw = md_file.read_text(encoding="utf-8")

        # 首页顶部自动加站名和副标题
        if md_file.stem == "index":
            head = (
                f"<h1>{esc(SITE['title'])}</h1>\n"
                f'<p class="subtitle">{esc(SITE["tagline"])}</p>\n'
                f'<blockquote class="welcome"><p>{esc(SITE["welcome"])}</p></blockquote>\n'
            )
        else:
            head = ""

        html = page(md_file.stem, head + md2html(raw), current=page_name)
        (ROOT / page_name).write_text(html, encoding="utf-8")
        built.append(page_name)

    # ---------- 文章 ----------
    POSTS.mkdir(exist_ok=True)
    (ROOT / "posts").mkdir(exist_ok=True)
    entries = []
    for md_file in sorted(POSTS.glob("*.md"), reverse=True):
        meta, body = split_frontmatter(md_file.read_text(encoding="utf-8"))
        title = meta.get("title", md_file.stem)
        date = meta.get("date", "")
        summary = meta.get("summary", "")
        slug = md_file.stem + ".html"

        article_html = (
            f'<p class="memory-date">{esc(date)}</p>'
            f"<h1>{esc(title)}</h1>"
            f"{md2html(body)}"
            f'<p><a href="../writing.html">← 回到文章列表</a></p>'
        )
        (ROOT / "posts" / slug).write_text(
            page(title, article_html, current="writing.html"), encoding="utf-8"
        )
        entries.append((date, title, summary, "posts/" + slug))

    # ---------- 文章列表（没有文章时也生成，避免导航死链） ----------
    if entries:
        items = "\n".join(
            f'<li><span class="item-date">{esc(d)}</span>'
            f'<a href="{href}">{esc(t)}</a>'
            + (f'<span class="item-note">{esc(s)}</span>' if s else "")
            + "</li>"
            for d, t, s, href in entries
        )
    else:
        items = '<li><span class="item-note">还没有文章。往 posts/ 里放一个 .md 文件，再跑一次脚本就会出现在这里。</span></li>'

    list_html = page(
        "文字",
        '<h1>文字</h1>\n<p class="subtitle">写过的东西，都收在这里</p>\n'
        f'<ul class="archive">\n{items}\n</ul>',
        current="writing.html",
    )
    (ROOT / "writing.html").write_text(list_html, encoding="utf-8")
    built.append("writing.html（由文章列表生成）")

    print("已生成：")
    for b in built:
        print("  -", b)
    print(f"  共 {len(entries)} 篇文章")


if __name__ == "__main__":
    main()
