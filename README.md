# えいこうの家庭菜園ノート

有機・無農薬の家庭菜園を初心者向けに発信するブログ（静的サイト）。
Cloudflare Pages でホスティング。

## 構成
- `index.html` … トップ（記事一覧）
- `articles/` … 記事ページ（例：`01-hajimekata.html`）
- `assets/style.css` … スタイル
- `images/` … 図解（記事ごとにフォルダ分け）

## 記事の追加方法
1. `articles/` に新しいHTMLを追加（既存記事をコピーして中身を差し替え）
2. `images/<回数>/` に図解を入れる
3. `index.html` の記事カードを1つ増やす
4. `git add -A && git commit && git push` → Cloudflare Pages が自動デプロイ

## アフィリエイト
- 本文中の `🔗リンク：◯◯` は、もしも/楽天/Amazon のリンクに差し替える。
- フッターとページ上部にアフィリエイト広告利用の表記あり（ステマ規制対応）。
