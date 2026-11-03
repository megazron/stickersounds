/* Bolti: chat demo with sound stickers. Plain JS, no build step. Chats live in localStorage,
   your own stickers (image + sound blobs) in IndexedDB, so nothing leaves the device. */
'use strict';
const $ = s => document.querySelector(s);
const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const now = () => Date.now();
const hhmm = t => new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
const pick = a => a[Math.floor(Math.random() * a.length)];

const CHATS = [
  { id: 'gang', name: 'Meme Gang 🔥', avatar: '🔥', bg: '#ff8a3d', sub: 'Rohan, Priya, Kabir, You', group: true, pack: 'desi',
    members: [{ n: 'Rohan', c: '#7fd1ff' }, { n: 'Priya', c: '#ff9ad5' }, { n: 'Kabir', c: '#7ee08a' }] },
  { id: 'rohan', name: 'Rohan', avatar: '😎', bg: '#5b3fd6', sub: 'online', pack: 'desi', members: [{ n: 'Rohan', c: '#7fd1ff' }] },
  { id: 'sam', name: 'Sam (London)', avatar: '🫖', bg: '#2a9d8f', sub: 'online', pack: 'og', members: [{ n: 'Sam', c: '#ffd166' }] },
];
const SEED = {
  gang: [['Priya', 't', 'Kal ka plan cancel ho gaya 😭'], ['Rohan', 's', 'moye-moye'], ['Kabir', 't', 'Fir se? 💀'], ['Kabir', 's', 'kya-ho-raha']],
  rohan: [['Rohan', 't', 'Bhai result aa gaya'], ['Rohan', 't', 'Pass ho gaya 🥳'], ['Rohan', 's', 'paisa']],
  sam: [['Sam', 't', 'Did you see the match last night?'], ['Sam', 's', 'emotional-damage']],
};
const REPLIES = { desi: ['😂😂😂', 'Bhai 💀', 'Hahaha sahi hai', 'Ye toh kamaal hai', 'Ek aur bhej', 'Sound ke saath alag hi level 🔊'],
  og: ['LMAO', '💀💀', 'No way 😂', 'The sound sends me', 'Okay that one got me', 'Again again'] };

let STICKERS = [], BYID = {}, MINE = [], db, cur = null, tab = 'desi';
let autoPlay = localStorage.getItem('bolti.auto') !== '0';
const store = { get: id => JSON.parse(localStorage.getItem('bolti.chat.' + id) || 'null'), set: (id, m) => localStorage.setItem('bolti.chat.' + id, JSON.stringify(m)) };

/* ---------- sound ---------- */
let playing = null;
function play(stickerId, node) {
  const s = BYID[stickerId]; if (!s) return;
  if (playing) { playing.a.pause(); playing.n && playing.n.classList.remove('playing'); }
  const a = new Audio(s.sound); playing = { a, n: node };
  if (node) node.classList.add('playing');
  const stop = () => { node && node.classList.remove('playing'); if (playing && playing.a === a) playing = null; };
  a.addEventListener('ended', stop); a.addEventListener('pause', stop);
  a.addEventListener('timeupdate', () => { if (a.currentTime > 6.5) a.pause(); });
  a.play().catch(stop);
}

/* ---------- storage for your own stickers ---------- */
function openDB() {
  return new Promise((res, rej) => { const r = indexedDB.open('bolti', 1);
    r.onupgradeneeded = () => r.result.createObjectStore('mine', { keyPath: 'id' });
    r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
}
const tx = (mode, fn) => new Promise((res, rej) => { const t = db.transaction('mine', mode); const r = fn(t.objectStore('mine')); t.oncomplete = () => res(r && r.result); t.onerror = () => rej(t.error); });
async function loadMine() {
  if (!db) return; const all = await tx('readonly', s => s.getAll());
  MINE.forEach(m => { URL.revokeObjectURL(m.img); URL.revokeObjectURL(m.sound); });
  MINE = (all || []).sort((a, b) => b.t - a.t).map(r => ({ id: r.id, pack: 'mine', caption: r.caption, dur: r.dur,
    img: URL.createObjectURL(r.img), sound: URL.createObjectURL(r.audio) }));
  MINE.forEach(m => BYID[m.id] = m);
}

/* ---------- chat list ---------- */
function msgsOf(c) {
  let m = store.get(c.id);
  if (!m) { const t0 = now() - 3600e3; m = SEED[c.id].map(([from, k, v], i) => ({ from, k, v, t: t0 + i * 60e3 })); store.set(c.id, m); }
  return m;
}
function preview(m) { if (!m) return ''; const who = m.from === 'me' ? 'You: ' : ''; return who + (m.k === 's' ? '🔊 Sound sticker' : m.v); }
function renderList() {
  const box = $('#chats'); box.innerHTML = '';
  CHATS.forEach(c => { const m = msgsOf(c); const last = m[m.length - 1];
    const row = el('div', 'chatrow' + (cur && cur.id === c.id ? ' on' : ''),
      `<div class="avatar" style="background:${c.bg}">${c.avatar}</div><div class="meta"><b>${esc(c.name)}</b><small>${esc(preview(last))}</small></div><small>${last ? hhmm(last.t) : ''}</small>`);
    row.onclick = () => openChat(c.id); box.appendChild(row); });
}

/* ---------- messages ---------- */
function stickerNode(id) {
  const s = BYID[id]; const b = el('button', 'st');
  if (!s) { b.innerHTML = '<div class="bubble">(sticker not on this device)</div>'; return b; }
  b.innerHTML = `<img src="${s.img}" alt="${esc(s.caption || 'sticker')}"><span class="chip"><span class="wave"><i></i><i></i><i></i></span>${(s.dur || 0).toFixed(1)}s</span>`;
  b.onclick = () => play(id, b); b.title = 'Tap to play';
  return b;
}
function msgNode(m) {
  const me = m.from === 'me'; const w = el('div', 'msg ' + (me ? 'me' : 'them'));
  if (!me && cur.group) { const mem = cur.members.find(x => x.n === m.from); w.appendChild(el('div', 'from', esc(m.from))).style.color = mem ? mem.c : '#fff'; }
  const body = m.k === 's' ? stickerNode(m.v) : el('div', 'bubble', esc(m.v));
  w.appendChild(body); w.appendChild(el('div', 'time', hhmm(m.t)));
  return { w, body };
}
function renderMsgs() {
  const box = $('#msgs'); box.innerHTML = ''; box.appendChild(el('div', 'day', 'Today'));
  msgsOf(cur).forEach(m => box.appendChild(msgNode(m).w)); box.scrollTop = box.scrollHeight;
}
function push(m, sound) {
  const all = msgsOf(cur); all.push(m); store.set(cur.id, all.slice(-200));
  const { w, body } = msgNode(m); $('#msgs').appendChild(w); $('#msgs').scrollTop = $('#msgs').scrollHeight;
  if (m.k === 's' && sound && autoPlay) play(m.v, body);
  renderList();
}
let replyTimer = null;
function friendReply() {
  clearTimeout(replyTimer); const chat = cur; const who = pick(chat.members);
  const typing = el('div', 'typing', `${esc(chat.group ? who.n : chat.name)} is typing…`);
  replyTimer = setTimeout(() => { if (cur !== chat) return; $('#msgs').appendChild(typing); $('#msgs').scrollTop = 1e9;
    replyTimer = setTimeout(() => { typing.remove(); if (cur !== chat) return;
      const useSticker = Math.random() < .6; const pool = STICKERS.filter(s => s.pack === chat.pack);
      push(useSticker ? { from: who.n, k: 's', v: pick(pool).id, t: now() } : { from: who.n, k: 't', v: pick(REPLIES[chat.pack]), t: now() }, true);
    }, 1100 + Math.random() * 900); }, 700);
}

/* ---------- open / close ---------- */
function openChat(id) {
  cur = CHATS.find(c => c.id === id); tab = cur.pack;
  $('#chat').hidden = false; $('#app').classList.add('inchat');
  $('#chatName').textContent = cur.name; $('#chatSub').textContent = cur.sub;
  const av = $('#chatAvatar'); av.textContent = cur.avatar; av.style.background = cur.bg;
  renderMsgs(); renderList(); closeTray();
  localStorage.setItem('bolti.last', id);
}
$('#backBtn').onclick = () => { $('#app').classList.remove('inchat'); closeTray(); };

/* ---------- composer + tray ---------- */
$('#composer').onsubmit = e => { e.preventDefault(); const v = $('#text').value.trim(); if (!v) return;
  $('#text').value = ''; push({ from: 'me', k: 't', v, t: now() }); friendReply(); };
function closeTray() { $('#tray').hidden = true; $('#stickerBtn').classList.remove('on'); }
$('#stickerBtn').onclick = () => { const t = $('#tray'); t.hidden = !t.hidden; $('#stickerBtn').classList.toggle('on', !t.hidden); if (!t.hidden) renderTray(); };
$('#text').onfocus = () => { if (matchMedia('(max-width:760px)').matches) closeTray(); };
function renderTray() {
  const tabs = $('#tabs'); tabs.innerHTML = '';
  [['desi', '🌶️ Desi'], ['og', '😂 OG + Trending'], ['mine', '⭐ Mine']].forEach(([k, label]) => {
    const b = el('button', tab === k ? 'on' : '', label); b.type = 'button'; b.onclick = () => { tab = k; renderTray(); }; tabs.appendChild(b); });
  const grid = $('#grid'); grid.innerHTML = '';
  const list = tab === 'mine' ? MINE : STICKERS.filter(s => s.pack === tab);
  if (tab === 'mine') { const mk = el('button', 'make', '+ Make<br>your own'); mk.type = 'button'; mk.onclick = openMaker; grid.appendChild(mk);
    if (!list.length) grid.appendChild(el('div', 'empty', 'Add any meme picture with its sound. It stays on this phone.')); }
  list.forEach(s => {
    const b = el('button', 'ts', `<img src="${s.img}" alt="${esc(s.caption)}" loading="lazy">`); b.type = 'button'; b.title = s.caption + ' (tap to send)';
    b.onclick = () => { push({ from: 'me', k: 's', v: s.id, t: now() }, true); friendReply(); };
    const pv = el('button', 'pv', '🔊'); pv.type = 'button'; pv.title = 'Preview sound';
    pv.onclick = e => { e.stopPropagation(); play(s.id, null); }; b.appendChild(pv);
    if (tab === 'mine') { const d = el('button', 'del', '✕'); d.type = 'button'; d.title = 'Delete';
      d.onclick = async e => { e.stopPropagation(); if (!confirm('Delete this sticker?')) return; await tx('readwrite', st => st.delete(s.id)); await loadMine(); renderTray(); };
      b.appendChild(d); }
    grid.appendChild(b); });
}
function setSoundBtn() { $('#soundBtn').textContent = autoPlay ? '🔊' : '🔇'; $('#soundBtn').title = autoPlay ? 'Sticker sounds auto-play (tap to mute)' : 'Sticker sounds muted (tap a sticker to play)'; }
$('#soundBtn').onclick = () => { autoPlay = !autoPlay; localStorage.setItem('bolti.auto', autoPlay ? '1' : '0'); setSoundBtn(); };
$('#infoBtn').onclick = () => $('#about').showModal();

/* ---------- sticker maker ---------- */
const mk = { img: null, audio: null, dur: 0, rec: null };
function openMaker() { Object.assign(mk, { img: null, audio: null, dur: 0 }); $('#mkImg').value = ''; $('#mkAud').value = ''; $('#mkCap').value = '';
  $('#mkStatus').textContent = ''; drawMaker(); $('#mkSave').disabled = $('#mkPlay').disabled = true; $('#maker').showModal(); }
function drawMaker() {
  const c = $('#mkCanvas'), g = c.getContext('2d'); g.clearRect(0, 0, 512, 512);
  if (mk.img) { const s = Math.min(472 / mk.img.width, 472 / mk.img.height); const w = mk.img.width * s, h = mk.img.height * s;
    g.save(); g.beginPath(); g.roundRect((512 - w) / 2, (512 - h) / 2, w, h, 36); g.clip(); g.drawImage(mk.img, (512 - w) / 2, (512 - h) / 2, w, h); g.restore();
    g.lineWidth = 14; g.strokeStyle = '#fff'; g.beginPath(); g.roundRect((512 - w) / 2, (512 - h) / 2, w, h, 36); g.stroke(); }
  const cap = $('#mkCap').value.trim();
  if (cap) { let fs = cap.length > 22 ? 40 : 54; g.font = `800 ${fs}px Baloo, sans-serif`; g.textAlign = 'center';
    g.lineJoin = 'round'; g.lineWidth = 12; g.strokeStyle = '#1b1b2f'; g.fillStyle = '#fff';
    g.strokeText(cap, 256, 480, 490); g.fillText(cap, 256, 480, 490); }
}
function ready() { $('#mkSave').disabled = !(mk.img && mk.audio); $('#mkPlay').disabled = !mk.audio; }
$('#mkCap').oninput = drawMaker;
$('#mkImg').onchange = e => { const f = e.target.files[0]; if (!f) return; const im = new Image();
  im.onload = () => { mk.img = im; drawMaker(); ready(); }; im.src = URL.createObjectURL(f); };
function setAudio(blob) { mk.audio = blob; const a = new Audio(URL.createObjectURL(blob));
  a.onloadedmetadata = () => { mk.dur = isFinite(a.duration) ? Math.min(6, a.duration) : 3; $('#mkStatus').textContent = `Sound ready (${mk.dur.toFixed(1)} s${a.duration > 6 ? ', plays the first 6 s' : ''})`; };
  ready(); }
$('#mkAud').onchange = e => { const f = e.target.files[0]; if (f) setAudio(f); };
$('#mkPlay').onclick = () => { if (!mk.audio) return; const a = new Audio(URL.createObjectURL(mk.audio)); a.ontimeupdate = () => { if (a.currentTime > 6) a.pause(); }; a.play(); };
$('#mkRec').onclick = async () => {
  if (mk.rec) { mk.rec.stop(); return; }
  try { const s = await navigator.mediaDevices.getUserMedia({ audio: true }); const r = new MediaRecorder(s); const parts = [];
    r.ondataavailable = e => parts.push(e.data);
    r.onstop = () => { s.getTracks().forEach(t => t.stop()); mk.rec = null; $('#mkRec').classList.remove('rec'); $('#mkRec').textContent = '● Record (max 6 s)';
      setAudio(new Blob(parts, { type: r.mimeType })); };
    r.start(); mk.rec = r; $('#mkRec').classList.add('rec'); $('#mkRec').textContent = '■ Stop'; setTimeout(() => mk.rec === r && r.stop(), 6000);
  } catch (e) { $('#mkStatus').textContent = 'Microphone not available. Pick a sound file instead.'; }
};
$('#makerForm').onsubmit = async e => {
  if (e.submitter && e.submitter.value !== 'save') return;
  e.preventDefault(); if (!(mk.img && mk.audio) || !db) return;
  const img = await new Promise(r => $('#mkCanvas').toBlob(r, 'image/webp', .85));
  const id = 'mine-' + now().toString(36);
  await tx('readwrite', s => s.put({ id, t: now(), caption: $('#mkCap').value.trim() || 'My sticker', img, audio: mk.audio, dur: mk.dur || 3 }));
  await loadMine(); $('#maker').close(); tab = 'mine'; $('#tray').hidden = false; $('#stickerBtn').classList.add('on'); renderTray();
};

/* ---------- start ---------- */
(async function init() {
  STICKERS = await (await fetch('stickers.json')).json(); STICKERS.forEach(s => BYID[s.id] = s);
  try { db = await openDB(); await loadMine(); } catch (e) { console.warn('IndexedDB unavailable', e); }
  setSoundBtn(); renderList();
  if (!matchMedia('(max-width:760px)').matches) openChat(localStorage.getItem('bolti.last') || 'gang');
  if (!localStorage.getItem('bolti.seen')) { localStorage.setItem('bolti.seen', '1'); $('#about').showModal(); }
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
})();
