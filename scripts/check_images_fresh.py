#!/usr/bin/env python3
"""ブログの画像が、図解の原本と同じ版かを照合する。

使い方:
    python3 scripts/check_images_fresh.py          # 照合するだけ
    python3 scripts/check_images_fresh.py --fix    # 古いものを原本で置き換える

なぜ要るか（2026-09-21に実害）:
    図解を直したのにブログ側のコピーを更新し忘れると、**本番に古い版が出たまま**になる。
    2026-09-20は「液体肥料」と書かれた図4が、2026-09-21は★付きの題名と
    「同じ株」の誤りが、それぞれブログに出たままだった。
    ★出力先は3か所（原稿／図書館／ブログHTML＋画像）。画像は忘れやすいのでこれで機械的に見る。

終了コード: 0=全部最新 / 1=古いものがある
"""
import os, sys, glob, hashlib, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC_ROOTS = [
    "/Users/sinnji19/CodexClaude/みずのさんノウハウ図書館/図解",
    "/Volumes/Suno/ノウハウ図書館/図解_使用済み",   # 公開済み記事の図解の退避先
]
SKIP = ("_旧版", "backup", "過去版", "drafts", "試作", "生成素材", "_検品")


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def build_index():
    src = {}
    for root in SRC_ROOTS:
        if not os.path.isdir(root):
            print(f"  ⚠ 見つかりません（SSD未接続？）: {root}")
            continue
        for r, d, fs in os.walk(root):
            if any(x in r for x in SKIP):
                continue
            for f in fs:
                if f.endswith(".png"):
                    src.setdefault(f, os.path.join(r, f))
    return src


def main():
    fix = "--fix" in sys.argv
    src = build_index()
    stale, missing, ok = [], [], 0
    for p in sorted(glob.glob("images/*/*.png")):
        f = os.path.basename(p)
        s = src.get(f)
        if not s:
            missing.append(p)
            continue
        if md5(p) == md5(s):
            ok += 1
        else:
            stale.append((p, s))

    print(f"■ 最新 {ok}枚 ／ ★古い {len(stale)}枚 ／ 原本が見つからない {len(missing)}枚")
    for p, s in stale:
        print(f"  ★古い: {p}")
        print(f"         原本 {s}")
    for p in missing[:10]:
        print(f"  原本なし: {p}")

    if stale and fix:
        for p, s in stale:
            shutil.copy2(s, p)
        print(f"\n✅ {len(stale)}枚を原本で置き換えました。")
        print("   → 次に `python3 scripts/png2webp.py` を回してから commit してください。")

    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
