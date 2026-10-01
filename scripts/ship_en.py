#!/usr/bin/env python3
"""英語版の1弾（4本）をブログへ取り込む。
   python3 scripts/ship_en.py spec.tsv
   spec.tsv: slug <TAB> JAスラッグ <TAB> 図解名 <TAB> alt <TAB> h2 <TAB> 抜粋 <TAB> カテゴリ <TAB> 読了
   ★アイキャッチのコピー・記事の移動・カード追加・日本語版hreflangまで一気にやる。"""
import sys, io, os, re, shutil, subprocess
G = '/Users/sinnji19/CodexClaude/みずのさんノウハウ図書館/図解/_英語版'
HOLD = '/tmp/claude-501/en15hold'
B = 'https://kateisaien-note.com'
rows = [l.rstrip('\n').split('\t') for l in io.open(sys.argv[1], encoding='utf-8') if l.strip()]
for slug, ja, zu, alt, h2, ex, cat, rt in rows:
    src = f'{G}/{zu}_図0_en.png'
    assert os.path.exists(src), f'アイキャッチが無い: {src}'
    shutil.copy(src, f'images/en/{slug}.png')
    if os.path.exists(f'{HOLD}/{slug}.html'):
        shutil.move(f'{HOLD}/{slug}.html', f'en/articles/{slug}.html')
    assert os.path.exists(f'en/articles/{slug}.html'), f'記事が無い: {slug}'
subprocess.run(['python3', 'scripts/png2webp.py'], check=True, capture_output=True)
p = 'en/index.html'; s = io.open(p, encoding='utf-8').read()
blk = ''
for slug, ja, zu, alt, h2, ex, cat, rt in rows:
    blk += f'''    <div class="card"><a href="articles/{slug}">
      <div class="thumb"><img src="../images/en/{slug}.webp" alt="{alt}" loading="lazy"></div>
      <div class="body">
        <h2>{h2}</h2>
        <p class="ex">{ex}</p>
        <div class="meta"><time datetime="2026-10-01">October 1, 2026</time><span class="cat">{cat}</span><span class="rtime">{rt}</span></div>
      </div>
    </a></div>\n\n'''
m = re.search(r'(\s*)<div class="card"><a href="articles/', s)
s = s[:m.start()] + "\n" + blk + s[m.start():].lstrip('\n')
io.open(p, 'w', encoding='utf-8').write(s)
print('カード数:', s.count('<div class="card">'))
for slug, ja, zu, alt, h2, ex, cat, rt in rows:   # 日本語版に双方向hreflang
    jp = f'articles/{ja}.html'; t = io.open(jp, encoding='utf-8').read(); o = t
    if 'rel="alternate" hreflang="ja"' not in t:
        links = f'<link rel="alternate" hreflang="ja" href="{B}/articles/{ja}">\n<link rel="alternate" hreflang="en" href="{B}/en/articles/{slug}">\n'
        mm = re.search(r'<link rel="canonical"[^>]*>\n', t); t = t[:mm.end()] + links + t[mm.end():]
    if 'lang-hint.js' not in t:
        t = t.replace('</body>', '<script src="/assets/lang-hint.js" defer></script>\n</body>', 1)
    if '/en/" hreflang="en"' not in t:
        t = t.replace('<a href="/privacy">プライバシーポリシー</a>',
                      '<a href="/privacy">プライバシーポリシー</a>　<a href="/en/" hreflang="en" lang="en">English</a>', 1)
    io.open(jp, 'w', encoding='utf-8').write(t); print(f'  {ja}', '更新' if t != o else '変更なし')
subprocess.run(['python3', 'scripts/build.py'], check=True, capture_output=True)
print('sitemap再生成 完了')
