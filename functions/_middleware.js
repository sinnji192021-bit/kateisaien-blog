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
  return context.next();
}
