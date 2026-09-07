// 旧URL（kateisaien-blog.pages.dev）と www 付きURLへのアクセスを、正規のホスト
// kateisaien-note.com へ301で転送する。
// プレビュー用のサブドメイン（<hash>.kateisaien-blog.pages.dev）は対象外にして、
// ホスト名は厳密一致で判定する。
const CANONICAL_HOST = "kateisaien-note.com";
const REDIRECT_HOSTS = new Set([
  "kateisaien-blog.pages.dev",
  "www.kateisaien-note.com",
]);

export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (REDIRECT_HOSTS.has(url.hostname)) {
    url.hostname = CANONICAL_HOST;
    url.protocol = "https:";
    return Response.redirect(url.toString(), 301);
  }
  return context.next();
}
