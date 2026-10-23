#!/usr/bin/env python3
"""Transcribe Li Qiqi Douyin audio (NNN.mp3) to transcripts (NNN.txt) with faster-whisper.

Usage:
  transcribe.py --model small --only 001     # test one file
  transcribe.py --model small                # bulk run (resumes: skips existing non-empty transcripts)
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

BASE = Path.home() / "workspace/goals/douyin-video-watch-through/files"
AUDIO_DIR = BASE / "audio"
OUT_DIR = BASE / "transcripts"
LIST_FILE = BASE / "李奇奇124视频清单.md"
LOG_FILE = Path.home() / "workspace/goals/douyin-video-watch-through/hidden_files/transcription_log.txt"

TITLE_RE = re.compile(r"^(\d+)\.\s+(.+?)\s+—\s+(https?://\S+)\s*$")


def load_titles():
    titles = {}
    for line in LIST_FILE.read_text(encoding="utf-8").splitlines():
        m = TITLE_RE.match(line.strip())
        if m:
            titles[m.group(1).zfill(3)] = m.group(2).strip()
    return titles


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="small")
    ap.add_argument("--model-path", default=None,
                    help="local model directory (bypasses HF hub download)")
    ap.add_argument("--only", default=None, help="transcribe only this serial, e.g. 001")
    args = ap.parse_args()

    # Compat shim: faster-whisper 1.2.1 calls av.open(..., metadata_errors="ignore"),
    # but the venv's av 19 removed that kwarg (and av<15 has no usable wheel here).
    # Drop the kwarg; our MP3s are standard files, so default metadata handling is fine.
    import av
    _orig_av_open = av.open

    def _av_open_compat(file, mode="r", **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(file, mode=mode, **kwargs)

    av.open = _av_open_compat

    from faster_whisper import WhisperModel

    titles = load_titles()
    log(f"loaded {len(titles)} titles from list file")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(AUDIO_DIR.glob("*.mp3"))
    if args.only:
        files = [f for f in files if f.stem == args.only]
        if not files:
            log(f"no audio file for serial {args.only}")
            return 2
    model_src = args.model_path or args.model
    log(f"model={model_src}, files to consider: {len(files)}")

    t0 = time.time()
    model = WhisperModel(model_src, device="cpu", compute_type="int8")
    log(f"model {model_src} loaded in {time.time() - t0:.0f}s")

    # Diagnosed 2026-10-22: these 8 MP3s are duplicate downloads (050/051/052/053/
    # 054/060 byte-identical; 056/057 byte-identical) containing music/noise with
    # no speech (no-VAD auto-detect run on 050: language guess km @0.29, 12 chars).
    # Skipping them here; they stay on the failure list with this cause.
    DIAGNOSED_NO_SPEECH = {"050", "051", "052", "053", "054", "056", "057", "060"}

    ok, fail, skipped = [], [], []
    total_audio = 0.0
    for f in sorted(files):
        serial = f.stem
        if serial in DIAGNOSED_NO_SPEECH:
            log(f"{serial}: SKIP diagnosed duplicate music-only audio, no speech")
            fail.append(serial)
            continue
        out = OUT_DIR / f"{serial}.txt"
        if out.exists() and out.stat().st_size > 50:
            # resume: already transcribed (title line + body)
            skipped.append(serial)
            continue
        title = titles.get(serial)
        if not title:
            log(f"{serial}: NO TITLE MATCH -> fail")
            fail.append(serial)
            continue
        try:
            s = time.time()
            segments, info = model.transcribe(
                str(f), language="zh", beam_size=5, vad_filter=True
            )
            text = "".join(seg.text for seg in segments).strip()
            dt = time.time() - s
            total_audio += info.duration
            if not text:
                log(f"{serial}: EMPTY transcript (audio {info.duration:.0f}s) -> fail")
                fail.append(serial)
                continue
            out.write_text(title + "\n\n" + text + "\n", encoding="utf-8")
            log(f"{serial}: OK chars={len(text)} audio={info.duration:.0f}s took={dt:.0f}s "
                f"speed={info.duration / max(dt, 1):.1f}x")
            ok.append(serial)
        except Exception as e:
            log(f"{serial}: ERROR {type(e).__name__}: {e} -> fail")
            fail.append(serial)

    log(f"DONE ok={len(ok)} fail={len(fail)} skipped={len(skipped)} "
        f"total_audio={total_audio:.0f}s failures={fail}")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
