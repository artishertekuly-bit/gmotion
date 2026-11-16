"""Cross-platform Vision tool locator for presenter tracking and subject segmentation.

Prefers native Apple Vision Swift tools when running on macOS with `swiftc`, and automatically
falls back to `vision_py.py` (MediaPipe Face Detection + rembg ONNX) on Ubuntu Linux GitHub Actions
and Windows.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(os.path.dirname(HERE), '.cache', 'vision')
TOOLS = ('person_track', 'subject_mask', 'largest_subject_mask')


def tool_cmd(name):
    """Return an argv prefix list suitable for `subprocess.Popen(tool_cmd(name) + args)`."""
    if name not in TOOLS:
        raise ValueError(name)
    src = os.path.join(HERE, 'vision', name + '.swift')
    swiftc = shutil.which('swiftc') if sys.platform == 'darwin' else None
    if swiftc and os.path.exists(src):
        exe = os.path.join(CACHE, name)
        if not os.path.exists(exe) or os.path.getmtime(src) > os.path.getmtime(exe):
            os.makedirs(CACHE, exist_ok=True)
            sys.stderr.write('compiling Vision helper %s ...\n' % name)
            subprocess.run([swiftc, '-O', src, '-o', exe], check=True)
        return [exe]
    return [sys.executable, '-X', 'utf8', os.path.join(HERE, 'vision_py.py'), name]


def tool(name):
    """Legacy single-path accessor (returns vision_py.py or compiled macOS binary)."""
    return tool_cmd(name)[-1] if len(tool_cmd(name)) == 1 else os.path.join(HERE, 'vision_py.py')


def upright_proxy(ffmpeg, src, dst, w, h, fps):
    """ffmpeg applies the rotation flag of phone videos; Vision then sees the picture upright."""
    subprocess.run([ffmpeg, '-v', 'error', '-y', '-i', src, '-an',
                    '-vf', 'scale=%d:%d:flags=bicubic,fps=%s' % (w, h, fps),
                    '-c:v', 'prores_ks', '-profile:v', '0', dst], check=True)
    return dst
