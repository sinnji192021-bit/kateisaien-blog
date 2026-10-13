#!/usr/bin/env python3
"""予約公開：記事設定/_予約公開.json から「その日の1本」だけをブログに公開する（2026-10-14）

★なぜ作ったか
  オーナーの指示「1日1本ずつ公開を必ず行って」。手作業だと、まとめて出したり日が空いたりする。
  → 原稿・図解・楽天枠を先に用意して予約表に並べ、毎朝launchdがその日の1本だけを出す。

★決まり
  ・1回の実行で公開するのは最大1本。今日すでに公開済みなら何もしない（取りこぼしても、まとめ出しはしない）
  ・予約表の date が今日以前で、まだ公開していないものの中から、いちばん古いものを1本
  ・作業前に git の未コミット変更があれば止める（ほかの作業の書きかけを巻きこまない）
  ・外部コマンドはすべて timeout 付き（共通ルール7）。失敗したら通知を出して止める
  ・公開後、本番URLが200になるまで最大5分確かめてログに残す

使い方: python3 scripts/予約公開.py [--dry]
"""
import datetime, json, os, shutil, subprocess, sys, time

ROOT = "/Users/sinnji19/Documents/kateisaien-blog"
LIB = "/Users/sinnji19/CodexClaude/みずのさんノウハウ図書館"
PY = sys.executable
SCHED = f"{ROOT}/記事設定/_予約公開.json"
LOG = f"{ROOT}/記事設定/_予約公開ログ.txt"
DRY = "--dry" in sys.argv
os.chdir(ROOT)


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M')} {msg}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def notify(msg):
    try:
        subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "ブログ予約公開"'],
                       timeout=20, capture_output=True)
    except Exception:
        pass


def run(cmd, t=600):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=t, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])} rc={r.returncode}: {(r.stderr or r.stdout)[-400:]}")
    return r.stdout


def published_today(today):
    if not os.path.exists(LOG):
        return False
    return any(l.startswith(today) and "◎ 公開" in l for l in open(LOG, encoding="utf-8"))


def main():
    today = datetime.date.today().isoformat()
    if published_today(today):
        log("・今日はもう1本公開済み。何もしない"); return 0
    sched = json.load(open(SCHED, encoding="utf-8"))
    arts = json.load(open("scripts/articles.json", encoding="utf-8"))
    have = {a["slug"] for a in arts["articles"]}
    todo = sorted([e for e in sched if e["date"] <= today and e["slug"] not in have], key=lambda e: e["date"])
    if not todo:
        left = [e for e in sched if e["slug"] not in have]
        log(f"・今日出す予約がない（残りの予約 {len(left)} 本）")
        if not left:
            notify("予約表が空です。次の記事の準備が必要です")
        return 0
    e = todo[0]
    sl = e["slug"]
    if DRY:
        log(f"（試し）今日出すのは {sl}"); return 0

    dirty = run(["/usr/bin/git", "status", "--porcelain"], 60).strip()
    if dirty:
        log(f"■ 未コミットの変更があるので止めた（{len(dirty.splitlines())}件）。ほかの作業中の可能性")
        notify(f"{sl} を公開できませんでした（未コミットの変更あり）"); return 1
    try:
        run(["/usr/bin/git", "pull", "--ff-only", "-q"], 120)
        # 1) 図解をコピー
        os.makedirs(f"images/{e['imgdir']}", exist_ok=True)
        for fn in e["figs"]:
            src = f"{LIB}/図解/{fn}"
            if not os.path.isfile(src):
                raise RuntimeError(f"図解が無い: {fn}")
            shutil.copy2(src, f"images/{e['imgdir']}/{fn}")
        # 2) articles.json に登録（日付は今日）
        a = dict(e["article"]); a["slug"] = sl; a["date"] = today
        arts["articles"].append(a)
        json.dump(arts, open("scripts/articles.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        # 3) 記事設定
        cfg = dict(e["cfg"]); cfg["slug"] = sl; cfg["date"] = today; cfg["src"] = e["src"]; cfg["imgdir"] = e["imgdir"]
        json.dump(cfg, open(f"記事設定/{sl}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        # 4) 変換〜組み立て
        run([PY, "scripts/ブログ版を公開用に変換.py", e["src"], sl], 900)
        run([PY, "scripts/add_aff.py", e["aff"]], 300)
        run([PY, "scripts/add_ga4.py"], 300)
        run([PY, "scripts/add_adsense.py", "pub-7926543135818453", "--all"], 300)
        run([PY, "scripts/add_img_size.py"], 600)
        run([PY, "scripts/make_thumbs.py"], 900)
        run([PY, "scripts/build.py"], 900)
        # 5) 点検（画像の欠け・必須タグ）
        html = open(f"articles/{sl}.html", encoding="utf-8").read()
        import re, urllib.parse
        miss = [x for x in re.findall(r'<img[^>]+src="([^"]+)"', html)
                if not x.startswith("http") and not os.path.exists(os.path.join("articles", urllib.parse.unquote(x)))]
        checks = {"画像の欠け": not miss, "GA4": "G-69D04PPM8P" in html, "広告": "adsbygoogle" in html,
                  "目次": 'class="toc' in html, "楽天": "me_id=" in html, "div": html.count("<div") == html.count("</div>")}
        bad = [k for k, v in checks.items() if not v]
        if bad:
            raise RuntimeError(f"点検で不合格: {bad} {miss[:3]}")
        # 6) コミット＆push
        run(["/usr/bin/git", "add", "-A", "articles", "images", "index.html", "sitemap.xml",
             "search-index.json", "scripts/articles.json", "記事設定"], 120)
        run(["/usr/bin/git", "commit", "-q", "-m",
             f"{e.get('title_short', sl)}をブログに追加：{sl}（予約公開）\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"], 120)
        run(["/usr/bin/git", "push", "-q", "origin", "HEAD"], 300)
    except Exception as ex:
        log(f"✕ {sl} の公開に失敗: {ex}")
        notify(f"{sl} の公開に失敗しました。ログを見てください"); return 1

    log(f"◎ 公開 {sl}（push済み）")
    url = f"https://kateisaien-note.com/articles/{sl}"
    for _ in range(20):
        try:
            code = subprocess.run(["/usr/bin/curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "15", url],
                                  capture_output=True, text=True, timeout=30).stdout
        except Exception:
            code = "err"
        if code == "200":
            log(f"  本番で表示を確認（200）: {url}"); notify(f"{sl} を公開しました"); return 0
        time.sleep(15)
    log(f"  △ 5分たっても本番が200にならない（最後={code}）。デプロイ待ちの可能性")
    notify(f"{sl} はpush済み。本番の表示はまだ確認できていません")
    return 0


if __name__ == "__main__":
    sys.exit(main())
