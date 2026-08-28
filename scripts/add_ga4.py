#!/usr/bin/env python3
"""GA4のタグを全HTMLの <head> 直後に入れる（重複挿入しない）。

使い方:
  python3 scripts/add_ga4.py            # 挿入
  python3 scripts/add_ga4.py --check    # 状態確認だけ
"""
import os, sys, glob, re

GA_ID = "G-69D04PPM8P"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

TAG = f"""<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_ID}');
</script>
"""

def targets():
    return sorted(glob.glob('articles/*.html')) + (['index.html'] if os.path.exists('index.html') else [])

def check():
    has = miss = 0
    for f in targets():
        s = open(f).read()
        if GA_ID in s: has += 1
        else: miss += 1; print("  未挿入:", f)
    print(f"GA4タグ入り {has}件 ／ 未挿入 {miss}件")

def install():
    n = skip = 0
    for f in targets():
        s = open(f).read()
        if GA_ID in s:
            skip += 1; continue
        m = re.search(r'<head>\s*\n', s)
        if not m:
            print("★<head>が見つからない:", f); continue
        s = s[:m.end()] + TAG + s[m.end():]
        open(f, 'w').write(s); n += 1
    print(f"挿入 {n}件 ／ すでに入っていた {skip}件")

if __name__ == '__main__':
    if '--check' in sys.argv: check()
    else: install(); check()
