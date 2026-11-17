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

# Движок фона вставляется в renderer через executeJavaScript после загрузки страницы.
ENGINE = r"""
(function(){
  'use strict';
  if(window.__ymBgV2) return;
  window.__ymBgV2 = true;

  var C = window.__YMBG__ || {};
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
    token: C.token || ''
  };

  function buildStyle(){
    return [
    'html,body{background:transparent !important;}',
    '#ym-bg{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden;background:#0d0d0d;',
      '--ym-blur:' + cfg.blur + 'px;--ym-bright:' + cfg.brightness + ';--ym-dim:' + cfg.dim + ';',
      '--ym-vig:' + cfg.vignette + ';--ym-nav:' + cfg.navbarDim + ';}',
    '#ym-bg .ym-layer{position:absolute;inset:0;opacity:0;transition:opacity ' + cfg.fade + 'ms ease;}',
    '#ym-bg .ym-layer.active{opacity:1;}',
    '#ym-bg .ym-media{width:100%;height:100%;object-fit:cover;object-position:center;display:block;',
      'filter:brightness(var(--ym-bright)) blur(var(--ym-blur));transform:scale(1.02) translateZ(0);}',
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
    '[class*="PlayerBarDesktopWithBackgroundProgressBar_root"]',
      '{background:rgba(14,14,14,' + (1 - cfg.playerTransparency).toFixed(2) + ') !important;' +
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
    ].join('\n');
  }
  var STYLE = buildStyle();

  function ensureStyle(){
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

  function setMedia(layer, url, isVideo){
    if(!layer) return;
    layer.textContent = '';
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
    }
    el.className = 'ym-media';
    layer.appendChild(el);
  }

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
      else setMedia(inactive, url, isVideo);
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
    '.ym-page-body{flex:1;min-height:0;overflow:auto;padding:10px 28px 14px;}',
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
    '#ym-nav-bg:hover{color:#fff;}'
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
          '<button class="ym-btn ghost ym-folder" style="width:100%;margin-top:8px">Открыть папку с фонами</button>',
          '<label class="ym-switch-row"><span>Адаптивный фон — обложка играющего трека</span><input type="checkbox" class="ym-adapt"><span class="ym-switch"></span></label>',
        '</section>',
      '</div>',
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
    var top = Math.round(r.top);
    var bottom = Math.min(r.bottom, window.innerHeight - 104);
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
    var statusEl = q('.ym-status');
    var pushTimer = null;

    function status(text, bad){
      statusEl.textContent = text || '';
      statusEl.style.color = bad ? '#ff8a8a' : 'rgba(255,255,255,.45)';
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
        adaptive: !!adaptEl.checked
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

    dimEl.value = cfg.dim; blurEl.value = cfg.blur; brightEl.value = cfg.brightness;
    vigEl.value = (cfg.vignette === undefined ? 0 : cfg.vignette);
    navEl.value = (cfg.navbarDim === undefined ? 0.35 : cfg.navbarDim);
    ptransEl.value = (cfg.playerTransparency === undefined ? 0.48 : cfg.playerTransparency);
    pblurEl.value = (cfg.playerBlur === undefined ? 20 : cfg.playerBlur);
    psatEl.value = (cfg.playerSaturate === undefined ? 1.15 : cfg.playerSaturate);
    adaptEl.checked = !!cfg.adaptive;
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
    q('.ym-folder').addEventListener('click', function(){
      fetch('http://127.0.0.1:47823/folder', {
        method: 'GET',
        headers: {'x-ymbg-token': cfg.token || ''}
      })
        .then(function(r){ return r.json(); })
        .then(function(r){ if(!r || !r.ok) status('Не удалось открыть папку', true); })
        .catch(function(){ status('Не удалось открыть папку', true); });
    });
    [dimEl, blurEl, brightEl, vigEl, navEl, ptransEl, pblurEl, psatEl].forEach(function(el){
      el.addEventListener('input', function(){ labels(); push(400); });
    });
    adaptEl.addEventListener('change', function(){ push(0); });
    q('.ym-apply').addEventListener('click', function(){ push(0); status('Применено'); });
    q('.ym-reset').addEventListener('click', function(){
      dimEl.value = 0.25; blurEl.value = 0; brightEl.value = 1; vigEl.value = 0; navEl.value = 0.35;
      ptransEl.value = 0.48; pblurEl.value = 20; psatEl.value = 1.15;
      adaptEl.checked = false;
      labels();
      push(0);
      status('Сброшено');
    });

    document.addEventListener('keydown', panelEsc);
    document.addEventListener('click', navGuard, true);
    window.addEventListener('resize', positionPage);
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

INJECT_FUNC = r"""
function __ymBgUserDir(){
  return require('electron').app.getPath('userData');
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

function __ymBgSafeMediaPath(dir, name){
  const path = require('node:path');
  const base = path.basename(String(name || ''));
  const ext = path.extname(base).toLowerCase();
  const allowed = ['.jpg','.jpeg','.png','.webp','.gif','.avif','.bmp',
                   '.mp4','.webm','.mov','.m4v','.ogv'];
  if(!/^custom-background(?:-[a-z0-9]{1,16})?\.[a-z0-9]{1,6}$/i.test(base) || allowed.indexOf(ext) === -1) return '';
  const full = path.resolve(dir, base);
  const rel = path.relative(dir, full);
  if(!rel || rel.startsWith('..') || path.isAbsolute(rel)) return '';
  return full;
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

function __ymBgReadPayload(){
  const __fs = require('node:fs');
  const __path = require('node:path');
  const __dir = __ymBgUserDir();

  let __cfg = {};
  try{
    let __raw = __fs.readFileSync(__path.join(__dir, 'custom-background.json'), 'utf8') || '';
    __raw = __raw.replace(/^\uFEFF/, '');
    __cfg = JSON.parse(__raw) || {};
  }catch(e){ __cfg = {}; }

  const __fileRaw = String(__cfg.file || '');
  const __fileBase = __path.basename(__fileRaw);
  const __file = __ymBgSafeMediaPath(__dir, __fileBase) ? __fileBase : '';
  const __info = __ymBgMediaInfo(__file);
  const __full = __file ? __ymBgSafeMediaPath(__dir, __file) : '';

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
    const __cssPath = __path.join(__dir, 'custom-background.css');
    const __cssSt = __fs.statSync(__cssPath);
    if(__cssSt.isFile() && __cssSt.size <= 1024 * 1024){
      __css = __fs.readFileSync(__cssPath, 'utf8') || '';
    }
  }catch(e){ __css = ''; }

  return {
    adaptive: !!__cfg.adaptive,
    src: __src,
    isVideo: __isVideo,
    web: String(__cfg.web || ''),
    webStamp: Number(__cfg.webStamp) || 0,
    webBase: __cfg.web ? ('http://127.0.0.1:47823/web/' + encodeURIComponent(__ymBgToken()) + '/') : '',
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
    web: String(cfg.web || ''),
    webStamp: Number(cfg.webStamp) || 0,
    webBase: cfg.web ? ('http://127.0.0.1:47823/web/' + encodeURIComponent(__ymBgToken()) + '/') : '',
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
  const PORT = 47823;
  const MAX = 2048 * 1024 * 1024;      // 2 ГБ: видео больше не упирается в 80 МБ
  const MAX_ZIP = 1024 * 1024 * 1024;  // архив обоев
  const MAX_JSON = 8 * 1024 * 1024;    // обычные настройки
  const ALLOWED_ORIGIN = 'music-application://desktop';
  const ALLOWED_EXT = ['.jpg','.png','.webp','.gif','.avif','.bmp','.mp4','.webm','.mov','.m4v','.ogv'];
  const WEB_DIR = path.join(dir, 'web-wallpaper');
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
    if(out.file !== undefined) out.file = path.basename(String(out.file || ''));
    return out;
  }

  function readCfg(){
    try{
      const p = path.join(dir, 'custom-background.json');
      const st = fs.statSync(p);
      if(!st.isFile() || st.size > 1024 * 1024) return {};
      let raw = fs.readFileSync(p, 'utf8') || '';
      raw = raw.replace(/^\uFEFF/, '');
      const cfg = JSON.parse(raw);
      if(!cfg || typeof cfg !== 'object' || Array.isArray(cfg)) return {};
      return clampNumbers(cfg);
    }catch(e){ return {}; }
  }
  function writeCfg(cfg){
    const target = path.join(dir, 'custom-background.json');
    const tmp = path.join(dir, '.custom-background.json.tmp');
    fs.writeFileSync(tmp, JSON.stringify(clampNumbers(cfg), null, 2), 'utf8');
    fs.renameSync(tmp, target);
  }
  function cleanMedia(keep){
    try{
      fs.readdirSync(dir).forEach(function(n){
        if(/^\.?custom-background(?:-[a-z0-9]{1,16})?\./i.test(n) && n !== keep){
          const ext = path.extname(n).toLowerCase();
          if(['.css', '.json', '.bak'].indexOf(ext) === -1){
            try{ fs.unlinkSync(path.join(dir, n)); }catch(e){}
          }
        }
      });
    }catch(e){}
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
  function queryToken(req){
    try{ return new URL(req.url, 'http://127.0.0.1').searchParams.get('t') || ''; }catch(e){ return ''; }
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
  function adoptMedia(tmpPath, ext){
    if(ALLOWED_EXT.indexOf(ext) === -1) throw new Error('формат не поддерживается');
    const name = mediaName(ext);
    const target = path.join(dir, name);
    try{ fs.renameSync(tmpPath, target); }
    catch(e){
      fs.copyFileSync(tmpPath, target);
      try{ fs.unlinkSync(tmpPath); }catch(_){}
    }
    try{ cleanMedia(name); }catch(e){}
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
        const w = writeMedia(data, ext);
        return {kind: 'media', file: w.name, bytes: w.bytes};
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
      const w = writeMedia(data, ext);
      return {kind: 'media', file: w.name, bytes: w.bytes,
        note: 'Wallpaper Engine: сцену без движка не проиграть — поставил ' +
              (ext === '.gif' ? 'анимированное превью (GIF)' : 'превью картинкой')};
    }
    throw new Error('в архиве нет ни видео, ни HTML-обоев, ни превью');
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
    return path.join(dir, '.ymbg-tmp-' + process.pid + '-' + Date.now() + '-' + tmpSeq + (ext || ''));
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
    const w = adoptMedia(got.path, ext);
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
      if(ext === '.zip') return await handleWallpaperZip(src);
      if(ext === '.html' || ext === '.htm') return {kind: 'web', web: installWebFile(src), note: 'HTML-обои'};
      if(ALLOWED_EXT.indexOf(ext) === -1) throw new Error('формат не поддерживается: ' + ext);
      if(st.size > MAX) throw new Error('файл больше 2 ГБ');
      const tmp = tempPath(ext);
      fs.copyFileSync(src, tmp);
      const w = adoptMedia(tmp, ext);
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
        const w = adoptMedia(got.path, ext);
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
      return [dir, app.getPath('pictures'), app.getPath('downloads'), app.getPath('desktop'), app.getPath('videos')]
        .filter(Boolean).map(function(p){ return path.resolve(p); });
    }catch(e){ return [path.resolve(dir)]; }
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
  function writeMedia(buf, ext){
    if(ALLOWED_EXT.indexOf(ext) === -1) throw new Error('формат не поддерживается');
    const name = mediaName(ext);
    const target = path.join(dir, name);
    fs.writeFileSync(target, buf);
    try{ cleanMedia(name); }catch(e){}
    return {name: name, bytes: buf.length};
  }

  async function handleApply(d){
    if(!d || typeof d !== 'object' || Array.isArray(d)) throw new Error('некорректный запрос');
    const cfg = readCfg();
    const existing = __ymBgSafeMediaPath(dir, cfg.file) ? path.basename(String(cfg.file)) : '';
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
      const w = writeMedia(buf, sniff);
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
        try{ cleanMedia(''); }catch(e){}
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
      const w = adoptMedia(tmp, ext);
      fileName = w.name; saved = w.bytes; mediaChanged = true;
    }

    if(cfg.web && mediaChanged) cfg.file = '';
    else if(fileName) cfg.file = fileName;
    Object.keys(NUMERIC).forEach(function(k){
      if(d[k] === undefined || d[k] === null || d[k] === '') return;
      const n = Number(d[k]);
      if(Number.isFinite(n)) cfg[k] = n;
    });
    if(d.adaptive !== undefined) cfg.adaptive = !!d.adaptive;
    else if(mediaChanged) cfg.adaptive = false;
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
      try{
        const { spawn } = require('node:child_process');
        const child = spawn('explorer.exe', [dir], {detached: true, stdio: 'ignore', windowsHide: true});
        child.unref();
        return reply(res, 200, {ok: true});
      }catch(e){
        return reply(res, 500, {ok: false, error: String((e && e.message) || e)});
      }
    }
    if(req.method === 'GET' && u === '/media'){
      if(!tokenEquals(queryToken(req), TOKEN)) return reply(res, 403, {ok: false, error: 'forbidden'});
      const cfg = readCfg();
      const full = __ymBgSafeMediaPath(dir, cfg.file);
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
          if(ext === '.html' || ext === '.htm'){
            const entry = installWebFile(tmp);
            out = {kind: 'web', web: entry, bytes: saved.bytes, note: 'HTML-обои'};
          } else if(ext === '.zip'){
            out = handleWallpaperZip(tmp);
          } else {
            const sniff = sniffExt(saved.head) || (ALLOWED_EXT.indexOf(ext) !== -1 ? ext : '');
            if(!sniff) throw new Error('формат не поддерживается');
            const w = adoptMedia(tmp, sniff);
            out = {kind: 'media', file: w.name, bytes: w.bytes};
          }
        } else {
          const sniff = sniffExt(saved.head);
          if(!sniff || ALLOWED_EXT.indexOf(sniff) === -1) throw new Error('формат не поддерживается');
          const w = adoptMedia(tmp, sniff);
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
          try{ cleanMedia(''); }catch(e){}
        }
        else { cfg.web = ''; cfg.file = out.file; }
        writeCfg(cfg);
        __ymBgBroadcast(__ymBgReadPayload());
        try{ if(fs.existsSync(tmp)) fs.unlinkSync(tmp); }catch(e){}
        return reply(res, 200, Object.assign({ok: true}, out));
      }catch(e){
        try{ if(fs.existsSync(tmp)) fs.unlinkSync(tmp); }catch(_){}
        return reply(res, 400, {ok: false, error: String((e && e.message) || e)});
      }
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
  try{ cleanMedia(path.basename(String(readCfg().file || ''))); }catch(e){}
  try{ srv.listen(PORT, '127.0.0.1'); }
  catch(e){ try{ console.error('[ymbg] listen failed:', (e && e.message) || e); }catch(_){} }
}

function __ymApplyCustomBackground(wc){
  __ymBgStartServer();
  try{
    const payload = __ymBgReadPayload();
    wc.executeJavaScript('window.__YMBG__=' + JSON.stringify(payload) + ';' + ENGINE_JS, true)
      .catch(function(){});
  }catch(e){}
}
""".replace("ENGINE_JS", json.dumps(ENGINE))

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
