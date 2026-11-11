// 旧URL（kateisaien-blog.pages.dev）と www 付きURLへのアクセスを、正規のホスト
// kateisaien-note.com へ301で転送する。
// プレビュー用のサブドメイン（<hash>.kateisaien-blog.pages.dev）は対象外にして、
// ホスト名は厳密一致で判定する。
const CANONICAL_HOST = "kateisaien-note.com";
const REDIRECT_HOSTS = new Set([
  "kateisaien-blog.pages.dev",
  "www.kateisaien-note.com",
]);

// ★作業用のファイル（予約表・スクリプト・メモ）はリポジトリにあるとそのまま配信されてしまう。
// 未公開記事のタイトルやMacのフォルダ名が読めたので、URLで開けないよう404を返す（2026-10-21）。
const BLOCK_PREFIXES = ["/記事設定/", "/scripts/", "/.claude/", "/functions/"];
const BLOCK_FILES = new Set(["/README.md", "/.gitignore", "/.DS_Store"]);

function isBlocked(pathname) {
  let p = pathname;
  try { p = decodeURIComponent(pathname); } catch (e) { /* そのまま判定 */ }
  if (BLOCK_FILES.has(p)) return true;
  return BLOCK_PREFIXES.some((pre) => p.startsWith(pre));
}

// ★★AdSense審査の間だけ、英語版（/en/）を審査と検索から外す（2026-11-11・オーナー承認「Aで」）
//   ・英語版は日本語記事の翻訳なので「複製されたコンテンツ」と見られている疑いがある
//   ・ページは消さない。リンク・URLからは今まで通り読める（海外向けに残すのがオーナー方針）
//   ・やること：①検索に載せない印（X-Robots-Tag: noindex）を付ける ②広告のコードを配信時に取り除く
//   ・サイトマップからは scripts/build.py の EN_IN_SITEMAP=False で外している
//   ★合格したら、ここを false にし、build.py の EN_IN_SITEMAP を True に戻して build.py を流す
const EN_REVIEW_MODE = true;

function isEnglish(pathname) {
  return pathname === "/en" || pathname.startsWith("/en/");
}

export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (isBlocked(url.pathname)) {
    return new Response("Not Found", {
      status: 404,
      headers: { "Content-Type": "text/plain; charset=utf-8", "X-Robots-Tag": "noindex" },
    });
  }
  if (REDIRECT_HOSTS.has(url.hostname)) {
    url.hostname = CANONICAL_HOST;
    url.protocol = "https:";
    return Response.redirect(url.toString(), 301);
  }
  const res = await context.next();
  if (EN_REVIEW_MODE && isEnglish(url.pathname)) {
    const out = new Response(res.body, res);
    out.headers.set("X-Robots-Tag", "noindex");
    const ct = out.headers.get("Content-Type") || "";
    if (ct.includes("text/html")) {
      return new HTMLRewriter()
        .on('script[src*="pagead2.googlesyndication.com"]', { element(el) { el.remove(); } })
        .on("ins.adsbygoogle", { element(el) { el.remove(); } })
        .transform(out);
    }
    return out;
  }
  return res;
}
