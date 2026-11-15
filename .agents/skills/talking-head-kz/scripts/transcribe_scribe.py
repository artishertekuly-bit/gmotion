#!/usr/bin/env python3
"""Word-level Kazakh transcript with ElevenLabs Scribe (replaces the engine's faster-whisper step).

    python -X utf8 scripts/transcribe_scribe.py PROJECT_DIR [--language kaz] [--model scribe_v1] [--env PATH/.env]
    python -X utf8 scripts/transcribe_scribe.py PROJECT_DIR --from-json analysis/scribe_raw.json     # no network, no cost

PAID: one request per run, billed by ElevenLabs for the length of the audio. Run it only after the person agreed,
and never twice for the same recording - the raw answer is kept in analysis/scribe_raw.json and --from-json
rebuilds everything from it for free.

Sends analysis/audio16k.wav (made by prepare_project.py). Writes analysis/asr.json in the engine's format:
[{start, end, text, words: [{s, e, w, p}]}] in source seconds, one entry per sentence.
The API key is read from $ELEVENLABS_API_KEY or from a .env file (ELEVENLABS_API_KEY=...) and is never printed.
"""
import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engine', 'scripts'))
from common import project_config, save_json  # noqa: E402

URL = 'https://api.elevenlabs.io/v1/speech-to-text'


def find_key(env_path, start_dir):
    key = os.environ.get('ELEVENLABS_API_KEY')
    if key:
        return key.strip()
    cands = [env_path] if env_path else []
    d = os.path.abspath(start_dir)
    for _ in range(6):                                   # the project folder and its parents
        cands.append(os.path.join(d, '.env'))
        d = os.path.dirname(d)
    cands.append(os.path.join(os.path.expanduser('~'), 'Motion', '.env'))
    for p in cands:
        if p and os.path.exists(p):
            for line in open(p, encoding='utf-8', errors='ignore'):
                if line.strip().startswith('ELEVENLABS_API_KEY'):
                    return line.split('=', 1)[1].strip().strip('"\'')
    return None


def call_scribe(wav, key, model, language):
    boundary = '----reel' + uuid.uuid4().hex
    parts = []
    for name, value in (('model_id', model), ('language_code', language), ('timestamps_granularity', 'word'),
                        ('tag_audio_events', 'false'), ('diarize', 'false')):
        parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, name, value)).encode())
    parts.append(('--%s\r\nContent-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
                  'Content-Type: audio/wav\r\n\r\n' % boundary).encode())
    parts.append(open(wav, 'rb').read())
    parts.append(('\r\n--%s--\r\n' % boundary).encode())
    req = urllib.request.Request(URL, data=b''.join(parts), method='POST', headers={
        'xi-api-key': key, 'Content-Type': 'multipart/form-data; boundary=' + boundary})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        sys.exit('ERROR: Scribe answered %s: %s' % (e.code, e.read().decode('utf-8', 'replace')[:400]))


def to_asr(raw):
    """Scribe words -> sentences of whisper-style words (leading space, punctuation attached)."""
    words = [w for w in raw.get('words', []) if w.get('type', 'word') == 'word' and (w.get('text') or '').strip()]
    segs, cur = [], []
    for w in words:
        lp = w.get('logprob')
        cur.append(dict(s=round(float(w['start']), 3), e=round(float(w['end']), 3), w=' ' + w['text'].strip(),
                        p=round(math.exp(lp), 3) if isinstance(lp, (int, float)) else 1))
        if w['text'].strip()[-1:] in '.?!…':
            segs.append(cur)
            cur = []
    if cur:
        segs.append(cur)
    return [dict(start=s[0]['s'], end=s[-1]['e'], text=''.join(x['w'] for x in s), words=s) for s in segs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--language', default='kaz', help='ISO 639-3 code: kaz (Kazakh), rus (Russian), eng')
    ap.add_argument('--model', default='scribe_v1')
    ap.add_argument('--env', help='path to a .env file with ELEVENLABS_API_KEY')
    ap.add_argument('--from-json', help='rebuild asr.json from a saved Scribe answer instead of calling the API')
    a = ap.parse_args()
    cfg = project_config(a.project)
    P = cfg['project_dir']
    raw_path = os.path.join(P, 'analysis', 'scribe_raw.json')
    if a.from_json:
        src = a.from_json if os.path.isabs(a.from_json) else os.path.join(P, a.from_json)
        raw = json.load(open(src, encoding='utf-8'))
    else:
        if os.path.exists(raw_path):
            sys.exit('analysis/scribe_raw.json already exists - use --from-json analysis/scribe_raw.json (free), '
                     'or delete it if a new paid transcription is really wanted')
        key = find_key(a.env, P)
        if not key:
            sys.exit('ERROR: no ELEVENLABS_API_KEY in the environment or in a .env file (pass --env)')
        wav = os.path.join(P, 'analysis', 'audio16k.wav')
        print('sending %.1f s of audio to ElevenLabs Scribe (%s, %s) ...' % (cfg.get('src_dur', 0), a.model, a.language), flush=True)
        raw = call_scribe(wav, key, a.model, a.language)
        save_json(raw, raw_path)
    asr = to_asr(raw)
    if not asr:
        sys.exit('ERROR: the transcript is empty: %s' % json.dumps(raw, ensure_ascii=False)[:300])
    save_json(asr, os.path.join(P, 'analysis', 'asr.json'))
    cfg['language'] = raw.get('language_code', a.language)
    save_json(cfg, os.path.join(P, 'project.json'))
    sys.stdout.reconfigure(encoding='utf-8')
    for s in asr:
        print('%6.2f-%6.2f %s' % (s['start'], s['end'], s['text']))
    print('\nlanguage: %s   sentences: %d   words: %d' % (cfg['language'], len(asr), sum(len(s['words']) for s in asr)))


if __name__ == '__main__':
    main()
