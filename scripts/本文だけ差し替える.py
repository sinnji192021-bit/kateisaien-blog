#!/usr/bin/env python3
"""既存記事の「本文」だけを、ブログ版の原稿で差し替える（2026-10-12）。

★なぜ全体を作り直さないのか
  記事HTMLは `md2article.py` のあと、次の注入を順に受けて完成している：
    add_aff（楽天HTML）／add_adsense／add_ga4／add_img_size／png2webp／build（目次・あわせて読みたい）
    ＋ ship_en（hreflang・lang-hint・search.js）
  白菜で全体を作り直したら、**楽天リンク3本・AdSense・GA4・hreflangが全部消えた**。
  → 既存記事は**本文だけ**入れ替え、周りの作り込みはそのまま残す。

★差し替える範囲
  <article> の中の「目次の直後」〜「アフィリ枠の直前」。
  目次・アフィリ枠・あわせて読みたい・次に読む は触らない（目次は build.py が作り直す）。

使い方:
  python3 scripts/本文だけ差し替える.py <ブログ版.md> <slug>
"""
import os, re, shutil, subprocess, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def new_body(src, slug):
    """md2article で一度HTMLを作り、その本文だけを取り出す"""
    cfgp = "/tmp/_swap_cfg.json"
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from importlib import import_module
    conv = import_module("ブログ版を公開用に変換")
    cfg = conv.build_cfg(src, slug)
    cfg["slug"] = "_swaptmp"
    json.dump(cfg, open(cfgp, "w"), ensure_ascii=False)
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "md2article.py"), cfgp],
                   stdout=subprocess.DEVNULL, check=True)
    tmp = os.path.join(ROOT, "articles", "_swaptmp.html")
    s = open(tmp, encoding="utf-8").read()
    os.remove(tmp)
    seg = s[s.find("<article"):s.find("</article>")]
    start = seg.find("</div>", seg.find('<div class="toc"')) + len("</div>")
    return seg[start:body_end(seg)], cfg


def body_end(seg):
    """本文の終わり＝aff / related / next のうち、いちばん手前に出るもの。
    ★2026-10-12：aff が無い記事では next が本文に紛れ込み、「次に読む」が二重になった。"""
    ps = [seg.find(f'<div class="{c}"') for c in ("aff", "related", "next")]
    ps = [p for p in ps if p > 0]
    return min(ps) if ps else len(seg)

def main(src, slug):
    dst = os.path.join(ROOT, "articles", slug + ".html")
    if not os.path.exists(dst):
        sys.exit(f"■ {dst} が無い。新規記事は『ブログ版を公開用に変換.py』を使う")
    shutil.copy2(dst, f"/tmp/{slug}.html.bak-swap")
    body, cfg = new_body(src, slug)
    s = open(dst, encoding="utf-8").read()
    a, b = s.find("<article"), s.find("</article>")
    seg = s[a:b]
    st = seg.find("</div>", seg.find('<div class="toc"')) + len("</div>")
    en = body_end(seg)
    if st <= 0 or en <= 0:
        sys.exit("■ 目次かアフィリ枠の目印が見つからない。手で確認すること")
    open(dst, "w", encoding="utf-8").write(s[:a] + seg[:st] + body + seg[en:] + s[b:])
    # タイトルまわりも新しい原稿に合わせる
    title = cfg.get("_title") or re.search(r"## ① タイトル欄\n```\n(.*?)\n```",
                                           open(src, encoding="utf-8").read(), re.S).group(1).strip()
    s = open(dst, encoding="utf-8").read()
    s = re.sub(r"(<title>)[^<]*(</title>)", lambda m: m.group(1) + title + "｜えいこうの家庭菜園ノート" + m.group(2), s, count=1)
    s = re.sub(r'(<h1[^>]*>)[^<]*(</h1>)', lambda m: m.group(1) + title + m.group(2), s, count=1)
    open(dst, "w", encoding="utf-8").write(s)
    for s2 in ("add_img_size.py", "png2webp.py", "build.py"):
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", s2)], stdout=subprocess.DEVNULL)
    print(f"◎ 本文を差し替えました: {dst}")
    print(f"   退避: /tmp/{slug}.html.bak-swap")
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("使い方: 本文だけ差し替える.py <ブログ版.md> <slug>")
    sys.exit(main(sys.argv[1], sys.argv[2]))
