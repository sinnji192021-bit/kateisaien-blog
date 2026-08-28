#!/usr/bin/env python3
"""記事のアフィリエイト枠プレースホルダを、rk/ の楽天HTMLで埋める。

使い方: python3 scripts/add_aff.py <config.json>
config: {"slug":"31-jagaimo","h":"1月に用意するもの",
         "items":[{"rk":"dansyaku","pick":"種芋（男爵）","cls":"good","desc":"..."}]}
  cls: good=おすすめ / なし=通常
★楽天HTMLは必ず <div class="rk">…</div> でくるむ（div開閉数を合わせるため）
"""
import json, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RK   = ROOT / "scripts" / "rk"

cfg  = json.load(open(sys.argv[1]))
f    = ROOT / "articles" / f"{cfg['slug']}.html"
s    = f.read_text()

blocks = [f'  <div class="aff">\n    <div class="h">{cfg["h"]}</div>']
for it in cfg["items"]:
    rk = (RK / f'{it["rk"]}.html').read_text().strip()
    cls = f' {it["cls"]}' if it.get("cls") else ""
    blocks.append(f'    <p class="pick{cls}">{it["pick"]}</p>')
    blocks.append(f'    <p>{it["desc"]}</p>')
    blocks.append(f'<div class="rk">{rk}</div>')
blocks.append("  </div>")
new = "\n".join(blocks)

# プレースホルダのHTMLコメントを丸ごと置き換える
pat = re.compile(r'[ \t]*<!-- ▼▼▼ アフィリエイト枠.*?▲▲▲ -->', re.S)
if not pat.search(s):
    sys.exit(f"✗ {cfg['slug']}: プレースホルダが見つかりません（すでに埋めた？）")
s = pat.sub(new, s, count=1)

if s.count("<div") != s.count("</div>"):
    sys.exit(f"✗ {cfg['slug']}: div開閉が不一致 {s.count('<div')}/{s.count('</div>')}")
f.write_text(s)
print(f"✅ {cfg['slug']}: 商品{len(cfg['items'])}件  div {s.count('<div')}/{s.count('</div>')}  楽天リンク{s.count('hb.afl.rakuten.co.jp')}")
