/* 言語の案内バー（2026-09-30）
 *
 * ★自動転送はしない。理由は2つ：
 *   ①Googleのクローラーは米国から来るので、自動転送すると日本語ページまで
 *     英語と判定され、日本語の検索結果から消えるおそれがある
 *   ②読者が自分で選んだ言語を奪うことになる（日本語で読みたい海外在住の人もいる）
 *
 * やっているのは「ブラウザの言語と、いま見ているページの言語が食い違っていたら、
 * もう片方への案内を1回だけ出す」だけ。閉じたら記憶して二度と出さない。
 * 行き先は、そのページ自身の <link rel="alternate" hreflang="..."> から取る。
 */
(function () {
  try {
    var pageLang = (document.documentElement.lang || 'ja').slice(0, 2);
    var want = (navigator.language || 'ja').slice(0, 2) === 'ja' ? 'ja' : 'en';
    if (want === pageLang) return;                       // 言語が合っている＝何もしない

    var alt = document.querySelector('link[rel="alternate"][hreflang="' + want + '"]');
    if (!alt) return;                                     // 対になるページが無ければ出さない
    var href = alt.getAttribute('href');
    if (!href || href === location.href.split('#')[0]) return;

    var key = 'langhint-' + want;
    try { if (localStorage.getItem(key) === 'off') return; } catch (e) {}

    var msg = want === 'en'
      ? ['This page is also available in English', 'Read in English', 'Not now']
      : ['この記事には日本語版があります', '日本語で読む', '閉じる'];

    // ★スマホでは貼り付けない（2026-10-02）
    //   幅375pxだと2行になって86px＝画面の11%あり、ヘッダーより上に居座っていた。
    //   これは「入口でもう片方の言語を知らせる」だけの案内なので、
    //   読み始めたら流れて消えてよい。パソコンでは1行40px程度なので貼り付けたまま。
    var st = document.createElement('style');
    st.textContent = [
      '.langhint{position:sticky;top:0;z-index:9999;background:#eef5ea;',
      '  border-bottom:1px solid #cfe0c6;padding:10px 14px;font-size:.94em;line-height:1.5;',
      '  display:flex;gap:12px;align-items:center;justify-content:center;flex-wrap:wrap;color:#2f5f24}',
      '.langhint a{font-weight:700;color:#2f7a22;text-decoration:underline}',
      '.langhint button{background:none;border:1px solid #b9cfae;border-radius:999px;',
      '  padding:5px 14px;font-size:.9em;color:#4b6b42;cursor:pointer}',
      '@media(max-width:560px){.langhint{position:static;padding:8px 12px;gap:8px;font-size:.88em}}'
    ].join('');
    document.head.appendChild(st);

    var bar = document.createElement('div');
    bar.className = 'langhint';
    bar.setAttribute('role', 'note');
    var span = document.createElement('span'); span.textContent = msg[0];
    var a = document.createElement('a'); a.href = href; a.textContent = msg[1] + ' →';
    var b = document.createElement('button'); b.type = 'button'; b.textContent = msg[2];
    b.addEventListener('click', function () {
      try { localStorage.setItem(key, 'off'); } catch (e) {}
      bar.remove();
    });
    bar.appendChild(span); bar.appendChild(a); bar.appendChild(b);
    document.body.insertBefore(bar, document.body.firstChild);
  } catch (e) { /* 案内が出せなくても、本文の表示は絶対に妨げない */ }
})();
