#!/usr/bin/env python3
"""英語版記事の7点検証。引数のslugだけ、無指定なら全部。"""
import sys,io,os,re,glob
slugs=sys.argv[1:] or [os.path.basename(f)[:-5] for f in sorted(glob.glob('en/articles/*.html'))]
bad=0
for sl in slugs:
    p=f'en/articles/{sl}.html'
    s=io.open(p,encoding='utf-8').read(); e=[]
    if 'G-69D04PPM8P' not in s: e.append('GA4無し')
    if f'canonical" href="https://kateisaien-note.com/en/articles/{sl}"' not in s: e.append('canonical不一致')
    m=re.search(r'hreflang="ja" href="https://kateisaien-note.com/articles/([^"]+)"',s)
    if not m: e.append('ja hreflang無し')
    else:
        j=f'articles/{m.group(1)}.html'
        if not os.path.exists(j): e.append(f'JA不在 {j}')
        elif f'/en/articles/{sl}"' not in io.open(j,encoding='utf-8').read(): e.append('逆hreflang無し')
    if 'lang-hint.js' not in s: e.append('lang-hint無し')
    for im in re.findall(r'src="(\.\./\.\./images/[^"]+)"',s):
        if not os.path.exists(os.path.normpath(os.path.join('en/articles',im))): e.append(f'画像欠 {im}')
    body=re.sub(r'<div class="figkey">.*?</div>','',re.sub(r'<head>.*?</head>','',s,flags=re.S),flags=re.S)
    jp=[x for x in re.findall(r'[ぁ-んァ-ヶ一-龥]+',re.sub(r'<[^>]+>','',body)) if x!='日本語']
    if jp: e.append(f'本文に日本語 {jp[:3]}')
    if s.count('figkey"')==0: e.append('対訳箱なし')
    print(('  ✓ ' if not e else '  ✗ ')+f'{sl:34}'+('  '+' / '.join(e) if e else ''))
    bad+= bool(e)
print(f'\nNG {bad} / {len(slugs)} 本')
