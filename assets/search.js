/* 全ページ共通のサイト内検索（2026-10-02）
 *
 * ヘッダーに🔍ボタンを足し、押すと検索パネルを開く。
 * ★TOPや404のように、ページ自身に大きな検索ボックス（#sbox）がある場合は、
 *   パネルを開かずにそこへスクロールして入力欄に合わせる（同じ機能を2つ出さない）。
 *
 * 日本語版・英語版のどちらでも動く。<html lang> で索引と行き先を切り替える。
 * ★リンクは必ず「/」から始める。記事は /articles/ の下にあるので、
 *   相対パスにすると階層のちがうページでこわれる。
 */
(function () {
  var EN = (document.documentElement.lang || 'ja').slice(0, 2) === 'en';
  var INDEX = EN ? '/en/search-index.json' : '/search-index.json';
  var PREFIX = EN ? '/en/' : '/';
  var T = EN ? {
    open: 'Search', title: 'Search this site',
    ph: 'e.g. tomatoes  slugs  frost', close: 'Close',
    hint: 'Searches the full text of all 104 articles',
    count: function (n) { return '<b>' + n + '</b> articles'; },
    more: function (n) { return 'and ' + n + ' more'; },
    none: function (q) {
      return 'Nothing matched "<b>' + q + '</b>".<br>'
        + 'Try a crop name (tomatoes, onions) or a problem (slugs, frost, watering).';
    }
  } : {
    open: '記事をさがす', title: 'サイト内検索',
    ph: '例：玉ねぎ　連作　水やり', close: '閉じる',
    hint: '記事104本の見出しと要点から、打ったそのままで探します',
    count: function (n) { return '<b>' + n + '</b> 件見つかりました'; },
    more: function (n) { return 'ほか ' + n + ' 件'; },
    none: function (q) {
      return '「<b>' + q + '</b>」に当てはまる記事は見つかりませんでした。<br>'
        + '野菜の名前（玉ねぎ・大根）や、困りごと（虫・雑草・水やり）で試してみてください。';
    }
  };

  // ── 体裁はこのファイルが自分で入れる（style.cssのキャッシュ待ちで崩れないように）
  var st = document.createElement('style');
  st.textContent = [
    '.navsearch{display:inline-flex;align-items:center;gap:6px;margin-left:12px;font:inherit;',
    '  font-size:13px;color:#3F7A33;background:#fff;border:1.5px solid #d8e0cf;border-radius:6px;',
    '  padding:7px 14px;cursor:pointer;white-space:nowrap}',
    '.navsearch:hover{background:#EAF3E4;border-color:#5FA049}',
    '.ssheet{position:fixed;inset:0;z-index:200;display:flex;align-items:flex-start;',
    '  justify-content:center;padding:70px 16px 24px}',
    '.ssheet[hidden]{display:none}',
    '.ssheet-bg{position:absolute;inset:0;background:rgba(30,30,25,.45)}',
    '.ssheet-box{position:relative;width:100%;max-width:720px;max-height:100%;overflow:auto;',
    '  background:#FBF7EF;border-radius:16px;padding:20px 22px;box-shadow:0 18px 50px rgba(0,0,0,.25)}',
    '.ssheet .sfield{border-width:2px;padding:12px 18px}',
    '.ssheet .sfield input{font-size:16px}',
    '.ssheet .sresults{margin-top:14px}',
    'body.sheet-open{overflow:hidden}',
    '@media(max-width:520px){.ssheet{padding:56px 10px 16px}',
    '  .ssheet-box{padding:14px 14px 16px;border-radius:14px}',
    '  .navsearch .t{display:none}.navsearch{padding:7px 11px}}'
  ].join('');
  document.head.appendChild(st);

  var inner = document.querySelector('header.site .inner');
  if (!inner) return;

  // ── ヘッダーのボタン
  var btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'navsearch';
  btn.setAttribute('aria-label', T.title);
  btn.innerHTML = '<span aria-hidden="true">🔍</span><span class="t">' + T.open + '</span>';
  var nav = inner.querySelector('.gnav');
  if (nav && nav.nextSibling) inner.insertBefore(btn, nav.nextSibling);
  else inner.appendChild(btn);

  // ── ページ自身に検索箱があるなら、そこへ送るだけ
  // ── スマホでは、読んでいる間（下へスクロール中）はヘッダーを引っ込める（2026-10-02）
  //    スマホのヘッダーは150pxあり、画面の約2割をずっと占めていた。
  //    上へ戻すとすぐ出るので、検索ボタンにはいつでも手が届く。
  (function () {
    var h = document.querySelector('header.site');
    if (!h || !window.matchMedia('(max-width:560px)').matches) return;
    var last = 0;
    window.addEventListener('scroll', function () {
      var y = window.scrollY;
      if (y > 240 && y > last + 6) h.classList.add('hdr-hide');
      else if (y < last - 6 || y <= 240) h.classList.remove('hdr-hide');
      last = y;
    }, { passive: true });
  })();

  var own = document.getElementById('sbox');
  if (own) {
    btn.addEventListener('click', function () {
      own.scrollIntoView({ behavior: 'smooth', block: 'center' });
      var i = own.querySelector('input');
      if (i) setTimeout(function () { i.focus(); }, 300);
    });
    return;
  }

  // ── 検索パネル
  var sheet = document.createElement('div');
  sheet.className = 'ssheet';
  sheet.hidden = true;
  sheet.innerHTML =
    '<div class="ssheet-bg"></div>'
    + '<div class="ssheet-box" role="dialog" aria-modal="true" aria-label="' + T.title + '">'
    + '  <label class="sfield">'
    + '    <span class="sicon" aria-hidden="true">🔍</span>'
    + '    <input type="search" autocomplete="off" placeholder="' + T.ph + '" aria-label="' + T.title + '">'
    + '    <button type="button" class="sx" aria-label="' + T.close + '">✕</button>'
    + '  </label>'
    + '  <p class="shint">' + T.hint + '</p>'
    + '  <div class="sresults"></div>'
    + '</div>';
  document.body.appendChild(sheet);

  var q = sheet.querySelector('input');
  var box = sheet.querySelector('.sresults');
  var hint = sheet.querySelector('.shint');
  var data = null, loading = false, timer = null;

  function norm(s) { return (s || '').normalize('NFKC').toLowerCase().trim(); }
  function kana(s) {
    return s.replace(/[ァ-ヶ]/g, function (c) {
      return String.fromCharCode(c.charCodeAt(0) - 0x60);
    });
  }
  function keys(s) { return EN ? [s] : [s, kana(s)]; }
  function url(p) { return p.indexOf('../') === 0 ? '/' + p.slice(3) : PREFIX + p; }

  function load() {
    if (data || loading) return Promise.resolve();
    loading = true;
    return fetch(INDEX)
      .then(function (r) { return r.json(); })
      .then(function (j) { data = j; loading = false; })
      .catch(function () { loading = false; data = []; });
  }

  function esc(s) {
    return (s || '').replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function hl(text, terms) {
    var out = esc(text);
    terms.forEach(function (t) {
      if (!t) return;
      var re = new RegExp('(' + t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
      out = out.replace(re, '<mark>$1</mark>');
    });
    return out;
  }

  function split(raw) { return norm(raw).split(/[\s　]+/).filter(Boolean); }

  function render(raw) {
    var terms = split(raw);
    if (!terms.length) { box.innerHTML = ''; hint.textContent = T.hint; return; }
    var hits = data.filter(function (a) {
      return terms.every(function (t) {
        return keys(t).some(function (k) { return a.s.indexOf(k) >= 0; });
      });
    });
    hits.forEach(function (a, i) {
      var t = a.ta || norm(a.t), d = a.da || norm(a.d), n = 0;
      terms.forEach(function (w) {
        if (keys(w).some(function (k) { return t.indexOf(k) >= 0; })) n += 10;
        else if (keys(w).some(function (k) { return d.indexOf(k) >= 0; })) n += 3;
      });
      a._i = i; a._sc = n;
    });
    hits.sort(function (x, y) { return (y._sc - x._sc) || (x._i - y._i); });

    hint.textContent = '';
    if (!hits.length) {
      box.innerHTML = '<div class="snone">' + T.none(esc(raw)) + '</div>';
      return;
    }
    var html = '<p class="scount">' + T.count(hits.length) + '</p>';
    hits.slice(0, 30).forEach(function (a) {
      html += '<a class="shit" href="' + url(a.u) + '">'
        + (a.i ? '<img src="' + url(a.i) + '" alt="" loading="lazy">' : '')
        + '<div><p class="st">' + hl(a.t, terms) + '</p>'
        + '<p class="sd">' + hl(a.d, terms) + '</p></div></a>';
    });
    if (hits.length > 30) html += '<p class="scount">' + T.more(hits.length - 30) + '</p>';
    box.innerHTML = html;
  }

  function open() {
    sheet.hidden = false;
    document.body.classList.add('sheet-open');
    load();
    setTimeout(function () { q.focus(); }, 30);
  }
  function close() {
    sheet.hidden = true;
    document.body.classList.remove('sheet-open');
    btn.focus();
  }

  btn.addEventListener('click', open);
  sheet.querySelector('.ssheet-bg').addEventListener('click', close);
  sheet.querySelector('.sx').addEventListener('click', close);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !sheet.hidden) close();
  });
  q.addEventListener('input', function () {
    var v = q.value;
    clearTimeout(timer);
    timer = setTimeout(function () { load().then(function () { render(v); }); }, 120);
  });
})();
