"""Download the MediaPipe landmark models (one-time setup).

    python download_models.py           # hand model (~7.8 MB), needed for Stage 2+
    python download_models.py --pose    # also the body-pose model (~5.8 MB)

Files come from Google's official MediaPipe model storage and are saved to
models/mediapipe/. Existing, complete files are skipped.
"""
from __future__ import annotations

import argparse
import ssl
import sys
import urllib.request

import config

BASE = "https://storage.googleapis.com/mediapipe-models"
MODELS = {
    "hand_landmarker.task": f"{BASE}/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
    "pose_landmarker_lite.task": f"{BASE}/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task",
}


def _ssl_context() -> ssl.SSLContext:
    """Verified TLS. python.org's macOS Python ships without root certificates,
    so prefer the certifi bundle (installed with streamlit's dependencies)."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def download(name: str, url: str) -> bool:
    dest = config.MEDIAPIPE_MODELS_DIR / name
    config.MEDIAPIPE_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=60, context=_ssl_context()) as resp:
            expected = int(resp.headers.get("Content-Length", 0))
            if dest.exists() and expected and dest.stat().st_size == expected:
                print(f"✓ {name} already present ({expected / 1e6:.1f} MB)")
                return True
            print(f"↓ {name} ({expected / 1e6:.1f} MB) from {url}")
            with open(tmp, "wb") as f:
                while chunk := resp.read(1 << 16):
                    f.write(chunk)
        if expected and tmp.stat().st_size != expected:
            raise IOError(f"size mismatch: got {tmp.stat().st_size}, expected {expected}")
        tmp.replace(dest)
        print(f"✓ saved to {dest}")
        return True
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        print(f"✗ {name} failed: {exc}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--pose", action="store_true", help="also download the pose model")
    args = parser.parse_args()
    wanted = ["hand_landmarker.task"] + (["pose_landmarker_lite.task"] if args.pose else [])
    results = [download(n, MODELS[n]) for n in wanted]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
