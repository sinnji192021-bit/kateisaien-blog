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

def div_blocks(text, opener):
    """text の中から opener で始まる <div> ブロックを、入れ子を数えて丸ごと抜き出す"""
    out, i = [], 0
    while True:
        k = text.find(opener, i)
        if k < 0:
            return out
        depth, j = 0, k
        while True:
            o, c = text.find("<div", j), text.find("</div>", j)
            if c < 0:
                return out
            if 0 <= o < c:
                depth += 1; j = o + 4
            else:
                depth -= 1; j = c + 6
                if depth == 0:
                    break
        out.append(text[k:j]); i = j

GREET = re.compile(r"<p>どうも、8150[^<]*</p>")

def trim_lead_and_desc(dst, src):
    """目次より前の「冒頭」を、あいさつ1行だけにする。説明文（description）も新しい要約に揃える。
    ★2026-10-13：本文だけ差し替えたら、目次の前に図書館版の書き出し・🗨️の吹き出し・旧図1・
      旧「基本データ」の見出しまで残っていた（公開済み55本すべて）。図書館との重複が残るうえ、
      新しい本文と食い違う断定もあったので、冒頭も差し替える。"""
    s = open(dst, encoding="utf-8").read()
    a = s.find("<article")
    toc = s.find('<div class="toc"', a)
    pm = s.find('<div class="postmeta"', a)
    img = s.find("<img", pm)
    if min(a, toc, pm, img) < 0 or not (pm < img < toc):
        return "冒頭の目印なし（そのまま）"
    ie = s.find(">", img) + 1
    lead = s[ie:toc]
    # ★2026-10-13：本文に「※」注記があると md2article が目次をそこへ置くため、
    #   目次より前の本文（この記事で分かること・本文の半分）まで削っていた（11月号・栽培日誌）。
    #   目次より前に見出しがあれば、冒頭ではないので削らない
    if "<h2" in lead:
        return "★目次より前に見出しがある（削らない）"
    g = GREET.search(lead)
    new_lead = "\n\n  " + g.group(0) + "\n\n  " if g else "\n\n  "
    s = s[:ie] + new_lead + s[toc:]
    summ = re.search(r"## ② 要約欄\n```\n(.*?)\n```", open(src, encoding="utf-8").read(), re.S)
    if summ:
        esc = lambda x: x.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
        raw = summ.group(1).strip()
        d, og = esc(raw[:120]), esc(raw[:100])          # md2article と同じ長さ
        s = re.sub(r'(<meta name="description" content=")[^"]*(")', lambda m: m.group(1) + d + m.group(2), s, count=1)
        s = re.sub(r'(<meta property="og:description" content=")[^"]*(")', lambda m: m.group(1) + og + m.group(2), s, count=1)
        dj = json.dumps(raw[:100], ensure_ascii=False)
    ttl = re.search(r"## ① タイトル欄\n```\n(.*?)\n```", open(src, encoding="utf-8").read(), re.S)
    if ttl:
        tt = ttl.group(1).strip()
        s = re.sub(r'(<meta property="og:title" content=")[^"]*(")',
                   lambda m: m.group(1) + tt.replace('"', "&quot;") + "｜えいこうの家庭菜園ノート" + m.group(2), s, count=1)
        s = re.sub(r'("@type":"BlogPosting","headline":)"(?:[^"\\]|\\.)*"',
                   lambda m: m.group(1) + json.dumps(tt, ensure_ascii=False), s, count=1)
    if summ:
        s = re.sub(r'("@type":"BlogPosting".*?"description":)"(?:[^"\\]|\\.)*"', lambda m: m.group(1) + dj, s, count=1, flags=re.S)
    open(dst, "w", encoding="utf-8").write(s)
    n = len(re.sub(r"<[^>]+>|\s", "", lead))
    return f"冒頭 {n}字 → {'あいさつ1行' if g else 'なし'}"

FIGDIR = "/Users/sinnji19/CodexClaude/みずのさんノウハウ図書館/図解"

def fix_figures(dst):
    """本文の図がブログ側に無ければ図解の原本から補い、ファイル名のままの alt を読める文にする。
    ★2026-10-13：2月号は図を作り直していたのに、ブログの images/ に入っておらず5枚とも出ていなかった。"""
    s = open(dst, encoding="utf-8").read()
    added = 0
    for d, name in set(re.findall(r'src="\.\./images/([^/"]+)/([^"/]+?)\.(?:png|webp)"', s)):
        png = os.path.join(ROOT, "images", d, name + ".png")
        if not os.path.exists(png) and not os.path.exists(png[:-4] + ".webp"):
            org = os.path.join(FIGDIR, name + ".png")
            if os.path.exists(org):
                shutil.copy2(org, png); added += 1
    s2 = re.sub(r'(<img src="\.\./images/[^"]+/([^"/]+?)\.(?:png|webp)" alt=")\2(")',
                lambda m: m.group(1) + re.sub(r"^.*?_図\d+_", "", m.group(2)) + m.group(3), s)
    if s2 != s:
        open(dst, "w", encoding="utf-8").write(s2)
    return added

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
    # ★2026-10-13：アフィリ枠が本文の途中に複数ある記事（01〜09）では、最初の枠で差し替えが止まり、
    #   その後ろに図書館版の旧本文（未承認の体験談を含む）が残っていた。
    #   → 本文の終わりは related / next のいちばん手前。間にあるアフィリ枠はすべて残して本文の後ろへまとめる
    ps = [seg.find(f'<div class="{c}"', st) for c in ("related", "next")]
    ps = [x for x in ps if x > 0]
    en = min(ps) if ps else -1
    if st <= 0 or en <= 0:
        sys.exit("■ 目次か related/next の目印が見つからない。手で確認すること")
    affs = div_blocks(seg[st:en], '<div class="aff">')
    open(dst, "w", encoding="utf-8").write(s[:a] + seg[:st] + body + "".join("\n  " + x + "\n" for x in affs) + "\n  " + seg[en:] + s[b:])
    # タイトルまわりも新しい原稿に合わせる
    title = cfg.get("_title") or re.search(r"## ① タイトル欄\n```\n(.*?)\n```",
                                           open(src, encoding="utf-8").read(), re.S).group(1).strip()
    s = open(dst, encoding="utf-8").read()
    s = re.sub(r"(<title>)[^<]*(</title>)", lambda m: m.group(1) + title + "｜えいこうの家庭菜園ノート" + m.group(2), s, count=1)
    s = re.sub(r'(<h1[^>]*>)[^<]*(</h1>)', lambda m: m.group(1) + title + m.group(2), s, count=1)
    open(dst, "w", encoding="utf-8").write(s)
    print("   " + trim_lead_and_desc(dst, src))
    k = fix_figures(dst)
    if k:
        print(f"   図を{k}枚補充")
    for s2 in ("add_img_size.py", "png2webp.py", "build.py"):
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", s2)], stdout=subprocess.DEVNULL)
    print(f"◎ 本文を差し替えました: {dst}")
    print(f"   退避: /tmp/{slug}.html.bak-swap")
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("使い方: 本文だけ差し替える.py <ブログ版.md> <slug>")
    sys.exit(main(sys.argv[1], sys.argv[2]))
