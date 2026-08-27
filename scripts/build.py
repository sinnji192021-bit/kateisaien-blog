#!/usr/bin/env python3
"""ブログの自動組み立て。

`scripts/articles.json` に記事を1件足して、このスクリプトを走らせるだけで
次のすべてが更新される：

  1. TOPの注目記事（featured）
  2. TOPの目的別チップ
  3. TOPのセクション別カード一覧（新しい記事ほど上）
  4. 各記事の「日付・カテゴリ・読了時間」行
  5. 各記事の目次（h2から自動生成・id付与も自動）
  6. 各記事の「あわせて読みたい」3本（同じカテゴリ優先→新着で補充）
  7. sitemap.xml

使い方:
    cd ~/Documents/kateisaien-blog && python3 scripts/build.py

差し込み位置はHTMLコメントの目印で管理しているので、
目印の外を手で書き換えても消えない。
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
import datetime as _dt

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "scripts" / "articles.json").read_text(encoding="utf-8"))
ARTS = DATA["articles"]  # check() で実在するものだけに絞る
BASE = DATA["site"]["base"]

JP = "{}年{}月{}日"


def jp_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return JP.format(int(y), int(m), int(d))


def read_minutes(slug: str) -> int:
    """本文の文字数から読了時間を実測する（1分=550字）。"""
    body = (ROOT / "articles" / f"{slug}.html").read_text(encoding="utf-8").split("<article", 1)[1]
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    return max(3, round(len(re.sub(r"<[^>]+>", "", body)) / 550))


def check() -> list[dict]:
    """記事HTMLとサムネが実在するものだけを対象にする。
    足りないものは止めずに警告して飛ばす（書きかけでもTOPが壊れないように）。"""
    ok, skipped = [], []
    for a in ARTS:
        miss = []
        if not (ROOT / "articles" / f"{a['slug']}.html").exists():
            miss.append(f"articles/{a['slug']}.html")
        if not (ROOT / a["thumb"]).exists():
            miss.append(a["thumb"])
        (skipped if miss else ok).append((a, miss))
    for a, miss in skipped:
        if miss:
            print(f'  ⚠️  {a["slug"]:18} まだ無いので飛ばしました → {" / ".join(miss)}')
    return [a for a, miss in ok]


def block(text: str, name: str, content: str) -> str:
    """<!-- BUILD:name --> 〜 <!-- /BUILD:name --> の中身を差し替える。
    目印が無ければ何もしない（手書き部分を壊さないため）。"""
    pat = re.compile(rf"(<!-- BUILD:{name} -->).*?(<!-- /BUILD:{name} -->)", re.S)
    if not pat.search(text):
        return text
    return pat.sub(lambda m: m.group(1) + "\n" + content + "\n  " + m.group(2), text)


def newest_first(items):
    return sorted(items, key=lambda a: (a["date"], a["slug"]), reverse=True)


# ---------------------------------------------------------------- TOP
def build_index() -> None:
    p = ROOT / "index.html"
    h = p.read_text(encoding="utf-8")
    mins = {a["slug"]: read_minutes(a["slug"]) for a in ARTS}
    newest = newest_first(ARTS)[0]["slug"]

    feat = next((a for a in ARTS if a.get("featured")), newest_first(ARTS)[0])
    fm = mins[feat["slug"]]
    featured = f'''  <a class="featured" href="articles/{feat["slug"]}.html">
    <div class="fthumb"><img src="{feat["thumb"]}" alt="{html.escape(feat["short"])}"></div>
    <div class="fbody">
      <span class="fbadge">🌞 今月の必読</span>
      <h2>{html.escape(feat["card"])}</h2>
      <p>{html.escape(feat["desc"])}</p>
      <div class="meta"><time datetime="{feat["date"]}">{jp_date(feat["date"])}</time><span class="cat{" g" if feat.get("catcolor")=="g" else ""}">{feat["cat"]}</span><span class="rtime">読了目安 約{fm}分</span></div>
      <span class="more">続きを読む →</span>
    </div>
  </a>'''
    h = block(h, "FEATURED", featured)

    chips = '  <nav class="chips" id="list">\n' + "".join(
        f'    <a href="{c["href"]}">{c["label"]}</a>\n' for c in DATA["chips"]
    ) + "  </nav>"
    h = block(h, "CHIPS", chips)

    out = []
    for sec in DATA["sections"]:
        rows = [a for a in ARTS if a.get("section") == sec["id"] and not a.get("featured")]
        if not rows:
            continue
        rows = newest_first(rows) if not sec.get("numbered") else sorted(rows, key=lambda a: a["slug"])
        out.append(f'  <div class="sec" id="{sec["id"]}"><h2>{sec["title"]}</h2><span class="en">{sec["en"]}</span></div>')
        out.append('  <div class="cards">')
        for i, a in enumerate(rows, 1):
            step = f'<span class="step">{i}</span>' if sec.get("numbered") else ""
            new = '<span class="new">NEW</span>' if a["slug"] == newest else ""
            cat = f'<span class="cat{" g" if a.get("catcolor")=="g" else ""}">{a["cat"]}</span>'
            out.append(f'''
    <div class="card"><a href="articles/{a["slug"]}.html">
      <div class="thumb"><img src="{a["thumb"]}" alt="{html.escape(a["short"])}" loading="lazy"></div>
      <div class="body">
        <h2>{step}{html.escape(a["card"])}</h2>
        <p class="ex">{html.escape(a["desc"])}</p>
        <div class="meta"><time datetime="{a["date"]}">{jp_date(a["date"])}</time>{cat}<span class="rtime">約{mins[a["slug"]]}分</span>{new}</div>
      </div>
    </a></div>''')
        out.append("\n  </div>\n")
    h = block(h, "CARDS", "\n".join(out))
    p.write_text(h, encoding="utf-8")
    print(f"index.html   注目記事={feat['slug']} / カード{len([a for a in ARTS if not a.get('featured')])}枚")


# ------------------------------------------------------------ 各記事
def pick_related(me: dict, n: int = 3) -> list[dict]:
    """同じカテゴリを優先し、足りない分は新着で埋める。"""
    if me.get("related"):
        by = {a["slug"]: a for a in ARTS}
        return [by[s] for s in me["related"] if s in by][:n]
    same = [a for a in newest_first(ARTS) if a["cat"] == me["cat"] and a["slug"] != me["slug"]]
    rest = [a for a in newest_first(ARTS) if a["slug"] != me["slug"] and a not in same]
    return (same + rest)[:n]


def build_articles() -> None:
    for a in ARTS:
        p = ROOT / "articles" / f"{a['slug']}.html"
        h = p.read_text(encoding="utf-8")
        m = read_minutes(a["slug"])

        cat = f'<span class="cat{" g" if a.get("catcolor")=="g" else ""}">{a["cat"]}</span>'
        meta = f'  <div class="postmeta"><time datetime="{a["date"]}">{jp_date(a["date"])}</time>{cat}<span class="rtime">読了目安 約{m}分</span></div>'
        if 'class="postmeta"' in h:
            h = re.sub(r'  <div class="postmeta">.*?</div>', meta, h, count=1, flags=re.S)
        else:
            h = re.sub(r"(<h1>.*?</h1>)", lambda mo: mo.group(1) + "\n" + meta, h, count=1, flags=re.S)

        # 見出しにidを振り直して目次を作る
        n = [0]
        def addid(mo):
            n[0] += 1
            return f'<h2 id="s{n[0]}">{mo.group(1)}</h2>'
        h = re.sub(r'<h2(?: id="s\d+")?>(.*?)</h2>', addid, h)
        heads = re.findall(r'<h2 id="s\d+">(.*?)</h2>', h)
        items = "".join(
            f'<li><a href="#s{i+1}">{re.sub(r"<[^>]+>", "", t)}</a></li>' for i, t in enumerate(heads)
        )
        toc = f'  <div class="toc">\n    <p class="t">📖 この記事の目次</p>\n    <ol>{items}</ol>\n  </div>'
        if 'class="toc"' in h:
            h = re.sub(r'  <div class="toc">.*?\n  </div>', toc, h, count=1, flags=re.S)
        elif heads:
            h = re.sub(r'(<h2 id="s1">)', toc + "\n\n  " + r"\1", h, count=1)

        cards = "".join(
            f'\n      <a href="{r["slug"]}.html"><div class="thumb"><img src="../{r["thumb"]}" '
            f'alt="{html.escape(r["short"])}" loading="lazy"></div><h4>{html.escape(r["short"])}</h4></a>'
            for r in pick_related(a)
        )
        rel = f'  <div class="related">\n    <p class="t">あわせて読みたい</p>\n    <div class="relgrid">{cards}\n    </div>\n  </div>'
        if 'class="related"' in h:
            h = re.sub(r'  <div class="related">.*?\n  </div>', rel, h, count=1, flags=re.S)
        else:
            h = h.replace('<div class="next">', rel + "\n\n  " + '<div class="next">', 1)

        p.write_text(h, encoding="utf-8")
        print(f'  {a["slug"]:18} 目次{len(heads)}項目 約{m}分 関連{len(pick_related(a))}本')


# ---------------------------------------------------------- sitemap
def _lastmod(a) -> str:
    """sitemap の lastmod を返す。

    ★articles.json の date は「ノウハウ図書館での公開予定日」で、未来日が入る。
      ブログ側の記事はすでに公開済みなので、未来日を lastmod に出してはいけない
      （Googleは未来の lastmod を無効とみなし、サイトマップの信頼度が下がる）。
      そこで「HTMLファイルの実際の更新日」を使い、それも無ければ今日で頭打ちにする。
    """
    today = _dt.date.today()
    f = ROOT / "articles" / f"{a['slug']}.html"
    if f.exists():
        d = _dt.date.fromtimestamp(f.stat().st_mtime)
    else:
        try:
            d = _dt.date.fromisoformat(a["date"])
        except Exception:
            d = today
    return min(d, today).isoformat()


def build_sitemap() -> None:
    today = _dt.date.today().isoformat()
    urls = [f"  <url>\n    <loc>{BASE}/</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>1.0</priority>\n  </url>"]
    for a in sorted(ARTS, key=lambda x: x["slug"]):
        urls.append(
            f"  <url>\n    <loc>{BASE}/articles/{a['slug']}.html</loc>\n"
            f"    <lastmod>{_lastmod(a)}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>"
        )
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n"
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")
    print(f"sitemap.xml  {len(ARTS)+1}件")


def main() -> None:
    global ARTS
    print("記事チェック")
    ARTS = check()
    if not ARTS:
        raise SystemExit("公開できる記事がありません")
    build_index()
    print("articles/")
    build_articles()
    build_sitemap()
    print("\n✅ 完了。ブラウザで確認して、よければ PUSH してください。")


if __name__ == "__main__":
    main()
