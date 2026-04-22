import os
import sys
import random
import subprocess
import time
import signal
from python_mpv_jsonipc import MPV

CHANNEL_ID = sys.argv[1]
RANGE = sys.argv[2] if len(sys.argv) > 2 else None
LOADING_VIDEO = "loading.mp4"
CACHE_DIR = "cache"
CACHE_FILE = os.path.join(CACHE_DIR, f"{CHANNEL_ID}.txt")

os.makedirs(CACHE_DIR, exist_ok=True)

if not os.path.isfile(CACHE_FILE):
    subprocess.run(
        f'yt-dlp --flat-playlist -j "https://www.youtube.com/channel/{CHANNEL_ID}" | jq -r \'.id\' > "{CACHE_FILE}"',
        shell=True,
        check=True
    )

with open(CACHE_FILE) as f:
    video_ids = [line.strip() for line in f if line.strip()]

total = len(video_ids)
if RANGE:
    start, end = map(int, RANGE.split('-'))
else:
    start, end = 1, total

random_line = random.randint(start, end)
video_id = video_ids[random_line - 1]
youtube_url = f"https://www.youtube.com/watch?v={video_id}"

SOCKET = f"/tmp/mpv_socket_{os.getpid()}"
MPV_LOG = os.path.expanduser("~/mpv_scriptlog.txt")

# Kill any existing mpv process using the same socket
if os.path.exists(SOCKET):
    try:
        pid_output = subprocess.check_output(
            f"lsof -t {SOCKET}", shell=True
        ).decode().strip()
        if pid_output:
            for pid in pid_output.splitlines():
                os.kill(int(pid), signal.SIGTERM)
        os.remove(SOCKET)
    except Exception:
        pass

print(f"Starting mpv with log at {MPV_LOG}")
mpv_proc = subprocess.Popen([
    "mpv",
    "--input-ipc-server=" + SOCKET,
    "--force-window=yes",
    "--idle=yes",
    "--no-terminal",
    f"--log-file={MPV_LOG}"
])

while not os.path.exists(SOCKET):
    time.sleep(0.1)

print("Connecting to mpv IPC...")
mpv = MPV(ipc_socket=SOCKET, start_mpv=False)

print("Loading and looping loading.mp4...")
mpv.loadfile(LOADING_VIDEO, "replace")
mpv.loop_file = "inf"

print("Appending YouTube video to playlist (seamless transition)...")
mpv.command("loadfile", youtube_url, "append-play")
mpv.loop_file = "no"  # Only loop the loading video

print("YouTube video will play when ready. Press Ctrl+C to exit and clean up.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting and cleaning up...")
    mpv.terminate()
    if os.path.exists(SOCKET):
        os.remove(SOCKET)
    print(f"\nTo debug mpv, run:\n  tail -f {MPV_LOG}\n")
