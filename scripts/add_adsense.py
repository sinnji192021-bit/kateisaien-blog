#!/usr/bin/env python3
"""Google AdSense のコードを入れる（既定は英語版 /en/ だけ）。

  python3 scripts/add_adsense.py --check              # いまの状態を見るだけ
  python3 scripts/add_adsense.py pub-0000000000000000 # 英語版に入れる＋ads.txtを作る
  python3 scripts/add_adsense.py pub-... --all        # 日本語ページにも入れる（※要相談）

★なぜ既定が /en/ だけか
  日本語ページは楽天アフィリエイトが422本入っていて、記事の世界観もはっきりしている。
  ノウハウ図書館でも「自動表示の広告が世界観を壊す」という指摘が最も支持されていた（2026-09-30調べ）。
  いっぽう英語ページは楽天が機能しないので、広告以外の収益手段が事実上ない。
  だから「英語版だけ広告を出す」という置き方にしてある。

★お金はかからない。AdSenseは登録・設置ともに無料で、支払いは受け取る側だけ。
"""
import glob, io, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

TAG = ('<script async src="https://pagead2.googlesyndication.com/pagead/js/'
       'adsbygoogle.js?client={pid}" crossorigin="anonymous"></script>\n')
MARK = "pagead2.googlesyndication.com"


def targets(all_pages):
    fs = ["en/index.html"] + sorted(glob.glob("en/articles/*.html")) + ["en/privacy.html"]
    if all_pages:
        fs += ["index.html", "privacy.html"] + sorted(glob.glob("articles/*.html"))
    return [f for f in fs if os.path.exists(f)]


def check():
    have = [f for f in targets(True) if MARK in io.open(f, encoding="utf-8").read()]
    en = [f for f in targets(False)]
    print(f"AdSenseのコードが入っているページ: {len(have)}")
    print(f"英語版のページ数: {len(en)}")
    print("ads.txt:", "あり" if os.path.exists("ads.txt") else "なし")
    for f in have[:10]:
        print("   ", f)


def install(pid, all_pages):
    if not re.fullmatch(r"pub-\d{16}", pid):
        sys.exit(f"✕ パブリッシャーIDの形が違います: {pid}\n"
                 "  AdSenseの管理画面に出る 'pub-' で始まる16桁の番号を渡してください。")
    n = 0
    for f in targets(all_pages):
        s = io.open(f, encoding="utf-8").read()
        if MARK in s:
            continue
        m = re.search(r"<head>\n", s)
        if not m:
            print("⚠ <head> が見つからない:", f); continue
        s = s[:m.end()] + TAG.format(pid=pid) + s[m.end():]
        io.open(f, "w", encoding="utf-8").write(s)
        n += 1
        print("入れた:", f)
    # ads.txt（これが無いとAdSenseに「収益に重大な影響」の警告が出る）
    line = f"google.com, {pid}, DIRECT, f08c47fec0942fa0\n"
    if not os.path.exists("ads.txt") or line not in io.open("ads.txt", encoding="utf-8").read():
        io.open("ads.txt", "a", encoding="utf-8").write(line)
        print("ads.txt に追記しました")
    print(f"\n■ {n}ページに入れました。"
          "\n★このあと AdSense の管理画面で「自動広告」をONにし、"
          "\n  表示するURLを /en/ に絞ってください（日本語ページに出さないため）。")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    if "--check" in args or not args:
        check()
    else:
        install(args[0], "--all" in args)
