#!/usr/bin/env python3
"""図書館投稿用.md → ブログ記事HTML 変換器

使い方:
  python3 scripts/md2article.py <設定JSON>

設定JSONの形:
{
  "src":   "/path/to/NN_◯◯_図書館投稿用.md",
  "slug":  "19-fuyu-shigoto",
  "imgdir":"19",
  "date":  "2026-10-10",
  "cat":   "育てて学ぶ",       # index側の表示カテゴリ
  "rtime": "約13分",
  "desc":  "meta description",
  "og":    "og:description",
  "next":  ["20-11gatsu.html", "【11月にまく・植える野菜】…"],
  "aff":   ["①防虫ネット", "②不織布"],       # アフィリ枠に書くコメント行
  "prevlink": ["17-ninniku.html", "にんにく"],  # 導入に差す「前回」リンク（任意）
  "img_alt": {"冬の畑仕事_図1_寒起こし": "…"},
  "bold":  ["太字にする一文", ...],
  "key":   ["部分強調する語句", ...],
  "links": {"元の文字列": "<a href=...>置換後</a>"}   # 任意の後処理
}
タイトルは .md の ① タイトル欄から自動で取る。
"""
import sys, os, re, json, html, unicodedata
from urllib.parse import quote

def build(cfg):
    t = open(cfg['src']).read()
    title = t.split('## ① タイトル欄')[1].split('```')[1].strip()
    body_md = t.split('（↓本文ここから）')[1].split('（↑本文ここまで）')[0].strip()
    thumb = t.split('## ④ アイキャッチ画像')[1].split('`')[1].split('/')[-1].replace('.png','')

    IMG   = cfg.get('img_alt', {})
    BOLD  = cfg.get('bold', [])
    KEY   = cfg.get('key', [])
    lines = [l.rstrip() for l in body_md.split('\n')]
    out, buf, toc, sec, i = [], [], [], 0, 0

    def flush():
        nonlocal buf
        if buf:
            out.append('  <ul>' + ''.join(f'<li>{x}</li>' for x in buf) + '</ul>')
            buf = []

    def deco(s):
        s = html.escape(s)
        for b in BOLD:
            eb = html.escape(b)
            if eb in s:
                s = s.replace(eb, f'<strong>{eb}</strong>')
        for k in KEY:
            ek = html.escape(k)
            if ek in s and '<strong>' not in s:
                s = s.replace(ek, f'<strong>{ek}</strong>', 1)
        return s

    while i < len(lines):
        l = lines[i].strip()
        if not l:
            i += 1; continue
        if l.startswith('🗨️'):
            q = []
            while i < len(lines) and lines[i].strip().startswith('🗨️'):
                q.append(f'<p>{html.escape(lines[i].strip())}</p>'); i += 1
            out.append('  <div class="quote">\n    ' + '\n    '.join(q) + '\n  </div>'); continue
        if l.startswith('〈大見出し〉'):
            flush(); sec += 1; ti = l.replace('〈大見出し〉', '')
            toc.append((f's{sec}', ti))
            out.append(f'\n  <h2 id="s{sec}">{html.escape(ti)}</h2>'); i += 1; continue
        if l.startswith('〈小見出し〉'):
            flush(); out.append(f'  <h3>{html.escape(l.replace("〈小見出し〉", ""))}</h3>'); i += 1; continue
        if l.startswith('〔画像：'):
            flush(); f = l.replace('〔画像：', '').replace('〕', '')
            out.append(f'  <img src="../images/{cfg["imgdir"]}/{f}.png" alt="{IMG.get(f, f)}">'); i += 1; continue
        if l.startswith('・'):
            buf.append(deco(l[1:])); i += 1; continue
        if l.startswith('✅'):
            cb = []
            while i < len(lines):
                s = lines[i].strip()
                if s.startswith('✅'):
                    cb.append(deco(s[1:].strip())); i += 1
                elif not s:
                    i += 1
                else:
                    break
            out.append('  <ul class="check">' + ''.join(f'<li>{x}</li>' for x in cb) + '</ul>'); continue
        if l.startswith('※'):
            flush()
            out.append(f'  <p style="background:#FFF8E1;border-left:4px solid #F0A500;'
                       f'padding:.8em 1em;border-radius:6px;">{html.escape(l)}</p>'); i += 1; continue
        # 番号付き手順（"1. " で始まる連続行）
        if re.match(r'^\d+\. ', l):
            flush(); ol = []
            while i < len(lines):
                s = lines[i].strip()
                if re.match(r'^\d+\. ', s):
                    ol.append(deco(re.sub(r'^\d+\. ', '', s))); i += 1
                elif not s:
                    i += 1
                else:
                    break
            out.append('  <ol>' + ''.join(f'<li>{x}</li>' for x in ol) + '</ol>'); continue
        flush()
        out.append(f'  <p>{deco(l)}</p>'); i += 1
    flush()

    body = '\n'.join(out)
    for old, new in cfg.get('links', {}).items():
        body = body.replace(html.escape(old), new) if html.escape(old) in body else body.replace(old, new)
    if cfg.get('prevlink'):
        h, label = cfg['prevlink']
        body = body.replace('定期便、', f'定期便、', 1)

    toc_html = ('\n\n  <div class="toc">\n    <p class="t">📖 この記事の目次</p>\n    <ol>'
                + ''.join(f'<li><a href="#{a}">{html.escape(b)}</a></li>' for a, b in toc)
                + '</ol>\n  </div>')
    # 目次は「※…」注記の直後、無ければ最初の <h2> の直前に入れる
    m = re.search(r'border-radius:6px;">※[^<]*</p>', body)
    if m:
        body = body[:m.end()] + toc_html + body[m.end():]
    else:
        k = body.find('\n  <h2 ')
        body = body[:k] + toc_html + body[k:]

    aff = ''
    if cfg.get('aff'):
        aff = ('\n  <!-- ▼▼▼ アフィリエイト枠（ユーザーが楽天HTMLを貼る）▼▼▼\n       '
               + '  '.join(cfg['aff'])
               + '\n       貼るときは必ず <div class="rk">…</div> でくるむこと（div開閉数が合わなくなるため）\n  ▲▲▲ -->\n')

    imgurl = ('https://kateisaien-note.com/images/'
              + cfg['imgdir'] + '/' + quote(thumb + '.png'))
    nx_href, nx_label = cfg['next']
    ymd = cfg['date']; y, mo, d = ymd.split('-')
    catcls = cfg.get('catcls', '')
    page = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}｜えいこうの家庭菜園ノート</title>
<meta name="description" content="{cfg['desc']}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://kateisaien-note.com/articles/{cfg['slug']}.html">
<meta name="theme-color" content="#5FA049">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}｜えいこうの家庭菜園ノート">
<meta property="og:description" content="{cfg['og']}">
<meta property="og:url" content="https://kateisaien-note.com/articles/{cfg['slug']}.html">
<meta property="og:image" content="{imgurl}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="../assets/style.css">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"BlogPosting","headline":{json.dumps(re.sub(r'[【】「」🌱🍓🍂❄️🧄🧅🥬🥕]', '', title), ensure_ascii=False)},"description":{json.dumps(cfg['og'], ensure_ascii=False)},"datePublished":"{ymd}","author":{{"@type":"Person","name":"えいこう（8150）"}},"publisher":{{"@type":"Organization","name":"えいこうの家庭菜園ノート"}},"mainEntityOfPage":"https://kateisaien-note.com/articles/{cfg['slug']}.html"}}
</script>
</head>
<body>
<div class="prbar">当サイトはアフィリエイト広告（Amazon・楽天等）を利用しています</div>
<header class="site"><div class="inner">
  <a class="logo" href="../index.html">🌱 えいこうの家庭菜園ノート</a>
  <nav class="gnav">
    <a href="../index.html">TOP</a>
    <a href="01-hajimekata.html">はじめての方へ</a>
    <a href="07-mushi.html">虫対策</a>
    <a href="../index.html#list">記事一覧</a>
  </nav>
  <a class="cta" href="{cfg.get('monthly','18-10gatsu.html')}">🌱 今月の作業</a>
</div></header>

<div class="wrap">
<a class="backlink" href="../index.html">← 記事一覧へ</a>
<article class="post">
  <h1>{title}</h1>
  <div class="postmeta"><time datetime="{ymd}">{y}年{int(mo)}月{int(d)}日</time><span class="cat {catcls}">{cfg['cat']}</span><span class="rtime">読了目安 {cfg['rtime']}</span></div>
  <img src="../images/{cfg['imgdir']}/{thumb}.png" alt="{title}">

{body}
{aff}
  <div class="next">
    <p class="t">次に読む</p>
    <a href="{nx_href}">{nx_label}</a>
  </div>
</article>
</div>

<footer class="site"><div class="inner">
  <p>© えいこうの家庭菜園ノート</p>
</div></footer>
</body>
</html>
'''
    dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'articles', cfg['slug'] + '.html')
    open(dst, 'w').write(page)
    return dst, title, sec, len(toc), body.count('<img')

if __name__ == '__main__':
    cfg = json.load(open(sys.argv[1]))
    dst, title, sec, ntoc, nimg = build(cfg)
    print(f"作成: {dst}")
    print(f"  タイトル: {title}")
    print(f"  h2={sec} 目次={ntoc} 画像={nimg+1}（アイキャッチ含む）")
