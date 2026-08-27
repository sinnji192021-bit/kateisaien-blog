#!/usr/bin/env python3
"""images/ 配下のPNGをWebP(q90)に変換し、HTML/JSONの参照を .webp に張り替える。

使い方:
  python3 scripts/png2webp.py          # 変換＋張り替え
  python3 scripts/png2webp.py --check  # 現状の確認だけ

★PNGは削除しない（図解の原本は みずのさんノウハウ図書館/図解/ にあるが、
  ブログ側のPNGも残しておけば、あとで別品質に作り直せる）。
  ただしCloudflare Pagesにはどちらもデプロイされるので、
  容量が気になったら .gitignore で images/**/*.png を除外する手もある。
"""
import os, sys, glob, re, json
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

def convert(quality=90):
    before = after = n = 0
    for png in sorted(glob.glob('images/*/*.png')):
        webp = png[:-4] + '.webp'
        if os.path.exists(webp) and os.path.getmtime(webp) >= os.path.getmtime(png):
            before += os.path.getsize(png); after += os.path.getsize(webp); n += 1
            continue
        Image.open(png).save(webp, 'WEBP', quality=quality, method=6)
        before += os.path.getsize(png); after += os.path.getsize(webp); n += 1
    return n, before, after

def rewrite():
    """HTML の src と og:image、articles.json の thumb を .webp へ"""
    changed = 0
    for f in glob.glob('articles/*.html') + ['index.html']:
        if not os.path.exists(f): continue
        s = o = open(f).read()
        s = re.sub(r'(src="\.\./images/[^"]+)\.png"', r'\1.webp"', s)
        s = re.sub(r'(src="images/[^"]+)\.png"',      r'\1.webp"', s)
        s = re.sub(r'(og:image" content="[^"]+images/[^"]+)\.png"', r'\1.webp"', s)
        if s != o:
            open(f, 'w').write(s); changed += 1
    p = 'scripts/articles.json'
    d = json.load(open(p))
    arr = d['articles'] if isinstance(d, dict) and 'articles' in d else d
    for a in arr:
        if a.get('thumb', '').endswith('.png'):
            a['thumb'] = a['thumb'][:-4] + '.webp'
    json.dump(d, open(p, 'w'), ensure_ascii=False, indent=2)
    return changed

if __name__ == '__main__':
    if '--check' in sys.argv:
        png = glob.glob('images/*/*.png'); webp = glob.glob('images/*/*.webp')
        pb = sum(os.path.getsize(f) for f in png); wb = sum(os.path.getsize(f) for f in webp)
        print(f"PNG  {len(png):3}枚 {pb/1024/1024:6.1f}MB")
        print(f"WebP {len(webp):3}枚 {wb/1024/1024:6.1f}MB")
        miss = [f for f in png if not os.path.exists(f[:-4]+'.webp')]
        print("未変換:", miss if miss else "なし")
        sys.exit()
    n, b, a = convert()
    print(f"変換 {n}枚: {b/1024/1024:.1f}MB → {a/1024/1024:.1f}MB（1/{b/a:.1f}）")
    c = rewrite()
    print(f"参照を張り替え: HTML {c}件 ＋ articles.json")
