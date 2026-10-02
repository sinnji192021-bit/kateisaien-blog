#!/usr/bin/env python3
"""英語版の検索インデックス（en/search-index.json）を作る（2026-10-02）。

日本語版の build_search.py は scripts/articles.json を読むが、英語版は
記事HTMLそのものが正なので、en/articles/*.html から直に拾う。

拾うもの: h1 / meta description / h2見出し / <strong>の強調 / 図解の対訳箱
検索は部分一致（英語なので小文字にそろえるだけでよい）。

使い方: python3 scripts/build_search_en.py
"""
import glob, html, io, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def text(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def pick(s, pat, default=""):
    m = re.search(pat, s, re.S)
    return html.unescape(m.group(1)).strip() if m else default


rows = []
for f in sorted(glob.glob("en/articles/*.html")):
    slug = os.path.basename(f)[:-5]
    s = io.open(f, encoding="utf-8").read()
    h1 = text(pick(s, r"<h1>(.*?)</h1>"))
    desc = pick(s, r'<meta name="description" content="([^"]*)"')
    img = pick(s, r'<meta property="og:image" content="([^"]*)"')
    img = img.replace("https://kateisaien-note.com/", "../")  # /en/ から見た相対
    # ★検索結果の行は96×64pxで出るので、小さいサムネを使う（2026-10-02）
    if img.startswith("../images/") and os.path.exists("images/thumb/" + img[len("../images/"):]):
        img = "../images/thumb/" + img[len("../images/"):]

    body = s.split("<article", 1)[-1]
    heads = " ".join(text(h) for h in re.findall(r"<h2[^>]*>(.*?)</h2>", body, re.S))
    strong = " ".join(text(h) for h in re.findall(r"<strong>(.*?)</strong>", body, re.S))
    # 図解の対訳箱（.figkey）は野菜名・作業名のかたまりなので検索に効く
    figkey = " ".join(text(h) for h in re.findall(
        r'<div class="figkey".*?>(.*?)</div>', body, re.S))

    # ★本文も検索に入れたいが、全文を持たせるとファイルが大きくなる。
    #   英語は単語で切れるので「出てくる単語を1回ずつ」にすると、
    #   取りこぼさないまま大きさが1/4になる（slugs/slugのような語尾違いも部分一致で当たる）
    full = " ".join([h1, desc, text(body)]).lower()
    words = sorted(set(re.findall(r"[a-z][a-z0-9'-]{1,}", full)))

    rows.append({
        "u": f"articles/{slug}",
        "t": h1,
        "d": desc if len(desc) <= 140 else desc[:138].rsplit(" ", 1)[0] + "…",
        "i": img,
        # ★全文を入れるとファイルが大きくなり読み込みが遅い。見出し＋強調＋図解の箱で十分当たる
        "s": " ".join(words),
    })

io.open("en/search-index.json", "w", encoding="utf-8").write(
    json.dumps(rows, ensure_ascii=False, separators=(",", ":")))
size = os.path.getsize("en/search-index.json") / 1024
print(f"en/search-index.json  {len(rows)}本  {size:.0f}KB")
