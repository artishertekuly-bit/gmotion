#!/usr/bin/env python3
"""Cross-platform Python Vision backend (Linux / Ubuntu GitHub Actions + Windows).

Replaces Apple Vision Swift binaries with MediaPipe + rembg (ONNX u2net / u2net_human_seg),
preserving the exact CLI and raw-gray stdout + faces.jsonl protocol expected by
`presenter_mattes.py` and `clip_matte.py`.

Subcommands:
    vision_py.py person_track VIDEO FACES_JSONL W H
    vision_py.py subject_mask VIDEO W H
    vision_py.py largest_subject_mask VIDEO W H
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import find_ffmpeg  # noqa: E402

FACE_LANDMARKER_URL = (
    'https://storage.googleapis.com/mediapipe-models/face_landmarker/'
    'face_landmarker/float16/1/face_landmarker.task'
)


def _ensure_face_landmarker_model():
    bundled = os.path.abspath(os.path.join(HERE, '..', '..', 'assets', 'models', 'face_landmarker.task'))
    if os.path.exists(bundled) and os.path.getsize(bundled) > 100000:
        return bundled
    cache_dir = os.path.join(os.path.dirname(HERE), '.cache', 'vision')
    os.makedirs(cache_dir, exist_ok=True)
    model_path = os.path.join(cache_dir, 'face_landmarker.task')
    if os.path.exists(model_path) and os.path.getsize(model_path) > 100000:
        return model_path
    try:
        import urllib.request
        with urllib.request.urlopen(FACE_LANDMARKER_URL, timeout=15) as resp:
            data = resp.read()
        if len(data) > 100000:
            with open(model_path, 'wb') as fh:
                fh.write(data)
            return model_path
    except Exception as exc:
        sys.stderr.write(f'vision_py: face_landmarker model download warn: {exc}\n')
    return None


def _iter_rgb_frames(ff, video_path, w, h):
    import subprocess
    cmd = [ff, '-v', 'error', '-i', video_path, '-an',
           '-vf', f'scale={w}:{h}:flags=bicubic',
           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    nb = w * h * 3
    try:
        while True:
            buf = proc.stdout.read(nb)
            if len(buf) < nb:
                break
            yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    finally:
        proc.stdout.close()
        proc.wait()


def _mar_from_landmarks(lms):
    """Compute Mouth Aspect Ratio using MediaPipe lip landmarks (13, 14) and corners (78, 308)."""
    try:
        p13, p14 = lms[13], lms[14]
        p78, p308 = lms[78], lms[308]
        v = math.hypot(p13.x - p14.x, p13.y - p14.y)
        h = max(math.hypot(p78.x - p308.x, p78.y - p308.y), 1e-5)
        return float(v / h)
    except Exception:
        return 0.0


def _bbox_from_landmarks(lms):
    xs = [float(p.x) for p in lms]
    ys = [float(p.y) for p in lms]
    x0, x1 = max(0.0, min(xs)), min(1.0, max(xs))
    y0, y1 = max(0.0, min(ys)), min(1.0, max(ys))
    return (x0 + x1) * 0.5, (y0 + y1) * 0.5, max(0.04, x1 - x0), max(0.05, y1 - y0)


def _init_face_detector():
    # 1) MediaPipe Tasks FaceLandmarker (num_faces=3, landmarks 13/14/78/308 for exact MAR)
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
        model_path = _ensure_face_landmarker_model()
        if model_path:
            opts = mp_vision.FaceLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=model_path),
                running_mode=mp_vision.RunningMode.IMAGE,
                num_faces=3,
                min_face_detection_confidence=0.45,
                min_face_presence_confidence=0.45,
            )
            det = mp_vision.FaceLandmarker.create_from_options(opts)
            sys.stderr.write(f'vision_py: initialized FaceLandmarker ({os.path.basename(model_path)})\n')
            return ('landmarker', det, mp)
    except Exception as exc:
        sys.stderr.write(f'vision_py: FaceLandmarker unavailable ({exc}), trying fallback...\n')
    # 2) Legacy MediaPipe solutions FaceMesh / FaceDetection
    try:
        import mediapipe as mp
        if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'face_mesh'):
            return ('mesh', mp.solutions.face_mesh.FaceMesh(static_image_mode=False, max_num_faces=3, min_detection_confidence=0.45), mp)
        if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'face_detection'):
            return ('solutions', mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.45), mp)
    except Exception:
        pass
    # 3) OpenCV multi-face Haar Cascade
    try:
        import cv2
        xml = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_alt2.xml')
        if not os.path.exists(xml):
            xml = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
        clf = cv2.CascadeClassifier(xml)
        if not clf.empty():
            return ('cv2', clf, cv2)
    except Exception:
        pass
    return (None, None, None)


def _detect_faces(det_tuple, rgb, prev_gray=None):
    """Return list of (cx, cy, w, h, mar_proxy) for up to 3 visible speakers."""
    kind, det, extra = det_tuple
    out = []
    if kind == 'landmarker' and det is not None:
        mp = extra
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        res = det.detect(mp_img)
        for lms in (res.face_landmarks or [])[:3]:
            cx, cy, fw, fh = _bbox_from_landmarks(lms)
            out.append((cx, cy, fw, fh, _mar_from_landmarks(lms)))
        return out
    if kind == 'mesh' and det is not None:
        res = det.process(rgb)
        for fl in (res.multi_face_landmarks or [])[:3]:
            cx, cy, fw, fh = _bbox_from_landmarks(fl.landmark)
            out.append((cx, cy, fw, fh, _mar_from_landmarks(fl.landmark)))
        return out
    if kind == 'solutions' and det is not None:
        res = det.process(rgb)
        for d in (res.detections or [])[:3]:
            bb = d.location_data.relative_bounding_box
            cx, cy = float(bb.xmin + bb.width / 2.0), float(bb.ymin + bb.height / 2.0)
            mar = 0.0
            if prev_gray is not None:
                h_im, w_im = rgb.shape[:2]
                y0 = max(0, int((bb.ymin + bb.height * 0.58) * h_im))
                y1 = min(h_im, int((bb.ymin + bb.height * 0.92) * h_im))
                x0 = max(0, int((bb.xmin + bb.width * 0.25) * w_im))
                x1 = min(w_im, int((bb.xmin + bb.width * 0.75) * w_im))
                if y1 > y0 + 2 and x1 > x0 + 2:
                    g_now = rgb[y0:y1, x0:x1].mean(axis=2)
                    mar = float(np.mean(np.abs(g_now - prev_gray[y0:y1, x0:x1])) / 25.0)
            out.append((cx, cy, float(bb.width), float(bb.height), mar))
        return out
    if kind == 'cv2' and det is not None:
        cv2 = extra
        h_im, w_im = rgb.shape[:2]
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        rects = det.detectMultiScale(gray, scaleFactor=1.12, minNeighbors=4, minSize=(max(32, w_im // 18), max(32, h_im // 18)))
        for rx, ry, rw, rh in sorted(rects, key=lambda r: int(r[2]) * int(r[3]), reverse=True)[:3]:
            mar = 0.0
            if prev_gray is not None:
                y0, y1 = max(0, int(ry + rh * 0.58)), min(h_im, int(ry + rh * 0.92))
                x0, x1 = max(0, int(rx + rw * 0.25)), min(w_im, int(rx + rw * 0.75))
                if y1 > y0 + 2 and x1 > x0 + 2:
                    mar = float(np.mean(np.abs(gray[y0:y1, x0:x1].astype(np.float32) - prev_gray[y0:y1, x0:x1])) / 25.0)
            out.append(((rx + rw * 0.5) / w_im, (ry + rh * 0.5) / h_im, rw / float(w_im), rh / float(h_im), mar))
        return out
    return out


def _estimate_face_from_mask(mask):
    """Fallback head box derived from the upper third of the rembg foreground silhouette."""
    ys, xs = np.where(mask >= 128)
    if len(ys) < 40:
        return None
    h, w = mask.shape[:2]
    y_min, y_max = int(ys.min()), int(ys.max())
    body_h = max(1, y_max - y_min)
    head_band = mask[y_min:min(h, y_min + max(24, int(body_h * 0.34)))]
    hy, hx = np.where(head_band >= 128)
    if len(hx) < 20:
        return None
    cx = float(np.median(hx)) / float(w)
    hw = max(0.08, float(np.percentile(hx, 95) - np.percentile(hx, 5)) / float(w))
    hh = max(hw * float(w) / float(h) * 1.15, float(body_h) * 0.28 / float(h))
    cy = float(y_min) / float(h) + hh * 0.52
    return cx, cy, hw, hh


def _init_rembg_session(model_name):
    try:
        from rembg import new_session, remove
        return remove, new_session(model_name)
    except Exception:
        return None, None


def _init_mp_selfie():
    try:
        import mediapipe as mp
        if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'selfie_segmentation'):
            return mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1)
    except Exception:
        pass
    return None


def _largest_component(mask_u8):
    from scipy.ndimage import label
    bw = mask_u8 >= 128
    labeled, ncomp = label(bw)
    if ncomp <= 1:
        return mask_u8
    counts = np.bincount(labeled.ravel())
    counts[0] = 0
    best = int(counts.argmax())
    return np.where(labeled == best, mask_u8, 0).astype(np.uint8)


def run_person_track(video_path, faces_path, w, h, fps=30.0, faces_only=False):
    from PIL import Image
    ff = find_ffmpeg()
    face_det = _init_face_detector()
    rembg_remove, rembg_sess = (None, None) if faces_only else _init_rembg_session('u2net_human_seg')
    mp_selfie = _init_mp_selfie() if (faces_only or rembg_remove is None) else None
    if not faces_only and rembg_remove is None and mp_selfie is None:
        sys.exit('ERROR: Install `rembg onnxruntime mediapipe` for cross-platform person segmentation.')

    win_len = max(5, int(round(float(fps) * 0.5)))
    tracks = []  # [{'id': int, 'x': float, 'y': float, 'mar_hist': [float, ...]}]
    next_id = 0
    prev_rgb = None
    prev_gray = None
    prev_active = 0

    out = sys.stdout.buffer
    write_faces = faces_path and faces_path != os.devnull
    fh = open(faces_path, 'w', encoding='utf-8') if write_faces else None
    try:
        for idx, rgb in enumerate(_iter_rgb_frames(ff, video_path, w, h)):
            gray = rgb.mean(axis=2).astype(np.float32)
            scene_cut = False
            if prev_rgb is not None:
                diff = float(np.mean(np.abs(rgb.astype(np.int16) - prev_rgb.astype(np.int16))))
                scene_cut = diff > 26.0
                if scene_cut:
                    tracks = []  # clean re-acquisition on hard montage cuts

            detected = _detect_faces(face_det, rgb, None if scene_cut else prev_gray)

            mask = None
            if not faces_only:
                if rembg_remove is not None:
                    m_img = rembg_remove(Image.fromarray(rgb), session=rembg_sess, only_mask=True)
                    mask = np.asarray(m_img.resize((w, h)), dtype=np.uint8)
                    if mask.ndim == 3:
                        mask = mask[:, :, 0]
                else:
                    seg = mp_selfie.process(rgb).segmentation_mask
                    mask = np.clip(seg * 255.0 + 0.5, 0, 255).astype(np.uint8)
                if not detected:
                    fb = _estimate_face_from_mask(mask)
                    if fb is not None:
                        detected = [(fb[0], fb[1], fb[2], fb[3], 0.0)]
            elif not detected and mp_selfie is not None:
                seg = mp_selfie.process(rgb).segmentation_mask
                m_fb = np.clip(seg * 255.0 + 0.5, 0, 255).astype(np.uint8)
                fb = _estimate_face_from_mask(m_fb)
                if fb is not None:
                    detected = [(fb[0], fb[1], fb[2], fb[3], 0.0)]

            # Assign speaker IDs + record MAR sliding window variance (0.5s)
            frame_speakers = []
            used_ids = set()
            for (cx, cy, fw, fh_v, mar) in detected:
                best_tr, best_d = None, 0.18
                for tr in tracks:
                    if tr['id'] in used_ids:
                        continue
                    d = math.hypot(cx - tr['x'], cy - tr['y'])
                    if d < best_d:
                        best_d, best_tr = d, tr
                if best_tr is None:
                    best_tr = {'id': next_id, 'x': cx, 'y': cy, 'mar_hist': []}
                    tracks.append(best_tr)
                    next_id += 1
                used_ids.add(best_tr['id'])
                best_tr['x'], best_tr['y'] = cx, cy
                best_tr['mar_hist'] = (best_tr['mar_hist'] + [mar])[-win_len:]
                mar_var = float(np.var(best_tr['mar_hist'])) if len(best_tr['mar_hist']) >= 3 else 0.0
                frame_speakers.append({
                    'id': best_tr['id'],
                    'x': round(cx, 5), 'y': round(cy, 5),
                    'w': round(fw, 5), 'h': round(fh_v, 5),
                    'mar': round(mar, 5), 'mar_var': round(mar_var, 6),
                })

            # Pick active speaker by highest MAR variance over the 0.5s window
            active_sp = None
            if frame_speakers:
                active_sp = max(frame_speakers, key=lambda s: (s['mar_var'], 1 if s['id'] == prev_active else 0, s['w'] * s['h']))
                prev_active = active_sp['id']

            if fh is not None:
                rec = {'f': idx, 'scene_cut_detected': bool(scene_cut)}
                if active_sp is not None:
                    rec.update(
                        x=active_sp['x'], y=active_sp['y'],
                        w=active_sp['w'], h=active_sp['h'],
                        active_speaker_id=active_sp['id'],
                        speakers=frame_speakers,
                    )
                fh.write(json.dumps(rec) + '\n')

            prev_rgb = rgb.copy()
            prev_gray = gray
            if not faces_only and mask is not None:
                out.write(mask.tobytes())
        if not faces_only:
            out.flush()
    finally:
        if fh is not None:
            fh.close()
        if face_det[1] is not None and hasattr(face_det[1], 'close'):
            face_det[1].close()
        if mp_selfie is not None and hasattr(mp_selfie, 'close'):
            mp_selfie.close()


def run_subject_mask(video_path, w, h, largest=False):
    from PIL import Image
    ff = find_ffmpeg()
    rembg_remove, rembg_sess = _init_rembg_session('u2net')
    mp_selfie = _init_mp_selfie() if rembg_remove is None else None
    if rembg_remove is None and mp_selfie is None:
        sys.exit('ERROR: Install `rembg onnxruntime` (or `mediapipe`) for subject segmentation.')

    out = sys.stdout.buffer
    for rgb in _iter_rgb_frames(ff, video_path, w, h):
        if rembg_remove is not None:
            m_img = rembg_remove(Image.fromarray(rgb), session=rembg_sess, only_mask=True)
            mask = np.asarray(m_img.resize((w, h)), dtype=np.uint8)
            if mask.ndim == 3:
                mask = mask[:, :, 0]
        else:
            seg = mp_selfie.process(rgb).segmentation_mask
            mask = np.clip(seg * 255.0 + 0.5, 0, 255).astype(np.uint8)
        if largest:
            mask = _largest_component(mask)
        out.write(mask.tobytes())
    out.flush()


def main():
    if len(sys.argv) < 2:
        sys.exit('usage: vision_py.py <person_track|subject_mask|largest_subject_mask> ...')
    cmd = sys.argv[1]
    if cmd == 'person_track':
        faces_only = '--faces-only' in sys.argv
        pos_args = [x for x in sys.argv[2:] if x != '--faces-only']
        fps_arg = float(pos_args[4]) if len(pos_args) > 4 else 30.0
        run_person_track(pos_args[0], pos_args[1], int(pos_args[2]), int(pos_args[3]), fps=fps_arg, faces_only=faces_only)
    elif cmd == 'subject_mask':
        run_subject_mask(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), largest=False)
    elif cmd == 'largest_subject_mask':
        run_subject_mask(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), largest=True)
    else:
        sys.exit(f'unknown vision_py subcommand: {cmd}')


if __name__ == '__main__':
    main()
