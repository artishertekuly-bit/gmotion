#!/usr/bin/env python3
"""Context-First YouTube Podcast Extractor for kz-kinetic-studio.

Fetches podcast metadata, YouTube Heatmap ("Most Replayed" peaks), and full
timestamped transcripts WITHOUT downloading heavy HD video locally.
Outputs a compact Markdown + JSON packet ready for the AI Context Window to pick
the highest-retention 45-60 s Talking Head segments and generate contextual 60/40 scripts.

Usage:
    python -X utf8 scripts/fetch_to_context.py --url "https://www.youtube.com/watch?v=..." --out work/podcast_ctx
    python -X utf8 scripts/fetch_to_context.py --url "..." --range 12:30-14:00 --out work/podcast_ctx
    python -X utf8 scripts/fetch_to_context.py --url "..." --use-scribe --range 05:00-10:00 --out work/podcast_ctx
    python -X utf8 scripts/fetch_to_context.py --from-info-json info.json --from-vtt subs.vtt --out work/podcast_ctx
"""
import argparse
import glob
import html
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def parse_timestamp(val):
    """Parse HH:MM:SS.mmm, MM:SS.mmm, or seconds string/number into float seconds."""
    if val is None or val == '':
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(',', '.')
    parts = s.split(':')
    try:
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return int(parts[0]) * 60.0 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600.0 + int(parts[1]) * 60.0 + float(parts[2])
    except ValueError:
        return None
    return None


def fmt_tc(sec):
    """Format seconds as MM:SS.d (or HH:MM:SS.d when >= 3600)."""
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60.0
    if h:
        return f"{h:02d}:{m:02d}:{s:04.1f}"
    return f"{m:02d}:{s:04.1f}"


def parse_range_arg(spec):
    if not spec:
        return None, None
    if '-' not in spec:
        t = parse_timestamp(spec)
        return t, None
    a, b = spec.split('-', 1)
    return parse_timestamp(a), parse_timestamp(b)


def clean_caption_text(raw):
    txt = html.unescape(raw)
    txt = re.sub(r'<[^>]+>', '', txt)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt


def parse_vtt_or_srt(path):
    """Parse .vtt or .srt subtitle file into deduplicated [{start, end, text}] segments."""
    with open(path, encoding='utf-8', errors='replace') as fh:
        content = fh.read()
    blocks = re.split(r'\r?\n\r?\n+', content.strip())
    tc_re = re.compile(
        r'(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?)\s*-->\s*(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?)'
    )
    segs = []
    for blk in blocks:
        lines = [ln.strip() for ln in blk.splitlines() if ln.strip()]
        if not lines:
            continue
        tc_idx = next((i for i, ln in enumerate(lines) if '-->' in ln), None)
        if tc_idx is None:
            continue
        m = tc_re.search(lines[tc_idx])
        if not m:
            continue
        s0, s1 = parse_timestamp(m.group(1)), parse_timestamp(m.group(2))
        if s0 is None or s1 is None or s1 <= s0:
            continue
        body = clean_caption_text(' '.join(lines[tc_idx + 1:]))
        if not body:
            continue
        # YouTube auto-captions often repeat the previous cue in the top line of the next rolling cue
        if segs and segs[-1]['text'] == body and s0 - segs[-1]['end'] < 0.5:
            segs[-1]['end'] = max(segs[-1]['end'], s1)
            continue
        if segs and body.startswith(segs[-1]['text']) and len(body) > len(segs[-1]['text']) and s0 <= segs[-1]['end'] + 0.2:
            tail = body[len(segs[-1]['text']):].strip()
            if tail:
                body = tail
        segs.append({'start': round(s0, 3), 'end': round(s1, 3), 'text': body})
    return segs


def parse_json3(path):
    """Parse YouTube json3 timedtext into [{start, end, text}] segments."""
    with open(path, encoding='utf-8', errors='replace') as fh:
        data = json.load(fh)
    segs = []
    for ev in data.get('events') or []:
        t0 = ev.get('tStartMs')
        dur = ev.get('dDurationMs', 0)
        pieces = ev.get('segs') or []
        txt = clean_caption_text(''.join(p.get('utf8', '') for p in pieces))
        if t0 is None or not txt:
            continue
        s0 = t0 / 1000.0
        s1 = s0 + max(dur, 200) / 1000.0
        segs.append({'start': round(s0, 3), 'end': round(s1, 3), 'text': txt})
    return segs


def find_ytdlp():
    exe = shutil.which('yt-dlp')
    if exe:
        return [exe]
    try:
        subprocess.run([sys.executable, '-m', 'yt_dlp', '--version'], capture_output=True, check=True)
        return [sys.executable, '-m', 'yt_dlp']
    except Exception:
        return None


def extract_heatmap_peaks(heatmap, top_n=8, min_gap=20.0):
    """Select well-spaced Most Replayed heatmap peaks from YouTube info JSON."""
    if not heatmap:
        return []
    ordered = sorted(
        [h for h in heatmap if h.get('value') is not None],
        key=lambda h: float(h.get('value', 0)),
        reverse=True,
    )
    chosen = []
    for h in ordered:
        st, en = float(h.get('start_time', 0.0)), float(h.get('end_time', 0.0))
        mid = (st + en) / 2.0
        if any(abs(mid - ((c['start'] + c['end']) / 2.0)) < min_gap for c in chosen):
            continue
        chosen.append({'start': round(st, 2), 'end': round(en, 2), 'score': round(float(h['value']), 4)})
        if len(chosen) >= top_n:
            break
    chosen.sort(key=lambda c: c['score'], reverse=True)
    return chosen


def snap_window(center_t, segments, duration, target_dur=52.0, min_dur=45.0, max_dur=60.0):
    """Snap a [start, end] clip around center_t onto clean transcript boundaries."""
    raw_start = max(0.0, center_t - target_dur * 0.38)
    raw_end = min(duration or (raw_start + max_dur), raw_start + target_dur)
    if not segments:
        return round(raw_start, 2), round(raw_end, 2)
    cand_starts = [s['start'] for s in segments if abs(s['start'] - raw_start) <= 8.0]
    s0 = min(cand_starts, key=lambda x: abs(x - raw_start)) if cand_starts else raw_start
    desired_end = s0 + target_dur
    cand_ends = [s['end'] for s in segments if s0 + min_dur <= s['end'] <= s0 + max_dur]
    if cand_ends:
        s1 = min(cand_ends, key=lambda x: abs(x - desired_end))
    else:
        s1 = min(duration or (s0 + max_dur), s0 + target_dur)
    return round(s0, 2), round(max(s0 + 10.0, s1), 2)


def build_candidate_windows(segments, peaks, duration, target_dur=52.0, range_bounds=(None, None)):
    """Build ranked 45-60 s candidate windows using heatmap peaks + transcript energy."""
    r0, r1 = range_bounds
    anchors = []
    if peaks:
        for pk in peaks:
            mid = (pk['start'] + pk['end']) / 2.0
            if r0 is not None and mid < r0:
                continue
            if r1 is not None and mid > r1:
                continue
            anchors.append((mid, pk['score'], 'youtube_heatmap'))
    # If no heatmap peaks or outside user range, sample density windows from transcript
    if not anchors and segments:
        t_start = r0 if r0 is not None else segments[0]['start']
        t_end = r1 if r1 is not None else segments[-1]['end']
        cur = t_start
        while cur + 35.0 <= t_end:
            win_words = sum(
                len(s['text'].split())
                for s in segments
                if cur <= s['start'] <= cur + target_dur
            )
            anchors.append((cur + target_dur * 0.38, round(min(1.0, win_words / 160.0), 3), 'speech_density'))
            cur += target_dur * 0.75

    windows = []
    for mid, score, source in anchors[:8]:
        s0, s1 = snap_window(mid, segments, duration, target_dur=target_dur)
        if r0 is not None:
            s0 = max(s0, r0)
        if r1 is not None:
            s1 = min(s1, r1)
        if s1 - s0 < 20.0:
            continue
        if any(abs(w['start'] - s0) < 18.0 for w in windows):
            continue
        snippet = ' '.join(s['text'] for s in segments if s['end'] > s0 and s['start'] < s1)
        windows.append({
            'start': s0,
            'end': s1,
            'duration': round(s1 - s0, 2),
            'start_tc': fmt_tc(s0),
            'end_tc': fmt_tc(s1),
            'score': score,
            'source': source,
            'preview': snippet[:280] + ('...' if len(snippet) > 280 else ''),
        })
    return windows


def run_ytdlp_metadata(ytdlp_cmd, url, out_dir, langs='kk,ru,en'):
    """Fetch info JSON + subtitles only (NO HD video download), resilient against HTTP 429 auto-sub limits."""
    import shutil
    import urllib.request
    os.makedirs(out_dir, exist_ok=True)
    tmpl = os.path.join(out_dir, 'source.%(ext)s')
    js_rt = ['--js-runtimes', 'node'] if shutil.which('node') else []
    cmd = ytdlp_cmd + js_rt + [
        '--no-playlist',
        '--skip-download',
        '--ignore-errors',
        '--write-info-json',
        '--write-subs',
        '--write-auto-subs',
        '--sub-langs', langs,
        '--sub-format', 'vtt/srt/json3/best',
        '-o', tmpl,
        url,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    info_files = sorted(glob.glob(os.path.join(out_dir, '*.info.json')))
    # If auto-sub translation failed with 429 before writing info.json, retry metadata-only pass
    if not info_files:
        cmd_meta = ytdlp_cmd + js_rt + [
            '--no-playlist', '--skip-download', '--write-info-json', '-o', tmpl, url
        ]
        res = subprocess.run(cmd_meta, capture_output=True, text=True, encoding='utf-8', errors='replace')
        info_files = sorted(glob.glob(os.path.join(out_dir, '*.info.json')))
    if not info_files:
        sys.stderr.write(res.stderr + '\n')
        sys.exit(f'ERROR: yt-dlp failed to fetch podcast metadata (code {res.returncode})')
    sub_files = []
    for ext in ('*.kk.*', '*.kz.*', '*.mn-orig.*', '*.ru.*', '*.en.*', '*.vtt', '*.srt', '*.json3'):
        sub_files.extend(glob.glob(os.path.join(out_dir, ext)))
    seen, ordered_subs = set(), []
    for p in sub_files:
        if p.endswith('.info.json') or p in seen:
            continue
        if p.lower().endswith(('.vtt', '.srt', '.json3')):
            seen.add(p)
            ordered_subs.append(p)
    # Fallback: pull original ASR/manual caption tracks directly from info.json (handles YouTube kk/ru 429 while mn-orig succeeds)
    if not ordered_subs and info_files:
        info = json.load(open(info_files[0], encoding='utf-8'))
        sources = [info.get('subtitles') or {}, info.get('automatic_captions') or {}]
        pref = [x.strip() for x in langs.split(',') if x.strip()]
        orig_keys = [k for src in sources for k in src.keys() if k.endswith('-orig')]
        for lang in pref + orig_keys + ['mn-orig']:
            for src in sources:
                entries = src.get(lang) or []
                vtts = [e.get('url') for e in entries if e.get('ext') == 'vtt' and e.get('url')]
                if vtts:
                    try:
                        req = urllib.request.Request(vtts[0], headers={'User-Agent': 'Mozilla/5.0'})
                        body = urllib.request.urlopen(req, timeout=12).read().decode('utf-8', 'replace')
                        fb_path = os.path.join(out_dir, f'source.{lang}.vtt')
                        with open(fb_path, 'w', encoding='utf-8') as fh:
                            fh.write(body)
                        ordered_subs.append(fb_path)
                        break
                    except Exception:
                        pass
            if ordered_subs:
                break
    return info_files[0] if info_files else None, ordered_subs


def optional_scribe_audio(ytdlp_cmd, url, out_dir, range_spec=None):
    """Download ONLY low-bandwidth audio (-f ba) for Scribe STT if captions are unavailable."""
    audio_dir = os.path.join(out_dir, 'audio_only')
    os.makedirs(audio_dir, exist_ok=True)
    audio_out = os.path.join(audio_dir, 'podcast_audio.%(ext)s')
    cmd = ytdlp_cmd + ['--no-playlist', '-f', 'bestaudio/ba', '-o', audio_out]
    if range_spec:
        s0, s1 = parse_range_arg(range_spec)
        if s0 is not None and s1 is not None:
            cmd += ['--download-sections', f'*{s0}-{s1}']
    cmd.append(url)
    subprocess.run(cmd, check=True)
    audio_files = [p for p in glob.glob(os.path.join(audio_dir, 'podcast_audio.*')) if not p.endswith('.part')]
    if not audio_files:
        sys.exit('ERROR: failed to fetch audio track for Scribe')
    scribe_py = os.path.join(HERE, 'transcribe_scribe.py')
    asr_dir = os.path.join(out_dir, 'scribe_work')
    os.makedirs(os.path.join(asr_dir, 'analysis'), exist_ok=True)
    subprocess.run([sys.executable, '-X', 'utf8', scribe_py, '--audio', audio_files[0], '--out', asr_dir], check=True)
    asr_path = os.path.join(asr_dir, 'analysis', 'asr.json')
    if not os.path.exists(asr_path):
        return []
    asr = json.load(open(asr_path, encoding='utf-8'))
    words = asr.get('words') or []
    segs, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 8 or str(w.get('w', '')).endswith(('.', '!', '?')):
            segs.append({
                'start': round(cur[0]['s'], 3),
                'end': round(cur[-1]['e'], 3),
                'text': ' '.join(x['w'] for x in cur).strip(),
            })
            cur = []
    if cur:
        segs.append({
            'start': round(cur[0]['s'], 3),
            'end': round(cur[-1]['e'], 3),
            'text': ' '.join(x['w'] for x in cur).strip(),
        })
    return segs


def filter_segments_by_range(segments, r0, r1):
    if r0 is None and r1 is None:
        return segments
    return [
        s for s in segments
        if (r0 is None or s['end'] >= r0) and (r1 is None or s['start'] <= r1)
    ]


def write_context_markdown(packet, md_path, max_lines=320):
    meta = packet['metadata']
    lines = [
        f"# Podcast Context Packet: {meta.get('title', 'Untitled')}",
        '',
        f"- **URL**: {meta.get('url', '')}",
        f"- **Channel**: {meta.get('channel', 'Unknown')}",
        f"- **Duration**: {fmt_tc(meta.get('duration') or 0)} ({meta.get('duration') or 0:.1f} s)",
        f"- **Subtitle Source**: {packet.get('subtitle_source', 'none')}",
        f"- **Cloud Clip Section Cmd**: `yt-dlp --download-sections \"*START-END\" \"{meta.get('url', '')}\"`",
        '',
        '## YouTube Most Replayed Heatmap Peaks',
    ]
    if packet['heatmap_peaks']:
        for i, pk in enumerate(packet['heatmap_peaks'], 1):
            lines.append(f"{i}. `{fmt_tc(pk['start'])} -> {fmt_tc(pk['end'])}` (heatmap score: `{pk['score']:.2f}`)")
    else:
        lines.append('- Heatmap telemetry unavailable for this video; using transcript density peaks.')
    lines += ['', '## Recommended 45-60 s Viral Talking-Head Windows']
    if packet['candidate_windows']:
        for i, w in enumerate(packet['candidate_windows'], 1):
            lines.append(
                f"{i}. **`{w['start_tc']} -> {w['end_tc']}`** (`{w['start']:.1f}s - {w['end']:.1f}s`, "
                f"{w['duration']:.0f}s, {w['source']} `{w['score']}`)\n   > {w['preview']}"
            )
    else:
        lines.append('- No automatic windows detected.')

    segs = packet['transcript']
    lines += ['', f'## Timestamped Transcript ({len(segs)} cues)']
    step = max(1, len(segs) // max_lines) if len(segs) > max_lines else 1
    if step > 1:
        lines.append(f'_(Condensed every {step} cue(s) to fit context window cleanly; full cues in context_packet.json)_')
    for s in segs[::step]:
        lines.append(f"- `[{fmt_tc(s['start'])} - {fmt_tc(s['end'])}]` ({s['start']:.1f}s): {s['text']}")

    with open(md_path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')


def main():
    ap = argparse.ArgumentParser(description='Fetch YouTube podcast transcript & heatmap into AI Context Window without heavy video download.')
    ap.add_argument('--url', help='YouTube podcast video URL')
    ap.add_argument('--range', dest='time_range', help='Optional focus window START-END (e.g. 12:30-15:00)')
    ap.add_argument('--langs', default='kk,ru,en', help='Preferred subtitle languages (comma-separated)')
    ap.add_argument('--target-dur', type=float, default=52.0, help='Target clip length in seconds (45-60)')
    ap.add_argument('--use-scribe', action='store_true', help='If captions missing, fetch audio-only stream and run transcribe_scribe.py')
    ap.add_argument('--from-info-json', help='Offline mode: parse an existing yt-dlp .info.json file')
    ap.add_argument('--from-vtt', help='Offline mode: parse an existing .vtt/.srt/.json3 subtitle file')
    ap.add_argument('--out', default='podcast_context', help='Output folder for context_packet.json and context_prompt.md')
    a = ap.parse_args()

    if not a.url and not (a.from_info_json or a.from_vtt):
        ap.error('Provide --url or --from-info-json / --from-vtt')

    os.makedirs(a.out, exist_ok=True)
    r0, r1 = parse_range_arg(a.time_range)

    info_path = a.from_info_json
    sub_paths = [a.from_vtt] if a.from_vtt else []
    ytdlp_cmd = None

    if a.url:
        ytdlp_cmd = find_ytdlp()
        if not ytdlp_cmd:
            sys.exit('ERROR: yt-dlp not found. Install it (`pip install yt-dlp`) to extract podcast context.')
        fetched_info, fetched_subs = run_ytdlp_metadata(ytdlp_cmd, a.url, a.out, langs=a.langs)
        info_path = info_path or fetched_info
        sub_paths = sub_paths or fetched_subs

    info = json.load(open(info_path, encoding='utf-8')) if info_path and os.path.exists(info_path) else {}
    segments, sub_source = [], 'none'
    for sp in sub_paths:
        if sp and os.path.exists(sp):
            if sp.lower().endswith('.json3'):
                segments = parse_json3(sp)
            else:
                segments = parse_vtt_or_srt(sp)
            if segments:
                sub_source = os.path.basename(sp)
                break

    if not segments and a.use_scribe and a.url and ytdlp_cmd:
        segments = optional_scribe_audio(ytdlp_cmd, a.url, a.out, range_spec=a.time_range)
        if segments:
            sub_source = 'elevenlabs_scribe_audio_only'

    segments = filter_segments_by_range(segments, r0, r1)
    duration = float(info.get('duration') or (segments[-1]['end'] if segments else 0.0))
    peaks = extract_heatmap_peaks(info.get('heatmap'))
    windows = build_candidate_windows(segments, peaks, duration, target_dur=a.target_dur, range_bounds=(r0, r1))

    packet = {
        'metadata': {
            'id': info.get('id'),
            'title': info.get('title') or 'Podcast',
            'channel': info.get('channel') or info.get('uploader'),
            'url': a.url or info.get('webpage_url') or '',
            'duration': round(duration, 2),
            'upload_date': info.get('upload_date'),
            'chapters': info.get('chapters') or [],
        },
        'subtitle_source': sub_source,
        'heatmap_peaks': peaks,
        'candidate_windows': windows,
        'transcript': segments,
    }
    json_path = os.path.join(a.out, 'context_packet.json')
    md_path = os.path.join(a.out, 'context_prompt.md')
    with open(json_path, 'w', encoding='utf-8') as fh:
        json.dump(packet, fh, ensure_ascii=False, indent=2)
    write_context_markdown(packet, md_path)
    sys.stdout.reconfigure(encoding='utf-8')
    print(f'Context extracted (zero heavy video download): {md_path}')
    print(f'  Transcript cues: {len(segments)} ({sub_source}) | Heatmap peaks: {len(peaks)} | Candidates: {len(windows)}')


if __name__ == '__main__':
    main()
