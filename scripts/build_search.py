#!/usr/bin/env python3
"""記事から検索インデックス（search-index.json）を作る。

articles.json の見出し・説明に加えて、記事本文から
・見出し（h2/h3）
・★を付けた強調文
を拾ってキーワードにする。日本語は分かち書きしないので、
検索は「部分一致」で行う（ライブラリ不要・完全オフライン）。

使い方: python3 scripts/build_search.py
"""
import json, re, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTS = json.loads((ROOT / "scripts" / "articles.json").read_text(encoding="utf-8"))

# ── 表記ゆれ辞書 ────────────────────────────────────────
# 記事は「玉ねぎ」と書くが、読者は「タマネギ」「たまねぎ」でも打つ。
# どれか1つでも本文にあれば、仲間の語をまとめて検索用テキストに足す。
ALIASES = [
    ["玉ねぎ", "たまねぎ", "タマネギ", "玉葱", "オニオン"],
    ["大根", "だいこん", "ダイコン"],
    ["にんじん", "人参", "ニンジン"],
    ["じゃがいも", "ジャガイモ", "馬鈴薯", "ポテト"],
    ["さつまいも", "サツマイモ", "薩摩芋", "さつま芋"],
    ["里芋", "さといも", "サトイモ"],
    ["きゅうり", "キュウリ", "胡瓜"],
    ["トマト", "とまと", "ミニトマト"],
    ["なす", "ナス", "茄子", "なすび"],
    ["ピーマン", "ぴーまん"],
    ["キャベツ", "きゃべつ"],
    ["白菜", "はくさい", "ハクサイ"],
    ["ブロッコリー", "ぶろっこりー"],
    ["ほうれん草", "ほうれんそう", "ホウレンソウ", "菠薐草"],
    ["小松菜", "こまつな", "コマツナ"],
    ["春菊", "しゅんぎく", "シュンギク"],
    ["レタス", "れたす"],
    ["ねぎ", "ネギ", "葱", "長ねぎ", "青ねぎ"],
    ["にんにく", "ニンニク", "大蒜"],
    ["いちご", "イチゴ", "苺", "ストロベリー"],
    ["枝豆", "えだまめ", "エダマメ"],
    ["そら豆", "そらまめ", "ソラマメ", "空豆"],
    ["スナップエンドウ", "すなっぷえんどう", "えんどう", "エンドウ", "絹さや"],
    ["落花生", "らっかせい", "ラッカセイ", "ピーナッツ"],
    ["とうもろこし", "トウモロコシ", "コーン"],
    ["かぼちゃ", "カボチャ", "南瓜"],
    ["ズッキーニ", "ずっきーに"],
    ["オクラ", "おくら"],
    ["ゴーヤ", "ごーや", "にがうり", "ニガウリ", "苦瓜"],
    ["スイカ", "すいか", "西瓜"],
    ["メロン", "めろん"],
    ["しそ", "シソ", "紫蘇", "大葉", "おおば"],
    ["しょうが", "ショウガ", "生姜"],
    ["みょうが", "ミョウガ", "茗荷"],
    ["ごぼう", "ゴボウ", "牛蒡"],
    ["かぶ", "カブ", "蕪"],
    ["虫", "害虫", "むし"],
    ["雑草", "草", "ざっそう"],
    ["肥料", "追肥", "元肥", "ひりょう"],
    ["水やり", "水", "みずやり", "灌水"],
    ["土", "土づくり", "土壌", "つち"],
    ["種", "タネ", "たね", "種まき", "タネまき"],
    ["苗", "なえ"],
    ["連作", "連作障害", "輪作"],
    ["マルチ", "まるち", "マルチング"],
    ["プランター", "ぷらんたー", "鉢", "ベランダ"],
    ["収穫", "しゅうかく"],
    ["保存", "ほぞん", "貯蔵"],
    ["剪定", "せんてい", "整枝", "摘心", "てきしん"],
    ["間引き", "まびき"],
    ["石灰", "せっかい"],
    ["堆肥", "たいひ", "腐葉土", "ぼかし"],
]

TAG = re.compile(r"<[^>]+>")
WS  = re.compile(r"\s+")


def text_of(html: str) -> str:
    return WS.sub(" ", TAG.sub(" ", html)).strip()


def extract(slug: str) -> dict:
    """記事HTMLから見出しと強調文を抜く。"""
    f = ROOT / "articles" / f"{slug}.html"
    if not f.exists():
        return {"heads": [], "keys": []}
    s = f.read_text(encoding="utf-8")
    body = s.split("</header>", 1)[-1]
    heads = [text_of(m) for m in re.findall(r"<h[23][^>]*>(.*?)</h[23]>", body, re.S)]
    # ★強調（<strong> と、本文に残る「★」始まりの文）
    keys = [text_of(m) for m in re.findall(r"<strong[^>]*>(.*?)</strong>", body, re.S)]
    heads = [h for h in heads if h and len(h) < 60]
    keys = [k for k in keys if k and len(k) < 80]
    return {"heads": heads[:30], "keys": keys[:40]}


def main() -> None:
    out = []
    for a in ARTS["articles"]:
        ex = extract(a["slug"])
        # 検索対象の文字列を1本にまとめる（小文字・NFKC で正規化）
        blob = " ".join([a.get("card", ""), a.get("short", ""), a.get("desc", ""),
                         a.get("cat", ""), *ex["heads"], *ex["keys"]])

        def widen(text: str) -> str:
            """表記ゆれ：仲間の語をどれか含むなら、その組をまるごと足す。"""
            extra = [w for grp in ALIASES if any(v in text for v in grp) for w in grp]
            return unicodedata.normalize("NFKC", text + " " + " ".join(sorted(set(extra)))).lower()

        blob = widen(blob)
        # 並び順の判定用に、タイトル／説明文だけを広げたものも持たせる
        title_blob = widen(a.get("card", "") + " " + a.get("short", ""))
        desc_blob = widen(a.get("desc", ""))
        out.append({
            "u": f"articles/{a['slug']}.html",
            "t": a.get("card", ""),
            "d": a.get("desc", ""),
            "c": a.get("cat", ""),
            "g": a.get("catcolor", "g"),
            "i": a.get("thumb", ""),
            "s": blob,
            "ta": title_blob,
            "da": desc_blob,
        })
    p = ROOT / "search-index.json"
    p.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    kb = p.stat().st_size / 1024
    print(f"search-index.json  {len(out)}件 / {kb:.0f}KB")


if __name__ == "__main__":
    main()
