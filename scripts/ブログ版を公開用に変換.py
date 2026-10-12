#!/usr/bin/env python3
"""ブログ版の原稿（記事原稿/NN_◯◯_ブログ版.md）を記事HTMLにする（2026-10-12）。

★なぜ作ったか
  `md2article.py` は設定JSONを引数に取るが、その設定JSONがどこにも保存されていなかった。
  毎回手で作り直す状態だったので、毎日更新が回らない。
  → 設定を `記事設定/<slug>.json` に残し、1コマンドで変換できるようにする。
  → 設定が無ければ、原稿とarticles.jsonから自動で組み立てて保存する。

使い方:
  python3 scripts/ブログ版を公開用に変換.py <ブログ版.md> <slug>
  例) python3 scripts/ブログ版を公開用に変換.py ~/CodexClaude/みずのさんノウハウ図書館/記事原稿/12_白菜_ブログ版.md 12-hakusai
"""
import json, os, re, shutil, subprocess, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFGDIR = os.path.join(ROOT, "記事設定")

def field(md, head):
    m = re.search(r"## " + head + r"[^\n]*\n```\n(.*?)\n```", md, re.S)
    return m.group(1).strip() if m else ""

def build_cfg(src, slug):
    md = open(src, encoding="utf-8").read()
    arts = json.load(open(os.path.join(ROOT, "scripts", "articles.json")))
    lst = arts["articles"] if isinstance(arts, dict) and "articles" in arts else arts
    cur = next((x for x in lst if x.get("slug") == slug), {})
    # 画像フォルダは既存記事の thumb から拾う（無ければ番号の先頭2桁）
    imgdir = ""
    if cur.get("thumb"):
        imgdir = cur["thumb"].split("/")[1]
    if not imgdir:
        imgdir = re.match(r"(\d+)", slug).group(1)
    # 本文の長さから読了時間（400字/分）
    body = md.split("（↓本文ここから）")[1].split("（↑本文ここまで）")[0]
    rtime = "約%d分" % max(3, round(len(re.sub(r"\s", "", body)) / 400))
    desc = field(md, "②")
    # 次の記事は既存の並びを引き継ぐ（無ければ記事一覧へ）
    nxt = cur.get("next") or ["../articles.html", "記事一覧へ"]
    return {
        "src": os.path.abspath(src),
        "slug": slug,
        "imgdir": imgdir,
        "date": datetime.date.today().isoformat(),
        "cat": cur.get("cat", "育てて学ぶ"),
        "rtime": rtime,
        "desc": desc[:120],
        "og": desc[:100],
        "next": nxt,
    }

AFF = re.compile(r'<div class="aff">.*?</div>\s*</div>', re.S)

def keep_affiliate(dst, before):
    """★手で貼った楽天リンクを引き継ぐ（2026-10-12）。

    `md2article.py` が作るアフィリ枠は、中身が空のコメント枠。
    本番の記事には、あとから手で楽天のHTMLが貼ってある（白菜は商品3つ）。
    作り直すとそれが消えるので、古いHTMLから枠ごと持ってきて差し替える。
    """
    if not before:
        return False
    old = AFF.search(before)
    if not old or "a.rakuten" not in old.group(0) and "me_id=" not in old.group(0):
        return False          # 中身が空の枠なら引き継ぐ必要はない
    now = open(dst, encoding="utf-8").read()
    new = AFF.search(now)
    if not new:
        return False
    open(dst, "w", encoding="utf-8").write(now.replace(new.group(0), old.group(0), 1))
    return True


def main(src, slug):
    os.makedirs(CFGDIR, exist_ok=True)
    cfgp = os.path.join(CFGDIR, slug + ".json")
    if os.path.exists(cfgp):
        cfg = json.load(open(cfgp))
        cfg["src"] = os.path.abspath(src)          # 原稿の場所だけは毎回いまの値に
    else:
        cfg = build_cfg(src, slug)
        print(f"★設定を新規作成: {cfgp}（あとから手で直してよい）")
    json.dump(cfg, open(cfgp, "w"), ensure_ascii=False, indent=1)
    dst = os.path.join(ROOT, "articles", slug + ".html")
    before = open(dst, encoding="utf-8").read() if os.path.exists(dst) else ""
    if before:
        shutil.copy2(dst, os.path.join("/tmp", slug + ".html.bak"))   # 念のため退避
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "md2article.py"), cfgp])
    if r.returncode:
        return r.returncode
    if keep_affiliate(dst, before):
        print("★手で貼ってあった楽天リンクを引き継ぎました")
    # ★ここまでは .png を指している。以下2つを必ず続けて走らせる：
    #   png2webp.py … 参照を .webp に張り替える
    #   build.py    … 目次・日付行・「あわせて読みたい」・sitemap を入れ直す
    for s2 in ("png2webp.py", "build.py"):
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", s2)],
                       stdout=subprocess.DEVNULL)
    print("◎ 変換・webp張り替え・組み立てまで完了")
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("使い方: ブログ版を公開用に変換.py <ブログ版.md> <slug>")
    sys.exit(main(sys.argv[1], sys.argv[2]))
