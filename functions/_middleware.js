// 旧URL（kateisaien-blog.pages.dev）へのアクセスを新ドメインへ301で転送する。
// プレビュー用のサブドメイン（<hash>.kateisaien-blog.pages.dev）は対象外にして、
// 本番のホスト名だけを厳密一致で判定する。
const OLD_HOST = "kateisaien-blog.pages.dev";
const NEW_HOST = "kateisaien-note.com";

export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (url.hostname === OLD_HOST) {
    url.hostname = NEW_HOST;
    url.protocol = "https:";
    return Response.redirect(url.toString(), 301);
  }
  return context.next();
}
