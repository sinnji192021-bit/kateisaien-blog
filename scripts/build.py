#!/usr/bin/env python3
"""ブログの自動組み立て。

`scripts/articles.json` に記事を1件足して、このスクリプトを走らせるだけで
次のすべてが更新される：

  1. TOPの注目記事（featured）
  2. TOPの目的別チップ
  3. TOPのセクション別カード一覧（新しい記事ほど上）
  4. 各記事の「日付・カテゴリ・読了時間」行
  5. 各記事の目次（h2から自動生成・id付与も自動）
  6. 各記事の「あわせて読みたい」3本（同じカテゴリ優先→新着で補充）
  7. sitemap.xml

使い方:
    cd ~/Documents/kateisaien-blog && python3 scripts/build.py

差し込み位置はHTMLコメントの目印で管理しているので、
目印の外を手で書き換えても消えない。
"""

from __future__ import annotations

import html
import json
import collections
import math
import re
import sys
from pathlib import Path
import datetime as _dt
import subprocess
from functools import lru_cache

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "scripts" / "articles.json").read_text(encoding="utf-8"))
ARTS = DATA["articles"]  # check() で実在するものだけに絞る
BASE = DATA["site"]["base"]

JP = "{}年{}月{}日"


def jp_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return JP.format(int(y), int(m), int(d))


@lru_cache(maxsize=1)
def _git_pubdates() -> dict:
    """記事HTMLがブログに最初にコミットされた日＝ブログでの実際の公開日を返す。

    ★articles.json の date は「ノウハウ図書館での公開予定日」で未来日が入る。
      そのまま表示すると、読者には「2027年12月4日」のような未来の日付が見える。
      ブログの表示日には、gitに最初に入った日（＝実際に公開した日）を使う。
    """
    # ★2026-11-08：iCloudにgitの中身を逃がされていると git log が失敗し、ここで黙って {} を返していた。
    #   → 全記事の表示日が articles.json の日付に化け、約90ページの日付が書き換わったままpushされた。
    #   黙って続けず止める（予約公開.py は失敗すると書きかけを戻して止まる）。
    r = None
    for _ in range(3):
        try:
            r = subprocess.run(
                ["git", "log", "--diff-filter=A", "--format=C%ad", "--date=short",
                 "--name-only", "--", "articles/*.html"],
                cwd=ROOT, capture_output=True, text=True, timeout=300,
            )
            if r.returncode == 0 and r.stdout.strip():
                break
        except subprocess.TimeoutExpired:
            r = None
    if r is None or r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError("git log で記事の公開日を取れなかった（表示日が化けるので止める）: "
                           + ((r.stderr or "")[-300:] if r else "timeout"))
    out = r.stdout
    dates, cur = {}, None
    for line in out.splitlines():
        if line.startswith("C"):
            cur = line[1:]
        elif line.startswith("articles/") and line.endswith(".html") and cur:
            # git log は新しい順。上書きし続けるので最後＝いちばん古いコミットが残る
            dates[line[len("articles/"):-len(".html")]] = cur
    return dates


def pub_date(a: dict) -> str:
    """表示用の公開日（ISO）。git初回コミット日 → 無ければ articles.json の date を今日で頭打ち。"""
    d = _git_pubdates().get(a["slug"])
    if d:
        return d
    return min(a["date"], _dt.date.today().isoformat())


def read_minutes(slug: str) -> int:
    """本文の文字数から読了時間を実測する（1分=550字）。"""
    body = (ROOT / "articles" / f"{slug}.html").read_text(encoding="utf-8").split("<article", 1)[1]
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    return max(3, round(len(re.sub(r"<[^>]+>", "", body)) / 550))


def check() -> list[dict]:
    """記事HTMLとサムネが実在するものだけを対象にする。
    足りないものは止めずに警告して飛ばす（書きかけでもTOPが壊れないように）。"""
    ok, skipped = [], []
    for a in ARTS:
        miss = []
        if not (ROOT / "articles" / f"{a['slug']}.html").exists():
            miss.append(f"articles/{a['slug']}.html")
        if not (ROOT / a["thumb"]).exists():
            miss.append(a["thumb"])
        (skipped if miss else ok).append((a, miss))
    for a, miss in skipped:
        if miss:
            print(f'  ⚠️  {a["slug"]:18} まだ無いので飛ばしました → {" / ".join(miss)}')
    return [a for a, miss in ok]


def block(text: str, name: str, content: str) -> str:
    """<!-- BUILD:name --> 〜 <!-- /BUILD:name --> の中身を差し替える。
    目印が無ければ何もしない（手書き部分を壊さないため）。"""
    pat = re.compile(rf"(<!-- BUILD:{name} -->).*?(<!-- /BUILD:{name} -->)", re.S)
    if not pat.search(text):
        return text
    return pat.sub(lambda m: m.group(1) + "\n" + content + "\n  " + m.group(2), text)


# ------------------------------------------------- 月別記事（◯月号）
MONTH_RE = re.compile(r"-(\d{1,2})gatsu$")


def thumb(path: str) -> str:
    """カード・関連記事に使う小さいサムネ（幅640px）のパス。
    ★記事の先頭に出る大きなアイキャッチには使わない（いちばん目立つ画像なので元のまま）。
      実体は scripts/make_thumbs.py が images/thumb/ に作る。"""
    rel = path[len("images/"):] if path.startswith("images/") else path
    cand = ROOT / "images" / "thumb" / rel
    return f"images/thumb/{rel}" if cand.exists() else path


def monthly_map() -> dict:
    """{月: 記事} の対応表。slug の「-10gatsu」から月を拾う。"""
    out = {}
    for a in ARTS:
        hit = MONTH_RE.search(a["slug"])
        if hit:
            out[int(hit.group(1))] = a
    return out


def jst_month() -> int:
    """日本時間の月。★UTCで判定すると月初・月末が1日ずれる。"""
    return (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=9)).month


def newest_first(items):
    return sorted(items, key=lambda a: (a["date"], a["slug"]), reverse=True)


# ---------------------------------------------------------------- TOP
def build_index() -> None:
    p = ROOT / "index.html"
    h = p.read_text(encoding="utf-8")
    mins = {a["slug"]: read_minutes(a["slug"]) for a in ARTS}
    newest = newest_first(ARTS)[0]["slug"]

    # ★注目記事（🌞 今月の必読）は「いまの月の号」を自動で選ぶ（2026-10-02）
    #   articles.json で featured:true を付けた記事があれば、そちらを優先する（手動の上書き用）。
    months = monthly_map()
    feat = (next((a for a in ARTS if a.get("featured")), None)
            or months.get(jst_month())
            or newest_first(ARTS)[0])
    fm = mins[feat["slug"]]
    featured = f'''  <a class="featured" href="articles/{feat["slug"]}">
    <div class="fthumb"><img src="{feat["thumb"]}" alt="{html.escape(feat["short"])}"></div>
    <div class="fbody">
      <span class="fbadge">🌞 今月の必読</span>
      <h2>{html.escape(feat["card"])}</h2>
      <p>{html.escape(feat["desc"])}</p>
      <div class="meta"><time datetime="{pub_date(feat)}">{jp_date(pub_date(feat))}</time><span class="cat{" g" if feat.get("catcolor")=="g" else ""}">{feat["cat"]}</span><span class="rtime">読了目安 約{fm}分</span></div>
      <span class="more">続きを読む →</span>
    </div>
  </a>'''

    # ★HTMLを作り直すのはpushするときだけなので、それだけでは翌月また古くなる。
    #   12か月分の中身をページに埋めておき、読み込んだ瞬間に当月へ差し替える。
    table = {
        str(mo): {
            "u": f'articles/{a["slug"]}', "i": a["thumb"], "alt": a["short"],
            "t": a["card"], "d": a["desc"], "dt": pub_date(a),
            "jp": jp_date(pub_date(a)), "c": a["cat"],
            "cg": a.get("catcolor") == "g", "m": mins[a["slug"]],
        }
        for mo, a in sorted(months.items())
    }
    featured += """
  <script>
  /* 🌞 今月の必読を、見ている月に合わせる（2026-10-02・build.pyが自動生成） */
  (function () {
    var M = """ + json.dumps(table, ensure_ascii=False) + """;
    var j = new Date(Date.now() + 9 * 3600 * 1000);   /* 日本時間 */
    var cur = M[j.getUTCMonth() + 1];
    var el = document.querySelector('a.featured');
    if (!cur || !el) return;
    if (el.getAttribute('href') !== cur.u) {
      el.setAttribute('href', cur.u);
      var img = el.querySelector('.fthumb img');
      img.src = cur.i; img.alt = cur.alt;
      el.querySelector('.fbody h2').textContent = cur.t;
      el.querySelector('.fbody p').textContent = cur.d;
      var tm = el.querySelector('time');
      tm.setAttribute('datetime', cur.dt); tm.textContent = cur.jp;
      var ct = el.querySelector('.cat');
      ct.textContent = cur.c; ct.className = 'cat' + (cur.cg ? ' g' : '');
      el.querySelector('.rtime').textContent = '読了目安 約' + cur.m + '分';
    }
    /* 下の一覧に同じ号が二重に出ないようにする（12本は必ず残す） */
    function dedupe() {
      var cards = document.querySelectorAll('.cards .card[data-mon]');
      for (var i = 0; i < cards.length; i++) {
        cards[i].hidden = (cards[i].getAttribute('data-mon') === String(j.getUTCMonth() + 1));
      }
    }
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', dedupe);
    } else { dedupe(); }
  })();
  </script>"""
    h = block(h, "FEATURED", featured)

    chips = '  <nav class="chips" id="list">\n' + "".join(
        f'    <a href="{c["href"]}">{c["label"]}</a>\n' for c in DATA["chips"]
    ) + "  </nav>"
    h = block(h, "CHIPS", chips)

    out = []
    for sec in DATA["sections"]:
        rows = [a for a in ARTS if a.get("section") == sec["id"]]
        # ★月別記事は12本すべて一覧に残す。注目記事は月で入れ替わるので、
        #   ここで外すと「先月号がページのどこにも無い」状態になる（二重表示はJSで消す）
        if sec["id"] != "monthly":
            rows = [a for a in rows if not a.get("featured")]
        if not rows:
            continue
        rows = newest_first(rows) if not sec.get("numbered") else sorted(rows, key=lambda a: a["slug"])
        out.append(f'  <div class="sec" id="{sec["id"]}"><h2>{sec["title"]}</h2><span class="en">{sec["en"]}</span></div>')
        out.append('  <div class="cards">')
        for i, a in enumerate(rows, 1):
            step = f'<span class="step">{i}</span>' if sec.get("numbered") else ""
            new = '<span class="new">NEW</span>' if a["slug"] == newest else ""
            cat = f'<span class="cat{" g" if a.get("catcolor")=="g" else ""}">{a["cat"]}</span>'
            mo = MONTH_RE.search(a["slug"])
            dm = f' data-mon="{int(mo.group(1))}"' if mo else ""
            hid = " hidden" if a["slug"] == feat["slug"] else ""
            out.append(f'''
    <div class="card"{dm}{hid}><a href="articles/{a["slug"]}">
      <div class="thumb"><img src="{thumb(a["thumb"])}" alt="{html.escape(a["short"])}" loading="lazy"></div>
      <div class="body">
        <h2>{step}{html.escape(a["card"])}</h2>
        <p class="ex">{html.escape(a["desc"])}</p>
        <div class="meta"><time datetime="{pub_date(a)}">{jp_date(pub_date(a))}</time>{cat}<span class="rtime">約{mins[a["slug"]]}分</span>{new}</div>
      </div>
    </a></div>''')
        out.append("\n  </div>\n")
    h = block(h, "CARDS", "\n".join(out))
    p.write_text(h, encoding="utf-8")
    print(f"index.html   注目記事={feat['slug']} / カード{sum(1 for x in out if x.lstrip().startswith('<div class="card"'))}枚（注目={feat['slug']}）")


# ------------------------------------------------------------ 各記事
# ------------------------------------------------------------ 関連記事の採点
# 「あわせて読みたい」は、以前は同カテゴリの新着3本を出していた。
# ただし「育てて学ぶ」が76記事と大きすぎて、中身の関係ない新着が並んでいた
# （例: 白菜の記事の下に 落ち葉・霜・野菜保存）。
# そこで、記事どうしの文章の重なりで選ぶ。日本語なので形態素解析は使わず、
# 2文字ずつの並び（文字bigram）のTF-IDFで測る。辞書も外部ライブラリも要らない。
_SIM_CACHE: dict[str, dict[str, float]] = {}

def _plain(slug: str) -> str:
    """記事本文からタグ・広告表・目次・関連欄を除いた素のテキスト。"""
    f = ROOT / "articles" / f"{slug}.html"
    if not f.exists():
        return ""
    t = f.read_text(encoding="utf-8")
    m = re.search(r"<article.*?</article>", t, re.S)
    t = m.group(0) if m else t
    t = re.sub(r"<(script|style|table)[^>]*>.*?</\1>", " ", t, flags=re.S)
    t = re.sub(r'<div class="(related|next|toc)".*?</div>\s*</div>', " ", t, flags=re.S)
    return re.sub(r"<[^>]+>", " ", t)

def _grams(t: str, w: int = 1) -> "collections.Counter[str]":
    t = re.sub(r"[\s0-9A-Za-z<>&;#/．。、，,.！!？?「」『』（）()：:・…\-—–\u3000]", "", t)
    c = collections.Counter()
    for i in range(len(t) - 1):
        c[t[i : i + 2]] += w
    return c

def _build_sim() -> None:
    """全記事のTF-IDFベクトルを1回だけ作る。見出し4・説明3・本文1の重み。"""
    vec = {a["slug"]: _grams(a.get("card", ""), 4) + _grams(a.get("desc", ""), 3)
                      + _grams(_plain(a["slug"]), 1) for a in ARTS}
    df: "collections.Counter[str]" = collections.Counter()
    for c in vec.values():
        for g in c:
            df[g] += 1
    n = len(vec)
    for slug, c in vec.items():
        # 半分以上の記事に出る語は、どこにでもある言葉なので捨てる
        v = {g: (1 + math.log(f)) * math.log(n / (1 + df[g]))
             for g, f in c.items() if df[g] < n * 0.5}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        _SIM_CACHE[slug] = {g: x / norm for g, x in v.items()}

def _sim(a: str, b: str) -> float:
    x, y = _SIM_CACHE.get(a, {}), _SIM_CACHE.get(b, {})
    if len(x) > len(y):
        x, y = y, x
    return sum(v * y[g] for g, v in x.items() if g in y)

def pick_related(me: dict, n: int = 3) -> list[dict]:
    """①手動指定 → ②文章の重なり → ③同カテゴリの新着、の順で選ぶ。"""
    by = {a["slug"]: a for a in ARTS}
    # ① articles.json に related: ["slug", ...] があれば、それが最優先
    if me.get("related"):
        return [by[s] for s in me["related"] if s in by][:n]
    # ② 文章の重なりで選ぶ
    if not _SIM_CACHE:
        _build_sim()
    scored = sorted(((_sim(me["slug"], a["slug"]), a["slug"]) for a in ARTS
                     if a["slug"] != me["slug"]), reverse=True)
    picked = [by[s] for v, s in scored[:n] if v >= 0.04]   # 似ていないものは採らない
    if len(picked) == n:
        return picked
    # ③ 足りなければ従来どおり同カテゴリ→新着で埋める
    have = {a["slug"] for a in picked} | {me["slug"]}
    same = [a for a in newest_first(ARTS) if a["cat"] == me["cat"] and a["slug"] not in have]
    rest = [a for a in newest_first(ARTS) if a["slug"] not in have and a not in same]
    return (picked + same + rest)[:n]


def build_articles() -> None:
    for a in ARTS:
        p = ROOT / "articles" / f"{a['slug']}.html"
        h = p.read_text(encoding="utf-8")
        m = read_minutes(a["slug"])

        cat = f'<span class="cat{" g" if a.get("catcolor")=="g" else ""}">{a["cat"]}</span>'
        meta = f'  <div class="postmeta"><time datetime="{pub_date(a)}">{jp_date(pub_date(a))}</time>{cat}<span class="rtime">読了目安 約{m}分</span></div>'
        if 'class="postmeta"' in h:
            h = re.sub(r'  <div class="postmeta">.*?</div>', meta, h, count=1, flags=re.S)
        else:
            h = re.sub(r"(<h1>.*?</h1>)", lambda mo: mo.group(1) + "\n" + meta, h, count=1, flags=re.S)

        # 見出しにidを振り直して目次を作る
        n = [0]
        def addid(mo):
            n[0] += 1
            return f'<h2 id="s{n[0]}">{mo.group(1)}</h2>'
        h = re.sub(r'<h2(?: id="s\d+")?>(.*?)</h2>', addid, h)
        heads = re.findall(r'<h2 id="s\d+">(.*?)</h2>', h)
        items = "".join(
            f'<li><a href="#s{i+1}">{re.sub(r"<[^>]+>", "", t)}</a></li>' for i, t in enumerate(heads)
        )
        toc = f'  <div class="toc">\n    <p class="t">📖 この記事の目次</p>\n    <ol>{items}</ol>\n  </div>'
        if 'class="toc"' in h:
            h = re.sub(r'  <div class="toc">.*?\n  </div>', toc, h, count=1, flags=re.S)
        elif heads:
            h = re.sub(r'(<h2 id="s1">)', toc + "\n\n  " + r"\1", h, count=1)

        cards = "".join(
            f'\n      <a href="{r["slug"]}"><div class="thumb"><img src="../{thumb(r["thumb"])}" '
            f'alt="{html.escape(r["short"])}" loading="lazy"></div><h4>{html.escape(r["short"])}</h4></a>'
            for r in pick_related(a)
        )
        rel = f'  <div class="related">\n    <p class="t">あわせて読みたい</p>\n    <div class="relgrid">{cards}\n    </div>\n  </div>'
        if 'class="related"' in h:
            h = re.sub(r'  <div class="related">.*?\n  </div>', rel, h, count=1, flags=re.S)
        else:
            h = h.replace('<div class="next">', rel + "\n\n  " + '<div class="next">', 1)

        p.write_text(h, encoding="utf-8")
        print(f'  {a["slug"]:18} 目次{len(heads)}項目 約{m}分 関連{len(pick_related(a))}本')


# ---------------------------------------------------------- sitemap
def _lastmod(a) -> str:
    """sitemap の lastmod を返す。

    ★articles.json の date は「ノウハウ図書館での公開予定日」で、未来日が入る。
      ブログ側の記事はすでに公開済みなので、未来日を lastmod に出してはいけない
      （Googleは未来の lastmod を無効とみなし、サイトマップの信頼度が下がる）。
      そこで「HTMLファイルの実際の更新日」を使い、それも無ければ今日で頭打ちにする。
    """
    today = _dt.date.today()
    f = ROOT / "articles" / f"{a['slug']}.html"
    if f.exists():
        d = _dt.date.fromtimestamp(f.stat().st_mtime)
    else:
        try:
            d = _dt.date.fromisoformat(a["date"])
        except Exception:
            d = today
    return min(d, today).isoformat()


def build_sitemap() -> None:
    today = _dt.date.today().isoformat()
    urls = [f"  <url>\n    <loc>{BASE}/</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>1.0</priority>\n  </url>"]
    for a in sorted(ARTS, key=lambda x: x["slug"]):
        urls.append(
            f"  <url>\n    <loc>{BASE}/articles/{a['slug']}</loc>\n"
            f"    <lastmod>{_lastmod(a)}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>"
        )
    # ---- 単独ページ（articles.json の管理外）----
    #   ★ここに足さないと、build.py を流すたびにサイトマップから消えます。
    #     about / contact は AdSense 審査で「運営者情報・お問い合わせがあること」を
    #     見られる重要ページなので、必ず残すこと（2026-10-09 に実際に消えた）。
    for extra in ("privacy.html", "about.html", "contact.html"):
        f = ROOT / extra
        if f.exists():
            lm = min(_dt.date.fromtimestamp(f.stat().st_mtime), _dt.date.today()).isoformat()
            urls.append(f"  <url>\n    <loc>{BASE}/{extra[:-5]}</loc>\n"
                        f"    <lastmod>{lm}</lastmod>\n    <changefreq>yearly</changefreq>\n    <priority>0.3</priority>\n  </url>")

    # ---- 英語版（/en/）。articles.json の管理外なので、実ファイルを見て足す ----
    #   ★ここを足さないと、build.py を流すたびに英語ページがサイトマップから消えます
    en_dir = ROOT / "en"
    n_en = 0
    if en_dir.is_dir():
        for f in sorted(en_dir.rglob("*.html")):
            rel = f.relative_to(ROOT).as_posix()            # 例 en/articles/sowing-depth.html
            loc = BASE + "/" + (rel[:-len("index.html")] if rel.endswith("index.html") else rel[:-len(".html")])
            lm = min(_dt.date.fromtimestamp(f.stat().st_mtime), _dt.date.today()).isoformat()
            pri = "0.9" if rel.endswith("index.html") else "0.8"
            urls.append(
                f"  <url>\n    <loc>{loc}</loc>\n"
                f"    <lastmod>{lm}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>{pri}</priority>\n  </url>"
            )
            n_en += 1

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n"
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")
    print(f"sitemap.xml  {len(ARTS)+1}件（日本語） ＋ {n_en}件（英語 /en/）")


def main() -> None:
    global ARTS
    # ★一覧カードと「あわせて読みたい」は幅640pxのサムネを読む。
    #   作り忘れると元の1280px（1枚200KB超）に戻ってしまうので、毎回ここで作る。
    try:
        import subprocess
        subprocess.run([sys.executable, str(ROOT / "scripts" / "make_thumbs.py")],
                       check=True, capture_output=True, text=True, timeout=900)
    except Exception as e:
        print(f"  ⚠️ サムネ作成を飛ばしました（{e}）")
    print("記事チェック")
    _post = True
    ARTS = check()
    if not ARTS:
        raise SystemExit("公開できる記事がありません")
    build_index()
    print("articles/")
    build_articles()
    build_sitemap()
    # 検索インデックス（サイト内検索用）も毎回作り直す
    import subprocess
    subprocess.run(["python3", str(ROOT / "scripts" / "build_search.py")], check=True)
    print("\n✅ 完了。ブラウザで確認して、よければ PUSH してください。")

    # ★一覧カードと「あわせて読みたい」を作り直したあとなので、
    #   そこで消えた width/height をここで入れ直す（レイアウトのずれ防止）
    try:
        import subprocess
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "add_img_size.py")],
                           check=True, capture_output=True, text=True, timeout=900)
        print(r.stdout.strip().splitlines()[-1])
    except Exception as e:
        print(f"  ⚠️ 画像サイズの付与を飛ばしました（{e}）")

if __name__ == "__main__":
    main()
