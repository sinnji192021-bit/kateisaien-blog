// 楽天アフィリエイトのリンクがクリックされたら、GA4 に aff_click イベントを送る（2026-11-03）
// GA4 の「イベント」で aff_click の数、どの記事からか（page_path）、どの商品か（link_url）が見られる
document.addEventListener('click', function (e) {
  var a = e.target.closest && e.target.closest('a[href*="hb.afl.rakuten.co.jp"]');
  if (!a || typeof gtag !== 'function') return;
  gtag('event', 'aff_click', {
    link_url: a.href,
    page_path: location.pathname,
    transport_type: 'beacon'
  });
}, true);
