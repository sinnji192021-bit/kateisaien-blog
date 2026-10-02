#!/usr/bin/env python3
"""カード・関連記事・検索結果に出す小さいサムネを作る（2026-10-02）。

★なぜ必要か
  一覧のカードも、記事末の「あわせて読みたい」も、検索結果の行も、
  表示されるのは幅220〜365pxなのに、**幅1280pxのアイキャッチをそのまま**
  読み込んでいた（1枚200KB前後）。
  TOPを最後までスクロールすると104枚＝約21MB、記事1本でも関連3枚で約750KB。
  → 幅640pxのサムネ（約50KB）を別に作って、そちらを読ませる。

  記事本文の先頭にある大きなアイキャッチ（.fthumb／記事の1枚目）は
  いちばん目立つ画像なので、画質を落とさないよう **元のまま** にしてある。

使い方: python3 scripts/make_thumbs.py [--check]
出力先: images/thumb/<元と同じ相対パス>
"""
import glob, os, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
W = 640
OUT = "images/thumb"


def targets():
    """カード等に出る画像＝各記事のアイキャッチ（日本語は 図0、英語は images/en/）"""
    fs = [f for f in glob.glob("images/*/*.webp") if "図0" in os.path.basename(f)]
    fs += glob.glob("images/en/*.webp")
    return sorted(set(fs))


def main(check=False):
    made = skipped = 0
    before = after = 0
    for src in targets():
        dst = os.path.join(OUT, os.path.relpath(src, "images"))
        before += os.path.getsize(src)
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            after += os.path.getsize(dst); skipped += 1; continue
        if check:
            made += 1; continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        im = Image.open(src).convert("RGB")
        if im.width > W:
            im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
        im.save(dst, "WEBP", quality=82, method=6)
        after += os.path.getsize(dst); made += 1
    print(f"サムネ {made}枚作成 / {skipped}枚はそのまま")
    if after:
        print(f"元 {before/1024/1024:.0f}MB → サムネ {after/1024/1024:.0f}MB "
              f"（1枚あたり平均 {after/max(1,made+skipped)/1024:.0f}KB）")


if __name__ == "__main__":
    main("--check" in sys.argv)
