#!/usr/bin/env python3
"""公開済みのブログ版記事の「冒頭」と説明文と図を、まとめて整える（2026-10-13）。

★なぜ要るか
  `本文だけ差し替える.py` は目次より後しか入れ替えていなかったので、
  目次の前に図書館版の書き出し・🗨️の吹き出し・旧図1・旧見出しが残っていた。
  → 冒頭をあいさつ1行にし、meta description を新しい要約にし、足りない図を補う。
  今後の公開は `本文だけ差し替える.py` の中で同じ処理が走る。

使い方:
  python3 scripts/冒頭をまとめて整える.py            # 公開済み全部
  python3 scripts/冒頭をまとめて整える.py 34-2gatsu  # 指定したslugだけ
"""
import glob, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = "/Users/sinnji19/CodexClaude/みずのさんノウハウ図書館"
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from importlib import import_module
swap = import_module("本文だけ差し替える")

KEYS = {"楽天": "a.rakuten", "AdSense": "adsbygoogle", "GA4": "G-69D04PPM8P", "hreflang": "hreflang"}

def targets():
    arts = json.load(open(os.path.join(ROOT, "scripts", "articles.json")))
    lst = arts["articles"] if isinstance(arts, dict) and "articles" in arts else arts
    t2s = {os.path.basename(x["thumb"]).replace(".webp", ""): x["slug"] for x in lst if x.get("thumb")}
    out = []
    for n in [l.split()[0] for l in open(f"{LIB}/tmp/ブログ版_公開済み.txt") if l.strip()]:
        fs = glob.glob(f"{LIB}/記事原稿/{n}_*_ブログ版.md")
        if not fs:
            continue
        m = re.search(r"## ④ アイキャッチ画像\s*\n`図解/([^`]+)\.png`", open(fs[0], encoding="utf-8").read())
        slug = t2s.get(m.group(1) if m else "")
        if slug:
            out.append((slug, fs[0]))
    return out

def counts(path):
    s = open(path, encoding="utf-8").read()
    return {k: s.count(v) for k, v in KEYS.items()}

def main(only):
    tg = [t for t in targets() if not only or t[0] in only]
    before = {}
    for slug, src in tg:
        dst = os.path.join(ROOT, "articles", slug + ".html")
        before[slug] = counts(dst)
        msg = swap.trim_lead_and_desc(dst, src)
        k = swap.fix_figures(dst)
        print(f"  {slug:22} {msg}" + (f"／図を{k}枚補充" if k else ""))
    for s2 in ("png2webp.py", "add_img_size.py", "build.py"):
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", s2)], stdout=subprocess.DEVNULL)
    bad = 0
    for slug, _ in tg:
        after = counts(os.path.join(ROOT, "articles", slug + ".html"))
        if after != before[slug]:
            bad += 1
            print(f"  ★{slug} 周りの数が変わった {before[slug]} → {after}")
    print(f"■ {len(tg)}本を整えた／周りが変わった {bad}本")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(set(sys.argv[1:])))
