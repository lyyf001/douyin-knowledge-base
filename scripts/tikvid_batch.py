#!/usr/bin/env python3
"""Batch download MP3 audio for 李奇奇读书号 Douyin videos via TikVid.

Method (verified on video #1, do not change):
  1. POST https://tikvid.io/api/ajaxSearch with UA=desktop Chrome,
     Referer: https://tikvid.io/en, X-Requested-With: XMLHttpRequest,
     form fields q=<douyin link>, lang=en. On status=ok, data is HTML;
     take the href of the <a> whose text is "Download MP3".
  2. GET that link with the same UA + Referer, save as MP3.
  3. Verify with ffprobe (duration > 0 counts as success).

Rules: sequential, parse->download immediately per video (links may
expire); a few seconds of sleep between videos; on 429 or a block
signal from the parse endpoint, stop immediately and report; a single
video failing is recorded and skipped, never retried in a loop.
"""
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

BASE = os.path.expanduser("~/workspace/goals/douyin-video-watch-through/files/audio")
URLS_FILE = os.path.join(BASE, "urls.txt")
LOG_FILE = os.path.join(BASE, "download_log.md")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
REFERER = "https://tikvid.io/en"
API = "https://tikvid.io/api/ajaxSearch"
SLEEP_BETWEEN = 4


class RateLimited(Exception):
    pass


def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    line = f"{ts()} {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def ffprobe_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=60).stdout.strip()
        d = float(out)
        return d if d > 0 else 0.0
    except Exception:
        return 0.0


def run_curl(args, timeout):
    """Run curl, return (http_code, stdout). Raises on curl-level failure."""
    p = subprocess.run(["curl", "-s", "-w", "\n%{http_code}"] + args,
                       capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise Exception(f"curl exit {p.returncode}: {p.stderr.strip()[:120]}")
    out = p.stdout
    body, _, code_s = out.rpartition("\n")
    try:
        code = int(code_s.strip())
    except ValueError:
        code = 0
    return code, body


def parse_mp3_link(q):
    try:
        code, body = run_curl([
            "--max-time", "60", "-A", UA, "-e", REFERER,
            "-H", "X-Requested-With: XMLHttpRequest",
            "--data-urlencode", f"q={q}", "--data", "lang=en", API], 90)
    except Exception as e:
        raise Exception(f"parse error: {e}")
    if code in (429, 403):
        raise RateLimited(f"parse HTTP {code}")
    if code != 200:
        raise Exception(f"parse HTTP {code}")
    try:
        j = json.loads(body)
    except Exception:
        raise Exception("parse: bad JSON")
    if j.get("status") != "ok":
        raise Exception(f"parse: status={j.get('status')}")
    page = j.get("data", "") or ""
    # Parse properly: find the <a> whose visible text contains "Download MP3"
    # and take its href verbatim (regex over raw HTML proved fragile here).
    from html.parser import HTMLParser

    class LinkFinder(HTMLParser):
        def __init__(self):
            super().__init__()
            self.current = None  # (href, text_parts)
            self.found = None

        def handle_starttag(self, tag, attrs):
            if tag == "a" and self.found is None:
                d = dict(attrs)
                self.current = (d.get("href"), [])

        def handle_data(self, data):
            if self.current is not None:
                self.current[1].append(data)

        def handle_endtag(self, tag):
            if tag == "a" and self.current is not None:
                href, parts = self.current
                text = "".join(parts)
                if href and "Download MP3" in text:
                    self.found = href
                self.current = None

    finder = LinkFinder()
    finder.feed(page)
    href = finder.found
    if not href:
        raise Exception("parse: no Download MP3 link in HTML")
    href = html.unescape(href).strip()
    if href.startswith("/"):
        href = "https://tikvid.io" + href
    if not href.startswith("http"):
        raise Exception(f"parse: unexpected href {href[:60]}")
    return href


def download(url, dest):
    tmp = dest + ".part"
    try:
        p = subprocess.run(
            ["curl", "-sL", "--max-time", "300", "-A", UA, "-e", REFERER,
             "-w", "\n%{http_code}", "-o", tmp, url],
            capture_output=True, text=True, timeout=330)
        code_s = p.stdout.strip().split("\n")[-1] if p.stdout.strip() else "0"
        try:
            code = int(code_s)
        except ValueError:
            code = 0
        if p.returncode != 0:
            raise Exception(f"curl exit {p.returncode}")
        if code in (429, 403):
            raise RateLimited(f"download HTTP {code}")
        if code != 200:
            raise Exception(f"download HTTP {code}")
    except RateLimited:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    except Exception as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise Exception(f"download error: {e}")
    os.replace(tmp, dest)


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    items = []
    with open(URLS_FILE, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2 and parts[0].isdigit():
                items.append((int(parts[0]), parts[1].strip()))
    items.sort()

    log("## TikVid 批量下载开始（逐支顺序，解析→立即下载）")
    ok, failed, skipped = 0, [], 0
    stopped = None
    processed = 0
    for num, url in items:
        dest = os.path.join(BASE, f"{num:03d}.mp3")
        if os.path.exists(dest) and ffprobe_duration(dest) > 0:
            skipped += 1
            continue
        if limit is not None and processed >= limit:
            break
        processed += 1
        try:
            link = parse_mp3_link(url)
            download(link, dest)
            dur = ffprobe_duration(dest)
            if dur <= 0:
                if os.path.exists(dest):
                    os.remove(dest)
                raise Exception("ffprobe duration 0 (not valid audio)")
            ok += 1
            log(f"{num:03d} OK {dur:.1f}s")
        except RateLimited as e:
            stopped = str(e)
            log(f"!!! RATE LIMITED, STOPPING at {num:03d}: {e}")
            break
        except Exception as e:
            failed.append((num, str(e)[:120]))
            log(f"{num:03d} FAIL {e}"[:200])
        if num != items[-1][0]:
            time.sleep(SLEEP_BETWEEN)

    log(f"## TikVid 批量下载结束：成功 {ok} 支，跳过已有 {skipped} 支，"
        f"失败 {len(failed)} 支，限流中断：{stopped or '否'}")
    for num, reason in failed:
        log(f"## 失败清单：{num:03d} {reason}")
    print(f"SUMMARY ok={ok} skipped={skipped} failed={len(failed)} "
          f"stopped={stopped or 'no'}", flush=True)
    for num, reason in failed:
        print(f"FAILED {num:03d} {reason}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
