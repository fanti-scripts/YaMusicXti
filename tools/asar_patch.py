import argparse
import base64
import hashlib
import json
import os
import shutil
import struct
import sys
import time

BLOCK = 4 * 1024 * 1024

MARKER = "__ymApplyCustomBackground"

# Палитра стилей обложек: id, подпись, два цвета градиента.
# Первые шесть — старые значения coverStyle, чтобы конфиги не ломались.
COVER_PRESETS = [
    {"id": "off", "name": "Как есть", "a": "", "b": ""},
    {"id": "mono", "name": "Ч/б", "a": "#0a0a0a", "b": "#f5f5f5"},
    {"id": "sepia", "name": "Сепия", "a": "#2a1608", "b": "#ffd9a3"},
    {"id": "azure", "name": "Лазурь", "a": "#04121f", "b": "#8fe3ff"},
    {"id": "violet", "name": "Фиолет", "a": "#150726", "b": "#c9a2ff"},
    {"id": "rose", "name": "Роза", "a": "#2a0714", "b": "#ffb3c9"},
    {"id": "violet-cyan", "name": "Фиолетово-голубой", "a": "#6a2bff", "b": "#00e5ff"},
    {"id": "candy", "name": "Конфетный", "a": "#ff9d00", "b": "#00db4e"},
    {"id": "lilac", "name": "Сиреневый", "a": "#4b1e78", "b": "#f0b6ff"},
    {"id": "mint-rasp", "name": "Мятно-малиновый", "a": "#a30f3f", "b": "#4ef0c0"},
    {"id": "superman", "name": "Супермен", "a": "#0b2a6b", "b": "#ff2d55"},
    {"id": "ruby", "name": "Рубиновый", "a": "#4a0a12", "b": "#ff2e4d"},
    {"id": "space", "name": "Космос", "a": "#12002e", "b": "#ff3ea5"},
    {"id": "amethyst", "name": "Аметистово-жёлтый", "a": "#3c0b5e", "b": "#ffd166"},
    {"id": "peach", "name": "Персиковый", "a": "#5a1f1a", "b": "#ffb59e"},
    {"id": "lavender", "name": "Лавандовый", "a": "#231348", "b": "#b79cff"},
    {"id": "purple-sea", "name": "Пурпурно-морской", "a": "#2a0636", "b": "#12c2c8"},
    {"id": "sunset", "name": "Солнечный закат", "a": "#5a1200", "b": "#ffb703"},
    {"id": "orange-rose", "name": "Оранжево-розовый", "a": "#6b1a00", "b": "#ff7eb6"},
    {"id": "blueberry", "name": "Черника", "a": "#0b1030", "b": "#6b8bff"},
    {"id": "ivy", "name": "Зелёный плющ", "a": "#062a16", "b": "#4ade80"},
    {"id": "mint-choc", "name": "Мятный шоколад", "a": "#2a1608", "b": "#5eead4"},
    {"id": "raspberry", "name": "Малиновый смузи", "a": "#3a0018", "b": "#ff5d8f"},
    {"id": "frost", "name": "Обморожение", "a": "#062033", "b": "#a5f3ff"},
    {"id": "cold-berry", "name": "Холодная ягода", "a": "#0d0a33", "b": "#7dd3fc"},
    {"id": "storm", "name": "Грозовое море", "a": "#071a2b", "b": "#38bdf8"},
    {"id": "emerald", "name": "Изумруд", "a": "#022c22", "b": "#34d399"},
    {"id": "gold", "name": "Золото", "a": "#2b1a00", "b": "#fbbf24"},
    {"id": "copper", "name": "Медный", "a": "#2b0f00", "b": "#ff8a3d"},
    {"id": "turquoise", "name": "Бирюза", "a": "#032a2a", "b": "#2dd4bf"},
    {"id": "coral", "name": "Коралл", "a": "#2e0a12", "b": "#ff8a80"},
    {"id": "sky", "name": "Небо", "a": "#06213d", "b": "#7dd3fc"},
    {"id": "siren", "name": "Сирень", "a": "#1f1235", "b": "#c4b5fd"},
    {"id": "fire", "name": "Огонь", "a": "#3b0505", "b": "#ff6b35"},
    {"id": "lime", "name": "Лайм", "a": "#16260a", "b": "#a3e635"},
    {"id": "fuchsia", "name": "Фуксия", "a": "#2a0630", "b": "#ff4fd8"},
    {"id": "ocean", "name": "Океан", "a": "#041f33", "b": "#38bdf8"},
    {"id": "ash", "name": "Пепел", "a": "#111318", "b": "#9aa4b2"},
    {"id": "terracotta", "name": "Терракота", "a": "#2a0f08", "b": "#e07a5f"},
    {"id": "sakura", "name": "Сакура", "a": "#2b0a1a", "b": "#ffb7d5"},
    {"id": "cobalt", "name": "Кобальт", "a": "#041a4a", "b": "#4f7cff"},
    {"id": "avocado", "name": "Авокадо", "a": "#10230b", "b": "#9ccc65"},
    {"id": "grape", "name": "Виноград", "a": "#220a33", "b": "#a855f7"},
    {"id": "glacier", "name": "Ледник", "a": "#0a1a2f", "b": "#93c5fd"},
    {"id": "toxic", "name": "Токсик", "a": "#1a2b00", "b": "#a3ff12"},
    {"id": "desert", "name": "Пустыня", "a": "#3a1205", "b": "#ff9f1c"},
    {"id": "aurora", "name": "Северное сияние", "a": "#031f1a", "b": "#5eead4"},
    {"id": "neon", "name": "Неон", "a": "#001a14", "b": "#00ffa3"},
    {"id": "pion", "name": "Пион", "a": "#2a0a14", "b": "#f9a8d4"},
    {"id": "pomegranate", "name": "Гранат", "a": "#2a050c", "b": "#e11d48"},
    {"id": "bourbon", "name": "Бурбон", "a": "#2a1208", "b": "#d97706"},
    {"id": "cosmic", "name": "Космическая пыль", "a": "#120a2a", "b": "#8b5cf6"},
]
PRESET_IDS = [p["id"] for p in COVER_PRESETS]
PRESETS_JSON = json.dumps(COVER_PRESETS, ensure_ascii=False, separators=(",", ":"))
PRESET_IDS_JSON = json.dumps(PRESET_IDS)

# Движок фона вставляется в renderer через executeJavaScript после загрузки страницы.
ENGINE = r"""
(function(){
  'use strict';
  if(window.__ymBgV2) return;
  window.__ymBgV2 = true;

  // Позиция трека: звук в Яндекс Музыке идёт через MediaSource, поэтому
  // <audio>.duration часто равен длине буфера (около 10 секунд), а не песни.
  // Ловим setPositionState — там настоящее время и длительность.
  (function(){
    if(window.__ymBgPosHook) return;
    window.__ymBgPosHook = true;
    window.__ymBgPos = null;
    var ms;
    try{ ms = navigator.mediaSession; }catch(e){}
    if(!ms) return;
    function wrap(obj){
      if(!obj || typeof obj.setPositionState !== 'function') return;
      var orig = obj.setPositionState;
      if(orig.__ymBgWrapped) return;
      var wrapped = function(state){
        try{
          if(state && isFinite(state.duration) && state.duration > 0){
            window.__ymBgPos = {
              duration: Number(state.duration),
              position: Number(state.position) || 0,
              rate: isFinite(state.playbackRate) ? Number(state.playbackRate) : 1,
              at: Date.now()
            };
          }
        }catch(e){}
        return orig.apply(obj, arguments);
      };
      wrapped.__ymBgWrapped = true;
      try{ obj.setPositionState = wrapped; }catch(e){}
    }
    wrap(ms);
    try{ wrap(Object.getPrototypeOf(ms)); }catch(e){}
  })();

  var C = window.__YMBG__ || {};
  var PRESETS = __PRESETS__;
  function presetById(id){
    for(var i = 0; i < PRESETS.length; i++){
      if(PRESETS[i].id === id) return PRESETS[i];
    }
    return null;
  }
  function normalizeCoverStyle(v){
    var s = String(v || '').toLowerCase();
    return presetById(s) ? s : 'mono';
  }

  // Дуотон: обложка переводится в ч/б и раскрашивается градиентом пресета —
  // тёмный тон уходит в тени, светлый в света. Поэтому исходный цвет картинки
  // не проступает ни в покое, ни на наведении, а палитра в панели совпадает
  // с тем, что видно на обложках.
  function hexRgb(h){
    h = String(h || '').replace('#', '');
    if(h.length === 3) h = h.charAt(0) + h.charAt(0) + h.charAt(1) + h.charAt(1) + h.charAt(2) + h.charAt(2);
    var n = parseInt(h, 16);
    if(!isFinite(n)) return [0, 0, 0];
    return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
  }

  var dtKey = '';
  function ensureDuotone(){
    if(!document.body) return;
    var key = PRESETS.length + '|' + PRESETS[PRESETS.length - 1].id;
    if(document.getElementById('ym-dt') && dtKey === key) return;
    var old = document.getElementById('ym-dt');
    if(old && old.parentNode) old.parentNode.removeChild(old);
    dtKey = key;
    var NS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(NS, 'svg');
    svg.id = 'ym-dt';
    svg.setAttribute('aria-hidden', 'true');
    svg.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden;pointer-events:none;';
    for(var i = 0; i < PRESETS.length; i++){
      var p = PRESETS[i];
      if(!p.a || !p.b) continue;
      var ca = hexRgb(p.a), cb = hexRgb(p.b);
      var f = document.createElementNS(NS, 'filter');
      f.setAttribute('id', 'ymdt-' + p.id);
      f.setAttribute('color-interpolation-filters', 'sRGB');
      var m = document.createElementNS(NS, 'feColorMatrix');
      m.setAttribute('type', 'matrix');
      m.setAttribute('values', '0.2126 0.7152 0.0722 0 0 ' +
        '0.2126 0.7152 0.0722 0 0 ' +
        '0.2126 0.7152 0.0722 0 0 ' +
        '0 0 0 1 0');
      var ct = document.createElementNS(NS, 'feComponentTransfer');
      ['R', 'G', 'B'].forEach(function(ch, idx){
        var e = document.createElementNS(NS, 'feFunc' + ch);
        e.setAttribute('type', 'table');
        e.setAttribute('tableValues', ca[idx].toFixed(3) + ' ' + cb[idx].toFixed(3));
        ct.appendChild(e);
      });
      f.appendChild(m);
      f.appendChild(ct);
      svg.appendChild(f);
    }
    document.body.appendChild(svg);
  }
  var cfg = {
    adaptive: !!C.adaptive,
    src: C.src || '',
    isVideo: !!C.isVideo,
    blur: Number(C.blur) || 0,
    brightness: (C.brightness === undefined || C.brightness === null) ? 1 : Number(C.brightness),
    dim: (C.dim === undefined || C.dim === null) ? 0.25 : Number(C.dim),
    vignette: (C.vignette === undefined || C.vignette === null) ? 0 : Number(C.vignette),
    navbarDim: (C.navbarDim === undefined || C.navbarDim === null) ? 0.35 : Number(C.navbarDim),
    playerTransparency: (C.playerTransparency === undefined || C.playerTransparency === null) ? 0.48 : Number(C.playerTransparency),
    playerBlur: (C.playerBlur === undefined || C.playerBlur === null) ? 20 : Number(C.playerBlur),
    playerSaturate: (C.playerSaturate === undefined || C.playerSaturate === null) ? 1.15 : Number(C.playerSaturate),
    fade: (C.fade === undefined || C.fade === null) ? 600 : Number(C.fade),
    poll: Number(C.poll) || 1500,
    file: C.file || '',
    web: C.web || '',
    webBase: C.webBase || '',
    webStamp: Number(C.webStamp) || 0,
    fit: String(C.fit || '') === 'cover' ? 'cover' : 'smart',
    // Один стиль на все обложки приложения: '' — как есть.
    coverStyle: normalizeCoverStyle(C.coverStyle),
    discordRpc: !!C.discordRpc,
    discordClientId: String(C.discordClientId || ''),
    token: C.token || ''
  };

  function buildStyle(){
    // blur(0px) всё равно заставляет Chromium прогонять фильтр через отдельный
    // проход — поэтому нулевое размытие в правило не попадает.
    var mediaFilter = 'filter:brightness(var(--ym-bright))' +
      (cfg.blur > 0 ? ' blur(var(--ym-blur))' : '') + ';';
    return [
    'html,body{background:transparent !important;}',
    '#ym-bg{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden;background:#0d0d0d;',
      '--ym-blur:' + cfg.blur + 'px;--ym-bright:' + cfg.brightness + ';--ym-dim:' + cfg.dim + ';',
      '--ym-vig:' + cfg.vignette + ';--ym-nav:' + cfg.navbarDim + ';}',
    '#ym-bg .ym-layer{position:absolute;inset:0;opacity:0;transition:opacity ' + cfg.fade + 'ms ease;}',
    '#ym-bg .ym-layer.active{opacity:1;}',
    // «Заполнить»: кадр ровно по окну (cover). Никаких scale(1.02) — лишнее
    // растяжение слоя и потеря резкости ни к чему.
    '#ym-bg .ym-media{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;',
      'object-position:center;display:block;' + mediaFilter + 'transform:translateZ(0);}',
    // «Умно»: передний слой показывает весь кадр (contain), задний — его же
    // размытая копия под cover, чтобы поля по краям не были чёрными.
    '#ym-bg .ym-media.ym-front{object-fit:contain;}',
    // Кадр, который почти совпадает по пропорциям с окном, растягиваем на всё
    // окно: обрезка минимальна, зато нет полей и размытых краёв.
    '#ym-bg .ym-media.ym-front.ym-fill{object-fit:cover;}',
    '#ym-bg .ym-media.ym-back{object-fit:cover;transform:scale(1.14) translateZ(0);',
      'filter:brightness(.7) saturate(1.1) blur(56px);}',
    // В режиме заполнения задний размытый слой не нужен — он скрыт, чтобы не
    // тратить кадры на лишний blur.
    '#ym-bg .ym-layer.ym-fill .ym-back{display:none;}',
    '#ym-bg iframe.ym-media{border:0;background:transparent;}',
    '#ym-bg .ym-shade{position:absolute;inset:0;background:rgba(0,0,0,var(--ym-dim));}',
    '#ym-bg .ym-vignette{position:absolute;inset:0;opacity:var(--ym-vig);',
      'background:radial-gradient(ellipse at center,rgba(0,0,0,0) 40%,rgba(0,0,0,.75) 100%);}',
    '[class*="DefaultLayout_root"],[class*="CommonLayout_root"],[class*="App_root"]',
      '{background:transparent !important;background-image:none !important;}',
    '[class*="Content_root"],[class*="Content_main"],[class*="VibePage_root__"]',
      '{background:transparent !important;background-image:none !important;}',
    '[class*="Content_main"]:not([class*="newVibe"])',
      '{background:linear-gradient(180deg,rgba(8,8,8,.42),rgba(8,8,8,.6)) !important;}',
    'html.ym-page-open [class*="Content_main"]',
      '{background:transparent !important;background-image:none !important;visibility:hidden !important;}',
    // Плеер выше панели «Фон»: backdrop-filter делает из плеера отдельный
    // контекст наложения с z-index:auto, и вертикальный ползунок громкости
    // (z-index 9999 внутри плеера) оказывался под панелью. Поднимаем сам
    // контекст плеера на его штатный уровень --ym-z-index-player.
    '[class*="PlayerBarDesktopWithBackgroundProgressBar_root"]',
      '{background:rgba(14,14,14,' + (1 - cfg.playerTransparency).toFixed(2) + ') !important;' +
      'z-index:var(--ym-z-index-player,300);' +
      '-webkit-backdrop-filter:blur(' + Math.round(cfg.playerBlur) + 'px) saturate(' + cfg.playerSaturate + ');' +
      'backdrop-filter:blur(' + Math.round(cfg.playerBlur) + 'px) saturate(' + cfg.playerSaturate + ');}',
    '[class*="SearchPage_skeletonHeaderWithUpperBlocks"]',
      '{background:transparent !important;background-image:none !important;' +
      '-webkit-backdrop-filter:none !important;backdrop-filter:none !important;border:0 !important;box-shadow:none !important;}',
    '[class*="VibePage_vibeAnimation__"],[class*="VibePage_bigCardPanelBackground__"],',
      '[class*="VibePage_artistCover__"],[class*="VibeArtistCover_"]',
      '{display:none !important;}',
    '[class*="Navbar_root__"]{background-color:rgba(8,8,8,var(--ym-nav)) !important;}',
    '[class*="TitleBar_root"]{background:transparent !important;background-image:none !important;' +
      '-webkit-backdrop-filter:none !important;backdrop-filter:none !important;border:0 !important;box-shadow:none !important;}'
    ].concat(themeRules()).join('\n');
  }

  // Стиль обложек — один на всё приложение: колесо подборок, альбомы,
  // плейлисты, миксы, артисты. Подложек под плитками нет: под иконками
  // пусто. Стиль держится и на наведении — исходный цвет не проступает.
  function themeRules(){
    var out = [
      // Жёлтая подпись «Встряхнуть мою волну» — как у остальных плиток колеса.
      '[class*="WheelItem_title_accentColor"]{color:var(--ym-controls-color-secondary-text-enabled_variant) !important;}'
    ];
    var preset = presetById(cfg.coverStyle);
    var wheel = '[class*="WheelItem_cover"] img, [class*="WheelItem_cover"] svg';
    var cover = 'img[class*="_cover__"], [class*="_cover__"] img';
    var avatar = 'img[class*="_avatar__"], [class*="_avatar__"] img, ' +
      'img[class*="ArtistCard_image"], [class*="ArtistItem_image"] img, ' +
      '[class*="ArtistsContent_image"] img, [class*="ArtistRecommendationMeta_avatar"] img, ' +
      '[class*="VibeRoomMemberAvatar"] img';
    if(preset && preset.a && preset.b){
      var ref = 'url(#ymdt-' + preset.id + ')';
      var base = 'filter:' + ref + ' !important;transition:filter .18s ease !important;';
      // Наведение лишь чуть подсвечивает плитку в том же тоне.
      var hot = 'filter:' + ref + ' brightness(1.07) !important;';
      function hoverEach(list){
        return list.split(',').map(function(s){ return s.trim() + ':hover'; }).join(', ');
      }
      var reveal = '[class*="WheelItem_root"]:hover img[class*="WheelItem_cover"], ' +
        'a:hover img[class*="_cover__"], button:hover img[class*="_cover__"], ' +
        '[class*="Card_root"]:hover img[class*="_cover__"], [class*="Item_root"]:hover img[class*="_cover__"], ' +
        '[class*="Cell_root"]:hover img[class*="_cover__"], ' +
        'a:hover img[class*="_avatar__"], button:hover img[class*="_avatar__"], ' +
        '[class*="Card_root"]:hover img[class*="_avatar__"], [class*="Item_root"]:hover img[class*="_avatar__"]';
      out.push(
        wheel + ', ' + cover + ', ' + avatar + '{' + base + '}',
        hoverEach(wheel) + ', ' + hoverEach(cover) + ', ' + hoverEach(avatar) + ', ' + reveal + '{' + hot + '}'
      );
    }
    // Своя аватарка в меню (UserIcon/UserID) всегда цветная.
    out.push('img[class*="UserIcon_"], [class*="UserIcon_root"] img, ' +
      'img[class*="UserID-Avatar"], [class*="UserID-Avatar"] img, [class*="UserID-Avatar"] *' +
      '{filter:none !important;opacity:1 !important;}');
    return out;
  }
  var STYLE = buildStyle();

  function ensureStyle(){
    ensureDuotone();
    var s = document.getElementById('ym-bg-style');
    if(!s){ s = document.createElement('style'); s.id = 'ym-bg-style'; document.head.appendChild(s); }
    if(s.textContent !== STYLE) s.textContent = STYLE;
    // Пользовательский CSS добавляем последним, чтобы он мог переопределять встроенные правила.
    if(cfg.css){
      var u = document.getElementById('ym-bg-user');
      if(!u){ u = document.createElement('style'); u.id = 'ym-bg-user'; }
      if(u.textContent !== cfg.css) u.textContent = cfg.css;
      if(u.parentNode !== document.head || u.nextSibling) document.head.appendChild(u);
    } else {
      var oldCss = document.getElementById('ym-bg-user');
      if(oldCss) oldCss.textContent = '';
    }
  }

  var root = null;
  function ensureRoot(){
    if(!document.body) return null;
    if(root && document.body.contains(root)) return root;
    root = document.getElementById('ym-bg');
    if(root) return root;
    root = document.createElement('div');
    root.id = 'ym-bg';
    var l1 = document.createElement('div'); l1.className = 'ym-layer active';
    var l2 = document.createElement('div'); l2.className = 'ym-layer';
    var shade = document.createElement('div'); shade.className = 'ym-shade';
    var vig = document.createElement('div'); vig.className = 'ym-vignette';
    root.appendChild(l1); root.appendChild(l2); root.appendChild(shade); root.appendChild(vig);
    document.body.insertBefore(root, document.body.firstChild);
    return root;
  }

  var navHost = null;
  var navBase = [];
  var navActive = false;
  var navActiveNative = null;
  var navActiveExtras = [];

  function navBaseClasses(){
    var nav = document.querySelector('[class*="Navbar_root__"]');
    if(!nav) return [];
    var links = nav.querySelectorAll('a[role="link"]');
    var base = null;
    for(var i = 0; i < links.length; i++){
      if(links[i].id === 'ym-nav-bg') continue;
      var cl = [];
      for(var j = 0; j < links[i].classList.length; j++) cl.push(links[i].classList[j]);
      if(base === null){ base = cl; continue; }
      var next = [];
      for(var k = 0; k < base.length; k++){
        if(cl.indexOf(base[k]) !== -1) next.push(base[k]);
      }
      base = next;
    }
    return base || [];
  }

  function applyNavClasses(el, base, extras, active){
    if(!el) return;
    var cls = base.slice();
    for(var i = 0; i < extras.length; i++){
      if(cls.indexOf(extras[i]) === -1) cls.push(extras[i]);
    }
    if(active && cls.indexOf('ym-nav-active') === -1) cls.push('ym-nav-active');
    el.className = cls.join(' ');
  }

  function syncNavActive(){
    var nav = document.querySelector('[class*="Navbar_root__"]');
    if(!nav) return;
    var base = navBase.length ? navBase : navBaseClasses();
    if(!base.length) return;
    var links = nav.querySelectorAll('a[role="link"]');
    for(var i = 0; i < links.length; i++){
      if(links[i].id === 'ym-nav-bg') continue;
      var extra = [];
      for(var j = 0; j < links[i].classList.length; j++){
        var c = links[i].classList[j];
        if(base.indexOf(c) === -1) extra.push(c);
      }
      if(extra.length){
        navActiveNative = links[i];
        navActiveExtras = extra;
        for(var k = 0; k < extra.length; k++) links[i].classList.remove(extra[k]);
        break;
      }
    }
    applyNavClasses(document.getElementById('ym-nav-bg'), base, navActiveExtras, true);
  }

  function ensureNav(){
    try{
      var nav = document.querySelector('[class*="Navbar_root__"]');
      if(!nav || !document.body) return;
      var links = nav.querySelectorAll('a[role="link"]');
      var natives = [];
      for(var i = 0; i < links.length; i++){
        if(links[i].id !== 'ym-nav-bg') natives.push(links[i]);
      }
      if(!natives.length) return;
      var last = natives[natives.length - 1];
      var prev = natives.length > 1 ? natives[natives.length - 2] : null;

      var base = navBaseClasses();
      if(!base.length) return;
      navBase = base;

      var host = document.getElementById('ym-nav-bg-host');
      if(!host){
        host = document.createElement('div');
        host.id = 'ym-nav-bg-host';
        host.style.cssText = 'position:fixed;left:20px;top:0;z-index:60;color:rgba(255,255,255,.5);';
        document.body.appendChild(host);

        var item = last.cloneNode(true);
        item.id = 'ym-nav-bg';
        item.removeAttribute('data-test-id');
        item.removeAttribute('data-state');
        item.removeAttribute('aria-current');
        item.removeAttribute('href');
        item.setAttribute('role', 'link');
        item.setAttribute('tabindex', '0');
        var span = item.querySelector('span');
        if(span){ span.textContent = 'Фон'; span.setAttribute('title', 'Фон'); }
        var svg = item.querySelector('svg');
        if(svg){
          svg.innerHTML = '<rect x="3.2" y="4.2" width="17.6" height="15.6" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"/>' +
                          '<circle cx="8.6" cy="9.6" r="1.7" fill="currentColor"/>' +
                          '<path d="M4.5 17.5l4.6-4.6 3.6 3.6 2.7-2.7 4.1 4.1" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>';
          svg.setAttribute('viewBox', '0 0 24 24');
          svg.setAttribute('fill', 'none');
        }
        item.style.width = '100%';
        item.style.height = '100%';
        item.style.boxSizing = 'border-box';
        item.addEventListener('click', function(e){
          e.preventDefault();
          e.stopPropagation();
          if(e.stopImmediatePropagation) e.stopImmediatePropagation();
          if(document.getElementById('ym-page')) positionPage();
          else openPanel();
        }, true);
        host.appendChild(item);
      }
      navHost = host;
      var el = document.getElementById('ym-nav-bg');

      // На всякий случай убираем старые копии, если они остались внутри React-дерева.
      var stray = nav.querySelectorAll('#ym-nav-bg');
      for(var s = 0; s < stray.length; s++){
        if(stray[s] !== el) stray[s].parentNode.removeChild(stray[s]);
      }

      applyNavClasses(el, base, navActiveExtras, navActive);

      var r = last.getBoundingClientRect();
      var pr = prev ? prev.getBoundingClientRect() : null;
      var gap = (pr && pr.height > 0 && r.top >= pr.bottom) ? Math.max(0, Math.round(r.top - pr.bottom)) : 4;
      var narrow = r.width < 100;
      if(el){
        var label = el.querySelector('span');
        if(label) label.style.display = narrow ? 'none' : '';
        el.style.padding = narrow ? '12px' : '';
        el.style.justifyContent = narrow ? 'center' : '';
      }
      if(!r.width || !r.height || r.bottom <= 0 || r.top >= window.innerHeight - 4){
        host.style.display = 'none';
      } else {
        host.style.display = 'block';
        host.style.left = Math.round(r.left) + 'px';
        host.style.top = Math.round(r.bottom + gap) + 'px';
        host.style.width = Math.round(r.width) + 'px';
        host.style.height = Math.round(r.height) + 'px';
      }

      if(pageOpen) syncNavActive();
    }catch(e){}
  }

  function makeMedia(url, isVideo, cls){
    var el;
    if(isVideo){
      el = document.createElement('video');
      el.src = url;
      el.autoplay = true; el.loop = true; el.muted = true; el.defaultMuted = true;
      el.volume = 0; el.playsInline = true;
      el.setAttribute('muted', ''); el.setAttribute('playsinline', '');
      var p = el.play(); if(p && p.catch) p.catch(function(){});
    } else {
      el = document.createElement('img');
      el.src = url;
      el.decoding = 'async';
    }
    el.className = 'ym-media' + (cls ? ' ' + cls : '');
    return el;
  }

  // Масштаб.
  // «Заполнить» — кадр целиком закрывает окно: пропорции сохраняются,
  // лишнее по краям обрезается. Один элемент, без трансформаций — максимум резкости.
  // «Умно» — решение принимается по конкретному кадру и текущему окну:
  // если обрезка при заполнении выходит небольшой, кадр заполняет окно целиком;
  // если кадр сильно не совпадает по пропорциям, он виден полностью, а поля
  // закрывает размытая копия того же кадра.
  // Допустимая обрезка при заполнении: во сколько раз ширина/высота кадра
  // отличается от окна. 1.22 — обрезается не больше ~18% одной стороны.
  var SMART_CROP_LIMIT = 1.22;

  function bindMediaMetrics(el, cb){
    if(!el) return;
    if(el.tagName === 'VIDEO'){
      if(el.readyState >= 1) cb();
      else el.addEventListener('loadedmetadata', cb, {once: true});
    } else {
      if(el.complete && el.naturalWidth) cb();
      else el.addEventListener('load', cb, {once: true});
    }
  }

  function mediaRatio(el){
    if(!el) return 0;
    var w = el.tagName === 'VIDEO' ? (el.videoWidth || 0) : (el.naturalWidth || 0);
    var h = el.tagName === 'VIDEO' ? (el.videoHeight || 0) : (el.naturalHeight || 0);
    if(!w || !h) return 0;
    return w / h;
  }

  function decideFit(layer, front, mode){
    if(!layer || !front) return;
    var fill = true;
    if(mode !== 'cover'){
      var mr = mediaRatio(front);
      var vr = (layer.clientWidth || 0) / (layer.clientHeight || 0);
      if(mr > 0 && vr > 0){
        var crop = mr > vr ? mr / vr : vr / mr;
        fill = crop <= SMART_CROP_LIMIT;
      }
    }
    if(front.classList.contains('ym-fill') !== fill) front.classList.toggle('ym-fill', fill);
    if(layer.classList.contains('ym-fill') !== fill) layer.classList.toggle('ym-fill', fill);
  }

  function setMedia(layer, url, isVideo, fit){
    if(!layer) return;
    layer.textContent = '';
    layer.classList.remove('ym-fill');
    try{
      var back = makeMedia(url, isVideo, 'ym-back');
      var front = makeMedia(url, isVideo, 'ym-front');
      layer.appendChild(back);
      layer.appendChild(front);
      layer.__ymFit = function(){ decideFit(layer, front, fit); };
      bindMediaMetrics(front, layer.__ymFit);
      layer.__ymFit();
    }catch(e){}
  }

  // Окно поменяло размер — пропорции другие, решение по масштабу пересчитываем.
  var resizeTimer = 0;
  function refitAll(){
    var r = document.getElementById('ym-bg');
    if(!r) return;
    var layers = r.querySelectorAll('.ym-layer');
    for(var i = 0; i < layers.length; i++){
      if(typeof layers[i].__ymFit === 'function') layers[i].__ymFit();
    }
  }
  window.addEventListener('resize', function(){
    if(resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(refitAll, 120);
  });

  function setWeb(layer, url){
    if(!layer) return;
    layer.textContent = '';
    var f = document.createElement('iframe');
    f.className = 'ym-media';
    f.setAttribute('allow', 'autoplay; fullscreen; encrypted-media');
    f.setAttribute('referrerpolicy', 'no-referrer');
    f.src = url;
    layer.appendChild(f);
  }

  function webSrc(){
    if(!cfg.web) return '';
    if(/^https?:\/\//i.test(cfg.web)) return cfg.web;
    var rel = String(cfg.web).split('/').filter(function(x){ return x; })
      .map(function(x){ return encodeURIComponent(x); }).join('/');
    var u = (cfg.webBase || '') + rel;
    // Метка сборки: после замены HTML-файла iframe должен перезагрузиться,
    // даже если имя файла осталось прежним.
    if(cfg.webStamp) u += '?v=' + encodeURIComponent(cfg.webStamp);
    return u;
  }

  var currentUrl = null;
  var currentWeb = false;
  function apply(url, isVideo, isWeb){
    if(!url) return;
    if(url === currentUrl && !!isWeb === currentWeb) return;
    var r = ensureRoot(); if(!r) return;
    var layers = r.querySelectorAll('.ym-layer');
    if(layers.length < 2) return;
    var active = r.querySelector('.ym-layer.active');
    var inactive = (active === layers[0]) ? layers[1] : layers[0];
    try{
      if(isWeb) setWeb(inactive, url);
      else setMedia(inactive, url, isVideo, cfg.fit);
    }catch(e){ return; }
    currentUrl = url;
    currentWeb = !!isWeb;
    // requestAnimationFrame в свёрнутом/перекрытом окне может не сработать,
    // поэтому подстраховываемся таймером — иначе новый фон остаётся в скрытом слое.
    var swapped = false;
    function swap(){
      if(swapped) return;
      swapped = true;
      inactive.classList.add('active');
      if(active) active.classList.remove('active');
      setTimeout(function(){
        if(active && !active.classList.contains('active')) active.textContent = '';
      }, cfg.fade + 120);
    }
    requestAnimationFrame(swap);
    setTimeout(swap, 150);
  }

  function clearMedia(){
    var r = ensureRoot(); if(!r) return;
    var layers = r.querySelectorAll('.ym-layer');
    for(var i = 0; i < layers.length; i++){
      layers[i].classList.remove('active');
      layers[i].textContent = '';
    }
    currentUrl = null;
    currentWeb = false;
    lastCover = null;
  }

  function hiRes(url){
    if(!url) return null;
    return url.replace(/%%/g, '1000x1000').replace(/\/\d+x\d+(?=[/?&]|$)/, '/1000x1000');
  }

  function bestSrc(img){
    var ss = img.getAttribute && img.getAttribute('srcset');
    if(!ss) return img.currentSrc || img.src;
    var parts = ss.split(',');
    var last = (parts[parts.length - 1] || '').trim().split(/\s+/)[0];
    return last || img.src;
  }

  function coverUrl(){
    var sels = [
      '[class*="AlbumCover_cover__"]',
      '[class*="PlayerBarDesktop"] img[src*="avatars.yandex.net"]',
      '[class*="VibePlayerBar_"] img[src*="avatars.yandex.net"]',
      '[class*="PlayerBar_"] img[src*="avatars.yandex.net"]'
    ];
    for(var i = 0; i < sels.length; i++){
      var imgs = document.querySelectorAll(sels[i]);
      for(var j = 0; j < imgs.length; j++){
        var im = imgs[j];
        var w = im.naturalWidth || im.width || 0;
        if(w < 60) continue;
        if(/ArtistCover|artist|avatar/i.test((im.className || '').toString())) continue;
        var u = bestSrc(im);
        if(u && u.indexOf('avatars.yandex.net') !== -1) return hiRes(u);
      }
    }
    return null;
  }

  function updateAll(d){
    if(!d || typeof d !== 'object') return;
    ['blur','brightness','dim','vignette','navbarDim','playerTransparency','playerBlur','playerSaturate','fade','poll'].forEach(function(k){
      if(d[k] !== undefined && d[k] !== null && d[k] !== '') cfg[k] = Number(d[k]);
    });
    if(d.adaptive !== undefined) cfg.adaptive = !!d.adaptive;
    if(d.coverStyle !== undefined) cfg.coverStyle = normalizeCoverStyle(d.coverStyle);
    if(d.discordRpc !== undefined) cfg.discordRpc = !!d.discordRpc;
    if(d.discordClientId !== undefined) cfg.discordClientId = String(d.discordClientId || '').replace(/[^0-9]/g, '').slice(0, 20);
    setRpcWatchers(cfg.discordRpc);
    var fitChanged = false;
    if(d.fit !== undefined){
      var f = String(d.fit || '') === 'cover' ? 'cover' : 'smart';
      if(f !== cfg.fit){
        cfg.fit = f;
        fitChanged = true;
      }
    }
    if(d.css !== undefined) cfg.css = String(d.css || '');
    if(d.file !== undefined) cfg.file = String(d.file || '');
    if(d.web !== undefined) cfg.web = String(d.web || '');
    if(d.webBase !== undefined) cfg.webBase = String(d.webBase || '');
    if(d.webStamp !== undefined) cfg.webStamp = Number(d.webStamp) || 0;
    if(d.src !== undefined){
      cfg.src = String(d.src || '');
      cfg.isVideo = !!d.isVideo;
    }
    // currentUrl не сбрасываем: apply() сам сравнит адрес. Иначе смена
    // любого ползунка перезапускала бы видео с начала.
    STYLE = buildStyle();
    ensureStyle();
    var r = ensureRoot();
    if(r){
      r.style.setProperty('--ym-dim', cfg.dim);
      r.style.setProperty('--ym-blur', cfg.blur + 'px');
      r.style.setProperty('--ym-bright', cfg.brightness);
      r.style.setProperty('--ym-vig', cfg.vignette);
      r.style.setProperty('--ym-nav', cfg.navbarDim);
    }
    var wu = webSrc();
    // Смена масштаба требует перерисовать текущий кадр (но не видео с нуля
    // при обычном движении ползунков).
    if(fitChanged){ currentUrl = null; lastCover = null; }
    setAdaptiveWatchers(cfg.adaptive);
    if(cfg.adaptive){
      lastCover = null;
      tick();
    } else if(wu){
      apply(wu, false, true);
    } else if(cfg.src){
      apply(cfg.src, cfg.isVideo, false);
    } else {
      clearMedia();
    }
  }
  window.addEventListener('ymbg:update', function(e){
    try{ updateAll(e.detail); }catch(err){}
  });

  var PANEL_CSS = [
    '#ym-page{position:fixed;z-index:90;display:flex;flex-direction:column;overflow:hidden;border-radius:20px;background:linear-gradient(180deg,rgba(20,20,22,.66),rgba(14,14,16,.84));-webkit-backdrop-filter:blur(26px) saturate(1.2);backdrop-filter:blur(26px) saturate(1.2);border:1px solid rgba(255,255,255,.07);box-shadow:0 24px 80px rgba(0,0,0,.45);color:#e6e6e6;font-family:"YS Text",sans-serif;}',
    '.ym-page-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding:20px 28px 4px;}',
    '.ym-page-title{margin:0;font-family:"YSMusic Headline","YS Text",sans-serif;font-size:32px;line-height:34px;font-weight:700;letter-spacing:-.2px;color:#e6e6e6;}',
    '.ym-page-sub{margin-top:7px;font-size:14px;line-height:20px;color:rgba(255,255,255,.5);}',
    '.ym-page-body{flex:1;min-height:0;overflow:auto;padding:10px 28px 28px;overscroll-behavior:contain;}',
    '.ym-page-body::-webkit-scrollbar{width:8px;}',
    '.ym-page-body::-webkit-scrollbar-thumb{background:rgba(255,255,255,.14);border-radius:4px;}',
    '.ym-grid{display:grid;grid-template-columns:minmax(0,1.12fr) minmax(0,.88fr);gap:16px;}',
    '@media (max-width: 980px){.ym-grid{grid-template-columns:1fr;}.ym-sliders{grid-template-columns:repeat(2,minmax(0,1fr));}}',
    '.ym-card{background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.06);border-radius:16px;padding:16px;box-sizing:border-box;}',
    '.ym-card-title{font-size:16px;font-weight:600;color:#e6e6e6;}',
    '.ym-card-label{font-size:11px;font-weight:600;letter-spacing:.6px;text-transform:uppercase;color:rgba(255,255,255,.4);margin-bottom:10px;}',
    '.ym-preview-box{position:relative;aspect-ratio:16/9;max-height:170px;border-radius:12px;overflow:hidden;background:#0b0d11;}',
    '.ym-preview-box img,.ym-preview-box video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:none;}',
    '.ym-preview-name{margin-top:11px;font-size:13px;color:#e6e6e6;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}',
    '.ym-preview-hint{margin-top:3px;font-size:12px;color:rgba(255,255,255,.42);}',
    '.ym-drop{border:1.5px dashed rgba(255,255,255,.16);border-radius:14px;background:rgba(255,255,255,.03);padding:12px 14px;text-align:center;cursor:pointer;transition:border-color .15s,background .15s;margin-top:12px;}',
    '.ym-drop:hover,.ym-drop.over{border-color:#ffdb4d;background:rgba(255,219,77,.07);}',
    '.ym-dtitle{font-size:13.5px;color:#e6e6e6;}',
    '.ym-dsub{font-size:12px;color:rgba(255,255,255,.45);margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}',
    '.ym-urlrow{display:flex;gap:8px;margin-top:8px;}',
    '.ym-input{flex:1;min-width:0;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08);border-radius:10px;color:#e6e6e6;padding:10px 12px;font-size:13px;font-family:inherit;outline:none;box-sizing:border-box;}',
    '.ym-input:focus{border-color:rgba(255,219,77,.55);}',
    '.ym-input::placeholder{color:rgba(255,255,255,.35);}',
    '.ym-hint{margin-top:6px;font-size:11.5px;line-height:16px;color:rgba(255,255,255,.35);}',
    '.ym-btn{border:0;border-radius:10px;font-family:inherit;font-size:13px;cursor:pointer;height:38px;padding:0 16px;}',
    '.ym-btn.ghost{background:rgba(255,255,255,.06);color:#e6e6e6;border:1px solid rgba(255,255,255,.1);}',
    '.ym-btn.ghost:hover{background:rgba(255,255,255,.11);}',
    '.ym-btn.primary{background:#ffdb4d;color:#17181c;font-weight:600;padding:0 24px;}',
    '.ym-btn.primary:hover{background:#ffe27a;}',
    '.ym-settings{margin-top:10px;}',
    '.ym-card-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}',
    '.ym-chips{display:flex;gap:6px;flex-wrap:wrap;}',
    '.ym-chip{border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.04);color:rgba(255,255,255,.7);border-radius:999px;padding:5px 12px;font-size:12px;cursor:pointer;font-family:inherit;}',
    '.ym-chip:hover{background:rgba(255,255,255,.1);color:#fff;}',
    '.ym-chip.on{background:rgba(255,219,77,.16);border-color:rgba(255,219,77,.55);color:#ffdb4d;}',
    '.ym-swatches{display:grid;grid-template-columns:repeat(auto-fill,minmax(118px,1fr));gap:8px;margin-top:12px;}',
    '.ym-swatch{position:relative;height:74px;border:0;border-radius:11px;cursor:pointer;padding:8px 9px;box-sizing:border-box;text-align:left;overflow:hidden;font-family:inherit;background-color:#1b1e25;background-size:cover;box-shadow:inset 0 0 0 1px rgba(255,255,255,.06);transition:transform .14s,box-shadow .14s;}',
    '.ym-swatch:hover{transform:translateY(-1px);box-shadow:inset 0 0 0 1px rgba(255,255,255,.24),0 6px 14px rgba(0,0,0,.35);}',
    '.ym-swatch.on{box-shadow:inset 0 0 0 2px #ffdb4d,0 6px 16px rgba(0,0,0,.4);}',
    '.ym-swatch-name{position:relative;z-index:2;display:block;font-size:11.5px;font-weight:600;line-height:14px;color:#fff;text-shadow:0 1px 3px rgba(0,0,0,.7);max-height:28px;overflow:hidden;padding-right:22px;}',
    '.ym-swatch-hex{position:absolute;left:9px;right:9px;bottom:7px;z-index:2;font-size:9px;line-height:11px;color:rgba(255,255,255,.88);text-shadow:0 1px 2px rgba(0,0,0,.75);letter-spacing:.2px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;}',
    '.ym-swatch-num{position:absolute;right:7px;top:7px;z-index:2;min-width:17px;height:17px;padding:0 4px;border-radius:999px;background:rgba(0,0,0,.42);color:#fff;font-size:9.5px;font-weight:700;line-height:17px;text-align:center;box-sizing:border-box;}',
    '.ym-swatch-none{background-image:repeating-linear-gradient(135deg,rgba(255,255,255,.08) 0 6px,rgba(255,255,255,.02) 6px 12px) !important;}',
    '.ym-swatch-none .ym-swatch-hex{color:rgba(255,255,255,.55);}',
    '.ym-fitrow{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:10px;font-size:12.5px;color:#d7dbe3;}',
    '.ym-fitrow .ym-chips{flex-wrap:nowrap;}',
    '.ym-gallery-card{margin-top:16px;}',
    '.ym-page-body > .ym-card.ym-settings,.ym-page-body > .ym-card.ym-themes{margin-top:16px;}',
    '.ym-gal{display:grid;grid-template-columns:repeat(auto-fill,minmax(156px,1fr));gap:10px;margin-top:12px;}',
    '.ym-gal-empty{display:none;font-size:12.5px;color:rgba(255,255,255,.4);margin-top:10px;}',
    '.ym-gal-tile{position:relative;aspect-ratio:16/9;border-radius:12px;overflow:hidden;background:#0b0d11;border:1px solid rgba(255,255,255,.08);cursor:pointer;transition:border-color .15s,transform .15s;}',
    '.ym-gal-tile:hover{border-color:rgba(255,219,77,.5);transform:translateY(-1px);}',
    '.ym-gal-tile.on{border-color:#ffdb4d;box-shadow:0 0 0 1px #ffdb4d inset;}',
    '.ym-gal-thumb{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;background:#12141a;}',
    '.ym-gal-badge{position:absolute;top:6px;left:6px;z-index:2;font-size:9.5px;font-weight:700;letter-spacing:.5px;padding:3px 7px;border-radius:999px;background:rgba(0,0,0,.62);color:#fff;text-transform:uppercase;pointer-events:none;}',
    '.ym-gal-name{position:absolute;left:0;right:0;bottom:0;z-index:2;padding:18px 8px 6px;font-size:10.5px;color:#fff;background:linear-gradient(transparent,rgba(0,0,0,.82));overflow:hidden;text-overflow:ellipsis;white-space:nowrap;pointer-events:none;}',
    '.ym-gal-icon{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:24px;color:rgba(255,255,255,.45);}',
    '.ym-gal-busy{opacity:.55;pointer-events:none;}',
    // Контекстное меню плитки и окно свойств.
    '.ym-ctx{position:fixed;z-index:400;min-width:190px;padding:6px;border-radius:12px;display:none;',
      'background:rgba(22,24,28,.97);border:1px solid rgba(255,255,255,.1);',
      'box-shadow:0 18px 50px rgba(0,0,0,.55);font-size:13px;color:#e6e6e6;}',
    '.ym-ctx.on{display:block;}',
    '.ym-ctx-item{padding:8px 10px;border-radius:8px;cursor:pointer;white-space:nowrap;}',
    '.ym-ctx-item:hover{background:rgba(255,255,255,.08);}',
    '.ym-ctx-item.ym-danger{color:#ff7a7a;}',
    '.ym-ctx-item.ym-danger:hover{background:rgba(255,90,90,.16);}',
    '.ym-ctx-sep{height:1px;margin:5px 8px;background:rgba(255,255,255,.08);}',
    '.ym-props{position:fixed;z-index:401;inset:0;display:none;align-items:center;',
      'justify-content:center;background:rgba(0,0,0,.55);}',
    '.ym-props.on{display:flex;}',
    '.ym-props-box{width:min(430px,92vw);max-height:80vh;overflow:auto;border-radius:16px;padding:18px 20px;',
      'background:linear-gradient(180deg,rgba(26,28,33,.99),rgba(17,18,22,.99));',
      'border:1px solid rgba(255,255,255,.1);box-shadow:0 30px 90px rgba(0,0,0,.65);}',
    '.ym-props-title{font-size:15px;font-weight:600;margin-bottom:12px;white-space:nowrap;',
      'overflow:hidden;text-overflow:ellipsis;}',
    '.ym-props-row{display:flex;justify-content:space-between;gap:16px;padding:6px 0;font-size:12.5px;',
      'border-bottom:1px solid rgba(255,255,255,.06);}',
    '.ym-props-row:last-child{border-bottom:0;}',
    '.ym-props-k{color:rgba(255,255,255,.45);flex:0 0 auto;}',
    '.ym-props-v{text-align:right;word-break:break-word;}',
    '.ym-props-close{margin-top:14px;width:100%;padding:9px;border-radius:10px;border:1px solid rgba(255,255,255,.12);',
      'background:rgba(255,255,255,.06);color:#e6e6e6;cursor:pointer;font-size:13px;}',
    '.ym-props-close:hover{background:rgba(255,255,255,.12);}',
    '.ym-gal-count{color:rgba(255,255,255,.35);font-weight:400;font-size:13px;}',
    '.ym-sliders{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:2px 20px;margin-top:8px;}',
    '.ym-ctl{min-width:0;}',
    '.ym-row{display:flex;justify-content:space-between;align-items:baseline;font-size:13px;color:#d7dbe3;margin-top:8px;}',
    '.ym-row b{color:rgba(255,255,255,.45);font-weight:400;font-size:12px;}',
    '.ym-range{-webkit-appearance:none;appearance:none;width:100%;height:4px;border-radius:2px;background:#2a2f3a;outline:none;margin-top:6px;}',
    '.ym-range::-webkit-slider-thumb{-webkit-appearance:none;width:14px;height:14px;border-radius:50%;background:#fff;cursor:pointer;border:0;box-shadow:0 1px 4px rgba(0,0,0,.4);}',
    '.ym-switch-row{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,.07);cursor:pointer;font-size:12.5px;line-height:17px;color:#d7dbe3;}',
    '.ym-switch-row input{display:none;}',
    '.ym-switch{width:42px;height:24px;border-radius:12px;background:#3a3f4a;position:relative;transition:background .15s;flex:0 0 auto;}',
    '.ym-switch:after{content:"";position:absolute;top:3px;left:3px;width:18px;height:18px;border-radius:50%;background:#fff;transition:transform .15s;}',
    '.ym-switch-row input:checked + .ym-switch{background:#ffdb4d;}',
    '.ym-switch-row input:checked + .ym-switch:after{transform:translateX(18px);background:#17181c;}',
    '.ym-page-foot{display:flex;align-items:center;gap:10px;padding:10px 28px 14px;border-top:1px solid rgba(255,255,255,.06);background:rgba(10,10,12,.25);}',
    '.ym-status{margin-left:auto;font-size:12px;color:rgba(255,255,255,.45);min-height:16px;text-align:right;}',
    '.ym-close{width:36px;height:36px;border-radius:10px;background:transparent;border:0;color:rgba(255,255,255,.5);font-size:17px;cursor:pointer;flex:0 0 auto;}',
    '.ym-close:hover{background:rgba(255,255,255,.08);color:#fff;}',
    '#ym-nav-bg.ym-nav-active{color:#e6e6e6 !important;}',
    '#ym-nav-bg:hover{color:#fff;}',
    '.ym-discord .ym-urlrow{margin-top:8px;}',
    '.ym-rpc-state.ok{color:#7ee787;}',
    '.ym-rpc-state.bad{color:#ff8a8a;}'
  ].join('\n');

  var PANEL_HTML = [
    '<div class="ym-page-head">',
      '<div>',
        '<h1 class="ym-page-title">Фон</h1>',
        '<div class="ym-page-sub">Оформление приложения: картинка, GIF или видео на весь экран</div>',
      '</div>',
      '<button class="ym-close" title="Закрыть">&#10005;</button>',
    '</div>',
    '<div class="ym-page-body">',
      '<div class="ym-grid">',
        '<section class="ym-card">',
          '<div class="ym-card-label">Сейчас</div>',
          '<div class="ym-preview-box"><img class="ym-preview-img" alt=""><video class="ym-preview-video" muted loop playsinline></video></div>',
          '<div class="ym-preview-name"></div>',
          '<div class="ym-preview-hint">Фон применяется сразу, без перезапуска</div>',
        '</section>',
        '<section class="ym-card">',
          '<div class="ym-card-title">Свой фон</div>',
          '<div class="ym-drop">',
            '<div class="ym-dtitle">Перетащи картинку, GIF, видео или .zip</div>',
            '<div class="ym-dsub">или нажми, чтобы выбрать файл</div>',
            '<input type="file" accept="image/*,video/*,.zip,.html,.htm" style="display:none">',
          '</div>',
          '<div class="ym-urlrow">',
            '<input class="ym-input ym-url" placeholder="Ссылка на обои, страница или HTML-код">',
            '<button class="ym-btn ghost ym-urlgo">Вставить</button>',
          '</div>',
          '<div class="ym-hint">JPG, PNG, WEBP, GIF, AVIF, BMP · MP4, WEBM, MOV · .zip (Wallpaper Engine) · .html-обои</div>',
          '<label class="ym-switch-row"><span>Адаптивный фон — обложка играющего трека</span><input type="checkbox" class="ym-adapt"><span class="ym-switch"></span></label>',
          '<div class="ym-fitrow"><span>Масштаб</span><div class="ym-chips">',
            '<button class="ym-chip ym-fit" data-fit="smart" title="Кадр целиком, если окно сильно другой формы; иначе заполняет экран">Умно</button>',
            '<button class="ym-chip ym-fit" data-fit="cover" title="Кадр всегда заполняет окно, лишнее по краям обрезается">Заполнить</button>',
          '</div></div>',
        '</section>',
      '</div>',
      '<section class="ym-card ym-gallery-card">',
        '<div class="ym-card-head">',
          '<div class="ym-card-title">Мои фоны <span class="ym-gal-count"></span></div>',
          '<div class="ym-chips">',
            '<button class="ym-chip ym-gal-refresh">Обновить</button>',
            '<button class="ym-chip ym-folder">Открыть папку</button>',
          '</div>',
        '</div>',
        '<div class="ym-gal-empty">В папке пока нет фонов — перетащи файл выше.</div>',
        '<div class="ym-gal"></div>',
      '</section>',
      '<section class="ym-card ym-settings">',
        '<div class="ym-card-head">',
          '<div class="ym-card-title">Настройки</div>',
          '<div class="ym-chips">',
            '<button class="ym-chip ym-preset" data-dim="0.25" data-blur="0" data-bright="1" data-vig="0" data-ptrans="0.15" data-pblur="0" data-psat="1">Стандарт</button>',
            '<button class="ym-chip ym-preset" data-dim="0.35" data-blur="8" data-bright="1.05" data-vig="0.25" data-ptrans="0.30" data-pblur="12" data-psat="1.05">Мягко</button>',
            '<button class="ym-chip ym-preset" data-dim="0.5" data-blur="0" data-bright="0.95" data-vig="0.5" data-ptrans="0.20" data-pblur="0" data-psat="1">Кино</button>',
            '<button class="ym-chip ym-preset" data-dim="0.3" data-blur="18" data-bright="1.1" data-vig="0" data-ptrans="0.48" data-pblur="20" data-psat="1.15">Стекло</button>',
          '</div>',
        '</div>',
        '<div class="ym-sliders">',
          '<div class="ym-ctl"><div class="ym-row"><span>Затемнение</span><b class="ym-dimv"></b></div><input type="range" class="ym-range ym-dim" min="0" max="0.9" step="0.01"></div>',
          '<div class="ym-ctl"><div class="ym-row"><span>Размытие</span><b class="ym-blurv"></b></div><input type="range" class="ym-range ym-blur" min="0" max="40" step="1"></div>',
          '<div class="ym-ctl"><div class="ym-row"><span>Яркость</span><b class="ym-brightv"></b></div><input type="range" class="ym-range ym-bright" min="0.2" max="1.6" step="0.01"></div>',
          '<div class="ym-ctl"><div class="ym-row"><span>Виньетка</span><b class="ym-vigv"></b></div><input type="range" class="ym-range ym-vig" min="0" max="1" step="0.01"></div>',
          '<div class="ym-ctl"><div class="ym-row"><span>Затемнение меню</span><b class="ym-navv"></b></div><input type="range" class="ym-range ym-nav" min="0" max="0.8" step="0.01"></div>',
          '<div class="ym-ctl"><div class="ym-row"><span>Прозрачность плеера</span><b class="ym-ptransv"></b></div><input type="range" class="ym-range ym-ptrans" min="0" max="0.95" step="0.01"></div>',
          '<div class="ym-ctl"><div class="ym-row"><span>Размытие плеера</span><b class="ym-pblurv"></b></div><input type="range" class="ym-range ym-pblur" min="0" max="40" step="1"></div>',
          '<div class="ym-ctl"><div class="ym-row"><span>Насыщенность плеера</span><b class="ym-psatv"></b></div><input type="range" class="ym-range ym-psat" min="0.5" max="2" step="0.01"></div>',
        '</div>',
      '</section>',
      '<section class="ym-card ym-discord">',
        '<div class="ym-card-head">',
          '<div class="ym-card-title">Discord</div>',
          '<div class="ym-card-label ym-rpc-state"></div>',
        '</div>',
        '<label class="ym-switch-row"><span>Показывать трек в статусе Discord</span><input type="checkbox" class="ym-rpc"><span class="ym-switch"></span></label>',
        '<div class="ym-urlrow">',
          '<input class="ym-input ym-rpcid" maxlength="24" inputmode="numeric" placeholder="Application ID из Discord Developer Portal">',
          '<button class="ym-btn ghost ym-rpc-save">Сохранить</button>',
        '</div>',
        '<div class="ym-hint">Application ID берётся из приложения на discord.com/developers/applications. В статусе появится кнопка со ссылкой на мод.</div>',
      '</section>',
      '<section class="ym-card ym-themes">',
        '<div class="ym-card-head">',
          '<div class="ym-card-title">Обложки</div>',
          '<div class="ym-card-label ym-coverstyle-now"></div>',
        '</div>',
        '<div class="ym-swatches">' + PRESETS.map(function(p, i){
          var two = !!(p.a && p.b);
          var grad = two ? ('linear-gradient(135deg,' + p.a + ' 0%,' + p.b + ' 100%)') : '';
          return '<button class="ym-swatch' + (two ? '' : ' ym-swatch-none') + '"' +
            ' data-style="' + p.id + '" title="' + p.name + '"' +
            (grad ? ' style="background-image:' + grad + '"' : '') + '>' +
            '<span class="ym-swatch-num">' + (i + 1) + '</span>' +
            '<span class="ym-swatch-name">' + p.name + '</span>' +
            '<span class="ym-swatch-hex">' + (two ? (p.a + ' · ' + p.b) : 'без эффекта') + '</span>' +
            '</button>';
        }).join('') + '</div>',
      '</section>',
    '</div>',
    '<div class="ym-page-foot">',
      '<button class="ym-btn primary ym-apply">Применить</button>',
      '<button class="ym-btn ghost ym-reset">Сбросить</button>',
      '<div class="ym-status"></div>',
    '</div>'
  ].join('');

  function panelApi(body){
    return fetch('http://127.0.0.1:47823/apply', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'x-ymbg-token': cfg.token || ''},
      body: JSON.stringify(body)
    }).then(function(r){ return r.json(); });
  }

  var pageOpen = false;
  var pageTimer = null;

  function pageRect(){
    var main = document.querySelector('[class*="Content_main"]');
    if(!main) return null;
    var r = main.getBoundingClientRect();
    if(!r.width || !r.height) return null;
    // Нижняя граница — реальная верхняя кромка плеера, а не магическое число:
    // иначе панель наезжает на ползунок громкости и кнопки плеера.
    var bottom = window.innerHeight - 104;
    var bar = document.querySelector('[class*="PlayerBarDesktop_root"], [class*="PlayerBar_root"], [class*="PlayerBarDesktopWithBackgroundProgressBar_root"]');
    if(bar){
      var br = bar.getBoundingClientRect();
      if(br.height > 0 && br.top > r.top + 120) bottom = Math.round(br.top) - 6;
    }
    var top = Math.round(r.top);
    bottom = Math.min(bottom, window.innerHeight - 8);
    return {left: Math.round(r.left), top: top, width: Math.round(r.width), height: Math.max(200, Math.round(bottom - top))};
  }

  function positionPage(){
    var el = document.getElementById('ym-page');
    if(!el) return;
    var r = pageRect();
    if(r){
      el.style.left = r.left + 'px';
      el.style.top = r.top + 'px';
      el.style.right = 'auto';
      el.style.bottom = 'auto';
      el.style.width = r.width + 'px';
      el.style.height = r.height + 'px';
    } else {
      el.style.left = '224px';
      el.style.top = '32px';
      el.style.right = '12px';
      el.style.bottom = '104px';
      el.style.width = 'auto';
      el.style.height = 'auto';
    }
  }

  function markNavActive(on){
    navActive = !!on;
    var el = document.getElementById('ym-nav-bg');
    if(on){
      syncNavActive();
    } else {
      if(navActiveNative && navActiveNative.isConnected){
        for(var i = 0; i < navActiveExtras.length; i++) navActiveNative.classList.add(navActiveExtras[i]);
      }
      navActiveNative = null;
      navActiveExtras = [];
      applyNavClasses(el, navBase.length ? navBase : navBaseClasses(), [], false);
    }
  }

  function navGuard(e){
    var t = e.target;
    if(!t || !t.closest) return;
    if(navHost && navHost.contains(t)) return;
    var page = document.getElementById('ym-page');
    if(page && page.contains(t)) return;
    if(!t.closest('[class*="Navbar_root__"]')) return;
    closePanel();
  }

  var vibeRedirecting = false;

  function openPanel(skipVibe){
    var existing = document.getElementById('ym-page');
    if(existing){
      pageOpen = true;
      positionPage();
      markNavActive(true);
      return;
    }
    // На «Моей волне» нижнего плеера нет — уходим в «Коллекцию», чтобы он появился.
    if(!skipVibe && !vibeRedirecting && document.querySelector('[class*="VibePage_root__"]')){
      var nav = document.querySelector('[class*="Navbar_root__"]');
      var collection = nav ? (nav.querySelector('a[data-test-id="NAVBAR_NAVIGATION_ITEM_COLLECTION"]') ||
                               nav.querySelector('a[href="/collection"]')) : null;
      if(!collection && nav){
        var navLinks = nav.querySelectorAll('a[role="link"]');
        for(var ni = 0; ni < navLinks.length; ni++){
          if((navLinks[ni].textContent || '').trim() === 'Коллекция'){ collection = navLinks[ni]; break; }
        }
      }
      if(collection){
        vibeRedirecting = true;
        try{ collection.click(); }catch(e){}
        var tries = 0;
        (function waitCollection(){
          var stillVibe = !!document.querySelector('[class*="VibePage_root__"]');
          if(!stillVibe || ++tries > 20){
            vibeRedirecting = false;
            openPanel(true);
          } else {
            setTimeout(waitCollection, 150);
          }
        })();
        return;
      }
    }
    if(!document.getElementById('ym-panel-style')){
      var st = document.createElement('style');
      st.id = 'ym-panel-style';
      st.textContent = PANEL_CSS;
      document.head.appendChild(st);
    }
    var old = document.getElementById('ym-panel-backdrop');
    if(old && old.parentNode) old.parentNode.removeChild(old);

    pageOpen = true;
    document.documentElement.classList.add('ym-page-open');

    var page = document.createElement('section');
    page.id = 'ym-page';
    page.innerHTML = PANEL_HTML;
    document.body.appendChild(page);
    positionPage();
    markNavActive(true);

    var q = function(sel){ return page.querySelector(sel); };
    var drop = q('.ym-drop');
    var fileInput = q('.ym-drop input[type=file]');
    var imgEl = q('.ym-preview-img');
    var videoEl = q('.ym-preview-video');
    var nameEl = q('.ym-preview-name');
    var dsub = q('.ym-dsub');
    var urlEl = q('.ym-url');
    var dimEl = q('.ym-dim'), blurEl = q('.ym-blur'), brightEl = q('.ym-bright'), vigEl = q('.ym-vig'), navEl = q('.ym-nav');
    var ptransEl = q('.ym-ptrans'), pblurEl = q('.ym-pblur'), psatEl = q('.ym-psat');
    var dimV = q('.ym-dimv'), blurV = q('.ym-blurv'), brightV = q('.ym-brightv'), vigV = q('.ym-vigv'), navV = q('.ym-navv');
    var ptransV = q('.ym-ptransv'), pblurV = q('.ym-pblurv'), psatV = q('.ym-psatv');
    var adaptEl = q('.ym-adapt');
    var rpcEl = q('.ym-rpc');
    var rpcIdEl = q('.ym-rpcid');
    var rpcStateEl = q('.ym-rpc-state');
    var styleBtns = page.querySelectorAll('.ym-swatch');
    var coverStyle = normalizeCoverStyle(cfg.coverStyle);
    var styleNow = q('.ym-coverstyle-now');
    var fitBtns = page.querySelectorAll('.ym-fit');
    var fit = String(cfg.fit || '') === 'cover' ? 'cover' : 'smart';
    var statusEl = q('.ym-status');
    var pushTimer = null;
    var galEl = q('.ym-gal');
    var galEmpty = q('.ym-gal-empty');
    var galCount = q('.ym-gal-count');
    var galObserver = null;
    var galSeq = 0;
    var openItem = String(cfg.file || '');

    function markFit(){
      for(var i = 0; i < fitBtns.length; i++){
        fitBtns[i].classList.toggle('on', fitBtns[i].getAttribute('data-fit') === fit);
      }
    }

    function markStyle(){
      for(var i = 0; i < styleBtns.length; i++){
        styleBtns[i].classList.toggle('on', styleBtns[i].getAttribute('data-style') === coverStyle);
      }
      var cur = presetById(coverStyle);
      if(styleNow) styleNow.textContent = cur ? cur.name : '';
    }

    function status(text, bad){
      statusEl.textContent = text || '';
      statusEl.style.color = bad ? '#ff8a8a' : 'rgba(255,255,255,.45)';
    }
    var rpcPoll = null;
    function refreshRpc(){
      try{
        fetch('http://127.0.0.1:47823/rpc', {headers: {'x-ymbg-token': cfg.token || ''}})
          .then(function(r){ return r.json(); })
          .then(function(r){
            if(!rpcStateEl) return;
            var s = r && r.status ? r.status : 'off';
            var map = {off: 'выключено', 'no-id': 'нужен Application ID',
                       'no-discord': 'Discord не запущен', connecting: 'подключаюсь…',
                       ok: 'подключено', error: 'ошибка'};
            rpcStateEl.textContent = map[s] || s;
            rpcStateEl.className = 'ym-card-label ym-rpc-state' +
              (s === 'ok' ? ' ok' : (s === 'error' ? ' bad' : ''));
            if(s === 'error' && r && r.error) rpcStateEl.title = r.error;
            else rpcStateEl.removeAttribute('title');
          }).catch(function(){});
      }catch(e){}
    }
    function fill(el){
      var min = Number(el.min) || 0, max = Number(el.max) || 1;
      var p = (Number(el.value) - min) / (max - min) * 100;
      el.style.background = 'linear-gradient(90deg,#ffdb4d 0%,#ffdb4d ' + p + '%,#2a2f3a ' + p + '%,#2a2f3a 100%)';
    }
    function labels(){
      dimV.textContent = Number(dimEl.value).toFixed(2);
      blurV.textContent = Math.round(Number(blurEl.value)) + ' px';
      brightV.textContent = Number(brightEl.value).toFixed(2);
      vigV.textContent = Number(vigEl.value).toFixed(2);
      navV.textContent = Number(navEl.value).toFixed(2);
      ptransV.textContent = Number(ptransEl.value).toFixed(2);
      pblurV.textContent = Math.round(Number(pblurEl.value)) + ' px';
      psatV.textContent = Number(psatEl.value).toFixed(2);
      fill(dimEl); fill(blurEl); fill(brightEl); fill(vigEl); fill(navEl);
      fill(ptransEl); fill(pblurEl); fill(psatEl);
    }
    function currentCfg(){
      return {
        dim: Number(dimEl.value),
        blur: Number(blurEl.value),
        brightness: Number(brightEl.value),
        vignette: Number(vigEl.value),
        navbarDim: Number(navEl.value),
        playerTransparency: Number(ptransEl.value),
        playerBlur: Number(pblurEl.value),
        playerSaturate: Number(psatEl.value),
        fit: fit,
        adaptive: !!adaptEl.checked,
        coverStyle: coverStyle,
        discordRpc: !!rpcEl.checked,
        discordClientId: String(rpcIdEl.value || '').replace(/[^0-9]/g, '').slice(0, 20)
      };
    }
    function push(delay){
      var body = currentCfg();
      updateAll(body);
      if(pushTimer) clearTimeout(pushTimer);
      pushTimer = setTimeout(function(){
        panelApi(body).catch(function(){});
      }, delay || 0);
    }
    function showPreview(src, isVideo){
      imgEl.style.display = 'none';
      videoEl.style.display = 'none';
      if(!src) return;
      if(isVideo){
        videoEl.src = src;
        videoEl.style.display = 'block';
        try{ var p = videoEl.play(); if(p && p.catch) p.catch(function(){}); }catch(e){}
      } else {
        imgEl.src = src;
        imgEl.style.display = 'block';
      }
    }

    function uploadTo(path, file, onDone){
      var xhr = new XMLHttpRequest();
      xhr.open('POST', 'http://127.0.0.1:47823' + path, true);
      xhr.setRequestHeader('x-ymbg-token', cfg.token || '');
      xhr.setRequestHeader('x-ymbg-name', encodeURIComponent(file.name || 'file'));
      xhr.upload.onprogress = function(e){
        if(e.lengthComputable) status('Загрузка ' + Math.round(e.loaded / e.total * 100) + '%…');
      };
      xhr.onload = function(){
        var r = {};
        try{ r = JSON.parse(xhr.responseText || '{}'); }catch(e){}
        if(xhr.status === 200 && r.ok) onDone(r);
        else status('Ошибка: ' + ((r && r.error) || ('HTTP ' + xhr.status)), true);
      };
      xhr.onerror = function(){ status('Музыка не отвечает', true); };
      status('Отправляю…');
      xhr.send(file);
    }

    function fmtSize(b){
      b = Number(b) || 0;
      return b >= 1048576 ? (b / 1048576).toFixed(1) + ' МБ' : Math.max(1, Math.round(b / 1024)) + ' КБ';
    }

    function afterWallpaper(r){
      adaptEl.checked = false;
      loadLibrary();
      if(r.kind === 'web'){
        imgEl.style.display = 'none';
        videoEl.style.display = 'none';
        nameEl.textContent = 'HTML-обои';
        dsub.textContent = r.note || 'Веб-обои';
        status(r.note || 'Готово: веб-обои');
        return;
      }
      nameEl.textContent = r.file || 'Фон';
      dsub.textContent = r.note || fmtSize(r.bytes);
      status(r.note || ('Готово: ' + (r.file || '')));
      setTimeout(function(){ showPreview(cfg.src, cfg.isVideo); }, 500);
    }

    function takeFile(f){
      var name = f.name || 'file';
      var ext = ('.' + name.split('.').pop()).toLowerCase();
      if(ext === '.zip' || ext === '.html' || ext === '.htm'){
        status(ext === '.zip' ? 'Разбираю архив…' : 'Ставлю HTML-обои…');
        uploadTo('/wallpaper', f, afterWallpaper);
        return;
      }
      var okExt = ['.jpg','.jpeg','.png','.webp','.gif','.avif','.bmp','.mp4','.webm','.mov','.m4v','.ogv'];
      if(okExt.indexOf(ext) === -1){ status('Формат не поддерживается: ' + ext, true); return; }
      if(f.size > 2 * 1024 * 1024 * 1024){ status('Файл больше 2 ГБ', true); return; }
      var isVideo = ['.mp4','.webm','.mov','.m4v','.ogv'].indexOf(ext) !== -1;
      uploadTo('/upload', f, function(r){
        nameEl.textContent = r.file;
        dsub.textContent = fmtSize(r.bytes) + ' · ' + ext.slice(1).toUpperCase();
        status('Готово: ' + r.file + ' (' + fmtSize(r.bytes) + ')');
        loadLibrary();
        setTimeout(function(){ showPreview(cfg.src, isVideo); }, 500);
      });
    }

    function applyUrl(){
      var raw = urlEl.value.trim();
      if(!raw){ status('Вставь ссылку или HTML-код', true); return; }
      status('Разбираю…');
      // Ссылка задаёт конкретный фон: адаптивный режим выключаем сразу,
      // иначе после загрузки фоном останется обложка трека, а не новый файл.
      adaptEl.checked = false;
      updateAll({adaptive:false});
      var body = currentCfg();
      body.url = raw;
      panelApi(body).then(function(r){
        if(r && r.ok){
          if(r.kind === 'web'){
            imgEl.style.display = 'none';
            videoEl.style.display = 'none';
            nameEl.textContent = 'HTML-обои';
            dsub.textContent = r.note || 'Веб-обои';
            status(r.note || 'Готово: веб-обои');
          } else {
            nameEl.textContent = r.file || 'Фон';
            dsub.textContent = r.note || 'Скачано по ссылке';
            status(r.note || ('Готово: ' + (r.file || '')));
            setTimeout(function(){ showPreview(cfg.src, r.isVideo); }, 600);
          }
        } else {
          status('Ошибка: ' + ((r && r.error) || 'неизвестно'), true);
        }
      }).catch(function(){ status('Музыка не отвечает', true); });
    }

    // ---------- галерея «Мои фоны» ----------
    function mediaUrl(file){
      return 'http://127.0.0.1:47823/media?t=' + encodeURIComponent(cfg.token || '') +
             '&f=' + encodeURIComponent(file);
    }
    function thumbUrl(file){
      return 'http://127.0.0.1:47823/thumb?t=' + encodeURIComponent(cfg.token || '') +
             '&f=' + encodeURIComponent(file);
    }
    function galIcon(tile, text){
      var ic = document.createElement('div');
      ic.className = 'ym-gal-icon';
      ic.textContent = text || '?';
      tile.appendChild(ic);
    }
    function setActiveTile(name){
      openItem = String(name || '');
      var tiles = galEl.querySelectorAll('.ym-gal-tile');
      for(var i = 0; i < tiles.length; i++){
        tiles[i].classList.toggle('on', tiles[i].getAttribute('data-name') === openItem);
      }
    }
    function useItem(it){
      status('Применяю: ' + it.name + '…');
      galEl.classList.add('ym-gal-busy');
      fetch('http://127.0.0.1:47823/use', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'x-ymbg-token': cfg.token || ''},
        body: JSON.stringify({f: it.name})
      })
        .then(function(r){ return r.json(); })
        .then(function(r){
          galEl.classList.remove('ym-gal-busy');
          if(!r || !r.ok){ status('Ошибка: ' + ((r && r.error) || 'неизвестно'), true); return; }
          adaptEl.checked = false;
          if(r.kind === 'web'){
            imgEl.style.display = 'none';
            videoEl.style.display = 'none';
            nameEl.textContent = 'HTML-обои';
            dsub.textContent = r.note || it.name;
          } else if(r.file){
            nameEl.textContent = r.file;
            dsub.textContent = r.note || fmtSize(it.size);
          }
          setActiveTile(it.name);
          status('Готово: ' + (r.note || it.name));
          loadLibrary();
        })
        .catch(function(){
          galEl.classList.remove('ym-gal-busy');
          status('Музыка не отвечает', true);
        });
    }
    function makeTile(it){
      var tile = document.createElement('div');
      tile.className = 'ym-gal-tile' + (it.active ? ' on' : '');
      tile.setAttribute('data-name', it.name);
      tile.title = it.name + (it.size ? ' · ' + fmtSize(it.size) : '');
      var badge = document.createElement('div');
      badge.className = 'ym-gal-badge';
      badge.textContent = it.kind === 'video' ? 'Видео' :
                          it.kind === 'archive' ? 'ZIP' :
                          it.kind === 'html' ? 'HTML' : 'Фото';
      tile.appendChild(badge);
      var media = null;
      if(it.kind === 'video'){
        media = document.createElement('video');
        media.className = 'ym-gal-thumb';
        media.muted = true; media.loop = true; media.playsInline = true;
        media.preload = 'metadata';
        media.setAttribute('muted', '');
        media.setAttribute('playsinline', '');
        media.addEventListener('mouseenter', function(){ try{ var p = media.play(); if(p && p.catch) p.catch(function(){}); }catch(e){} });
        media.addEventListener('mouseleave', function(){ try{ media.pause(); }catch(e){} });
        tile.appendChild(media);
      } else if(it.kind === 'image' || it.kind === 'archive'){
        media = document.createElement('img');
        media.className = 'ym-gal-thumb';
        media.alt = '';
        media.loading = 'lazy';
        media.decoding = 'async';
        media.addEventListener('error', function(){
          if(!media) return;
          if(media.getAttribute('data-full') === '1'){
            if(media.parentNode) media.parentNode.removeChild(media);
            galIcon(tile, '?');
            return;
          }
          media.setAttribute('data-full', '1');
          media.src = mediaUrl(it.name);
        });
        media.src = thumbUrl(it.name);
        tile.appendChild(media);
      } else {
        galIcon(tile, 'HTML');
      }
      var label = document.createElement('div');
      label.className = 'ym-gal-name';
      label.textContent = it.name;
      tile.appendChild(label);
      tile.addEventListener('click', function(){ useItem(it); });
      tile.addEventListener('contextmenu', function(ev){
        ev.preventDefault();
        ev.stopPropagation();
        openCtxMenu(ev.clientX, ev.clientY, it);
      });
      if(media && it.kind === 'video'){
        if(galObserver) galObserver.observe(tile);
        else media.src = mediaUrl(it.name) + '#t=0.2';
      }
      return tile;
    }
    function renderLibrary(items){
      items = Array.isArray(items) ? items : [];
      if(galObserver){ try{ galObserver.disconnect(); }catch(e){} galObserver = null; }
      galEl.textContent = '';
      galEmpty.style.display = items.length ? 'none' : 'block';
      galCount.textContent = items.length ? '· ' + items.length : '';
      try{
        galObserver = new IntersectionObserver(function(entries){
          for(var i = 0; i < entries.length; i++){
            if(!entries[i].isIntersecting) continue;
            var tile = entries[i].target;
            var v = tile.querySelector('video');
            if(v && !v.src) v.src = mediaUrl(tile.getAttribute('data-name')) + '#t=0.2';
            galObserver.unobserve(tile);
          }
        }, {root: q('.ym-page-body'), threshold: 0.15});
      }catch(e){ galObserver = null; }
      for(var i = 0; i < items.length; i++) galEl.appendChild(makeTile(items[i]));
    }
    // ---------- контекстное меню и свойства ----------
    var ctxEl = null;
    function ctxNode(tag, cls, text){
      var el = document.createElement(tag);
      if(cls) el.className = cls;
      if(text !== undefined) el.textContent = text;
      return el;
    }
    function closeCtxMenu(){
      dropCtxListeners();
      if(ctxEl && ctxEl.parentNode) ctxEl.parentNode.removeChild(ctxEl);
      ctxEl = null;
    }
    function openCtxMenu(x, y, it){
      closeCtxMenu();
      var menu = ctxNode('div', 'ym-ctx on');
      if(it.kind === 'archive' || it.kind === 'html'){
        var openZip = ctxNode('div', 'ym-ctx-item', it.kind === 'html' ? 'Открыть файл' : 'Открыть архив');
        openZip.addEventListener('click', function(){ closeCtxMenu(); openEntry(it, 'file'); });
        menu.appendChild(openZip);
      }
      var showIn = ctxNode('div', 'ym-ctx-item', 'Показать в проводнике');
      showIn.addEventListener('click', function(){ closeCtxMenu(); openEntry(it, 'folder'); });
      menu.appendChild(showIn);
      menu.appendChild(ctxNode('div', 'ym-ctx-sep'));
      var props = ctxNode('div', 'ym-ctx-item', 'Свойства');
      props.addEventListener('click', function(){ closeCtxMenu(); showProps(it); });
      menu.appendChild(props);
      menu.appendChild(ctxNode('div', 'ym-ctx-sep'));
      var del = ctxNode('div', 'ym-ctx-item ym-danger', 'Удалить');
      del.addEventListener('click', function(){ closeCtxMenu(); removeItem(it); });
      menu.appendChild(del);
      document.body.appendChild(menu);
      var w = menu.offsetWidth || 190;
      var h = menu.offsetHeight || 80;
      menu.style.left = Math.max(8, Math.min(x, window.innerWidth - w - 8)) + 'px';
      menu.style.top = Math.max(8, Math.min(y, window.innerHeight - h - 8)) + 'px';
      ctxEl = menu;
      setTimeout(function(){
        window.addEventListener('mousedown', onCtxOutside, true);
        window.addEventListener('keydown', onCtxEsc, true);
      }, 0);
    }
    function onCtxOutside(ev){
      if(ctxEl && ev.target && ctxEl.contains(ev.target)) return;
      closeCtxMenu();
    }
    function onCtxEsc(ev){
      if(ev.key === 'Escape') closeCtxMenu();
    }
    function dropCtxListeners(){
      window.removeEventListener('mousedown', onCtxOutside, true);
      window.removeEventListener('keydown', onCtxEsc, true);
    }
    function fmtTime(sec){
      sec = Number(sec) || 0;
      if(!sec) return '';
      var m = Math.floor(sec / 60), s = Math.round(sec % 60);
      if(s === 60){ m += 1; s = 0; }
      return m + ':' + (s < 10 ? '0' : '') + s;
    }
    function propRow(box, k, v){
      if(v === undefined || v === null || v === '') return;
      var row = ctxNode('div', 'ym-props-row');
      row.appendChild(ctxNode('div', 'ym-props-k', k));
      row.appendChild(ctxNode('div', 'ym-props-v', String(v)));
      box.appendChild(row);
    }
    function showProps(it){
      var box = ctxNode('div', 'ym-props on');
      var card = ctxNode('div', 'ym-props-box');
      card.appendChild(ctxNode('div', 'ym-props-title', it.name));
      var body = ctxNode('div', 'ym-props-body', 'Загружаю…');
      card.appendChild(body);
      var close = ctxNode('button', 'ym-props-close', 'Закрыть');
      close.addEventListener('click', function(){ if(box.parentNode) box.parentNode.removeChild(box); });
      card.appendChild(close);
      box.appendChild(card);
      box.addEventListener('mousedown', function(ev){ if(ev.target === box) box.parentNode.removeChild(box); });
      document.body.appendChild(box);

      fetch('http://127.0.0.1:47823/info?t=' + encodeURIComponent(cfg.token || '') +
            '&f=' + encodeURIComponent(it.name))
        .then(function(r){ return r.json(); })
        .then(function(r){
          body.textContent = '';
          if(!r || !r.ok){ body.textContent = 'Не удалось прочитать файл'; return; }
          var kindName = r.kind === 'video' ? 'Видео' :
                         r.kind === 'image' ? 'Картинка' :
                         r.kind === 'archive' ? 'Архив обоев' : 'HTML-обои';
          propRow(body, 'Тип', kindName);
          propRow(body, 'Формат', (r.ext || '').replace('.', '').toUpperCase());
          propRow(body, 'Размер', fmtSize(r.size));
          if(r.width && r.height) propRow(body, 'Разрешение', r.width + ' × ' + r.height);
          if(r.megapixels) propRow(body, 'Мегапиксели', r.megapixels.toFixed(1));
          if(r.aspect) propRow(body, 'Соотношение', r.aspect);
          if(r.fps) propRow(body, 'Кадры/с', r.fps.toFixed(2) + ' fps');
          if(r.duration) propRow(body, 'Длительность', fmtTime(r.duration));
          if(r.codec) propRow(body, 'Кодек', r.codec);
          if(r.bitrate) propRow(body, 'Битрейт', (r.bitrate / 1000000).toFixed(2) + ' Мбит/с');
          if(r.frames) propRow(body, 'Кадров', r.frames);
          if(r.entries) propRow(body, 'Файлов в архиве', r.entries);
          if(r.type) propRow(body, 'Тип сцены', r.type);
          if(r.preview) propRow(body, 'Превью', r.preview);
          if(r.texture) propRow(body, 'Текстура сцены', r.texture);
          if(r.mtime) propRow(body, 'Изменён', new Date(r.mtime).toLocaleString());
          propRow(body, 'Папка', r.dir === 'archives' ? 'Архивы' : 'Фоны');
          propRow(body, 'Файл', r.name);
        })
        .catch(function(){ body.textContent = 'Музыка не отвечает'; });
    }
    function openEntry(it, mode){
      fetch('http://127.0.0.1:47823/open', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'x-ymbg-token': cfg.token || ''},
        body: JSON.stringify({f: it.name, mode: mode === 'folder' ? 'folder' : 'file'})
      })
        .then(function(r){ return r.json(); })
        .then(function(r){
          if(!r || !r.ok) status('Не удалось открыть: ' + ((r && r.error) || 'неизвестно'), true);
        })
        .catch(function(){ status('Музыка не отвечает', true); });
    }

    function removeItem(it){
      if(!confirm('Удалить «' + it.name + '»?')) return;
      status('Удаляю: ' + it.name + '…');
      fetch('http://127.0.0.1:47823/remove', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'x-ymbg-token': cfg.token || ''},
        body: JSON.stringify({f: it.name})
      })
        .then(function(r){ return r.json(); })
        .then(function(r){
          if(!r || !r.ok){ status('Ошибка: ' + ((r && r.error) || 'неизвестно'), true); return; }
          status('Удалено: ' + it.name);
          loadLibrary();
        })
        .catch(function(){ status('Музыка не отвечает', true); });
    }

    function loadLibrary(notify){
      var seq = ++galSeq;
      galEl.classList.add('ym-gal-busy');
      fetch('http://127.0.0.1:47823/library', {
        headers: {'x-ymbg-token': cfg.token || ''}
      })
        .then(function(r){ return r.json(); })
        .then(function(r){
          if(seq !== galSeq) return;
          galEl.classList.remove('ym-gal-busy');
          if(!r || !r.ok){ status('Не удалось прочитать папку', true); return; }
          renderLibrary(r.items || []);
          if(notify) status('Список обновлён');
        })
        .catch(function(){
          if(seq !== galSeq) return;
          galEl.classList.remove('ym-gal-busy');
          status('Музыка не отвечает', true);
        });
    }
    function openFolder(){
      status('Открываю папку…');
      fetch('http://127.0.0.1:47823/folder', {
        method: 'GET',
        headers: {'x-ymbg-token': cfg.token || ''}
      })
        .then(function(r){ return r.json(); })
        .then(function(r){
          if(r && r.ok) status('Папка открыта');
          else status('Не удалось открыть папку', true);
        })
        .catch(function(){ status('Не удалось открыть папку', true); });
    }
    function onBgUpdate(e){
      var d = e && e.detail ? e.detail : {};
      if(d.fit){
        fit = String(d.fit);
        markFit();
      }
      if(d.file && d.src){
        nameEl.textContent = d.file;
        showPreview(d.src, !!d.isVideo);
      } else if(d.web){
        imgEl.style.display = 'none';
        videoEl.style.display = 'none';
        nameEl.textContent = 'HTML-обои';
        dsub.textContent = /^https?:\/\//i.test(d.web) ? 'Веб-обои по ссылке' : 'Веб-обои из .zip';
      }
    }

    dimEl.value = cfg.dim; blurEl.value = cfg.blur; brightEl.value = cfg.brightness;
    vigEl.value = (cfg.vignette === undefined ? 0 : cfg.vignette);
    navEl.value = (cfg.navbarDim === undefined ? 0.35 : cfg.navbarDim);
    ptransEl.value = (cfg.playerTransparency === undefined ? 0.48 : cfg.playerTransparency);
    pblurEl.value = (cfg.playerBlur === undefined ? 20 : cfg.playerBlur);
    psatEl.value = (cfg.playerSaturate === undefined ? 1.15 : cfg.playerSaturate);
    adaptEl.checked = !!cfg.adaptive;
    rpcEl.checked = !!cfg.discordRpc;
    rpcIdEl.value = String(cfg.discordClientId || '');
    markStyle();
    if(cfg.web){
      nameEl.textContent = 'HTML-обои';
      dsub.textContent = /^https?:\/\//i.test(cfg.web) ? 'Веб-обои по ссылке' : 'Веб-обои из .zip';
      imgEl.style.display = 'none';
      videoEl.style.display = 'none';
    } else {
      if(cfg.file) nameEl.textContent = cfg.file;
      if(cfg.src) showPreview(cfg.src, cfg.isVideo);
    }
    labels();
    markFit();
    loadLibrary();
    window.addEventListener('ymbg:update', onBgUpdate);

    page.addEventListener('click', function(e){
      var chip = e.target && e.target.closest ? e.target.closest('.ym-preset') : null;
      if(!chip) return;
      dimEl.value = chip.getAttribute('data-dim');
      blurEl.value = chip.getAttribute('data-blur');
      brightEl.value = chip.getAttribute('data-bright');
      vigEl.value = chip.getAttribute('data-vig');
      if(chip.hasAttribute('data-ptrans')) ptransEl.value = chip.getAttribute('data-ptrans');
      if(chip.hasAttribute('data-pblur')) pblurEl.value = chip.getAttribute('data-pblur');
      if(chip.hasAttribute('data-psat')) psatEl.value = chip.getAttribute('data-psat');
      labels();
      push(0);
      status('Пресет: ' + (chip.textContent || '').trim());
    });
    for(var fi = 0; fi < fitBtns.length; fi++){
      fitBtns[fi].addEventListener('click', function(){
        fit = this.getAttribute('data-fit') || 'smart';
        markFit();
        push(0);
        status('Масштаб: ' + (this.textContent || '').trim());
      });
    }
    q('.ym-close').addEventListener('click', closePanel);
    drop.addEventListener('click', function(){ fileInput.click(); });
    drop.addEventListener('dragover', function(e){ e.preventDefault(); drop.classList.add('over'); });
    drop.addEventListener('dragleave', function(){ drop.classList.remove('over'); });
    drop.addEventListener('drop', function(e){
      e.preventDefault();
      drop.classList.remove('over');
      if(e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) takeFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', function(){
      if(fileInput.files && fileInput.files[0]) takeFile(fileInput.files[0]);
    });
    urlEl.addEventListener('keydown', function(e){ if(e.key === 'Enter') applyUrl(); });
    q('.ym-urlgo').addEventListener('click', applyUrl);
    var folderBtns = page.querySelectorAll('.ym-folder');
    for(var fb = 0; fb < folderBtns.length; fb++){
      folderBtns[fb].addEventListener('click', openFolder);
    }
    q('.ym-gal-refresh').addEventListener('click', function(){
      status('Обновляю список…');
      loadLibrary(true);
    });
    [dimEl, blurEl, brightEl, vigEl, navEl, ptransEl, pblurEl, psatEl].forEach(function(el){
      el.addEventListener('input', function(){ labels(); push(400); });
    });
    adaptEl.addEventListener('change', function(){ push(0); });
    rpcEl.addEventListener('change', function(){
      if(rpcEl.checked && !String(rpcIdEl.value || '').trim()){
        status('Сначала вставь Application ID', true);
      }
      push(0);
      refreshRpc();
    });
    q('.ym-rpc-save').addEventListener('click', function(){
      if(!String(rpcIdEl.value || '').trim()){
        status('Вставь Application ID из Discord Developer Portal', true);
        return;
      }
      push(0);
      status('Discord: сохранено');
      refreshRpc();
    });
    rpcIdEl.addEventListener('keydown', function(e){
      if(e.key === 'Enter'){ q('.ym-rpc-save').click(); }
    });
    for(var si = 0; si < styleBtns.length; si++){
      styleBtns[si].addEventListener('click', function(){
        coverStyle = normalizeCoverStyle(this.getAttribute('data-style'));
        markStyle();
        push(0);
        var cur = presetById(coverStyle);
        status('Обложки: ' + (cur ? cur.name : coverStyle));
      });
    }
    q('.ym-apply').addEventListener('click', function(){ push(0); status('Применено'); });
    q('.ym-reset').addEventListener('click', function(){
      dimEl.value = 0.25; blurEl.value = 0; brightEl.value = 1; vigEl.value = 0; navEl.value = 0.35;
      ptransEl.value = 0.48; pblurEl.value = 20; psatEl.value = 1.15;
      adaptEl.checked = false;
      coverStyle = 'mono';
      markStyle();
      fit = 'smart';
      markFit();
      labels();
      push(0);
      status('Сброшено');
    });

    refreshRpc();
    rpcPoll = setInterval(refreshRpc, 2500);

    document.addEventListener('keydown', panelEsc);
    document.addEventListener('click', navGuard, true);
    window.addEventListener('resize', positionPage);
    page.__ymCleanup = function(){
      window.removeEventListener('ymbg:update', onBgUpdate);
      if(rpcPoll){ clearInterval(rpcPoll); rpcPoll = null; }
      if(galObserver){ try{ galObserver.disconnect(); }catch(e){} galObserver = null; }
    };
    if(pageTimer) clearInterval(pageTimer);
    pageTimer = setInterval(function(){
      if(!document.getElementById('ym-page')){
        if(pageOpen){ pageOpen = false; openPanel(); }
      } else {
        positionPage();
      }
    }, 500);
  }

  function panelEsc(e){
    if(e.key === 'Escape') closePanel();
  }

  function closePanel(){
    var el = document.getElementById('ym-page');
    if(el && el.__ymCleanup){ try{ el.__ymCleanup(); }catch(e){} }
    if(el && el.parentNode) el.parentNode.removeChild(el);
    pageOpen = false;
    document.documentElement.classList.remove('ym-page-open');
    markNavActive(false);
    document.removeEventListener('keydown', panelEsc);
    document.removeEventListener('click', navGuard, true);
    window.removeEventListener('resize', positionPage);
    if(pageTimer){ clearInterval(pageTimer); pageTimer = null; }
  }

  window.__ymBgOpenPanel = openPanel;

  var lastCover = null;
  function tick(){
    if(!cfg.adaptive) return;
    var u = coverUrl();
    if(u){
      if(u !== lastCover){ lastCover = u; apply(u, false, false); }
      return;
    }
    // Ничего не играет — оставляем пользовательский фон вместо пустого экрана.
    lastCover = null;
    var wu = webSrc();
    if(wu){
      if(currentUrl !== wu) apply(wu, false, true);
    } else if(cfg.src && currentUrl !== cfg.src){
      apply(cfg.src, cfg.isVideo, false);
    }
  }

  var adaptTimer = null;
  var adaptObserver = null;
  function setAdaptiveWatchers(on){
    if(on){
      if(!adaptTimer) adaptTimer = setInterval(tick, cfg.poll || 1500);
      if(!adaptObserver){
        try{
          adaptObserver = new MutationObserver(schedule);
          adaptObserver.observe(document.body, {
            childList: true, subtree: true, attributes: true, attributeFilter: ['src', 'srcset']
          });
        }catch(e){ adaptObserver = null; }
      }
    } else {
      if(adaptTimer){ clearInterval(adaptTimer); adaptTimer = null; }
      if(adaptObserver){ try{ adaptObserver.disconnect(); }catch(e){} adaptObserver = null; }
    }
  }

  var scheduled = false;
  function schedule(){
    if(scheduled) return;
    scheduled = true;
    setTimeout(function(){ scheduled = false; tick(); }, 150);
  }

  // Discord: renderer присылает текущий трек главному процессу, а тот
  // общается с Discord по именованному каналу. Так не нужен ни Python,
  // ни отдельная программа.
  var rpcTimer = null;
  var rpcLastKey = '';
  var rpcLastAt = 0;
  function rpcSend(obj){
    try{
      fetch('http://127.0.0.1:47823/rpc', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'x-ymbg-token': cfg.token || ''},
        body: JSON.stringify(obj)
      }).catch(function(){});
    }catch(e){}
  }
  function rpcSnapshot(){
    var md = null;
    try{ md = navigator.mediaSession && navigator.mediaSession.metadata; }catch(e){}
    var title = md && md.title ? String(md.title) : '';
    var artist = md && md.artist ? String(md.artist) : '';
    var album = md && md.album ? String(md.album) : '';
    var cover = '';
    try{
      if(md && md.artwork && md.artwork.length){
        cover = String(md.artwork[md.artwork.length - 1].src || '');
      }
    }catch(e){}
    if(!cover) cover = coverUrl() || '';
    if(cover) cover = hiRes(cover);
    var playing = false;
    try{ playing = !!(navigator.mediaSession && navigator.mediaSession.playbackState === 'playing'); }catch(e){}
    if(!title){
      var bar = document.querySelector('[class*="PlayerBarDesktop_root"], [class*="PlayerBar_root"], [class*="VibePlayerBar_root"]');
      if(bar){
        var lines = String(bar.innerText || '').split('\n').map(function(v){ return v.trim(); }).filter(Boolean);
        if(lines.length){
          title = lines[0] || '';
          for(var i = 1; i < lines.length && !artist; i++){
            if(!/^\d+:\d+/.test(lines[i])) artist = lines[i];
          }
        }
      }
    }
    var pos = 0, dur = 0;
    // 1) Настоящие значения из mediaSession.setPositionState.
    try{
      var ps = window.__ymBgPos;
      if(ps && isFinite(ps.duration) && ps.duration > 0){
        dur = ps.duration;
        pos = ps.position || 0;
        if(playing && isFinite(ps.rate)) pos += (Date.now() - ps.at) / 1000 * ps.rate;
        if(pos < 0) pos = 0;
        if(pos > dur) pos = dur;
      }
    }catch(e){}
    // 2) Текст плеера вида «1:23 / 4:56» — если позиции ещё нет.
    if(!dur){
      try{
        var barEl = document.querySelector('[class*="PlayerBarDesktop_root"], [class*="PlayerBar_root"], [class*="PlayerBarDesktop"]');
        var text = barEl ? String(barEl.innerText || '') : '';
        var times = [];
        var re = /(\d{1,2}):(\d{2})/g, mm;
        while((mm = re.exec(text))) times.push(Number(mm[1]) * 60 + Number(mm[2]));
        if(times.length >= 2){
          dur = times[times.length - 1];
          pos = times[times.length - 2];
        }
      }catch(e){}
    }
    // 3) <audio>/<video> — запасной вариант.
    if(!dur){
      try{
        var media = document.querySelectorAll('audio, video');
        for(var j = 0; j < media.length; j++){
          var a = media[j];
          if(!a || !isFinite(a.duration) || a.duration <= 0) continue;
          if(!a.paused) playing = true;
          if(!a.paused || a.currentTime > 0){
            pos = Number(a.currentTime) || 0;
            dur = Number(a.duration) || 0;
            break;
          }
        }
      }catch(e){}
    }
    return {title: title, artist: artist, album: album, cover: cover,
            playing: playing, pos: pos, dur: dur};
  }
  function rpcTick(){
    if(!cfg.discordRpc) return;
    var s = rpcSnapshot();
    // Пауза, смена трека, перемотка раз в 10 секунд — этого хватает.
    var key = [s.title, s.artist, s.album, s.cover, s.playing ? 1 : 0,
               Math.round(s.dur), Math.round(s.pos / 10)].join('\u0001');
    var now = Date.now();
    // Раз в 25 секунд повторяем, чтобы статус не считался устаревшим на паузе.
    if(key === rpcLastKey && now - rpcLastAt < 25000) return;
    rpcLastKey = key;
    rpcLastAt = now;
    rpcSend(s);
  }
  function setRpcWatchers(on){
    if(on){
      if(!rpcTimer) rpcTimer = setInterval(rpcTick, 2500);
      rpcTick();
    } else {
      if(rpcTimer){ clearInterval(rpcTimer); rpcTimer = null; }
      rpcLastKey = '';
    }
  }

  function boot(){
    ensureStyle();
    ensureRoot();
    ensureNav();
    setInterval(ensureNav, 400);
    var wu = webSrc();
    if(cfg.adaptive){
      var c = coverUrl();
      if(c){ lastCover = c; apply(c, false, false); }
      else if(wu){ apply(wu, false, true); }
      else if(cfg.src){ apply(cfg.src, cfg.isVideo, false); }
    } else if(wu){
      apply(wu, false, true);
    } else if(cfg.src){
      apply(cfg.src, cfg.isVideo, false);
    }

    if(cfg.adaptive){
      setAdaptiveWatchers(true);
    }
    setRpcWatchers(!!cfg.discordRpc);

    // Страховка: если приложение пересоздало body — возвращаем слой.
    setInterval(function(){
      if(!document.getElementById('ym-bg')){
        currentUrl = null;
        lastCover = null;
        ensureStyle();
        ensureRoot();
        if(cfg.adaptive) tick();
        else if(webSrc()) apply(webSrc(), false, true);
        else if(cfg.src) apply(cfg.src, cfg.isVideo, false);
      }
    }, 3000);
  }

  if(document.body) boot();
  else document.addEventListener('DOMContentLoaded', boot);
})();
"""

# Палитра и список id подставляются в движок и в Node-часть патча.
ENGINE = ENGINE.replace("__PRESETS__", PRESETS_JSON)

INJECT_FUNC = r"""
function __ymBgUserDir(){
  return require('electron').app.getPath('userData');
}

// Папка с обоями пользователя: только фоны, без служебных файлов.
function __ymBgWallDir(){
  const path = require('node:path');
  return path.join(__ymBgUserDir(), 'wallpapers');
}

// Служебные файлы мода: настройки, CSS, кэш превью и распакованных архивов.
function __ymBgCacheDir(){
  const path = require('node:path');
  return path.join(process.env.LOCALAPPDATA || __ymBgUserDir(), 'YandexMusic-bg');
}

function __ymBgReadText(){
  const fs = require('node:fs');
  for(let i = 0; i < arguments.length; i++){
    const p = arguments[i];
    if(!p) continue;
    try{ return fs.readFileSync(p, 'utf8') || ''; }catch(e){}
  }
  return '';
}

function __ymBgToken(){
  // Токен живёт только в памяти процесса. На диск он не попадает.
  if(!global.__ymBgToken){
    try{
      global.__ymBgToken = require('node:crypto').randomBytes(32).toString('hex');
    }catch(e){
      global.__ymBgToken = '';
    }
  }
  return global.__ymBgToken;
}

function __ymBgCacheMediaDir(){
  const path = require('node:path');
  return path.join(__ymBgCacheDir(), 'media');
}

function __ymBgSafeMediaPath(dir, name){
  const fs = require('node:fs');
  const path = require('node:path');
  const base = path.basename(String(name || ''));
  if(!base || base.charAt(0) === '.') return '';
  const ext = path.extname(base).toLowerCase();
  const allowed = ['.jpg','.jpeg','.png','.webp','.gif','.avif','.bmp',
                   '.mp4','.webm','.mov','.m4v','.ogv'];
  if(allowed.indexOf(ext) === -1) return '';
  const dirs = [dir, __ymBgWallDir(), __ymBgUserDir(), __ymBgCacheMediaDir()];
  for(let i = 0; i < dirs.length; i++){
    if(!dirs[i]) continue;
    const full = path.resolve(dirs[i], base);
    const rel = path.relative(dirs[i], full);
    if(!rel || rel.startsWith('..') || path.isAbsolute(rel)) continue;
    try{ if(fs.statSync(full).isFile()) return full; }catch(e){}
  }
  return '';
}

function __ymBgMediaInfo(file){
  const path = require('node:path');
  const ext = path.extname(String(file || '')).toLowerCase();
  const mimes = {'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.webp':'image/webp',
                 '.gif':'image/gif','.avif':'image/avif','.bmp':'image/bmp',
                 '.mp4':'video/mp4','.webm':'video/webm','.mov':'video/quicktime',
                 '.m4v':'video/mp4','.ogv':'video/ogg'};
  const videoExts = ['.mp4', '.webm', '.mov', '.m4v', '.ogv'];
  return {ext: ext, isVideo: videoExts.indexOf(ext) !== -1, mime: mimes[ext] || ''};
}

// Стиль обложек: одна настройка на всё приложение.
// Список id подставляется из палитры COVER_PRESETS при сборке патча.
const COVER_STYLES = __PRESET_IDS__;
function normalizeCoverStyle(v){
  const s = String(v || '').toLowerCase();
  return COVER_STYLES.indexOf(s) === -1 ? 'mono' : s;
}

function __ymBgReadPayload(){
  const __fs = require('node:fs');
  const __path = require('node:path');
  const __dir = __ymBgUserDir();
  const __wall = __ymBgWallDir();
  const __cache = __ymBgCacheDir();

  let __cfg = {};
  try{
    const __raw = __ymBgReadText(__path.join(__cache, 'custom-background.json'),
                                 __path.join(__dir, 'custom-background.json'))
      .replace(/^\uFEFF/, '');
    __cfg = JSON.parse(__raw) || {};
  }catch(e){ __cfg = {}; }

  const __fileRaw = String(__cfg.file || '');
  const __fileBase = __path.basename(__fileRaw);
  const __file = __ymBgSafeMediaPath(__wall, __fileBase) ? __fileBase : '';
  const __info = __ymBgMediaInfo(__file);
  const __full = __file ? __ymBgSafeMediaPath(__wall, __file) : '';

  let __src = '';
  let __isVideo = false;
  try{
    if(!__full) throw new Error('no media');
    const __st = __fs.statSync(__full);
    if(__st.isFile() && __st.size > 0){
      __isVideo = __info.isVideo;
      // Отдаём файл локальным сервером (с Range), а не data:-строкой:
      // так видео любого размера не раздувается в renderer и не ест память.
      __src = 'http://127.0.0.1:47823/media?t=' + encodeURIComponent(__ymBgToken()) +
              '&v=' + Math.round(__st.mtimeMs || Date.now());
    }
  }catch(e){ __src = ''; __isVideo = false; }

  let __css = '';
  try{
    const __cssCandidates = [__path.join(__cache, 'custom-background.css'),
                             __path.join(__dir, 'custom-background.css')];
    for(let i = 0; i < __cssCandidates.length; i++){
      try{
        const __cssSt = __fs.statSync(__cssCandidates[i]);
        if(__cssSt.isFile() && __cssSt.size <= 1024 * 1024){
          __css = __fs.readFileSync(__cssCandidates[i], 'utf8') || '';
          break;
        }
      }catch(e){}
    }
  }catch(e){ __css = ''; }

  return {
    adaptive: !!__cfg.adaptive,
    coverStyle: normalizeCoverStyle(__cfg.coverStyle),
    discordRpc: !!__cfg.discordRpc,
    discordClientId: __ymBgDiscordId(__cfg.discordClientId),
    src: __src,
    isVideo: __isVideo,
    web: String(__cfg.web || ''),
    webStamp: Number(__cfg.webStamp) || 0,
    webBase: __cfg.web ? ('http://127.0.0.1:47823/web/' + encodeURIComponent(__ymBgToken()) + '/') : '',
    fit: String(__cfg.fit || 'smart'),
    css: __css,
    blur: __cfg.blur,
    brightness: __cfg.brightness,
    dim: __cfg.dim,
    vignette: __cfg.vignette,
    navbarDim: __cfg.navbarDim,
    playerTransparency: __cfg.playerTransparency,
    playerBlur: __cfg.playerBlur,
    playerSaturate: __cfg.playerSaturate,
    fade: __cfg.fade,
    poll: __cfg.poll,
    file: __file,
    token: __ymBgToken()
  };
}

function __ymBgSettingsPayload(cfg){
  return {
    adaptive: !!cfg.adaptive,
    coverStyle: normalizeCoverStyle(cfg.coverStyle),
    discordRpc: !!cfg.discordRpc,
    discordClientId: __ymBgDiscordId(cfg.discordClientId),
    web: String(cfg.web || ''),
    webStamp: Number(cfg.webStamp) || 0,
    webBase: cfg.web ? ('http://127.0.0.1:47823/web/' + encodeURIComponent(__ymBgToken()) + '/') : '',
    fit: String(cfg.fit || 'smart'),
    blur: cfg.blur,
    brightness: cfg.brightness,
    dim: cfg.dim,
    vignette: cfg.vignette,
    navbarDim: cfg.navbarDim,
    playerTransparency: cfg.playerTransparency,
    playerBlur: cfg.playerBlur,
    playerSaturate: cfg.playerSaturate,
    fade: cfg.fade,
    poll: cfg.poll,
    file: String(cfg.file || '')
  };
}

function __ymBgBroadcast(payload){
  try{
    const { BrowserWindow } = require('electron');
    const js = 'window.dispatchEvent(new CustomEvent("ymbg:update",{detail:' + JSON.stringify(payload) + '}));';
    BrowserWindow.getAllWindows().forEach(function(w){
      try{ w.webContents.executeJavaScript(js, true).catch(function(){}); }catch(e){}
    });
  }catch(e){}
}

// Discord Rich Presence: главный процесс говорит с Discord по каналу
// discord-ipc-N, а трек ему присылает renderer на /rpc.
function __ymBgDiscordId(v){
  return String(v || '').replace(/[^0-9]/g, '').slice(0, 20);
}

function __ymBgDiscordConfig(){
  try{
    const fs = require('node:fs');
    const path = require('node:path');
    const f = path.join(__ymBgCacheDir(), 'custom-background.json');
    const raw = fs.readFileSync(f, 'utf8').replace(/^\uFEFF/, '');
    const c = JSON.parse(raw) || {};
    return {on: !!c.discordRpc, id: __ymBgDiscordId(c.discordClientId)};
  }catch(e){ return {on: false, id: ''}; }
}

function __ymBgDiscordStart(){
  if(global.__ymBgDiscord) return;
  const net = require('node:net');
  const fs = require('node:fs');
  const path = require('node:path');
  const DIR = __ymBgCacheDir();
  const REPO_URL = 'https://github.com/fanti-scripts/yandex-music-bg';

  function log(text){
    try{
      fs.mkdirSync(DIR, {recursive: true});
      const f = path.join(DIR, 'discord.log');
      let size = 0;
      try{ size = fs.statSync(f).size; }catch(e){}
      if(size > 200000) fs.writeFileSync(f, '');
      fs.appendFileSync(f, new Date().toISOString() + '  ' + text + '\n', 'utf8');
    }catch(e){}
  }

  const st = {
    sock: null, ready: false, id: '', seq: 0, buf: Buffer.alloc(0),
    retryAt: 0, backoff: 2000, status: 'off', error: '',
    active: false, lastKey: '', lastSent: 0
  };
  global.__ymBgDiscord = st;
  global.__ymBgDiscordLog = log;
  global.__ymBgDiscordStatus = function(){
    return {status: st.status, error: st.error, ready: st.ready};
  };

  function setStatus(s, err){ st.status = s; st.error = err || ''; }

  function close(){
    const s = st.sock;
    st.sock = null;
    st.ready = false;
    st.buf = Buffer.alloc(0);
    if(s){ try{ s.destroy(); }catch(e){} }
  }

  function send(op, obj){
    const s = st.sock;
    if(!s || s.destroyed) return false;
    let body;
    try{ body = Buffer.from(JSON.stringify(obj), 'utf8'); }catch(e){ return false; }
    if(body.length > 1024 * 1024) return false;
    const head = Buffer.alloc(8);
    head.writeUInt32LE(op, 0);
    head.writeUInt32LE(body.length, 4);
    try{ s.write(Buffer.concat([head, body])); return true; }
    catch(e){ return false; }
  }

  function searchUrl(text){
    const base = 'https://music.yandex.ru/search?text=';
    const s = String(text || '').trim();
    for(let cut = s.length; cut > 0; cut -= 2){
      const q = s.slice(0, cut).trim();
      if(!q) break;
      const url = base + encodeURIComponent(q);
      if(url.length <= 250) return url;
    }
    return '';
  }

  function buildActivity(track){
    const title = String(track.title || '').slice(0, 128);
    const artist = String(track.artist || '').slice(0, 128);
    const album = String(track.album || '').slice(0, 128);
    const act = {
      type: 2,
      details: title,
      state: (artist || 'Яндекс Музыка') + (track.playing ? '' : ' · пауза'),
      instance: false
    };
    const cover = String(track.cover || '');
    if(/^https:\/\//i.test(cover) && cover.length <= 256){
      act.assets = {large_image: cover, large_text: album || 'Яндекс Музыка'};
    }
    if(track.playing && track.dur > 0 && track.pos >= 0 && track.pos < track.dur){
      const now = Date.now();
      act.timestamps = {
        start: now - Math.round(track.pos * 1000),
        end: now + Math.round((track.dur - track.pos) * 1000)
      };
    }
    const buttons = [{label: 'Скачать мод', url: REPO_URL}];
    const search = searchUrl((artist + ' ' + title).trim());
    if(search) buttons.push({label: 'Найти трек', url: search});
    act.buttons = buttons;
    return act;
  }

  function setActivity(track){
    if(!st.ready) return;
    const act = track && track.title ? buildActivity(track) : null;
    const key = act ? [track.title, track.artist, track.album, track.cover,
                       track.playing ? 1 : 0, Math.round(track.dur),
                       Math.round(track.pos / 10)].join('\u0001') : '';
    const now = Date.now();
    if(key === st.lastKey && st.active === !!act && now - st.lastSent < 20000) return;
    st.seq += 1;
    const ok = send(1, {
      cmd: 'SET_ACTIVITY',
      args: {pid: process.pid, activity: act},
      nonce: String(st.seq)
    });
    if(ok){
      st.lastKey = key;
      st.active = !!act;
      st.lastSent = now;
    }
  }

  function drop(reason){
    if(st.sock) log('Discord: соединение потеряно (' + reason + ')');
    close();
    st.ready = false;
    st.lastKey = '';
    st.active = false;
    st.retryAt = Date.now() + st.backoff;
    st.backoff = Math.min(st.backoff * 1.7, 30000);
    setStatus('error', reason);
  }

  function onData(chunk){
    st.buf = Buffer.concat([st.buf, chunk]);
    while(st.buf.length >= 8){
      const op = st.buf.readUInt32LE(0);
      const len = st.buf.readUInt32LE(4);
      if(len > 1024 * 1024){ drop('слишком большой кадр'); return; }
      if(st.buf.length < 8 + len) break;
      const body = st.buf.slice(8, 8 + len).toString('utf8');
      st.buf = st.buf.slice(8 + len);
      let msg = {};
      try{ msg = JSON.parse(body) || {}; }catch(e){ msg = {}; }
      if(op === 3){ send(4, msg); continue; }
      if(op === 2){ drop('Discord закрыл канал'); return; }
      if(msg.evt === 'READY'){
        st.ready = true;
        st.backoff = 2000;
        st.retryAt = 0;
        st.lastKey = '';
        st.active = false;
        setStatus('ok');
        const user = msg.data && msg.data.user ? msg.data.user.username : '';
        log('подключено к Discord' + (user ? ' как ' + user : ''));
      } else if(msg.evt === 'ERROR'){
        const data = msg.data || {};
        setStatus('error', data.message || 'ошибка Discord');
        log('ошибка Discord: ' + JSON.stringify(data));
        if(data.code === 4000){   // неверный Application ID — не долбим Discord
          close();
          st.retryAt = Date.now() + 600000;
        }
      }
    }
  }

  function connect(id){
    close();
    st.ready = false;
    const override = String(process.env.YMBG_DISCORD_PIPE || '').trim();
    let idx = 0;
    (function next(){
      if(st.id !== id) return;
      if(idx > 9){
        setStatus('no-discord');
        st.retryAt = Date.now() + st.backoff;
        st.backoff = Math.min(st.backoff * 1.7, 30000);
        return;
      }
      const pipe = override || ('\\\\.\\pipe\\discord-ipc-' + idx);
      const s = net.connect(pipe);
      let connected = false;
      s.once('connect', function(){
        connected = true;
        st.sock = s;
        st.buf = Buffer.alloc(0);
        try{ s.setNoDelay(true); }catch(e){}
        send(0, {v: 1, client_id: id});
      });
      s.once('error', function(e){
        try{ s.destroy(); }catch(_){}
        if(!connected){
          idx = override ? 10 : idx + 1;
          next();
        } else {
          drop((e && e.code) || 'error');
        }
      });
      s.once('close', function(){
        if(st.sock === s) drop('канал закрыт');
      });
      s.on('data', function(chunk){
        if(st.sock === s) onData(chunk);
      });
    })();
  }

  function tick(){
    const conf = __ymBgDiscordConfig();
    if(!conf.on){
      if(st.active) setActivity(null);
      if(st.sock) close();
      st.id = '';
      st.lastKey = '';
      setStatus('off');
      return;
    }
    if(!conf.id){
      if(st.active) setActivity(null);
      if(st.sock) close();
      st.id = '';
      setStatus('no-id');
      return;
    }
    if(st.id !== conf.id){
      close();
      st.id = conf.id;
      st.retryAt = 0;
      st.backoff = 2000;
      st.lastKey = '';
      st.active = false;
      setStatus('connecting');
    }
    if(!st.ready){
      if(!st.sock && Date.now() >= st.retryAt) connect(conf.id);
      return;
    }
    const track = global.__ymBgNow ? Object.assign({}, global.__ymBgNow) : null;
    if(track && track.playing && track.at && track.dur > 0){
      // Догоняем позицию до момента отправки: Discord считает прогресс сам.
      track.pos = Math.min(track.dur, track.pos + (Date.now() - track.at) / 1000);
    }
    if(!track || !track.title || Date.now() - (Number(track.at) || 0) > 30000){
      setActivity(null);
      return;
    }
    setActivity(track);
  }

  global.__ymBgNow = global.__ymBgNow || null;
  setInterval(tick, 1500);
  tick();
}

function __ymBgStartServer(){
  if(global.__ymBgServer) return;
  global.__ymBgServer = true;

  const http = require('node:http');
  const fs = require('node:fs');
  const path = require('node:path');
  const crypto = require('node:crypto');
  const zlib = require('node:zlib');
  const net = require('node:net');
  const dns = require('node:dns').promises;
  const dir = __ymBgUserDir();
  const WALL_DIR = __ymBgWallDir();
  const PORT = 47823;
  const MAX = 2048 * 1024 * 1024;      // 2 ГБ: видео больше не упирается в 80 МБ
  const MAX_ZIP = 1024 * 1024 * 1024;  // архив обоев
  const MAX_JSON = 8 * 1024 * 1024;    // обычные настройки
  const ALLOWED_ORIGIN = 'music-application://desktop';
  const ALLOWED_EXT = ['.jpg','.png','.webp','.gif','.avif','.bmp','.mp4','.webm','.mov','.m4v','.ogv'];
  // Папка с обоями пользователя — только фоны. Всё, что мод создаёт сам
  // (настройки, CSS, превью, HTML-обои, распакованные из архивов файлы),
  // лежит в отдельной папке в LocalAppData.
  const CACHE_DIR = __ymBgCacheDir();
  const CFG_DIR = CACHE_DIR;
  const MEDIA_DIR = path.join(CACHE_DIR, 'media');
  const WEB_DIR = path.join(CACHE_DIR, 'web');
  const MIME = {
    '.html':'text/html; charset=utf-8', '.htm':'text/html; charset=utf-8',
    '.js':'text/javascript; charset=utf-8', '.mjs':'text/javascript; charset=utf-8',
    '.css':'text/css; charset=utf-8', '.json':'application/json; charset=utf-8',
    '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.png':'image/png', '.webp':'image/webp',
    '.gif':'image/gif', '.avif':'image/avif', '.bmp':'image/bmp', '.svg':'image/svg+xml',
    '.mp4':'video/mp4', '.webm':'video/webm', '.mov':'video/quicktime', '.m4v':'video/mp4',
    '.ogv':'video/ogg', '.mp3':'audio/mpeg', '.ogg':'audio/ogg', '.wav':'audio/wav',
    '.woff':'font/woff', '.woff2':'font/woff2', '.ttf':'font/ttf', '.otf':'font/otf',
    '.wasm':'application/wasm', '.glsl':'text/plain; charset=utf-8', '.txt':'text/plain; charset=utf-8'
  };
  const NUMERIC = {
    dim: [0, 0.9], blur: [0, 40], brightness: [0.2, 1.6], vignette: [0, 1],
    navbarDim: [0, 0.8], playerTransparency: [0, 0.95], playerBlur: [0, 40],
    playerSaturate: [0.5, 2], fade: [0, 5000], poll: [500, 10000]
  };

  // Одноразовый токен на запуск приложения: не хранится на диске.
  const TOKEN = __ymBgToken();

  // Убираем старый токен, который раньше лежал открытым текстом.
  try{ fs.unlinkSync(path.join(dir, 'ymbg.token')); }catch(e){}

  function clampNumbers(obj){
    const out = obj && typeof obj === 'object' ? obj : {};
    Object.keys(NUMERIC).forEach(function(k){
      if(out[k] === undefined || out[k] === null || out[k] === '') return;
      const n = Number(out[k]);
      if(!Number.isFinite(n)) return;
      out[k] = Math.min(NUMERIC[k][1], Math.max(NUMERIC[k][0], n));
    });
    if(out.adaptive !== undefined) out.adaptive = !!out.adaptive;
    if(out.coverStyle !== undefined) out.coverStyle = normalizeCoverStyle(out.coverStyle);
    if(out.discordRpc !== undefined) out.discordRpc = !!out.discordRpc;
    if(out.discordClientId !== undefined) out.discordClientId = __ymBgDiscordId(out.discordClientId);
    // Старые три галочки тем больше не нужны.
    delete out.wheelQuiet; delete out.coverQuiet; delete out.avatarQuiet;
    if(out.file !== undefined) out.file = path.basename(String(out.file || ''));
    return out;
  }

  // Масштаб: два варианта. «Умно» — кадр целиком, поля закрывает размытая
  // копия; «Заполнить» — cover, лишнее по краям обрезается.
  function normalizeFit(v){
    const f = String(v || '').toLowerCase();
    return f === 'cover' ? 'cover' : 'smart';
  }
  function readCfg(){
    try{
      const candidates = [path.join(CFG_DIR, 'custom-background.json'),
                          path.join(dir, 'custom-background.json')];
      for(let i = 0; i < candidates.length; i++){
        let raw = '';
        try{
          const st = fs.statSync(candidates[i]);
          if(!st.isFile() || st.size > 1024 * 1024) continue;
          raw = fs.readFileSync(candidates[i], 'utf8') || '';
        }catch(e){ continue; }
        raw = raw.replace(/^\uFEFF/, '');
        const cfg = JSON.parse(raw);
        if(!cfg || typeof cfg !== 'object' || Array.isArray(cfg)) return {};
        return clampNumbers(cfg);
      }
      return {};
    }catch(e){ return {}; }
  }
  function writeCfg(cfg){
    try{ fs.mkdirSync(CFG_DIR, {recursive: true}); }catch(e){}
    const target = path.join(CFG_DIR, 'custom-background.json');
    const tmp = path.join(CFG_DIR, '.custom-background.json.tmp');
    fs.writeFileSync(tmp, JSON.stringify(clampNumbers(cfg), null, 2), 'utf8');
    fs.renameSync(tmp, target);
  }
  const VIDEO_EXT = ['.mp4','.webm','.mov','.m4v','.ogv'];
  const IMAGE_EXT = ['.jpg','.jpeg','.png','.webp','.gif','.avif','.bmp'];
  const LIB_EXT = IMAGE_EXT.concat(VIDEO_EXT, ['.zip','.html','.htm']);
  const THUMB_DIR = path.join(CACHE_DIR, 'thumbs');
  const TMP_DIR = path.join(CACHE_DIR, 'tmp');
  // Всё, что не является фоном и лежало в папке обоев, переезжает сюда:
  // архивы, старые HTML-обои, служебные файлы сторонних программ.
  const IMPORT_DIR = path.join(CACHE_DIR, 'legacy');
  // Архивы обоев (.zip, .html) живут отдельно от папки фонов, но видны
  // в галерее «Мои фоны» — папка обоев остаётся только с картинками и видео.
  const ARCHIVE_DIR = path.join(CACHE_DIR, 'archives');

  function ensureDirs(){
    [CACHE_DIR, CFG_DIR, MEDIA_DIR, WEB_DIR, THUMB_DIR, TMP_DIR, IMPORT_DIR, ARCHIVE_DIR, WALL_DIR].forEach(function(d){
      try{ fs.mkdirSync(d, {recursive: true}); }catch(e){}
    });
  }

  function moveFile(src, dst){
    try{
      if(fs.existsSync(dst)){ fs.unlinkSync(src); return; }
      fs.renameSync(src, dst);
    }catch(e){
      try{ fs.copyFileSync(src, dst); fs.unlinkSync(src); }catch(_){}
    }
  }

  // Новая раскладка: фоны живут отдельной папкой, служебные файлы старых
  // версий из корневой папки переезжают в кэш.
  function migrateLayout(){
    try{
      fs.readdirSync(dir).forEach(function(n){
        const src = path.join(dir, n);
        let st;
        try{ st = fs.statSync(src); }catch(e){ return; }
        if(!st.isFile()) return;
        if(/^\.ymbg-tmp-/.test(n) || /^\.custom-background/i.test(n) && /\.tmp$/i.test(n)){
          try{ fs.unlinkSync(src); }catch(e){}
          return;
        }
        if(LIB_EXT.indexOf(path.extname(n).toLowerCase()) !== -1){
          moveFile(src, path.join(WALL_DIR, n));
          return;
        }
        if(/^custom-background\.(json|css)(\.|$)/i.test(n)){
          moveFile(src, path.join(CFG_DIR, n));
        }
      });
    }catch(e){}
    try{
      const legacyWeb = path.join(dir, 'web-wallpaper');
      if(fs.existsSync(legacyWeb)){
        fs.readdirSync(legacyWeb).forEach(function(n){
          try{ moveFile(path.join(legacyWeb, n), path.join(WEB_DIR, n)); }catch(e){}
        });
        try{ fs.rmdirSync(legacyWeb); }catch(e){}
      }
    }catch(e){}
    try{
      const legacyThumbs = path.join(dir, 'thumbs');
      if(fs.existsSync(legacyThumbs)) fs.rmSync(legacyThumbs, {recursive: true, force: true});
    }catch(e){}
  }

  // Папка обоев — только фоны. Архив или HTML, положенный туда руками,
  // сразу ставится фоном (распаковывается в кэш) и из папки убирается.
  // Всё прочее, что не картинка и не видео, переезжает в кэш без удаления.
  function isBackgroundFile(name){
    const ext = path.extname(String(name || '')).toLowerCase();
    return IMAGE_EXT.indexOf(ext) !== -1 || VIDEO_EXT.indexOf(ext) !== -1;
  }

  function sweepWallDir(){
    let moved = 0;
    try{
      fs.mkdirSync(IMPORT_DIR, {recursive: true});
    }catch(e){}
    let names = [];
    try{ names = fs.readdirSync(WALL_DIR); }catch(e){ names = []; }
    for(let i = 0; i < names.length; i++){
      const n = names[i];
      if(!n || n.charAt(0) === '.') continue;
      const src = path.join(WALL_DIR, n);
      let st;
      try{ st = fs.statSync(src); }catch(e){ continue; }
      if(st.isDirectory()){
        try{ fs.renameSync(src, path.join(IMPORT_DIR, n)); moved++; }catch(e){}
        continue;
      }
      if(!st.isFile()) continue;
      const ext = path.extname(n).toLowerCase();
      if(isBackgroundFile(n)) continue;

      // .zip и .html — фон, просто упакованный. Он переезжает в отдельную
      // папку архивов и остаётся виден в галерее «Мои фоны».
      if(ext === '.zip' || ext === '.html' || ext === '.htm'){
        const adst = path.join(ARCHIVE_DIR, n);
        if(!fs.existsSync(adst)){
          try{ fs.renameSync(src, adst); moved++; continue; }
          catch(e){ try{ fs.copyFileSync(src, adst); fs.unlinkSync(src); moved++; continue; }catch(_){} }
        } else {
          try{ fs.unlinkSync(src); }catch(e){}
          continue;
        }
      }

      const dst = path.join(IMPORT_DIR, n);
      if(fs.existsSync(dst)){ try{ fs.unlinkSync(src); }catch(e){} continue; }
      try{ fs.renameSync(src, dst); moved++; }
      catch(e){
        try{ fs.copyFileSync(src, dst); fs.unlinkSync(src); moved++; }catch(_){}
      }
    }
    return moved;
  }

  function cleanTmp(){    // Временные загрузки держим в кэше; заодно убираем хвосты старой версии
    // из папки с обоями.
    try{
      fs.readdirSync(TMP_DIR).forEach(function(n){
        try{ fs.unlinkSync(path.join(TMP_DIR, n)); }catch(e){}
      });
    }catch(e){}
    try{
      [dir, CFG_DIR].forEach(function(base){
        try{
          fs.readdirSync(base).forEach(function(n){
            if(/^\.ymbg-tmp-/.test(n) || /^\.custom-background\.json\.tmp$/.test(n)){
              try{ fs.unlinkSync(path.join(base, n)); }catch(e){}
            }
          });
        }catch(e){}
      });
    }catch(e){}
  }
  function safeFileIn(base, name, exts){
    const baseName = path.basename(String(name || ''));
    if(!baseName || baseName.charAt(0) === '.') return '';
    const ext = path.extname(baseName).toLowerCase();
    if((exts || ALLOWED_EXT).indexOf(ext) === -1) return '';
    const full = path.resolve(base, baseName);
    const rel = path.relative(base, full);
    if(!rel || rel.startsWith('..') || path.isAbsolute(rel)) return '';
    try{ if(!fs.statSync(full).isFile()) return ''; }catch(e){ return ''; }
    return full;
  }
  function safeUserFile(name, exts){
    // Фоны ищутся в папке обоев; архивы — в своей папке; корень профиля
    // проверяем только ради файлов, которые ещё не успели переехать.
    return safeFileIn(WALL_DIR, name, exts) ||
           safeFileIn(ARCHIVE_DIR, name, exts) ||
           safeFileIn(dir, name, exts);
  }
  // Файлы, извлечённые из архивов, лежат в кэше — ищем и там.
  function safeMediaFile(name, exts){
    return safeUserFile(name, exts) || safeFileIn(MEDIA_DIR, name, exts);
  }
  function thumbDir(){
    try{ fs.mkdirSync(THUMB_DIR, {recursive: true}); }catch(e){}
    return THUMB_DIR;
  }
  function cacheKey(full){
    const st = fs.statSync(full);
    return crypto.createHash('sha1')
      .update(full + '|' + st.size + '|' + Math.round(st.mtimeMs || 0))
      .digest('hex');
  }
  function makeImageThumb(full){
    let key = '';
    try{ key = cacheKey(full); }catch(e){ return ''; }
    const out = path.join(thumbDir(), key + '.jpg');
    try{ if(fs.statSync(out).size > 0) return out; }catch(e){}
    let img;
    try{ img = require('electron').nativeImage.createFromPath(full); }
    catch(e){ return ''; }
    try{
      if(!img || img.isEmpty()) return '';
      const sz = img.getSize();
      if(sz.width > 480) img = img.resize({width: 480, quality: 'good'});
      const jpg = img.toJPEG(78);
      if(!jpg || !jpg.length) return '';
      fs.writeFileSync(out, jpg);
      return out;
    }catch(e){ return ''; }
  }
  function zipPreview(zipPath){
    let key = '';
    try{ key = cacheKey(zipPath); }catch(e){ return ''; }
    const tdir = thumbDir();
    const exts = ['.gif', '.jpg', '.png'];
    for(let i = 0; i < exts.length; i++){
      const p = path.join(tdir, key + exts[i]);
      try{ if(fs.statSync(p).size > 0) return p; }catch(e){}
    }
    let st;
    try{ st = fs.statSync(zipPath); }catch(e){ return ''; }
    if(st.size > 256 * 1024 * 1024) return '';
    try{
      const buf = fs.readFileSync(zipPath);
      const z = readZip(buf);
      let pv = findEntry(z, 'preview.gif') || findEntry(z, 'preview.jpg') ||
               findEntry(z, 'preview.jpeg') || findEntry(z, 'preview.png');
      if(!pv){
        const pics = z.filter(function(e){
          return !e.dir && /\.(gif|jpe?g|png)$/i.test(e.name) && e.usize > 0 && e.usize < 12 * 1024 * 1024;
        }).sort(function(a, b){ return b.usize - a.usize; });
        pv = pics[0] || null;
      }
      if(!pv) return '';
      const data = zipEntry(buf, pv);
      const ext = path.extname(pv.name).toLowerCase();
      const outExt = ext === '.png' ? '.png' : (ext === '.gif' ? '.gif' : '.jpg');
      const target = path.join(tdir, key + outExt);
      fs.writeFileSync(target, data);
      return target;
    }catch(e){ return ''; }
  }
  // ---------- метаданные для окна «Свойства» ----------
  function imageSize(buf){
    try{
      if(buf.length > 24 && buf[0] === 0x89 && buf[1] === 0x50){
        return {w: buf.readUInt32BE(16), h: buf.readUInt32BE(20)};
      }
      if(buf.length > 10 && buf.toString('ascii', 0, 3) === 'GIF'){
        return {w: buf.readUInt16LE(6), h: buf.readUInt16LE(8)};
      }
      if(buf.length > 26 && buf[0] === 0x42 && buf[1] === 0x4d){
        return {w: Math.abs(buf.readInt32LE(18)), h: Math.abs(buf.readInt32LE(22))};
      }
      if(buf.length > 30 && buf.toString('ascii', 0, 4) === 'RIFF' &&
         buf.toString('ascii', 8, 12) === 'WEBP'){
        const kind = buf.toString('ascii', 12, 16);
        if(kind === 'VP8X'){
          const w = 1 + (buf[24] | (buf[25] << 8) | (buf[26] << 16));
          const h = 1 + (buf[27] | (buf[28] << 8) | (buf[29] << 16));
          return {w: w, h: h};
        }
        if(kind === 'VP8 '){
          return {w: buf.readUInt16LE(26) & 0x3fff, h: buf.readUInt16LE(28) & 0x3fff};
        }
        if(kind === 'VP8L'){
          const b = buf.readUInt32LE(21);
          return {w: (b & 0x3fff) + 1, h: ((b >> 14) & 0x3fff) + 1};
        }
      }
      if(buf.length > 4 && buf[0] === 0xff && buf[1] === 0xd8){
        let p = 2;
        while(p + 9 < buf.length){
          if(buf[p] !== 0xff){ p++; continue; }
          const m = buf[p + 1];
          if(m === 0xd8 || m === 0x01 || (m >= 0xd0 && m <= 0xd7)){ p += 2; continue; }
          const len = buf.readUInt16BE(p + 2);
          if(m >= 0xc0 && m <= 0xcf && m !== 0xc4 && m !== 0xc8 && m !== 0xcc){
            return {w: buf.readUInt16BE(p + 7), h: buf.readUInt16BE(p + 5)};
          }
          p += 2 + len;
        }
      }
    }catch(e){}
    return null;
  }

  function mp4Boxes(buf, start, end){
    const out = [];
    let p = start;
    while(p + 8 <= end){
      let size = buf.readUInt32BE(p);
      const type = buf.toString('ascii', p + 4, p + 8);
      let head = 8;
      if(size === 1){
        if(p + 16 > end) break;
        size = Number(buf.readBigUInt64BE(p + 8));
        head = 16;
      } else if(size === 0){
        size = end - p;
      }
      if(size < head || p + size > end) break;
      out.push({type: type, start: p + head, end: p + size});
      p += size;
    }
    return out;
  }

  function mp4Meta(buf){
    if(buf.length < 32 || buf.toString('ascii', 4, 8) !== 'ftyp') return null;
    const top = mp4Boxes(buf, 0, buf.length);
    const moov = top.filter(function(b){ return b.type === 'moov'; })[0];
    if(!moov) return null;
    const kids = mp4Boxes(buf, moov.start, moov.end);
    const meta = {};
    const mvhd = kids.filter(function(b){ return b.type === 'mvhd'; })[0];
    if(mvhd){
      const v = buf[mvhd.start];
      if(v === 1){
        meta.timescale = buf.readUInt32BE(mvhd.start + 20);
        meta.duration = Number(buf.readBigUInt64BE(mvhd.start + 24)) / (meta.timescale || 1);
      } else {
        meta.timescale = buf.readUInt32BE(mvhd.start + 12);
        meta.duration = buf.readUInt32BE(mvhd.start + 16) / (meta.timescale || 1);
      }
    }
    const traks = kids.filter(function(b){ return b.type === 'trak'; });
    for(let i = 0; i < traks.length; i++){
      const tk = mp4Boxes(buf, traks[i].start, traks[i].end);
      const tkhd = tk.filter(function(b){ return b.type === 'tkhd'; })[0];
      const mdia = tk.filter(function(b){ return b.type === 'mdia'; })[0];
      if(!tkhd || !mdia) continue;
      const md = mp4Boxes(buf, mdia.start, mdia.end);
      const hdlr = md.filter(function(b){ return b.type === 'hdlr'; })[0];
      const isVideo = hdlr && buf.toString('ascii', hdlr.start + 8, hdlr.start + 12) === 'vide';
      if(!isVideo) continue;
      const tv = buf[tkhd.start];
      const wOff = tv === 1 ? tkhd.start + 88 : tkhd.start + 76;
      if(wOff + 8 <= tkhd.end){
        meta.width = Math.round(buf.readUInt32BE(wOff) / 65536);
        meta.height = Math.round(buf.readUInt32BE(wOff + 4) / 65536);
      }
      const minf = md.filter(function(b){ return b.type === 'minf'; })[0];
      const stbl = minf ? mp4Boxes(buf, minf.start, minf.end).filter(function(b){ return b.type === 'stbl'; })[0] : null;
      if(stbl){
        const sb = mp4Boxes(buf, stbl.start, stbl.end);
        const stsz = sb.filter(function(b){ return b.type === 'stsz'; })[0];
        const stsd = sb.filter(function(b){ return b.type === 'stsd'; })[0];
        if(stsz) meta.frames = buf.readUInt32BE(stsz.start + 8);
        if(stsd && stsd.start + 20 <= stsd.end){
          meta.codec = buf.toString('ascii', stsd.start + 12, stsd.start + 16);
        }
      }
      break;
    }
    if(meta.duration && meta.frames){
      meta.fps = meta.frames / meta.duration;
      meta.bitrate = (buf.length * 8) / meta.duration;
    }
    return meta;
  }

  function webmMeta(buf){
    if(!(buf[0] === 0x1a && buf[1] === 0x45 && buf[2] === 0xdf && buf[3] === 0xa3)) return null;
    const out = {};
    function readVint(p){
      const b = buf[p];
      if(!b) return null;
      let len = 1, mask = 0x80;
      while(len <= 8 && !(b & mask)){ len++; mask >>= 1; }
      if(len > 8) return null;
      let v = b & (mask - 1);
      for(let i = 1; i < len; i++) v = v * 256 + buf[p + i];
      return {v: v, len: len};
    }
    function readUInt(p, n){
      let v = 0;
      for(let i = 0; i < n; i++) v = v * 256 + buf[p + i];
      return v;
    }
    function findTag(a, b, c){
      for(let i = 0; i < buf.length - 3; i++){
        if(buf[i] === a && buf[i + 1] === b && buf[i + 2] === c) return i + 3;
      }
      return -1;
    }
    const pairs = [[[0x42, 0x82, 0x40], 'width'], [[0x42, 0xba, 0x40], 'height']];
    for(let i = 0; i < pairs.length; i++){
      const at = findTag(pairs[i][0][0], pairs[i][0][1], pairs[i][0][2]);
      if(at < 0) continue;
      const size = readVint(at);
      if(!size || size.v <= 0 || size.v > 4) continue;
      out[pairs[i][1]] = readUInt(at + size.len, size.v);
    }
    return (out.width && out.height) ? out : null;
  }

  function zipMeta(full, buf){
    const z = readZip(buf);
    const out = {entries: z.filter(function(e){ return !e.dir; }).length};
    let pj = null;
    for(let i = 0; i < z.length; i++){
      if(!z[i].dir && /(^|\/)project\.json$/i.test(z[i].name)){ pj = z[i]; break; }
    }
    if(pj){
      try{
        const j = JSON.parse(zipEntry(buf, pj).toString('utf8')) || {};
        if(j.type) out.type = String(j.type);
        if(j.preview) out.preview = String(j.preview);
        if(j.title) out.title = String(j.title);
      }catch(e){}
    }
    return out;
  }

  function libraryItems(){
    const cfg = readCfg();
    const activeFile = cfg.file ? path.basename(String(cfg.file)) : '';
    const activeLib = cfg.lib ? path.basename(String(cfg.lib)) : '';
    const out = [];
    // Папка фонов: картинки и видео.
    const collect = function(base, exts){
      let names = [];
      try{ names = fs.readdirSync(base); }catch(e){ names = []; }
      for(let i = 0; i < names.length; i++){
        const name = names[i];
        if(!name || name.charAt(0) === '.') continue;
        const ext = path.extname(name).toLowerCase();
        if(exts.indexOf(ext) === -1) continue;
        let st;
        try{ st = fs.statSync(path.join(base, name)); }catch(e){ continue; }
        if(!st.isFile() || !st.size) continue;
        const kind = VIDEO_EXT.indexOf(ext) !== -1 ? 'video' :
                     IMAGE_EXT.indexOf(ext) !== -1 ? 'image' :
                     (ext === '.zip' ? 'archive' : 'html');
        out.push({
          name: name,
          kind: kind,
          size: st.size,
          mtime: Math.round(st.mtimeMs || st.mtime || 0),
          active: activeLib ? (name === activeLib) : (name === activeFile)
        });
      }
    };
    collect(WALL_DIR, IMAGE_EXT.concat(VIDEO_EXT, ['.zip','.html','.htm']));
    // Папка архивов: сюда попадают zip и html, найденные в папке фонов.
    collect(ARCHIVE_DIR, ['.zip','.html','.htm']);
    out.sort(function(a, b){ return b.mtime - a.mtime; });
    return out.slice(0, 300);
  }
  // Имя файла из ссылки: «clip.mp4» с сайта останется «clip.mp4».
  function nameFromUrl(u){
    try{
      const p = new URL(String(u)).pathname || '';
      const last = p.split('/').filter(Boolean).pop() || '';
      return decodeURIComponent(last);
    }catch(e){ return ''; }
  }
  function extFromType(type){
    const t = String(type || '').toLowerCase().split(';')[0].trim();
    const map = {'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp','image/gif':'.gif',
                 'image/avif':'.avif','image/bmp':'.bmp','video/mp4':'.mp4','video/webm':'.webm',
                 'video/quicktime':'.mov','video/ogg':'.ogv'};
    return map[t] || '';
  }
  function reply(res, code, obj){
    const body = Buffer.from(JSON.stringify(obj));
    const headers = {
      'Content-Type':'application/json; charset=utf-8',
      'Content-Length':body.length,
      'Cache-Control':'no-store',
      'X-Content-Type-Options':'nosniff'
    };
    if(res.__ymOrigin === ALLOWED_ORIGIN){
      headers['Access-Control-Allow-Origin'] = ALLOWED_ORIGIN;
      headers['Vary'] = 'Origin';
    }
    res.writeHead(code, headers);
    res.end(body);
  }
  function tokenEquals(a, b){
    const aa = Buffer.from(String(a || ''), 'utf8');
    const bb = Buffer.from(String(b || ''), 'utf8');
    if(!aa.length || aa.length !== bb.length) return false;
    try{ return crypto.timingSafeEqual(aa, bb); }catch(e){ return false; }
  }
  function authorized(req){
    return tokenEquals(req.headers['x-ymbg-token'], TOKEN);
  }
  function originAllowed(req){
    const o = req.headers.origin;
    return !o || o === ALLOWED_ORIGIN;
  }
  function hostAllowed(req){
    const h = String(req.headers.host || '').toLowerCase();
    return h === '127.0.0.1:47823' || h === 'localhost:47823';
  }

  // ---------- общая раздача файлов (Range нужен для больших видео) ----------
  function mimeOf(name){
    return MIME[path.extname(String(name || '')).toLowerCase()] || 'application/octet-stream';
  }
  function safeWebPath(rel){
    const base = path.resolve(WEB_DIR);
    const full = path.resolve(base, String(rel || '').replace(/^[/\\]+/, ''));
    const r = path.relative(base, full);
    if(!r || r.startsWith('..') || path.isAbsolute(r)) return '';
    return full;
  }
  function serveFile(req, res, full, name){
    let st;
    try{ st = fs.statSync(full); }catch(e){ return reply(res, 404, {ok:false, error:'not found'}); }
    if(!st.isFile()) return reply(res, 404, {ok:false, error:'not found'});
    const headers = {
      'Content-Type': mimeOf(name || full),
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff'
    };
    if(res.__ymOrigin === ALLOWED_ORIGIN){
      headers['Access-Control-Allow-Origin'] = ALLOWED_ORIGIN;
      headers['Vary'] = 'Origin';
      headers['Access-Control-Expose-Headers'] = 'Content-Length, Content-Range, Accept-Ranges';
    }
    let start = 0, end = st.size - 1, code = 200;
    const m = /^bytes=(\d*)-(\d*)$/.exec(String(req.headers.range || '').trim());
    if(m && st.size > 0 && !(m[1] === '' && m[2] === '')){
      if(m[1] === '') start = Math.max(0, st.size - Number(m[2]));
      else {
        start = Number(m[1]);
        if(m[2] !== '') end = Math.min(st.size - 1, Number(m[2]));
      }
      if(!Number.isFinite(start) || start > end || start >= st.size){
        res.writeHead(416, {'Content-Range': 'bytes */' + st.size, 'Content-Length': '0'});
        return res.end();
      }
      code = 206;
      headers['Content-Range'] = 'bytes ' + start + '-' + end + '/' + st.size;
    }
    headers['Content-Length'] = String(Math.max(0, end - start + 1));
    res.writeHead(code, headers);
    if(req.method === 'HEAD') return res.end();
    const stream = fs.createReadStream(full, {start: start, end: Math.max(start, end)});
    stream.on('error', function(){ try{ res.destroy(); }catch(e){} });
    stream.pipe(res);
  }
  function queryParam(req, name){
    try{ return new URL(req.url, 'http://127.0.0.1').searchParams.get(name) || ''; }catch(e){ return ''; }
  }
  function queryToken(req){
    return queryParam(req, 't');
  }

  // ---------- приём файлов потоком (без base64 и без лимита 80 МБ) ----------
  function saveStream(req, target, max){
    return new Promise(function(resolve, reject){
      const out = fs.createWriteStream(target);
      let total = 0, head = Buffer.alloc(0), done = false;
      function fail(err){
        if(done) return;
        done = true;
        try{ out.destroy(); }catch(e){}
        try{ fs.unlinkSync(target); }catch(e){}
        reject(err instanceof Error ? err : new Error(String(err)));
      }
      req.on('data', function(c){
        if(done) return;
        total += c.length;
        if(total > max){
          try{ req.destroy(); }catch(e){}
          return fail(new Error('файл больше ' + Math.round(max / 1048576) + ' МБ'));
        }
        if(head.length < 64) head = Buffer.concat([head, c.subarray(0, 64 - head.length)]);
        if(!out.write(c)){
          try{ req.pause(); }catch(e){}
          out.once('drain', function(){ try{ req.resume(); }catch(e){} });
        }
      });
      req.on('error', fail);
      out.on('error', fail);
      req.on('end', function(){
        if(done) return;
        out.end(function(){ if(done) return; done = true; resolve({path: target, bytes: total, head: head}); });
      });
    });
  }

  function readJsonBody(req, max){
    return new Promise(function(resolve, reject){
      let chunks = [], total = 0, done = false;
      req.on('data', function(c){
        if(done) return;
        total += c.length;
        if(total > max){
          done = true;
          try{ req.destroy(); }catch(e){}
          return reject(new Error('слишком большой запрос'));
        }
        chunks.push(c);
      });
      req.on('error', function(e){ if(!done){ done = true; reject(e); } });
      req.on('end', function(){
        if(done) return;
        done = true;
        try{ resolve(JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}')); }
        catch(e){ reject(new Error('bad json')); }
      });
    });
  }
  async function webToFile(resp, target, max){
    const out = fs.createWriteStream(target);
    const reader = resp.body && resp.body.getReader ? resp.body.getReader() : null;
    let total = 0, head = Buffer.alloc(0);
    if(!reader){
      const buf = Buffer.from(await resp.arrayBuffer());
      if(buf.length > max) throw new Error('файл больше ' + Math.round(max / 1048576) + ' МБ');
      fs.writeFileSync(target, buf);
      return {path: target, bytes: buf.length, head: buf.subarray(0, 64)};
    }
    try{
      while(true){
        const step = await reader.read();
        if(step.done) break;
        const chunk = Buffer.from(step.value);
        total += chunk.length;
        if(total > max){
          try{ await reader.cancel(); }catch(e){}
          throw new Error('файл больше ' + Math.round(max / 1048576) + ' МБ');
        }
        if(head.length < 64) head = Buffer.concat([head, chunk.subarray(0, 64 - head.length)]);
        if(!out.write(chunk)) await new Promise(function(ok){ out.once('drain', ok); });
      }
    }catch(e){
      try{ out.destroy(); }catch(_){}
      try{ fs.unlinkSync(target); }catch(_){}
      throw e;
    }
    await new Promise(function(ok, bad){ out.end(ok); out.on('error', bad); });
    return {path: target, bytes: total, head: head};
  }

  function mediaName(ext){
    return 'custom-background-' + crypto.randomBytes(4).toString('hex') + ext;
  }
  // Имя из файла пользователя: «Мой клип.mp4» остаётся «Мой клип.mp4».
  function stemOf(raw){
    let base = path.basename(String(raw || ''));
    try{ base = decodeURIComponent(base); }catch(e){}
    base = base.replace(/[\\/:*?"<>|\u0000-\u001f]/g, ' ').replace(/\s+/g, ' ').trim();
    base = base.replace(/^\.+/, '');
    if(!base) return '';
    const ext = path.extname(base);
    const stem = ext ? base.slice(0, base.length - ext.length) : base;
    return stem.slice(0, 70).trim();
  }
  function adoptMedia(tmpPath, ext, rawName){
    if(ALLOWED_EXT.indexOf(ext) === -1) throw new Error('формат не поддерживается');
    const stem = stemOf(rawName);
    const size = (function(){ try{ return fs.statSync(tmpPath).size; }catch(e){ return 0; } })();
    let name = '';
    if(stem){
      for(let i = 0; i < 60; i++){
        const candidate = (i ? stem + '-' + (i + 1) : stem) + ext;
        const full = path.join(WALL_DIR, candidate);
        try{
          const st = fs.statSync(full);
          if(st.isFile()){
            // Такой же файл уже лежит в папке — второй экземпляр не нужен.
            if(size && st.size === size){
              try{ fs.unlinkSync(tmpPath); }catch(e){}
              return {name: candidate, bytes: st.size};
            }
            continue;
          }
        }catch(e){}
        name = candidate;
        break;
      }
    }
    if(!name) name = mediaName(ext);
    const target = path.join(WALL_DIR, name);
    try{ fs.renameSync(tmpPath, target); }
    catch(e){
      fs.copyFileSync(tmpPath, target);
      try{ fs.unlinkSync(tmpPath); }catch(_){}
    }
    return {name: name, bytes: fs.statSync(target).size};
  }

  // ---------- zip (Wallpaper Engine и обычные архивы) ----------
  function readZip(buf){
    let eocd = -1;
    const min = Math.max(0, buf.length - 0xFFFF - 22);
    for(let i = buf.length - 22; i >= min; i--){
      if(i >= 0 && buf.readUInt32LE(i) === 0x06054b50){ eocd = i; break; }
    }
    if(eocd < 0) throw new Error('это не zip-архив');
    const count = buf.readUInt16LE(eocd + 10);
    const cdOff = buf.readUInt32LE(eocd + 16);
    if(cdOff === 0xFFFFFFFF) throw new Error('zip64 не поддерживается');
    const list = [];
    let p = cdOff;
    for(let i = 0; i < count; i++){
      if(p + 46 > buf.length || buf.readUInt32LE(p) !== 0x02014b50) break;
      const method = buf.readUInt16LE(p + 10);
      const csize = buf.readUInt32LE(p + 20);
      const usize = buf.readUInt32LE(p + 24);
      const nlen = buf.readUInt16LE(p + 28);
      const elen = buf.readUInt16LE(p + 30);
      const clen = buf.readUInt16LE(p + 32);
      const off = buf.readUInt32LE(p + 42);
      const name = buf.toString('utf8', p + 46, p + 46 + nlen);
      p += 46 + nlen + elen + clen;
      if(!name) continue;
      list.push({name: name, dir: /\/$/.test(name), method: method, csize: csize, usize: usize, off: off});
    }
    if(!list.length) throw new Error('архив пустой');
    return list;
  }
  function zipEntry(buf, e){
    const q = e.off;
    if(q + 30 > buf.length || buf.readUInt32LE(q) !== 0x04034b50) throw new Error('повреждённый архив');
    if(e.usize > 512 * 1024 * 1024) throw new Error('файл в архиве больше 512 МБ');
    const nlen = buf.readUInt16LE(q + 26);
    const elen = buf.readUInt16LE(q + 28);
    const start = q + 30 + nlen + elen;
    const comp = buf.subarray(start, start + e.csize);
    if(e.method === 0) return Buffer.from(comp);
    if(e.method === 8){
      return zlib.inflateRawSync(comp, {maxOutputLength: Math.max(1024 * 1024, Math.min(e.usize + 1024, MAX))});
    }
    throw new Error('сжатие в архиве не поддерживается');
  }
  function findEntry(z, name){
    const want = String(name || '').replace(/\\/g, '/').replace(/^\/+/, '').toLowerCase();
    if(!want) return null;
    for(let i = 0; i < z.length; i++){
      if(!z[i].dir && z[i].name.replace(/^\/+/, '').toLowerCase() === want) return z[i];
    }
    for(let i = 0; i < z.length; i++){
      if(!z[i].dir && z[i].name.toLowerCase().slice(-want.length) === want) return z[i];
    }
    return null;
  }
  function pickLargest(z, exts){
    let best = null;
    for(let i = 0; i < z.length; i++){
      if(z[i].dir || exts.indexOf(path.extname(z[i].name).toLowerCase()) === -1) continue;
      if(!best || z[i].usize > best.usize) best = z[i];
    }
    return best;
  }
  function resetWebDir(){
    try{ fs.rmSync(WEB_DIR, {recursive: true, force: true}); }catch(e){}
    fs.mkdirSync(WEB_DIR, {recursive: true});
  }
  function installWebFromZip(buf, z, prefix, entryName){
    const files = z.filter(function(e){ return !e.dir && e.name.indexOf(prefix) === 0; });
    if(!files.length) throw new Error('архив пустой');
    let total = 0;
    for(let i = 0; i < files.length; i++){
      total += files[i].usize;
      if(total > 512 * 1024 * 1024) throw new Error('веб-обои больше 512 МБ');
    }
    resetWebDir();
    for(let i = 0; i < files.length; i++){
      const rel = files[i].name.slice(prefix.length).replace(/\\/g, '/');
      if(/^project\.json$/i.test(rel)) continue;
      const target = safeWebPath(rel);
      if(!target) continue;
      fs.mkdirSync(path.dirname(target), {recursive: true});
      fs.writeFileSync(target, zipEntry(buf, files[i]));
    }
    let entry = String(entryName || 'index.html').replace(/\\/g, '/');
    let full = safeWebPath(entry);
    if(!full || !fs.existsSync(full)){
      entry = 'index.html';
      full = safeWebPath(entry);
      if(!full || !fs.existsSync(full)){
        const found = files.filter(function(f){ return /(^|\/)index\.html?$/i.test(f.name); })[0];
        if(!found) throw new Error('в архиве нет index.html');
        entry = found.name.slice(prefix.length).replace(/\\/g, '/');
      }
    }
    return entry;
  }
  // ---------- Wallpaper Engine: scene.pkg ----------
  // Сцена WE — это .pkg с текстурами и шейдерами. Сам движок не воспроизвести,
  // но исходные текстуры внутри лежат как есть: вытаскиваем самую большую
  // картинку сцены, а не превью из архива.
  function pkgEntries(buf){
    if(buf.length < 12) return [];
    const magicLen = buf.readUInt32LE(0);
    if(magicLen < 4 || magicLen > 32) return [];
    const magic = buf.toString('ascii', 4, 4 + magicLen);
    if(magic.indexOf('PKGV') !== 0) return [];
    let p = 4 + magicLen;
    const count = buf.readUInt32LE(p); p += 4;
    if(!count || count > 100000) return [];
    const list = [];
    for(let i = 0; i < count && p + 8 <= buf.length; i++){
      const n = buf.readUInt32LE(p); p += 4;
      if(p + n > buf.length) break;
      const name = buf.toString('utf8', p, p + n); p += n;
      const off = buf.readUInt32LE(p); p += 4;
      const size = buf.readUInt32LE(p); p += 4;
      list.push({name: name, off: off, size: size});
    }
    const headerEnd = p;
    for(let i = 0; i < list.length; i++){
      const e = list[i];
      const start = headerEnd + e.off;
      if(start < 0 || start + e.size > buf.length) continue;
      e.data = buf.subarray(start, start + e.size);
    }
    return list.filter(function(e){ return e.data; });
  }

  const PNG_SIG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  const PNG_END = Buffer.from([0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82]);

  function pngFromTex(tex){
    const at = tex.indexOf(PNG_SIG);
    if(at < 0) return null;
    const end = tex.indexOf(PNG_END, at);
    if(end < 0) return null;
    const png = tex.subarray(at, end + 8);
    if(png.length < 57 || png.length > 64 * 1024 * 1024) return null;
    let w = 0, h = 0;
    try{ w = png.readUInt32BE(16); h = png.readUInt32BE(20); }catch(e){ return null; }
    if(!w || !h || w > 8192 || h > 8192) return null;
    return {buf: png, width: w, height: h};
  }

  // Старые архивы хранят текстуры сжатыми (DXT1/DXT5/RGBA). Декодируем вручную,
  // без внешних зависимостей: zlib уже под рукой, PNG собираем сами.
  function crc32(buf){
    if(!crc32.table){
      const t = new Int32Array(256);
      for(let n = 0; n < 256; n++){
        let c = n;
        for(let k = 0; k < 8; k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
        t[n] = c;
      }
      crc32.table = t;
    }
    const t = crc32.table;
    let c = -1;
    for(let i = 0; i < buf.length; i++) c = t[(c ^ buf[i]) & 255] ^ (c >>> 8);
    return (c ^ -1) >>> 0;
  }
  function pngChunk(type, data){
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
    const body = Buffer.concat([Buffer.from(type, 'ascii'), data]);
    const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(body));
    return Buffer.concat([len, body, crc]);
  }
  function encodePng(rgba, w, h){
    const stride = w * 4 + 1;
    const raw = Buffer.alloc(stride * h);
    for(let y = 0; y < h; y++){
      raw[y * stride] = 0;
      rgba.copy(raw, y * stride + 1, y * w * 4, (y + 1) * w * 4);
    }
    const ihdr = Buffer.alloc(13);
    ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4);
    ihdr[8] = 8; ihdr[9] = 6;
    return Buffer.concat([PNG_SIG, pngChunk('IHDR', ihdr),
      pngChunk('IDAT', zlib.deflateSync(raw, {level: 9})), pngChunk('IEND', Buffer.alloc(0))]);
  }
  function rgb565(v){
    return [Math.round(((v >> 11) & 31) * 255 / 31),
            Math.round(((v >> 5) & 63) * 255 / 63),
            Math.round((v & 31) * 255 / 31)];
  }
  function mixCol(a, b, wa, wb){
    const t = wa + wb;
    return [Math.round((a[0] * wa + b[0] * wb) / t),
            Math.round((a[1] * wa + b[1] * wb) / t),
            Math.round((a[2] * wa + b[2] * wb) / t)];
  }
  function decodeDxt(src, w, h, out, alpha){
    const bw = Math.max(1, Math.ceil(w / 4)), bh = Math.max(1, Math.ceil(h / 4));
    let s = 0;
    for(let by = 0; by < bh; by++){
      for(let bx = 0; bx < bw; bx++){
        let alphas = null;
        if(alpha){
          const a0 = src[s], a1 = src[s + 1];
          const ab = [src[s+2], src[s+3], src[s+4], src[s+5], src[s+6], src[s+7]];
          alphas = [a0, a1];
          if(a0 > a1){
            for(let i = 1; i <= 6; i++) alphas.push(Math.round(((7 - i) * a0 + i * a1) / 7));
          } else {
            for(let i = 1; i <= 4; i++) alphas.push(Math.round(((5 - i) * a0 + i * a1) / 5));
            alphas.push(0, 255);
          }
          s += 8;
          var abits = ab;
        }
        const c0 = src.readUInt16LE(s), c1 = src.readUInt16LE(s + 2);
        const bits = src.readUInt32LE(s + 4);
        s += 8;
        const col = [rgb565(c0), rgb565(c1)];
        if(c0 > c1){
          col.push(mixCol(col[0], col[1], 1, 2), mixCol(col[0], col[1], 2, 1));
        } else {
          col.push(mixCol(col[0], col[1], 1, 1), [0, 0, 0]);
        }
        for(let py = 0; py < 4; py++){
          for(let px = 0; px < 4; px++){
            const bi = py * 4 + px;
            const x = bx * 4 + px, y = by * 4 + py;
            if(x >= w || y >= h) continue;
            const c = col[(bits >>> (2 * bi)) & 3];
            let a = 255;
            if(alphas){
              const bit = bi * 3;
              const ai = ((abits[bit >> 3] >> (bit & 7)) |
                          (abits[(bit >> 3) + 1] << (8 - (bit & 7)))) & 7;
              a = alphas[ai] === undefined ? 255 : alphas[ai];
            }
            const o = (y * w + x) * 4;
            out[o] = c[0]; out[o + 1] = c[1]; out[o + 2] = c[2]; out[o + 3] = a;
          }
        }
      }
    }
    return out;
  }
  function texToPng(tex){
    if(tex.length < 40) return null;
    if(tex.toString('ascii', 0, 8) !== 'TEXV0005') return null;
    let p = 16;
    const format = tex.readUInt32LE(p); p += 4;
    p += 4;
    let w = tex.readUInt32LE(p); p += 4;
    let h = tex.readUInt32LE(p); p += 4;
    p += 8;
    // Ищем блок данных: у разных версий разное число служебных полей.
    let at = tex.indexOf('TEXB', 24);
    if(at < 0) return null;
    const version = tex.toString('ascii', at, at + 8);
    let q = at + 8;
    if(version === 'TEXB0002' || version === 'TEXB0003') q += 4;
    q += 4; // число изображений
    const mips = tex.readUInt32LE(q); q += 4;
    if(!mips) return null;
    if(version === 'TEXB0003'){
      w = tex.readUInt32LE(q); q += 4;
      h = tex.readUInt32LE(q); q += 4;
    }
    const bytes = tex.readUInt32LE(q); q += 4;
    if(!w || !h || w > 8192 || h > 8192 || !bytes || q + bytes > tex.length) return null;
    const data = tex.subarray(q, q + bytes);
    const out = Buffer.alloc(w * h * 4, 255);
    if(format === 4 || format === 7) decodeDxt(data, w, h, out, true);
    else if(format === 5 || format === 3) decodeDxt(data, w, h, out, false);
    else if(format === 0){
      const n = Math.min(w * h * 4, data.length);
      for(let i = 0; i < n; i++) out[i] = data[i];
    } else return null;
    return {buf: encodePng(out, w, h), width: w, height: h};
  }

  function imageFromPkg(pkgBuf){
    const entries = pkgEntries(pkgBuf);
    if(!entries.length) return null;
    let best = null;
    for(let i = 0; i < entries.length; i++){
      const e = entries[i];
      if(!/\.tex$/i.test(e.name)) continue;
      let img = null;
      try{ img = pngFromTex(e.data) || texToPng(e.data); }catch(err){ img = null; }
      if(!img) continue;
      if(!best || img.width * img.height > best.width * best.height) best = img;
    }
    return best;
  }

  function installWebFile(srcPath){
    resetWebDir();
    fs.copyFileSync(srcPath, path.join(WEB_DIR, 'index.html'));
    return 'index.html';
  }
  function handleWallpaperZip(zipPath){
    const st = fs.statSync(zipPath);
    if(st.size > MAX_ZIP) throw new Error('архив больше 1 ГБ');
    const buf = fs.readFileSync(zipPath);
    const z = readZip(buf);
    let pj = null;
    for(let i = 0; i < z.length; i++){
      if(!z[i].dir && /(^|\/)project\.json$/i.test(z[i].name)){ pj = z[i]; break; }
    }
    let project = {};
    if(pj){
      try{ project = JSON.parse(zipEntry(buf, pj).toString('utf8')) || {}; }catch(e){ project = {}; }
    }
    const prefix = pj ? pj.name.slice(0, pj.name.lastIndexOf('/') + 1) : '';
    const type = String(project.type || '').toLowerCase();
    const entryName = String(project.file || '');
    // Имя извлекаемого из архива файла привязано к содержимому архива:
    // повторное применение того же .zip перезаписывает файл, а не плодит копии.
    const zipKey = crypto.createHash('sha1').update(buf).digest('hex').slice(0, 8);

    if(type === 'web'){
      const entry = installWebFromZip(buf, z, prefix, entryName);
      return {kind: 'web', web: entry, note: 'Веб-обои (HTML) из архива'};
    }

    if(type === 'video' || type === ''){
      let picked = entryName ? findEntry(z, prefix + entryName) : null;
      if(!picked) picked = pickLargest(z, ['.mp4', '.webm', '.mov', '.m4v', '.ogv']);
      if(picked){
        const data = zipEntry(buf, picked);
        let ext = path.extname(picked.name).toLowerCase();
        if(ext === '.jpeg') ext = '.jpg';
        const sniff = sniffExt(data);
        if(sniff && ALLOWED_EXT.indexOf(sniff) !== -1 && sniff !== ext &&
           !(sniff === '.mp4' && ext === '.m4v')) ext = sniff;
        const w = writeMedia(data, ext, 'custom-background-' + zipKey + ext, MEDIA_DIR);
        return {kind: 'media', file: w.name, bytes: w.bytes};
      }
    }

    // Сцена Wallpaper Engine: берём исходную текстуру из scene.pkg, а не превью.
    const pkgs = z.filter(function(e){ return !e.dir && /\.pkg$/i.test(e.name); });
    for(let pi = 0; pi < pkgs.length; pi++){
      let img = null;
      try{
        img = imageFromPkg(zipEntry(buf, pkgs[pi]));
      }catch(e){ img = null; }
      if(img){
        const w = writeMedia(img.buf, '.png', 'custom-background-' + zipKey + '.png', MEDIA_DIR);
        return {kind: 'media', file: w.name, bytes: w.bytes,
          note: 'Wallpaper Engine: исходная текстура сцены ' + img.width + '×' + img.height};
      }
    }

    // scene/application (или видео не нашлось): без Wallpaper Engine сцену не проиграть,
    // поэтому берём анимированное превью из архива, если оно есть.
    let pv = findEntry(z, prefix + 'preview.gif') || findEntry(z, 'preview.gif');
    if(!pv){
      pv = findEntry(z, prefix + 'preview.jpg') || findEntry(z, 'preview.jpg') ||
           findEntry(z, prefix + 'preview.png') || findEntry(z, 'preview.png');
    }
    if(pv){
      const data = zipEntry(buf, pv);
      const ext = path.extname(pv.name).toLowerCase() === '.png' ? '.png' : (path.extname(pv.name).toLowerCase() === '.gif' ? '.gif' : '.jpg');
      const w = writeMedia(data, ext, 'custom-background-' + zipKey + ext, MEDIA_DIR);
      return {kind: 'media', file: w.name, bytes: w.bytes,
        note: 'Wallpaper Engine: сцену без движка не проиграть — поставил ' +
              (ext === '.gif' ? 'анимированное превью (GIF)' : 'превью картинкой')};
    }
    // Последний шанс: любая картинка внутри архива.
    const anyPic = pickLargest(z, ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif', '.bmp']);
    if(anyPic){
      const data = zipEntry(buf, anyPic);
      let ext = path.extname(anyPic.name).toLowerCase();
      if(ext === '.jpeg') ext = '.jpg';
      const sniff = sniffExt(data);
      if(sniff && ALLOWED_EXT.indexOf(sniff) !== -1) ext = sniff;
      const w = writeMedia(data, ext, 'custom-background-' + zipKey + ext, MEDIA_DIR);
      return {kind: 'media', file: w.name, bytes: w.bytes,
        note: 'Из архива взята картинка ' + anyPic.name.split('/').pop()};
    }
    throw new Error('в архиве нет ни видео, ни картинок, ни HTML-обоев');
  }

  // ---------- ссылка / HTML-код обоев ----------
  function decodeHtml(s){
    return String(s || '')
      .replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#0*39;/g, "'")
      .replace(/&apos;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>')
      .replace(/&#x2F;/gi, '/').replace(/&#0*47;/g, '/');
  }
  function attrsOf(tag){
    const out = {};
    const re = /([\w:.-]+)\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+))/g;
    let m;
    while((m = re.exec(tag))){
      out[m[1].toLowerCase()] = decodeHtml(m[3] !== undefined ? m[3] : (m[4] !== undefined ? m[4] : m[5]));
    }
    return out;
  }
  function absUrl(u, base){
    try{ return new URL(String(u || '').trim(), base || undefined).toString(); }catch(e){ return ''; }
  }
  function isVideoUrl(u){
    return /\.(mp4|webm|mov|m4v|ogv)(\?|#|$)/i.test(String(u || ''));
  }
  function isMediaUrl(u){
    return /\.(mp4|webm|mov|m4v|ogv|gif|jpe?g|png|webp|avif|bmp)(\?|#|$)/i.test(String(u || ''));
  }
  function htmlSources(html, base){
    const out = {video: '', image: '', embed: '', zip: ''};
    const src = String(html || '');
    const tags = src.match(/<(meta|video|source|iframe|a)\b[^>]*>/gi) || [];
    for(let i = 0; i < tags.length; i++){
      const tag = tags[i];
      const a = attrsOf(tag);
      const key = String(a.property || a.name || a.itemprop || '').toLowerCase();
      const content = a.content || '';
      const href = a.src || a.href || a['data-src'] || a['data-video-src'] || a['data-url'] || '';
      const abs = href ? absUrl(href, base) : '';
      if(!out.video && content && /^(og:video(:url|:secure_url)?|twitter:player:stream|contenturl)$/.test(key) && isMediaUrl(content)){
        out.video = absUrl(content, base);
      }
      if(!out.image && content && /^(og:image(:url|:secure_url)?|twitter:image|image)$/.test(key)){
        out.image = absUrl(content, base);
      }
      if(/^<video\b/i.test(tag) && abs && isVideoUrl(abs)) out.video = out.video || abs;
      if(/^<source\b/i.test(tag) && abs && isVideoUrl(abs)) out.video = out.video || abs;
      if(/^<iframe\b/i.test(tag) && abs && /^https?:/i.test(abs)) out.embed = out.embed || abs;
      if(/^<a\b/i.test(tag) && abs && /\.zip(\?|#|$)/i.test(abs) && !out.zip) out.zip = abs;
    }
    if(!out.video){
      const m = src.match(/https?:\/\/[^\s"'<>\\]+\.(?:mp4|webm|mov|m4v|ogv)(?:\?[^\s"'<>\\]*)?/i);
      if(m) out.video = decodeHtml(m[0]);
    }
    if(!out.image){
      const m = src.match(/https?:\/\/[^\s"'<>\\]+\.(?:gif|jpe?g|png|webp)(?:\?[^\s"'<>\\]*)?/i);
      if(m) out.image = decodeHtml(m[0]);
    }
    return out;
  }

  let tmpSeq = 0;
  function tempPath(ext){
    tmpSeq++;
    try{ fs.mkdirSync(TMP_DIR, {recursive: true}); }catch(e){}
    return path.join(TMP_DIR, 'ymbg-' + process.pid + '-' + Date.now() + '-' + tmpSeq + (ext || ''));
  }

  async function fetchToTemp(url, max, ext){
    const tmp = tempPath(ext);
    const ctl = new AbortController();
    const timer = setTimeout(function(){ ctl.abort(); }, 20 * 60 * 1000);
    try{
      const got = await fetchMedia(url, ctl.signal);
      const r = got.resp;
      if(!r.ok) throw new Error('HTTP ' + r.status);
      const ct = String(r.headers.get('content-type') || '').toLowerCase().split(';')[0].trim();
      const len = Number(r.headers.get('content-length') || 0);
      if(len && len > max) throw new Error('файл больше ' + Math.round(max / 1048576) + ' МБ');
      const saved = await webToFile(r, tmp, max);
      return {path: saved.path, bytes: saved.bytes, head: saved.head, contentType: ct, finalUrl: got.url};
    } finally { clearTimeout(timer); }
  }

  async function installMediaFromUrl(url){
    const got = await fetchToTemp(url, MAX);
    const ct = got.contentType;
    if(ct.indexOf('text/') === 0 || ct === 'application/json' || ct === 'application/xhtml+xml' || ct === 'application/xml'){
      try{ fs.unlinkSync(got.path); }catch(e){}
      throw new Error('ссылка ведёт на страницу, а не на файл');
    }
    const sniff = sniffExt(got.head);
    let ext = sniff || extFromType(ct);
    if(!ext){
      try{ ext = path.extname(new URL(got.finalUrl).pathname).toLowerCase(); }catch(e){ ext = ''; }
    }
    if(ext === '.jpeg') ext = '.jpg';
    if(!ext || ALLOWED_EXT.indexOf(ext) === -1){
      try{ fs.unlinkSync(got.path); }catch(e){}
      throw new Error('ссылка ведёт не на картинку или видео');
    }
    if(sniff && sniff !== ext && !(sniff === '.mp4' && ext === '.m4v')) ext = sniff;
    const w = adoptMedia(got.path, ext, nameFromUrl(got.finalUrl || url));
    return {kind: 'media', file: w.name, bytes: w.bytes};
  }

  async function resolveSource(raw){
    const src = String(raw || '').trim();
    if(!src) throw new Error('пустая ссылка');

    // HTML-код (embed/video/iframe) — вытаскиваем источник
    if(src.indexOf('<') !== -1){
      const found = htmlSources(src, '');
      if(found.video) return await installMediaFromUrl(found.video);
      if(found.zip) return await handleWallpaperZipFromUrl(found.zip);
      if(found.embed) return {kind: 'web', web: found.embed, note: 'HTML-обои (iframe)'};
      if(found.image) return await installMediaFromUrl(found.image);
      throw new Error('в HTML-коде не нашёл ни видео, ни iframe');
    }

    // Локальный путь
    if(/^[a-zA-Z]:[\\/]/.test(src) || src.indexOf('\\\\') === 0){
      let st;
      try{ st = fs.statSync(src); }catch(e){ throw new Error('файл не найден: ' + src); }
      if(!st.isFile()) throw new Error('это не файл');
      const ext = path.extname(src).toLowerCase();
      if(ext === '.zip'){
        const tmpZip = tempPath('.zip');
        fs.copyFileSync(src, tmpZip);
        try{ return await handleWallpaperZip(tmpZip); }
        finally{ try{ if(fs.existsSync(tmpZip)) fs.unlinkSync(tmpZip); }catch(e){} }
      }
      if(ext === '.html' || ext === '.htm'){
        const tmpHtml = tempPath(ext);
        fs.copyFileSync(src, tmpHtml);
        try{ return {kind: 'web', web: installWebFile(tmpHtml), note: 'HTML-обои'}; }
        finally{ try{ if(fs.existsSync(tmpHtml)) fs.unlinkSync(tmpHtml); }catch(e){} }
      }
      if(ALLOWED_EXT.indexOf(ext) === -1) throw new Error('формат не поддерживается: ' + ext);
      if(st.size > MAX) throw new Error('файл больше 2 ГБ');
      const tmp = tempPath(ext);
      fs.copyFileSync(src, tmp);
      const w = adoptMedia(tmp, ext, path.basename(src));
      return {kind: 'media', file: w.name, bytes: w.bytes};
    }

    const u = await assertPublicUrl(src);

    if(isMediaUrl(u.toString())){
      return await installMediaFromUrl(u.toString());
    }

    const got = await fetchToTemp(u.toString(), MAX_ZIP, '.tmp');
    const ct = got.contentType;
    try{
      if(ct === 'application/zip' || ct === 'application/x-zip-compressed' ||
         (got.head && got.head.toString('ascii', 0, 2) === 'PK')){
        const zr = await handleWallpaperZip(got.path);
        return zr;
      }
      if(ct.indexOf('text/html') === 0 || ct === 'application/xhtml+xml'){
        let html = '';
        try{ html = fs.readFileSync(got.path, 'utf8').slice(0, 4 * 1024 * 1024); }catch(e){ html = ''; }
        const found = htmlSources(html, got.finalUrl);
        if(found.video) return await installMediaFromUrl(found.video);
        if(found.zip) return await handleWallpaperZipFromUrl(found.zip);
        if(found.image) return await installMediaFromUrl(found.image);
        if(found.embed) return {kind: 'web', web: found.embed, note: 'HTML-обои (iframe со страницы)'};
        throw new Error('на странице не нашлось видео или обоев — нужна прямая ссылка или .zip');
      }
      const sniff = sniffExt(got.head);
      let ext = sniff || extFromType(ct);
      if(ext === '.jpeg') ext = '.jpg';
      if(ext && ALLOWED_EXT.indexOf(ext) !== -1){
        if(sniff && sniff !== ext) ext = sniff;
        const w = adoptMedia(got.path, ext, nameFromUrl(got.finalUrl || u.toString()));
        return {kind: 'media', file: w.name, bytes: w.bytes};
      }
      throw new Error('ссылка ведёт не на картинку, видео или архив');
    } finally {
      try{ if(fs.existsSync(got.path)) fs.unlinkSync(got.path); }catch(e){}
    }
  }

  async function handleWallpaperZipFromUrl(url){
    const got = await fetchToTemp(url, MAX_ZIP, '.zip');
    try{ return await handleWallpaperZip(got.path); }
    finally{ try{ fs.unlinkSync(got.path); }catch(e){} }
  }

  function isPrivateIPv4(ip){
    const p = String(ip).split('.').map(Number);
    if(p.length !== 4 || p.some(function(n){ return !Number.isInteger(n) || n < 0 || n > 255; })) return true;
    if(p[0] === 0 || p[0] === 10 || p[0] === 127) return true;
    if(p[0] === 100 && p[1] >= 64 && p[1] <= 127) return true;
    if(p[0] === 169 && p[1] === 254) return true;
    if(p[0] === 172 && p[1] >= 16 && p[1] <= 31) return true;
    if(p[0] === 192 && p[1] === 168) return true;
    if(p[0] === 192 && p[1] === 0 && (p[2] === 0 || p[2] === 2)) return true;
    if(p[0] === 198 && (p[1] === 18 || p[1] === 19)) return true;
    if(p[0] === 203 && p[1] === 0 && p[2] === 113) return true;
    if(p[0] >= 224) return true;
    return false;
  }
  function isPrivateIPv6(ip){
    let s = String(ip).toLowerCase();
    if(s.indexOf('::ffff:') === 0) return isPrivateIPv4(s.slice(7));
    if(s === '::' || s === '::1') return true;
    if(s.indexOf('fc') === 0 || s.indexOf('fd') === 0) return true;
    if(/^fe[89ab]/.test(s)) return true;
    if(s.indexOf('ff') === 0) return true;
    return false;
  }
  async function assertPublicUrl(raw){
    let u;
    try{ u = new URL(String(raw)); }catch(e){ throw new Error('некорректная ссылка'); }
    if(u.protocol !== 'http:' && u.protocol !== 'https:') throw new Error('разрешены только ссылки http(s)');
    if(u.username || u.password) throw new Error('ссылка с логином или паролем запрещена');
    const port = u.port || (u.protocol === 'https:' ? '443' : '80');
    if(port !== '80' && port !== '443') throw new Error('разрешены только порты 80 и 443');
    const host = u.hostname.replace(/^\[|\]$/g, '').toLowerCase();
    if(!host) throw new Error('пустой адрес');
    if(host === 'localhost' || host.endsWith('.localhost') || host.endsWith('.local') ||
       host.endsWith('.internal') || host.endsWith('.home.arpa')){
      throw new Error('локальные адреса запрещены');
    }
    const ipVer = net.isIP(host);
    if(ipVer === 4 && isPrivateIPv4(host)) throw new Error('локальные адреса запрещены');
    if(ipVer === 6 && isPrivateIPv6(host)) throw new Error('локальные адреса запрещены');
    if(ipVer === 0){
      let addrs = [];
      try{ addrs = await dns.lookup(host, {all: true, verbatim: true}); }
      catch(e){ throw new Error('не удалось проверить адрес сайта'); }
      if(!addrs.length) throw new Error('не удалось проверить адрес сайта');
      for(let i = 0; i < addrs.length; i++){
        const a = addrs[i];
        if(a.family === 4 && isPrivateIPv4(a.address)) throw new Error('локальные адреса запрещены');
        if(a.family === 6 && isPrivateIPv6(a.address)) throw new Error('локальные адреса запрещены');
      }
    }
    return u;
  }
  function sniffExt(buf){
    if(!buf || buf.length < 12) return '';
    const h = buf;
    if(h[0] === 0xFF && h[1] === 0xD8 && h[2] === 0xFF) return '.jpg';
    if(h[0] === 0x89 && h[1] === 0x50 && h[2] === 0x4E && h[3] === 0x47) return '.png';
    if(h.toString('ascii', 0, 4) === 'GIF8') return '.gif';
    if(h.toString('ascii', 0, 4) === 'RIFF' && h.toString('ascii', 8, 12) === 'WEBP') return '.webp';
    if(h.toString('ascii', 0, 2) === 'BM') return '.bmp';
    if(h.toString('ascii', 0, 4) === 'OggS') return '.ogv';
    if(h[0] === 0x1A && h[1] === 0x45 && h[2] === 0xDF && h[3] === 0xA3) return '.webm';
    if(h.toString('ascii', 4, 8) === 'ftyp'){
      const brand = h.toString('ascii', 8, 12).toLowerCase();
      if(brand === 'avif' || brand === 'avis') return '.avif';
      if(brand === 'mif1' || brand === 'heic' || brand === 'heix'){
        // HEIF-контейнер: AVIF принимаем только если совместимый бренд действительно avif.
        const head = h.toString('ascii', 0, Math.min(h.length, 64)).toLowerCase();
        if(head.indexOf('avif') !== -1 || head.indexOf('avis') !== -1) return '.avif';
        return '';
      }
      if(brand === 'qt  ') return '.mov';
      return '.mp4';
    }
    return '';
  }

  async function fetchMedia(url, signal){
    let current = String(url);
    for(let hop = 0; hop <= 5; hop++){
      await assertPublicUrl(current);
      const r = await fetch(current, {redirect: 'manual', signal: signal, headers: {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'accept': 'image/avif,image/webp,image/gif,image/*,video/*,*/*;q=0.8',
        'referer': 'https://www.pinterest.com/'
      }});
      if([301,302,303,307,308].indexOf(r.status) !== -1){
        const loc = r.headers.get('location');
        try{ if(r.body) await r.body.cancel(); }catch(e){}
        if(!loc) throw new Error('перенаправление без адреса');
        current = new URL(loc, current).toString();
        continue;
      }
      return {resp: r, url: current};
    }
    throw new Error('слишком много перенаправлений');
  }

  function allowedFileRoots(){
    try{
      const { app } = require('electron');
      return [WALL_DIR, dir, app.getPath('pictures'), app.getPath('downloads'), app.getPath('desktop'), app.getPath('videos')]
        .filter(Boolean).map(function(p){ return path.resolve(p); });
    }catch(e){ return [path.resolve(WALL_DIR), path.resolve(dir)]; }
  }
  function isInside(root, full){
    const rel = path.relative(path.resolve(root), full);
    return !!rel && !rel.startsWith('..') && !path.isAbsolute(rel);
  }
  function resolveAllowedFile(input){
    const src = path.resolve(String(input || ''));
    let real = '';
    try{ real = fs.realpathSync(src); }catch(e){ throw new Error('файл не найден'); }
    const roots = allowedFileRoots();
    let ok = false;
    for(let i = 0; i < roots.length; i++){
      let realRoot = roots[i];
      try{ realRoot = fs.realpathSync(realRoot); }catch(e){}
      if(isInside(realRoot, real)){ ok = true; break; }
    }
    if(!ok) throw new Error('можно выбирать файлы только из папок пользователя');
    const st = fs.statSync(real);
    if(!st.isFile()) throw new Error('это не файл');
    if(!st.size) throw new Error('файл пустой');
    if(st.size > MAX) throw new Error('файл больше 2 ГБ');
    return {real: real, st: st};
  }
  function writeMedia(buf, ext, name, targetDir){
    if(ALLOWED_EXT.indexOf(ext) === -1) throw new Error('формат не поддерживается');
    const base = targetDir || dir;
    try{ fs.mkdirSync(base, {recursive: true}); }catch(e){}
    const fileName = name || mediaName(ext);
    const target = path.join(base, fileName);
    fs.writeFileSync(target, buf);
    return {name: fileName, bytes: buf.length};
  }

  async function handleApply(d){
    if(!d || typeof d !== 'object' || Array.isArray(d)) throw new Error('некорректный запрос');
    const cfg = readCfg();
    const existing = __ymBgSafeMediaPath(WALL_DIR, cfg.file) ? path.basename(String(cfg.file)) : '';
    let fileName = existing;
    let saved = 0;
    let mediaChanged = false;
    let webNote = '';

    if(d.dataUri !== undefined && d.dataUri !== ''){
      const raw = String(d.dataUri);
      if(raw.length > 90 * 1024 * 1024) throw new Error('файл больше 64 МБ');
      const m = /^data:([^;,]*)(;base64)?,([\s\S]*)$/.exec(raw);
      if(!m) throw new Error('не удалось прочитать файл');
      const mime = (m[1] || '').toLowerCase();
      if(mime && mime.indexOf('image/') !== 0 && mime.indexOf('video/') !== 0 &&
         mime !== 'application/octet-stream'){
        throw new Error('формат не поддерживается');
      }
      let buf;
      try{
        buf = m[2] ? Buffer.from(m[3], 'base64') : Buffer.from(decodeURIComponent(m[3]), 'utf8');
      }catch(e){ throw new Error('не удалось прочитать файл'); }
      if(!buf.length) throw new Error('пустой файл');
      if(buf.length > 64 * 1024 * 1024) throw new Error('файл больше 64 МБ');
      const sniff = sniffExt(buf);
      if(!sniff) throw new Error('формат не поддерживается');
      // У вставленного из буфера файла нет имени — кладём его в кэш, папку не засоряем.
      const w = writeMedia(buf, sniff, '', MEDIA_DIR);
      fileName = w.name; saved = w.bytes; mediaChanged = true;
    } else if(d.url !== undefined && d.url !== ''){
      const out = await resolveSource(String(d.url));
      if(out.kind === 'web'){
        cfg.web = String(out.web || '');
        cfg.file = '';
        cfg.adaptive = false;
        cfg.webStamp = Date.now();
        mediaChanged = true;
        webNote = out.note || '';
        saved = 0;
      } else {
        cfg.web = '';
        fileName = out.file || '';
        saved = out.bytes || 0;
        mediaChanged = true;
        webNote = out.note || '';
      }
    } else if(d.file !== undefined && d.file !== ''){
      const picked = resolveAllowedFile(d.file);
      let ext = path.extname(picked.real).toLowerCase();
      if(ext === '.jpeg') ext = '.jpg';
      if(ALLOWED_EXT.indexOf(ext) === -1) throw new Error('формат не поддерживается');
      if(picked.st.size > MAX) throw new Error('файл больше 2 ГБ');
      const tmp = tempPath(ext);
      fs.copyFileSync(picked.real, tmp);
      // Выбранный из папки файл остаётся с читаемым именем и не дублируется.
      const w = adoptMedia(tmp, ext, path.basename(picked.real));
      fileName = w.name; saved = w.bytes; mediaChanged = true;
    }

    if(cfg.web && mediaChanged) cfg.file = '';
    else if(fileName) cfg.file = fileName;
    if(mediaChanged) cfg.lib = '';
    Object.keys(NUMERIC).forEach(function(k){
      if(d[k] === undefined || d[k] === null || d[k] === '') return;
      const n = Number(d[k]);
      if(Number.isFinite(n)) cfg[k] = n;
    });
    if(d.adaptive !== undefined) cfg.adaptive = !!d.adaptive;
    else if(mediaChanged) cfg.adaptive = false;
    if(d.coverStyle !== undefined) cfg.coverStyle = normalizeCoverStyle(d.coverStyle);
    if(d.discordRpc !== undefined) cfg.discordRpc = !!d.discordRpc;
    if(d.discordClientId !== undefined) cfg.discordClientId = __ymBgDiscordId(d.discordClientId);
    if(d.fit !== undefined){
      cfg.fit = normalizeFit(d.fit);
    }
    writeCfg(cfg);

    const payload = mediaChanged ? __ymBgReadPayload() : __ymBgSettingsPayload(cfg);
    __ymBgBroadcast(payload);
    const info = __ymBgMediaInfo(fileName || cfg.file);
    return {ok: true, kind: cfg.web ? 'web' : 'media', web: cfg.web || '',
            file: cfg.web ? '' : (fileName || cfg.file), bytes: saved,
            isVideo: !!info.isVideo, note: webNote || ''};
  }

  const srv = http.createServer(async function(req, res){
    res.__ymOrigin = req.headers.origin || '';
    if(!hostAllowed(req)) return reply(res, 403, {ok: false, error: 'forbidden'});
    if(!originAllowed(req)) return reply(res, 403, {ok: false, error: 'forbidden'});

    const u = (req.url || '').split('?')[0];
    if(req.method === 'OPTIONS'){
      if(!req.headers.origin) return reply(res, 403, {ok: false, error: 'forbidden'});
      res.writeHead(204, {
        'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Access-Control-Allow-Headers': 'content-type,x-ymbg-token,x-ymbg-name',
        'Access-Control-Max-Age': '600',
        'Vary': 'Origin',
        'Content-Length': '0'
      });
      return res.end();
    }
    if(req.method === 'GET' && u === '/ping'){
      return reply(res, 200, {ok: true, app: 'yandex-music'});
    }
    if(req.method === 'GET' && u === '/folder'){
      if(!authorized(req)) return reply(res, 403, {ok: false, error: 'forbidden'});
      let err = '';
      try{
        const { shell } = require('electron');
        if(shell && typeof shell.openPath === 'function'){
          err = String(await shell.openPath(WALL_DIR) || '');
        } else {
          err = 'no shell';
        }
      }catch(e){ err = String((e && e.message) || e); }
      if(err){
        try{
          const { spawn } = require('node:child_process');
          const child = spawn('explorer.exe', [WALL_DIR], {detached: true, stdio: 'ignore', windowsHide: true});
          child.on('error', function(){});
          child.unref();
          err = '';
        }catch(e){ err = String((e && e.message) || e); }
      }
      if(err) return reply(res, 500, {ok: false, error: err});
      return reply(res, 200, {ok: true, dir: WALL_DIR});
    }
    if(req.method === 'GET' && u === '/library'){
      if(!authorized(req)) return reply(res, 403, {ok: false, error: 'forbidden'});
      try{
        sweepWallDir();
        return reply(res, 200, {ok: true, dir: WALL_DIR, items: libraryItems()});
      }catch(e){
        return reply(res, 500, {ok: false, error: String((e && e.message) || e)});
      }
    }
    if(req.method === 'GET' && u === '/thumb'){
      if(!tokenEquals(queryToken(req), TOKEN)) return reply(res, 403, {ok: false, error: 'forbidden'});
      const name = queryParam(req, 'f');
      const full = safeUserFile(name, LIB_EXT);
      if(!full) return reply(res, 404, {ok: false, error: 'not found'});
      const ext = path.extname(full).toLowerCase();
      let thumb = '';
      if(ext === '.zip') thumb = zipPreview(full);
      else if(VIDEO_EXT.indexOf(ext) === -1 && ext !== '.html' && ext !== '.htm') thumb = makeImageThumb(full);
      if(!thumb) return reply(res, 404, {ok: false, error: 'no preview'});
      return serveFile(req, res, thumb, thumb);
    }
    if(req.method === 'GET' && u === '/info'){
      if(!tokenEquals(queryToken(req), TOKEN)) return reply(res, 403, {ok: false, error: 'forbidden'});
      const name = path.basename(String(queryParam(req, 'f') || ''));
      const inWall = safeFileIn(WALL_DIR, name, LIB_EXT);
      const inArch = inWall ? '' : safeFileIn(ARCHIVE_DIR, name, ['.zip', '.html', '.htm']);
      const full = inWall || inArch;
      if(!full) return reply(res, 404, {ok: false, error: 'файл не найден'});
      let st;
      try{ st = fs.statSync(full); }catch(e){ return reply(res, 404, {ok: false, error: 'файл не найден'}); }
      const ext = path.extname(name).toLowerCase();
      const out = {
        ok: true,
        name: name,
        ext: ext,
        size: st.size,
        mtime: Math.round(st.mtimeMs || 0),
        dir: inWall ? 'wallpapers' : 'archives',
        kind: VIDEO_EXT.indexOf(ext) !== -1 ? 'video' :
              IMAGE_EXT.indexOf(ext) !== -1 ? 'image' :
              (ext === '.zip' ? 'archive' : 'html')
      };
      try{
        if(out.kind === 'image' || ext === '.gif'){
          const head = fs.readFileSync(full);
          const dim = imageSize(head);
          if(dim && dim.w && dim.h){
            out.width = dim.w; out.height = dim.h;
            out.megapixels = (dim.w * dim.h) / 1000000;
            const r = dim.w / dim.h;
            out.aspect = Math.abs(r - 16 / 9) < 0.02 ? '16:9' :
                         Math.abs(r - 9 / 16) < 0.02 ? '9:16' :
                         Math.abs(r - 21 / 9) < 0.02 ? '21:9' :
                         Math.abs(r - 4 / 3) < 0.02 ? '4:3' :
                         Math.abs(r - 1) < 0.02 ? '1:1' : (dim.w + ':' + dim.h);
          }
        } else if(out.kind === 'video'){
          if(st.size <= 512 * 1024 * 1024){
            const buf = fs.readFileSync(full);
            const meta = mp4Meta(buf) || webmMeta(buf) || {};
            if(meta.width) out.width = meta.width;
            if(meta.height) out.height = meta.height;
            if(out.width && out.height) out.megapixels = (out.width * out.height) / 1000000;
            if(meta.duration) out.duration = meta.duration;
            if(meta.fps && isFinite(meta.fps)) out.fps = meta.fps;
            if(meta.frames) out.frames = meta.frames;
            if(meta.codec) out.codec = meta.codec;
            if(meta.bitrate && isFinite(meta.bitrate)) out.bitrate = meta.bitrate;
          }
        } else if(ext === '.zip'){
          if(st.size <= 512 * 1024 * 1024){
            const buf = fs.readFileSync(full);
            const zm = zipMeta(full, buf);
            if(zm.entries) out.entries = zm.entries;
            if(zm.type) out.type = zm.type;
            if(zm.preview) out.preview = zm.preview;
            try{
              const z = readZip(buf);
              const pkgEntry = z.filter(function(e){ return !e.dir && /\.pkg$/i.test(e.name); })[0];
              if(pkgEntry){
                const img = imageFromPkg(zipEntry(buf, pkgEntry));
                if(img) out.texture = img.width + ' × ' + img.height;
              }
            }catch(e){}
          }
        }
      }catch(e){}
      return reply(res, 200, out);
    }

    if(req.method === 'POST' && u === '/open'){
      if(!authorized(req)) return reply(res, 403, {ok: false, error: 'forbidden'});
      const ct = String(req.headers['content-type'] || '').toLowerCase();
      if(ct.indexOf('application/json') !== 0) return reply(res, 415, {ok: false, error: 'нужен application/json'});
      let body;
      try{ body = await readJsonBody(req, 64 * 1024); }
      catch(e){ return reply(res, 400, {ok: false, error: String((e && e.message) || e)}); }
      const name = path.basename(String((body && body.f) || ''));
      const wantFolder = String((body && body.mode) || 'file') === 'folder';
      const inWall = safeFileIn(WALL_DIR, name, LIB_EXT);
      const inArch = inWall ? '' : safeFileIn(ARCHIVE_DIR, name, ['.zip', '.html', '.htm']);
      const full = inWall || inArch;
      if(!full) return reply(res, 404, {ok: false, error: 'файл не найден'});
      let err = '';
      try{
        const electron = require('electron');
        const shell = electron && electron.shell;
        if(wantFolder){
          // showItemInFolder — штатный способ Electron: открывает проводник
          // и выделяет файл, без возни с аргументами explorer.exe.
          if(shell && typeof shell.showItemInFolder === 'function'){
            shell.showItemInFolder(full);
          } else {
            const { spawn } = require('node:child_process');
            const child = spawn('explorer.exe', ['/select,"' + full + '"'], {detached: true, stdio: 'ignore'});
            child.on('error', function(){});
            child.unref();
          }
        } else {
          if(shell && typeof shell.openPath === 'function'){
            err = String(await shell.openPath(full) || '');
          }
          if(err){
            const { spawn } = require('node:child_process');
            const child = spawn('cmd.exe', ['/c', 'start', '', full], {detached: true, stdio: 'ignore', windowsHide: true});
            child.on('error', function(){});
            child.unref();
            err = '';
          }
        }
      }catch(e){ err = String((e && e.message) || e); }
      if(err) return reply(res, 500, {ok: false, error: err});
      return reply(res, 200, {ok: true});
    }

    if(req.method === 'POST' && u === '/remove'){
      if(!authorized(req)) return reply(res, 403, {ok: false, error: 'forbidden'});
      const ct = String(req.headers['content-type'] || '').toLowerCase();
      if(ct.indexOf('application/json') !== 0) return reply(res, 415, {ok: false, error: 'нужен application/json'});
      let body;
      try{ body = await readJsonBody(req, 256 * 1024); }
      catch(e){ return reply(res, 400, {ok: false, error: String((e && e.message) || e)}); }
      const name = path.basename(String((body && body.f) || ''));
      const inWall = safeFileIn(WALL_DIR, name, LIB_EXT);
      const inArch = inWall ? '' : safeFileIn(ARCHIVE_DIR, name, ['.zip', '.html', '.htm']);
      const full = inWall || inArch;
      if(!full) return reply(res, 404, {ok: false, error: 'файл не найден'});
      try{ fs.unlinkSync(full); }
      catch(e){ return reply(res, 500, {ok: false, error: 'не удалось удалить: файл занят'}); }
      const cfg = readCfg();
      let changed = false;
      if(path.basename(String(cfg.file || '')) === name){ cfg.file = ''; changed = true; }
      if(path.basename(String(cfg.lib || '')) === name){
        cfg.lib = '';
        if(cfg.file === name) cfg.file = '';
        changed = true;
      }
      if(changed){
        try{ writeCfg(cfg); }catch(e){}
        try{ __ymBgBroadcast(__ymBgReadPayload()); }catch(e){}
      }
      return reply(res, 200, {ok: true, removed: name});
    }

    if(req.method === 'GET' && u === '/media'){
      if(!tokenEquals(queryToken(req), TOKEN)) return reply(res, 403, {ok: false, error: 'forbidden'});
      const want = queryParam(req, 'f');
      const cfg = readCfg();
      const full = want ? safeMediaFile(want, ALLOWED_EXT) : __ymBgSafeMediaPath(WALL_DIR, cfg.file);
      if(!full) return reply(res, 404, {ok: false, error: 'no media'});
      return serveFile(req, res, full, full);
    }

    if((req.method === 'GET' || req.method === 'HEAD') && u.indexOf('/web/') === 0){
      const m = /^\/web\/([^/]+)\/(.*)$/.exec(u);
      if(!m || !tokenEquals(decodeURIComponent(m[1]), TOKEN)) return reply(res, 403, {ok: false, error: 'forbidden'});
      let rel = '';
      try{ rel = decodeURIComponent(m[2] || ''); }catch(e){ rel = ''; }
      if(!rel) rel = 'index.html';
      let full = safeWebPath(rel);
      try{
        if(full && fs.statSync(full).isDirectory()){
          rel = rel.replace(/\/+$/, '') + '/index.html';
          full = safeWebPath(rel);
        }
      }catch(e){}
      if(!full) return reply(res, 404, {ok: false, error: 'not found'});
      return serveFile(req, res, full, rel);
    }

    if(req.method === 'POST' && (u === '/upload' || u === '/wallpaper')){
      if(!authorized(req)) return reply(res, 403, {ok: false, error: 'forbidden'});
      const isWallpaper = u === '/wallpaper';
      const tmp = tempPath(isWallpaper ? '.wp' : '.up');
      let saved;
      try{ saved = await saveStream(req, tmp, isWallpaper ? MAX_ZIP : MAX); }
      catch(e){
        return reply(res, 413, {ok: false, error: String((e && e.message) || e)});
      }
      try{
        let out;
        if(isWallpaper){
          let name = String(req.headers['x-ymbg-name'] || '');
          try{ name = decodeURIComponent(name); }catch(e){}
          const ext = path.extname(name).toLowerCase();
          if(ext === '.zip' || ext === '.html' || ext === '.htm'){
            // Оригинал архива остаётся в отдельной папке и виден в галерее;
            // в папку фонов он не попадает.
            try{
              const safeName = path.basename(name).replace(/[\\/:*?"<>|]/g, '_');
              if(safeName && safeName.charAt(0) !== '.'){
                const adst = path.join(ARCHIVE_DIR, safeName);
                if(!fs.existsSync(adst)) fs.copyFileSync(tmp, adst);
              }
            }catch(e){}
          }
          if(ext === '.html' || ext === '.htm'){
            // HTML-обои распаковываются в кэш: в папке пользователя остаются только его фоны.
            out = {kind: 'web', web: installWebFile(tmp), bytes: saved.bytes, note: 'HTML-обои'};
          } else if(ext === '.zip'){
            out = handleWallpaperZip(tmp);
          } else {
            const sniff = sniffExt(saved.head) || (ALLOWED_EXT.indexOf(ext) !== -1 ? ext : '');
            if(!sniff) throw new Error('формат не поддерживается');
            const w = adoptMedia(tmp, sniff, name);
            out = {kind: 'media', file: w.name, bytes: w.bytes};
          }
        } else {
          const sniff = sniffExt(saved.head);
          if(!sniff || ALLOWED_EXT.indexOf(sniff) === -1) throw new Error('формат не поддерживается');
          const rawName = String(req.headers['x-ymbg-name'] || '');
          const w = adoptMedia(tmp, sniff, rawName);
          out = {kind: 'media', file: w.name, bytes: w.bytes};
          const info = __ymBgMediaInfo(w.name);
          out.isVideo = !!info.isVideo;
        }
        const cfg = readCfg();
        cfg.adaptive = false;
        if(out.kind === 'web'){
          cfg.web = String(out.web || '');
          cfg.file = '';
          cfg.webStamp = Date.now();
        }
        else { cfg.web = ''; cfg.file = out.file; }
        cfg.lib = '';
        writeCfg(cfg);
        __ymBgBroadcast(__ymBgReadPayload());
        try{ if(fs.existsSync(tmp)) fs.unlinkSync(tmp); }catch(e){}
        return reply(res, 200, Object.assign({ok: true}, out));
      }catch(e){
        try{ if(fs.existsSync(tmp)) fs.unlinkSync(tmp); }catch(_){}
        return reply(res, 400, {ok: false, error: String((e && e.message) || e)});
      }
    }

    if(req.method === 'POST' && u === '/use'){
      if(!authorized(req)) return reply(res, 403, {ok: false, error: 'forbidden'});
      const ct = String(req.headers['content-type'] || '').toLowerCase();
      if(ct.indexOf('application/json') !== 0) return reply(res, 415, {ok: false, error: 'нужен application/json'});
      let body;
      try{ body = await readJsonBody(req, 256 * 1024); }
      catch(e){ return reply(res, 400, {ok: false, error: String((e && e.message) || e)}); }
      const name = path.basename(String((body && body.f) || ''));
      const full = safeUserFile(name, LIB_EXT);
      if(!full) return reply(res, 400, {ok: false, error: 'файл не найден в папке фонов'});
      try{
        const ext = path.extname(full).toLowerCase();
        let out = {kind: 'media', file: name};
        if(ext === '.zip'){
          out = await handleWallpaperZip(full);
        } else if(ext === '.html' || ext === '.htm'){
          out = {kind: 'web', web: installWebFile(full), note: 'HTML-обои'};
        }
        const cfg = readCfg();
        cfg.adaptive = false;
        cfg.webStamp = Date.now();
        if(out.kind === 'web'){
          cfg.web = String(out.web || '');
          cfg.file = '';
        } else {
          cfg.web = '';
          cfg.file = out.file || name;
        }
        cfg.lib = name;
        writeCfg(cfg);
        __ymBgBroadcast(__ymBgReadPayload());
        return reply(res, 200, {ok: true, kind: cfg.web ? 'web' : 'media',
          file: cfg.web ? '' : cfg.file, web: cfg.web || '', note: out.note || ''});
      }catch(e){
        return reply(res, 400, {ok: false, error: String((e && e.message) || e)});
      }
    }

    if(req.method === 'POST' && u === '/rpc'){
      if(!authorized(req)) return reply(res, 403, {ok: false, error: 'forbidden'});
      const ct = String(req.headers['content-type'] || '').toLowerCase();
      if(ct.indexOf('application/json') !== 0) return reply(res, 415, {ok: false, error: 'нужен application/json'});
      let body;
      try{ body = await readJsonBody(req, 64 * 1024); }
      catch(e){ return reply(res, 400, {ok: false, error: String((e && e.message) || e)}); }
      const num = function(v){ const n = Number(v); return Number.isFinite(n) && n >= 0 ? n : 0; };
      const prevTitle = global.__ymBgNow && global.__ymBgNow.title;
      global.__ymBgNow = {
        title: String((body && body.title) || '').slice(0, 256),
        artist: String((body && body.artist) || '').slice(0, 256),
        album: String((body && body.album) || '').slice(0, 256),
        cover: String((body && body.cover) || '').slice(0, 512),
        playing: !!(body && body.playing),
        pos: num(body && body.pos),
        dur: num(body && body.dur),
        at: Date.now()
      };
      if(global.__ymBgDiscordLog && global.__ymBgNow.title && global.__ymBgNow.title !== prevTitle){
        global.__ymBgDiscordLog('трек: ' + (global.__ymBgNow.artist || '?') + ' — ' + global.__ymBgNow.title +
          (global.__ymBgNow.playing ? '' : ' (пауза)'));
      }
      return reply(res, 200, {ok: true});
    }
    if(req.method === 'GET' && u === '/rpc'){
      if(!authorized(req)) return reply(res, 403, {ok: false, error: 'forbidden'});
      const st = (global.__ymBgDiscordStatus && global.__ymBgDiscordStatus()) || {status: 'off'};
      return reply(res, 200, {ok: true, status: st.status || 'off', error: st.error || ''});
    }

    if(req.method === 'POST' && u === '/apply'){
      if(!authorized(req)) return reply(res, 403, {ok: false, error: 'forbidden'});
      const ct = String(req.headers['content-type'] || '').toLowerCase();
      if(ct.indexOf('application/json') !== 0) return reply(res, 415, {ok: false, error: 'нужен application/json'});
      let chunks = [];
      let total = 0;
      let closed = false;
      req.on('data', function(c){
        if(closed) return;
        total += c.length;
        if(total > MAX_JSON){
          closed = true;
          try{ reply(res, 413, {ok: false, error: 'слишком большой запрос'}); }catch(e){}
          req.destroy();
          return;
        }
        chunks.push(c);
      });
      req.on('end', function(){
        if(closed) return;
        closed = true;
        let body = {};
        try{ body = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}'); }
        catch(e){ return reply(res, 400, {ok: false, error: 'bad json'}); }
        handleApply(body)
          .then(function(r){ reply(res, 200, r); })
          .catch(function(e){ reply(res, 500, {ok: false, error: String((e && e.message) || e)}); });
      });
      req.on('error', function(){
        if(closed) return;
        closed = true;
        try{ reply(res, 400, {ok: false, error: 'bad request'}); }catch(e){}
      });
      return;
    }
    reply(res, 404, {ok: false, error: 'not found'});
  });
  srv.on('error', function(e){
    try{ console.error('[ymbg] server error:', (e && e.message) || e); }catch(_){}
  });
  try{ ensureDirs(); }catch(e){}
  try{ migrateLayout(); }catch(e){}
  try{ sweepWallDir(); }catch(e){}
  try{ cleanTmp(); }catch(e){}
  try{ srv.listen(PORT, '127.0.0.1'); }
  catch(e){ try{ console.error('[ymbg] listen failed:', (e && e.message) || e); }catch(_){} }
  try{ __ymBgDiscordStart(); }catch(e){}
}

function __ymApplyCustomBackground(wc){
  __ymBgStartServer();
  try{
    const payload = __ymBgReadPayload();
    wc.executeJavaScript('window.__YMBG__=' + JSON.stringify(payload) + ';' + ENGINE_JS, true)
      .catch(function(){});
  }catch(e){}
}
""".replace("__PRESET_IDS__", PRESET_IDS_JSON).replace("ENGINE_JS", json.dumps(ENGINE))

ANCHOR_FUNC = "const electron=require('electron')"
ANCHOR_HANDLER = 'webContents.on("did-finish-load", () => {'
ANCHOR_INSERT = 'webContents.insertCSS(`'

# Версия патча считается от содержимого: любое изменение кода => перепатчивание.
MARKER_VERSION = "__ymBg" + hashlib.sha256(
    (INJECT_FUNC + ENGINE).encode("utf-8")
).hexdigest()[:10]

def copy_retry(src, dst, attempts=60, delay=0.25):
    last = None
    for _ in range(attempts):
        try:
            shutil.copy2(src, dst)
            return
        except PermissionError as e:
            last = e
            time.sleep(delay)
    raise last


def replace_retry(src, dst, attempts=60, delay=0.25):
    last = None
    for _ in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError as e:
            last = e
            time.sleep(delay)
    raise last


def read_asar(path):
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        total = f.tell()
        f.seek(0)
        head = f.read(16)
        if len(head) < 16:
            raise ValueError("asar too small")
        header_size = struct.unpack("<I", head[4:8])[0]
        if header_size < 8 or header_size > 64 * 1024 * 1024 or 8 + header_size > total:
            raise ValueError("invalid asar header size")
        f.seek(8)
        hdr = f.read(header_size)
        start = hdr.find(b"{")
        if start < 0:
            raise ValueError("asar header json not found")
        header, _ = json.JSONDecoder().raw_decode(hdr[start:].decode("utf-8", "ignore"))
        data_start = 8 + header_size
        f.seek(data_start)
        data = f.read()
    return header, data


def integrity(buf):
    blocks = [hashlib.sha256(buf[i:i + BLOCK]).hexdigest()
              for i in range(0, len(buf), BLOCK)]
    return {
        "algorithm": "SHA256",
        "hash": hashlib.sha256(buf).hexdigest(),
        "blockSize": BLOCK,
        "blocks": blocks,
    }


def collect_files(node, prefix=""):
    out = []
    for name, meta in node.get("files", {}).items():
        p = f"{prefix}/{name}" if prefix else name
        if "files" in meta:
            out.extend(collect_files(meta, p))
        else:
            out.append((p, meta))
    return out


def find_node(header, path):
    node = header
    for part in path.split("/"):
        node = node.get("files", {}).get(part)
        if node is None:
            return None
    return node


def extract(header, data, path):
    meta = find_node(header, path)
    if not meta:
        return None
    o, s = int(meta["offset"]), int(meta["size"])
    return data[o:o + s]


def write_asar(path, header, files, blobs):
    data = bytearray()
    for p, meta in files:
        chunk = blobs[p]
        meta["size"] = len(chunk)
        meta["offset"] = str(len(data))
        meta["integrity"] = integrity(chunk)
        data += chunk

    json_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    pad = (-(4 + len(json_bytes))) % 4
    str_payload = struct.pack("<I", len(json_bytes)) + json_bytes + b"\0" * pad
    header_buf = struct.pack("<I", len(str_payload)) + str_payload
    size_buf = struct.pack("<I", 4) + struct.pack("<I", len(header_buf))

    with open(path, "wb") as f:
        f.write(size_buf)
        f.write(header_buf)
        f.write(data)


def read_version(header, data):
    raw = extract(header, data, "package.json")
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8")).get("version")
    except Exception:
        return None


def cmd_apply(asar):
    backup = asar + ".orig"
    cur_header, cur_data = read_asar(asar)
    cur_version = read_version(cur_header, cur_data)
    cur_index = extract(cur_header, cur_data, "index.js") or b""

    if MARKER.encode() in cur_index and MARKER_VERSION.encode() in cur_index:
        print(f"already patched (version {cur_version})")
        return

    backup_ok = False
    if os.path.exists(backup):
        try:
            bh, bd = read_asar(backup)
            backup_ok = read_version(bh, bd) == cur_version
        except Exception:
            backup_ok = False

    if not backup_ok:
        copy_retry(asar, backup)
        print("backup:", backup)

    # Всегда патчим от чистой копии — так обновление версии патча не требует ручных действий.
    header, data = read_asar(backup)
    files = collect_files(header)
    files.sort(key=lambda x: int(x[1]["offset"]))

    index_js = (extract(header, data, "index.js") or b"").decode("utf-8")
    if MARKER in index_js:
        shutil.copy2(asar, asar + ".broken")
        sys.exit("backup is already patched; restore app.asar from a clean install")

    if ANCHOR_FUNC not in index_js:
        sys.exit("anchor for function insert not found")
    index_js = index_js.replace(
        ANCHOR_FUNC,
        "// " + MARKER_VERSION + "\n" + INJECT_FUNC + "\n" + ANCHOR_FUNC,
        1,
    )

    if ANCHOR_HANDLER not in index_js or ANCHOR_INSERT not in index_js:
        sys.exit("did-finish-load anchor not found")
    index_js = index_js.replace(
        ANCHOR_HANDLER + "\n    " + ANCHOR_INSERT,
        ANCHOR_HANDLER + "\n    " + MARKER + "(webContents);\n    " + ANCHOR_INSERT,
        1,
    )

    blobs = {}
    for p, meta in files:
        o, s = int(meta["offset"]), int(meta["size"])
        blobs[p] = data[o:o + s]
    blobs["index.js"] = index_js.encode("utf-8")

    tmp = asar + ".new"
    write_asar(tmp, header, files, blobs)
    replace_retry(tmp, asar)
    print(f"patched app.asar (version {cur_version})")


def cmd_restore(asar):
    backup = asar + ".orig"
    if not os.path.exists(backup):
        sys.exit("no backup found: " + backup)
    tmp = asar + ".restore.tmp"
    try:
        copy_retry(backup, tmp)
        replace_retry(tmp, asar)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    print("restored app.asar from", backup)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["apply", "restore"])
    ap.add_argument("--asar", default=os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Programs", "YandexMusic", "resources", "app.asar"))
    args = ap.parse_args()
    if not os.path.exists(args.asar):
        sys.exit("app.asar not found: " + args.asar)
    if args.action == "apply":
        cmd_apply(args.asar)
    else:
        cmd_restore(args.asar)


if __name__ == "__main__":
    main()
