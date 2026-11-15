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
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import find_ffmpeg  # noqa: E402


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


def _init_face_detector():
    try:
        import mediapipe as mp
        if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'face_detection'):
            return ('solutions', mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.45))
    except Exception:
        pass
    return (None, None)


def _detect_face(det_tuple, rgb):
    kind, det = det_tuple
    if kind == 'solutions' and det is not None:
        res = det.process(rgb)
        if res.detections:
            # Take highest-confidence primary speaker face
            d = max(res.detections, key=lambda x: x.score[0] if x.score else 0.0)
            bb = d.location_data.relative_bounding_box
            cx = float(bb.xmin + bb.width / 2.0)
            cy = float(bb.ymin + bb.height / 2.0)
            return cx, cy, float(bb.width), float(bb.height)
    return None


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


def run_person_track(video_path, faces_path, w, h):
    from PIL import Image
    ff = find_ffmpeg()
    face_det = _init_face_detector()
    rembg_remove, rembg_sess = _init_rembg_session('u2net_human_seg')
    mp_selfie = _init_mp_selfie() if rembg_remove is None else None

    if rembg_remove is None and mp_selfie is None:
        sys.exit('ERROR: Install `rembg onnxruntime mediapipe` for cross-platform person segmentation.')

    out = sys.stdout.buffer
    write_faces = faces_path and faces_path != os.devnull
    fh = open(faces_path, 'w', encoding='utf-8') if write_faces else None
    try:
        for idx, rgb in enumerate(_iter_rgb_frames(ff, video_path, w, h)):
            face = _detect_face(face_det, rgb)
            if fh is not None:
                rec = {'f': idx}
                if face is not None:
                    rec.update(x=round(face[0], 5), y=round(face[1], 5), w=round(face[2], 5), h=round(face[3], 5))
                fh.write(json.dumps(rec) + '\n')

            if rembg_remove is not None:
                m_img = rembg_remove(Image.fromarray(rgb), session=rembg_sess, only_mask=True)
                mask = np.asarray(m_img.resize((w, h)), dtype=np.uint8)
                if mask.ndim == 3:
                    mask = mask[:, :, 0]
            else:
                seg = mp_selfie.process(rgb).segmentation_mask
                mask = np.clip(seg * 255.0 + 0.5, 0, 255).astype(np.uint8)

            out.write(mask.tobytes())
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
        run_person_track(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]))
    elif cmd == 'subject_mask':
        run_subject_mask(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), largest=False)
    elif cmd == 'largest_subject_mask':
        run_subject_mask(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), largest=True)
    else:
        sys.exit(f'unknown vision_py subcommand: {cmd}')


if __name__ == '__main__':
    main()
