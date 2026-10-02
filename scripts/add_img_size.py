#!/usr/bin/env python3
"""画像タグに width / height を入れる（2026-10-02）。

★なぜ必要か
  サイト内の画像1522枚すべてに縦横の指定が無く、読み込みが終わるまで
  ブラウザが場所を確保できない。そのため画像が入った瞬間に本文が下へずれる。
  （Googleが測っている CLS＝レイアウトのずれ が悪化し、読者も読みかけの行を見失う）

  style.css に img{max-width:100%;height:auto} があるので、
  width/height を書いても見た目の大きさは変わらない。
  ブラウザは縦横比だけを先に受け取って、場所を取っておいてくれる。

★楽天など外部の画像は触らない（サイズが分からないうえ、向こうのHTMLなので）。

使い方: python3 scripts/add_img_size.py
"""
import glob, io, os, re, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

_size = {}


def size_of(path):
    if path not in _size:
        try:
            with Image.open(path) as im:
                _size[path] = im.size
        except Exception:
            _size[path] = None
    return _size[path]


def fix(page):
    base = os.path.dirname(page) or "."
    s = io.open(page, encoding="utf-8").read()
    n = [0]

    def rep(m):
        tag = m.group(0)
        if "width=" in tag and "height=" in tag:
            return tag
        src = re.search(r'src="([^"]+)"', tag)
        if not src:
            return tag
        p = src.group(1)
        if p.startswith(("http", "data:")):      # 楽天など外部はそのまま
            return tag
        f = os.path.normpath(os.path.join(base, p))
        wh = size_of(f)
        if not wh:
            return tag
        n[0] += 1
        return tag[:-1].rstrip() + f' width="{wh[0]}" height="{wh[1]}">'

    s2 = re.sub(r"<img[^>]*>", rep, s)
    if n[0]:
        io.open(page, "w", encoding="utf-8").write(s2)
    return n[0]


def main():
    pages = (["index.html", "privacy.html", "404.html", "en/index.html", "en/privacy.html"]
             + sorted(glob.glob("articles/*.html")) + sorted(glob.glob("en/articles/*.html")))
    total = files = 0
    for p in pages:
        if not os.path.exists(p):
            continue
        k = fix(p)
        if k:
            total += k; files += 1
    print(f"画像に縦横サイズを入れた: {total}枚 / {files}ページ")


if __name__ == "__main__":
    main()
