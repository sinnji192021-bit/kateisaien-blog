// /kongetsu  →  「その月」の月別記事へ転送する（2026-10-02）
//
// ★なぜ関数にしたか
//   ヘッダーの「🌱 今月の作業」ボタンは、以前は各ページに月別記事のURLを
//   直書きしていた。毎月105ファイルを手で直す作りだったため、10月になっても
//   8月号が開く状態で放置されていた（2026-10-02に発見）。
//   この関数を1枚置いて全ページから /kongetsu を指せば、以後は何もしなくてよい。
//
// ★日付は日本時間で判定する（Cloudflareの実行場所はUTCなので、月初・月末が1日ずれる）
// ★転送先はサイトマップに載せないページなので noindex を付ける

const BY_MONTH = {
  1: "30-1gatsu",
  2: "34-2gatsu",
  3: "39-3gatsu",
  4: "43-4gatsu",
  5: "48-5gatsu",
  6: "52-6gatsu",
  7: "57-7gatsu",
  8: "08-8gatsu",
  9: "11-9gatsu",
  10: "18-10gatsu",
  11: "21-11gatsu",
  12: "26-12gatsu",
};

export function onRequest(context) {
  const jst = new Date(Date.now() + 9 * 60 * 60 * 1000);
  const slug = BY_MONTH[jst.getUTCMonth() + 1];
  const to = new URL(`/articles/${slug}`, context.request.url);
  return new Response(null, {
    status: 302, // ★月で変わるので恒久転送(301)にはしない
    headers: {
      Location: to.toString(),
      "Cache-Control": "no-store",
      "X-Robots-Tag": "noindex",
    },
  });
}
