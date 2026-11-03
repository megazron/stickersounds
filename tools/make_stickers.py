"""Builds the built-in sound stickers: original meme-style art (512x512 WebP, like a chat sticker) + a short sound
(the line spoken by an offline voice, mixed with a synthesized sound effect) as MP3. Writes app/stickers/*.webp,
app/sounds/*.mp3 and app/stickers.json.  Run: python tools/make_stickers.py  (needs piper, numpy, Pillow, ffmpeg,
playwright + a Chromium)"""
import os, io, json, glob, math, wave, subprocess, hashlib
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); APP = f'{ROOT}/app'
VOICES = os.path.expanduser('~/.local/share/piper_voices'); FF = os.path.expanduser('~/.local/bin/ffmpeg')
CACHE = f'{ROOT}/.cache'; os.makedirs(CACHE, exist_ok=True)
SR = 44100
V = {'hi_m': 'hi_IN-pratham-medium', 'hi_f': 'hi_IN-priyamvada-medium', 'en_m': 'en_US-ryan-medium'}

# id, pack, caption on the sticker, spoken line, voice, sound effect, (body colour, eyes, mouth, extras), mix
STICKERS = [
    # ---- Desi
    ('rasode', 'desi', 'Rasode mein kaun tha?', 'रसोड़े में कौन था?', 'hi_f', 'dun', ('#ffb347', 'wide', 'o', ['boom', 'question']), 'voice_sfx'),
    ('kya-ho-raha', 'desi', 'Ye kya ho raha hai?', 'ये क्या हो रहा है?', 'hi_m', 'boom', ('#7fd1ff', 'wide', 'scream', ['sweat']), 'voice_sfx'),
    ('bhai-kya-kar', 'desi', 'Bhai kya kar raha hai tu?', 'भाई, क्या कर रहा है तू?', 'hi_m', 'scratch', ('#ff8fa3', 'angry', 'frown', ['question']), 'sfx_voice'),
    ('paisa', 'desi', 'Paisa hi paisa hoga', 'पैसा ही पैसा होगा!', 'hi_m', 'coins', ('#7ee08a', 'money', 'grin', ['coins', 'sparkle']), 'voice_sfx'),
    ('moye-moye', 'desi', 'Moye moye', 'मोये मोये', 'hi_f', 'trombone', ('#b39cff', 'cry', 'wavy', ['tears']), 'sfx_voice'),
    ('bas-kar-pagle', 'desi', 'Bas kar pagle, rulayega kya?', 'बस कर पगले, रुलाएगा क्या?', 'hi_m', 'violin', ('#9ad0ff', 'cry', 'frown', ['tears']), 'over'),
    ('khush-bahut', 'desi', 'Aaj khush toh bahut hoge tum', 'आज खुश तो बहुत होगे तुम!', 'hi_m', 'riser', ('#ff7a59', 'angry', 'smirk', ['fire']), 'over'),
    ('control-uday', 'desi', 'Control Uday, control!', 'कंट्रोल उदय, कंट्रोल!', 'hi_m', 'riser', ('#ff5d5d', 'angry', 'flat', ['fire', 'sweat']), 'over'),
    ('utha-le', 'desi', 'Utha le re baba', 'उठा ले रे बाबा... उठा ले!', 'hi_m', 'thunder', ('#a7b0c0', 'tired', 'frown', ['thunder']), 'sfx_voice'),
    ('maza-aayega', 'desi', 'Abhi maza aayega na bhidu', 'अभी मज़ा आएगा ना भिडू!', 'hi_m', 'drumroll', ('#ffd84d', 'shades', 'grin', ['sparkle']), 'over'),
    ('kehna-kya', 'desi', 'Kehna kya chahte ho?', 'कहना क्या चाहते हो?', 'hi_f', 'hmm', ('#ffc6e0', 'side', 'flat', ['question']), 'voice_sfx'),
    ('bahut-hard', 'desi', 'Bahut hard!', 'बहुत हार्ड!', 'hi_m', 'airhorn', ('#ff9f1c', 'shades', 'grin', ['fire', 'boom']), 'voice_sfx'),
    # ---- Desi trending
    ('tumse-na-ho', 'trend', 'Tumse na ho payega', 'तुमसे ना हो पाएगा।', 'hi_m', 'trombone', ('#c4b5fd', 'tired', 'flat', []), 'voice_sfx'),
    ('kitne-aadmi', 'trend', 'Kitne aadmi the?', 'कितने आदमी थे?', 'hi_m', 'dun', ('#d6a46b', 'angry', 'smirk', ['boom']), 'voice_sfx'),
    ('dil-se-bura', 'trend', 'Dil se bura lagta hai bhai', 'दिल से बुरा लगता है भाई।', 'hi_m', 'violin', ('#93c5fd', 'cry', 'frown', ['tears']), 'over'),
    ('apun-bhagwan', 'trend', 'Apun hi bhagwan hai', 'आज मुझे फिर ऐसा लगा... अपुन ही भगवान है।', 'hi_m', 'ding', ('#fde047', 'shades', 'smirk', ['sparkle']), 'over'),
    ('kaun-hai-ye-log', 'trend', 'Kaun hai ye log? Kahan se aate hain?', 'कौन हैं ये लोग? कहाँ से आते हैं?', 'hi_m', 'hmm', ('#86efac', 'wide', 'o', ['question']), 'voice_sfx'),
    ('kis-line-mein', 'trend', 'Bhai sahab ye kis line mein aa gaye aap?', 'भाई साहब, ये किस लाइन में आ गए आप?', 'hi_m', 'scratch', ('#fca5a5', 'side', 'smirk', ['question']), 'sfx_voice'),
    ('risk-nahi', 'trend', 'Bilkul risk nahi lene ka', 'बिलकुल रिस्क नहीं लेने का।', 'hi_m', 'riser', ('#67e8f9', 'side', 'flat', ['sweat']), 'over'),
    ('baburao-style', 'trend', 'Ye Baburao ka style hai', 'ये बाबूराव का स्टाइल है!', 'hi_m', 'airhorn', ('#fdba74', 'shades', 'grin', ['boom']), 'voice_sfx'),
    ('mummy-kasam', 'trend', 'Mummy kasam!', 'मम्मी कसम!', 'hi_f', 'boom', ('#f9a8d4', 'wide', 'o', ['sweat']), 'voice_sfx'),
    ('kaand', 'trend', 'Ho gaya kaand', 'हो गया कांड!', 'hi_m', 'boom', ('#f87171', 'wide', 'scream', ['fire']), 'voice_sfx'),
    ('thak-gaya', 'trend', 'Main thak gaya hoon', 'मैं थक गया हूँ।', 'hi_m', 'trombone', ('#a1a1aa', 'tired', 'wavy', ['sweat']), 'voice_sfx'),
    ('sahi-khel-gaya', 'trend', 'Sahi khel gaya bhai', 'सही खेल गया भाई!', 'hi_m', 'coins', ('#4ade80', 'happy', 'grin', ['sparkle']), 'voice_sfx'),
    # ---- OG and trending
    ('bruh', 'og', 'Bruh.', 'Bruh.', 'en_m', 'boom', ('#c7c7c7', 'tired', 'flat', []), 'voice_sfx'),
    ('emotional-damage', 'og', 'Emotional damage!', 'Emotional damage!', 'en_m', 'boom', ('#ff6b6b', 'wide', 'scream', ['boom']), 'voice_sfx'),
    ('sheesh', 'og', 'Sheeesh', 'Sheeeeesh!', 'en_m', 'sparkle', ('#5ee7df', 'shades', 'smirk', ['sparkle']), 'over'),
    ('oh-no', 'og', 'Oh no no no no', 'Oh no. No no no no no.', 'en_m', 'trombone', ('#ffd166', 'wide', 'o', ['sweat']), 'voice_sfx'),
    ('to-be-continued', 'og', 'To be continued...', 'To be continued.', 'en_m', 'riff', ('#c9a227', 'side', 'smirk', ['arrow']), 'sfx_voice'),
    ('stonks', 'og', 'Stonks', 'Stonks!', 'en_m', 'coins', ('#4dd599', 'money', 'grin', ['chart']), 'voice_sfx'),
    ('this-is-fine', 'og', 'This is fine.', 'This is fine. Everything is fine.', 'en_m', 'fire', ('#ffb26b', 'happy', 'grin', ['fire', 'sweat']), 'over'),
    ('sus', 'og', 'Kinda sus', 'Hmm. Kinda sus.', 'en_m', 'hmm', ('#ff4d6d', 'side', 'flat', ['question']), 'voice_sfx'),
    ('aura', 'og', 'Aura +1000', 'Plus one thousand aura.', 'en_m', 'ding', ('#a78bfa', 'stars', 'smirk', ['sparkle']), 'sfx_voice'),
    ('skill-issue', 'og', 'Skill issue', 'Skill issue.', 'en_m', 'boom', ('#60a5fa', 'shades', 'smirk', []), 'voice_sfx'),
    ('delulu', 'og', 'Delulu is the solulu', 'Delulu is the solulu.', 'en_m', 'sparkle', ('#ff9ad5', 'stars', 'grin', ['hearts']), 'over'),
    ('six-seven', 'og', '6 7', 'Six. Seven.', 'en_m', 'drumroll', ('#34d399', 'happy', 'grin', ['boom']), 'over'),
]


# ------------------------------------------------------------------ sound effects (all synthesized here)
def t_(d): return np.arange(int(d * SR)) / SR
def env(n, a=.005, r=.2):
    e = np.ones(n); na, nr = max(1, int(a * SR)), max(1, int(r * SR)); e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr); return e
def lp(x, k=8):
    return np.convolve(x, np.ones(k) / k, 'same')
rng = np.random.default_rng(7)


def sfx(kind):
    if kind == 'boom':                                   # deep cinematic thud
        t = t_(1.3); f = 45 + 90 * np.exp(-t * 7); ph = 2 * np.pi * np.cumsum(f) / SR
        x = np.tanh(2.5 * np.sin(ph)) * np.exp(-t * 2.6); x[:400] += rng.standard_normal(400) * np.linspace(.6, 0, 400); return x * .9
    if kind == 'dun':                                     # dramatic three brass hits
        out = []
        for i, (f, d) in enumerate([(147, .32), (139, .32), (110, 1.2)]):
            t = t_(d); x = sum(np.sign(np.sin(2 * np.pi * f * k * t)) / k for k in (1, 1.5, 2)) * env(len(t), .01, .25)
            out.append(lp(x, 10) * (.5 if i < 2 else .7)); out.append(np.zeros(int(.06 * SR)))
        return np.concatenate(out)
    if kind == 'scratch':                                 # record scratch
        t = t_(.55); w = np.sin(2 * np.pi * 3.5 * t) ** 2; n = rng.standard_normal(len(t))
        x = np.zeros_like(n); a = 0
        for i in range(len(n)): a += (.05 + .5 * w[i]) * (n[i] - a); x[i] = a
        return x * 2.2 * env(len(t), .005, .05)
    if kind == 'coins':                                   # cha-ching
        out = np.zeros(int(1.1 * SR))
        for k, st in enumerate([0, .09, .2, .33, .45]):
            t = t_(.6); f = 2600 + 300 * k
            x = (np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * f * 2.76 * t)) * np.exp(-t * 9) * .35
            i = int(st * SR); out[i:i + len(x)] += x[:len(out) - i]
        return out
    if kind == 'trombone':                                # wah wah wah waaah
        out = []
        for f, d in [(233, .38), (220, .38), (208, .38), (196, 1.1)]:
            t = t_(d); vib = 1 + (.012 * np.sin(2 * np.pi * 6 * t) if d > 1 else 0)
            ph = 2 * np.pi * np.cumsum(f * vib) / SR; x = sum(np.sin(k * ph) / k for k in range(1, 8))
            wah = .4 + .6 * np.sin(np.pi * np.clip(t / d, 0, 1)); out.append(lp(x * wah, 6) * env(len(t), .02, .08) * .35)
        return np.concatenate(out)
    if kind == 'violin':                                  # sad violin
        out = []
        for f, d in [(440, .7), (415, .7), (392, .7), (349, 1.4)]:
            t = t_(d); ph = 2 * np.pi * np.cumsum(f * (1 + .006 * np.sin(2 * np.pi * 5.5 * t))) / SR
            x = sum(np.sin(k * ph) / k ** 1.3 for k in range(1, 10)); out.append(x * env(len(t), .15, .2) * .22)
        return np.concatenate(out)
    if kind == 'airhorn':
        out = []
        for d in (.18, .18, .6):
            t = t_(d); x = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (466, 554, 698)) / 3
            out += [lp(x, 4) * env(len(t), .005, .03) * .45, np.zeros(int(.05 * SR))]
        return np.concatenate(out)
    if kind == 'riser':                                   # tension riser
        t = t_(1.6); f = 200 * 2 ** (t * 1.6); ph = 2 * np.pi * np.cumsum(f) / SR
        return (np.sin(ph) * .25 + lp(rng.standard_normal(len(t)), 3) * .12) * (t / t[-1]) ** 1.5
    if kind == 'thunder':
        t = t_(1.8); n = lp(rng.standard_normal(len(t)), 60) * 6
        crack = rng.standard_normal(len(t)) * np.exp(-t * 18) * .6
        return np.tanh((n * np.exp(-t * 1.6) + crack)) * .7
    if kind == 'drumroll':
        out = np.zeros(int(1.6 * SR)); tt = 0; gap = .07
        while tt < 1.2:
            h = rng.standard_normal(int(.05 * SR)) * np.exp(-np.arange(int(.05 * SR)) / SR * 60) * .35
            i = int(tt * SR); out[i:i + len(h)] += h; tt += gap; gap = max(.03, gap * .96)
        c = t_(.4); i = int(1.2 * SR); out[i:i + len(c)] += rng.standard_normal(len(c)) * np.exp(-c * 6) * .5
        return out
    if kind == 'hmm':                                     # curious boop
        t = t_(.45); f = 330 + 330 * (t / t[-1]) ** 2; ph = 2 * np.pi * np.cumsum(f) / SR
        return np.sin(ph) * env(len(t), .01, .1) * .4
    if kind == 'sparkle':
        out = np.zeros(int(1.0 * SR))
        for k in range(9):
            t = t_(.4); f = 1800 + 220 * k + rng.uniform(-60, 60)
            x = np.sin(2 * np.pi * f * t) * np.exp(-t * 10) * .18; i = int(k * .08 * SR); out[i:i + len(x)] += x[:len(out) - i]
        return out
    if kind == 'ding':                                    # holy ding + choir pad
        t = t_(1.6); bell = sum(np.sin(2 * np.pi * 880 * r * t) * a for r, a in [(1, .5), (2.4, .25), (5.4, .12)]) * np.exp(-t * 3)
        pad = sum(np.sin(2 * np.pi * f * t) for f in (440, 554, 659)) / 3 * np.sin(np.pi * t / t[-1]) * .3
        return bell * .6 + pad
    if kind == 'riff':                                    # walking bass riff into a stop
        notes = [110, 110, 131, 147, 165, 147, 131, 98]; out = []
        for f in notes:
            t = t_(.16); x = sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 2, 3)) * np.exp(-t * 8) * .5; out.append(x)
        t = t_(.5); f = 300 * np.exp(-t * 6) + 20; out.append(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4) * .3)
        return np.concatenate(out)
    if kind == 'fire':
        t = t_(1.4); x = lp(rng.standard_normal(len(t)), 20) * .5
        for _ in range(40):
            i = rng.integers(0, len(t) - 300); x[i:i + 300] += rng.standard_normal(300) * np.exp(-np.arange(300) / 60) * .5
        return x * .5
    raise KeyError(kind)


def voice(text, v):
    key = hashlib.md5(f'{v}|{text}'.encode()).hexdigest()[:12]; p = f'{CACHE}/{key}.wav'
    if not os.path.exists(p):
        subprocess.run(['piper', '-m', f'{VOICES}/{V[v]}.onnx', '--length_scale', '0.95', '-f', p], input=text.encode(),
                       check=True, capture_output=True)
    w = wave.open(p); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    from scipy.signal import resample_poly
    x = resample_poly(x, SR, w.getframerate())
    nz = np.where(np.abs(x) > .01)[0]; x = x[max(0, nz[0] - 400):nz[-1] + 800]          # trim silence
    return x / (np.abs(x).max() + 1e-9) * .9


def mix(v, s, how):
    s = s / (np.abs(s).max() + 1e-9) * .75
    if how == 'voice_sfx': parts = [(v, 0), (s, len(v) / SR + .05)]
    elif how == 'sfx_voice': parts = [(s, 0), (v, len(s) / SR * .55)]
    else: parts = [(s * .55, 0), (v, .15)]
    n = int(max(len(x) / SR + o for x, o in parts) * SR) + 1; out = np.zeros(n)
    for x, o in parts: i = int(o * SR); out[i:i + len(x)] += x
    out /= max(1, np.abs(out).max() / .95); return out


# ------------------------------------------------------------------ sticker art (original characters)
def face_svg(col, eyes, mouth, extras):
    ink = '#1b1b2f'; g = []
    # back extras
    if 'boom' in extras:
        g.append(''.join(f'<path d="M256 236 L{256 + 250 * math.cos(a):.0f} {236 + 250 * math.sin(a):.0f}" stroke="#fff3" stroke-width="26"/>' for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)))
    if 'fire' in extras:
        g.append('<g fill="#ff6b00" stroke="#1b1b2f" stroke-width="6">' + ''.join(
            f'<path d="M{x} 470 q-40 -80 10 -150 q10 60 40 40 q20 -50 0 -90 q90 70 40 200z"/>' for x in (40, 170, 300, 400)) + '</g>'
                 '<g fill="#ffd400">' + ''.join(f'<path d="M{x + 25} 465 q-15 -40 10 -70 q30 40 10 70z"/>' for x in (40, 170, 300, 400)) + '</g>')
    # body
    g.append(f'<path d="M256 50 C390 50 450 140 450 245 C450 360 370 430 256 430 C142 430 62 360 62 245 C62 140 122 50 256 50Z" fill="{col}" stroke="{ink}" stroke-width="10"/>')
    g.append('<ellipse cx="190" cy="120" rx="60" ry="26" fill="#fff" opacity=".35" transform="rotate(-20 190 120)"/>')
    if 'blush' in extras or mouth in ('grin',) and eyes in ('happy', 'stars'):
        g.append('<ellipse cx="150" cy="285" rx="34" ry="18" fill="#ff5c8a" opacity=".45"/><ellipse cx="362" cy="285" rx="34" ry="18" fill="#ff5c8a" opacity=".45"/>')
    ex, ey = (180, 332), 215
    E = {
        'wide': ''.join(f'<circle cx="{x}" cy="{ey}" r="46" fill="#fff" stroke="{ink}" stroke-width="8"/><circle cx="{x}" cy="{ey + 4}" r="12" fill="{ink}"/>' for x in ex),
        'happy': ''.join(f'<path d="M{x - 38} {ey + 12} q38 -50 76 0" fill="none" stroke="{ink}" stroke-width="12" stroke-linecap="round"/>' for x in ex),
        'angry': ''.join(f'<circle cx="{x}" cy="{ey + 10}" r="30" fill="#fff" stroke="{ink}" stroke-width="8"/><circle cx="{x + (8 if x < 256 else -8)}" cy="{ey + 14}" r="12" fill="{ink}"/>' for x in ex)
                 + f'<path d="M135 160 L230 195" stroke="{ink}" stroke-width="14" stroke-linecap="round"/><path d="M377 160 L282 195" stroke="{ink}" stroke-width="14" stroke-linecap="round"/>',
        'cry': ''.join(f'<path d="M{x - 36} {ey} q36 30 72 0" fill="none" stroke="{ink}" stroke-width="12" stroke-linecap="round"/>' for x in ex),
        'side': ''.join(f'<path d="M{x - 42} {ey} h84 a42 34 0 0 1 -84 0z" fill="#fff" stroke="{ink}" stroke-width="8"/><circle cx="{x + 24}" cy="{ey + 14}" r="13" fill="{ink}"/>' for x in ex)
                + f'<path d="M140 175 h80 M292 175 h80" stroke="{ink}" stroke-width="12" stroke-linecap="round"/>',
        'shades': f'<path d="M110 190 h292 v18 h-10 q-6 60 -66 60 q-58 0 -64 -52 h-12 q-6 52 -64 52 q-60 0 -66 -60 h-10z" fill="{ink}"/><path d="M150 205 l30 0 l-40 40z" fill="#fff" opacity=".5"/>',
        'money': ''.join(f'<circle cx="{x}" cy="{ey}" r="44" fill="#fff" stroke="{ink}" stroke-width="8"/><text x="{x}" y="{ey + 24}" font-family="B" font-weight="800" font-size="70" text-anchor="middle" fill="#16a34a">₹</text>' for x in ex),
        'tired': ''.join(f'<circle cx="{x}" cy="{ey}" r="34" fill="#fff" stroke="{ink}" stroke-width="8"/><circle cx="{x}" cy="{ey + 12}" r="11" fill="{ink}"/><path d="M{x - 40} {ey - 2} h80 v-40 h-80z" fill="{col}"/><path d="M{x - 36} {ey - 2} h72" stroke="{ink}" stroke-width="9" stroke-linecap="round"/>' for x in ex),
        'stars': ''.join(f'<path d="M{x} {ey - 44} l13 28 31 4 -23 21 6 31 -27 -15 -27 15 6 -31 -23 -21 31 -4z" fill="#ffd400" stroke="{ink}" stroke-width="7" stroke-linejoin="round"/>' for x in ex),
    }
    g.append(E[eyes])
    my = 330
    M = {
        'o': f'<ellipse cx="256" cy="{my}" rx="30" ry="38" fill="{ink}"/><ellipse cx="256" cy="{my + 18}" rx="18" ry="12" fill="#ff6b81"/>',
        'scream': f'<path d="M206 {my - 30} q50 -20 100 0 q10 80 -50 95 q-60 -15 -50 -95z" fill="{ink}"/><ellipse cx="256" cy="{my + 42}" rx="26" ry="15" fill="#ff6b81"/>',
        'grin': f'<path d="M170 {my - 25} h172 q0 85 -86 85 q-86 0 -86 -85z" fill="{ink}"/><path d="M182 {my - 25} h148 v22 h-148z" fill="#fff"/><ellipse cx="256" cy="{my + 38}" rx="40" ry="16" fill="#ff6b81"/>',
        'flat': f'<path d="M206 {my} h100" stroke="{ink}" stroke-width="13" stroke-linecap="round"/>',
        'frown': f'<path d="M196 {my + 25} q60 -55 120 0" fill="none" stroke="{ink}" stroke-width="13" stroke-linecap="round"/>',
        'smirk': f'<path d="M200 {my + 5} q70 30 115 -25" fill="none" stroke="{ink}" stroke-width="13" stroke-linecap="round"/>',
        'wavy': f'<path d="M190 {my + 10} q16 -22 33 0 t33 0 t33 0 t33 0" fill="none" stroke="{ink}" stroke-width="12" stroke-linecap="round"/>',
    }
    g.append(M[mouth])
    # front extras
    if 'thunder' in extras:
        g.append(f'<g transform="translate(330 0) scale(.8)"><path d="M150 120 h-130 a45 45 0 0 1 10 -88 a60 60 0 0 1 112 10 a40 40 0 0 1 8 78z" fill="#8b93a7" stroke="{ink}" stroke-width="8"/><path d="M95 120 l-30 60 h32 l-22 55 l62 -78 h-34 l22 -37z" fill="#ffd400" stroke="{ink}" stroke-width="7" stroke-linejoin="round"/></g>')
    if 'tears' in extras:
        g.append(''.join(f'<path d="M{x} 235 q-14 90 4 170 q22 -80 4 -170z" fill="#4cc9f0" stroke="{ink}" stroke-width="5"/>' for x in (165, 343)))
    if 'sweat' in extras:
        g.append(f'<path d="M405 120 q-26 40 0 60 q26 -20 0 -60z" fill="#4cc9f0" stroke="{ink}" stroke-width="6"/>')
    if 'question' in extras:
        g.append(f'<text x="420" y="120" font-family="B" font-weight="800" font-size="130" fill="#fff" stroke="{ink}" stroke-width="7" paint-order="stroke" transform="rotate(14 420 120)">?</text>')
    if 'coins' in extras:
        g.append(''.join(f'<g transform="translate({x} {y})"><ellipse rx="34" ry="34" fill="#ffd400" stroke="{ink}" stroke-width="7"/><text y="20" font-family="B" font-weight="800" font-size="50" text-anchor="middle" fill="#b45309">₹</text></g>' for x, y in ((70, 110), (440, 80), (455, 330))))
    if 'sparkle' in extras:
        g.append(''.join(f'<path d="M{x} {y - s} q{s * .15} {s * .85} {s} {s} q{-s * .85} {s * .15} {-s} {s} q{-s * .15} {-s * .85} {-s} {-s} q{s * .85} {-s * .15} {s} {-s}z" fill="#fff59d" stroke="{ink}" stroke-width="5"/>' for x, y, s in ((70, 90, 40), (450, 70, 32), (460, 360, 26))))
    if 'hearts' in extras:
        g.append(''.join(f'<path d="M{x} {y} c-20 -30 -60 -10 -40 20 l40 35 l40 -35 c20 -30 -20 -50 -40 -20z" fill="#ff4d8d" stroke="{ink}" stroke-width="6"/>' for x, y in ((80, 80), (440, 90))))
    if 'arrow' in extras:
        g.append(f'<g transform="translate(250 395) rotate(-6)"><path d="M0 0 h170 v-28 l60 52 l-60 52 v-28 h-170z" fill="#e8c547" stroke="{ink}" stroke-width="7"/></g>')
    if 'chart' in extras:
        g.append(f'<g transform="translate(330 40)"><path d="M0 150 l40 -50 l30 25 l70 -100" fill="none" stroke="#16a34a" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/><path d="M110 25 h40 v40" fill="none" stroke="#16a34a" stroke-width="16" stroke-linecap="round"/></g>')
    return ''.join(g)


def sticker_svg(caption, art):
    col, eyes, mouth, extras = art
    size = 64 if len(caption) <= 12 else 54 if len(caption) <= 20 else 46
    words, lines, cur = caption.split(), [], ''
    for w in words:
        if len(cur) + len(w) + 1 > 16: lines.append(cur); cur = w
        else: cur = (cur + ' ' + w).strip()
    lines.append(cur)
    y0 = 470 - (len(lines) - 1) * size * .92
    cap = ''.join(f'<text x="256" y="{y0 + i * size * .92:.0f}" text-anchor="middle" font-family="B" font-weight="800" font-size="{size}" '
                  f'fill="#fff" stroke="#1b1b2f" stroke-width="12" paint-order="stroke" stroke-linejoin="round">{l}</text>' for i, l in enumerate(lines))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
<defs><style>@font-face{{font-family:B;src:url(file://{APP}/fonts/baloo2-latin.woff2)}}</style>
<filter id="o" x="-10%" y="-10%" width="120%" height="120%"><feMorphology in="SourceAlpha" operator="dilate" radius="9" result="d"/>
<feFlood flood-color="#fff"/><feComposite in2="d" operator="in" result="w"/><feGaussianBlur in="d" stdDeviation="6" result="s"/>
<feOffset in="s" dy="5" result="so"/><feFlood flood-color="#000" flood-opacity=".28"/><feComposite in2="so" operator="in" result="sh"/>
<feMerge><feMergeNode in="sh"/><feMergeNode in="w"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
<g filter="url(#o)"><g transform="translate(256 230) scale(.86) translate(-256 -240)">{face_svg(col, eyes, mouth, extras)}</g>
<g transform="rotate(-4 256 440)">{cap}</g></g></svg>'''


def main():
    from playwright.sync_api import sync_playwright
    exe = glob.glob(os.path.expanduser('~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome'))[0]
    meta = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe); pg = b.new_page(viewport={'width': 512, 'height': 512})
        for sid, pack, caption, line, v, fx, art, how in STICKERS:
            hp = f'{CACHE}/{sid}.html'
            open(hp, 'w').write(f'<html><body style="margin:0;background:transparent">{sticker_svg(caption, art)}</body></html>')
            pg.goto(f'file://{hp}'); pg.wait_for_timeout(150)
            png = pg.screenshot(omit_background=True, clip={'x': 0, 'y': 0, 'width': 512, 'height': 512})
            Image.open(io.BytesIO(png)).save(f'{APP}/stickers/{sid}.webp', 'WEBP', quality=82, method=6)
            audio = mix(voice(line, v), sfx(fx), how)
            wp = f'{CACHE}/{sid}.wav'
            with wave.open(wp, 'w') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((audio * 32767).astype(np.int16).tobytes())
            subprocess.run([FF, '-loglevel', 'error', '-y', '-i', wp, '-ac', '1', '-ar', '44100', '-b:a', '64k', f'{APP}/sounds/{sid}.mp3'], check=True)
            meta.append({'id': sid, 'pack': pack, 'caption': caption, 'img': f'stickers/{sid}.webp', 'sound': f'sounds/{sid}.mp3',
                         'dur': round(len(audio) / SR, 2)})
            print(sid, meta[-1]['dur'], 's')
        b.close()
    json.dump(meta, open(f'{APP}/stickers.json', 'w'), indent=1, ensure_ascii=False)
    kb = sum(os.path.getsize(f) for f in glob.glob(f'{APP}/stickers/*') + glob.glob(f'{APP}/sounds/*')) / 1024
    print(len(meta), 'stickers,', round(kb), 'KB')


if __name__ == '__main__':
    main()
