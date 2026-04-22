import os
import sys
import random
import subprocess
import time
import signal
import argparse
from python_mpv_jsonipc import MPV

def select_random_video(video_ids, start, end):
    """Select a random video from the list."""
    random_line = random.randint(start, end)
    video_id = video_ids[random_line - 1]
    return f"https://www.youtube.com/watch?v={video_id}"

# Parse command line arguments
parser = argparse.ArgumentParser(description='Play random YouTube videos from a channel.')
parser.add_argument('channel_id', help='YouTube channel ID')
parser.add_argument('range', nargs='?', help='Range of videos (e.g., 1-100)')
parser.add_argument('--playlist', type=int, help='Create playlist of N random videos')
parser.add_argument('--shuffle', action='store_true', help='Shuffle the playlist')
args = parser.parse_args()

CHANNEL_ID = args.channel_id
RANGE = args.range
PLAYLIST_SIZE = args.playlist
SHUFFLE = args.shuffle
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

# Generate playlist or single video
if PLAYLIST_SIZE:
    # Ensure playlist size doesn't exceed available videos
    available_videos = min(PLAYLIST_SIZE, end - start + 1)
    if available_videos < PLAYLIST_SIZE:
        print(f"Warning: Only {available_videos} videos available in range {start}-{end}")

    # Generate non-repeating random indices
    indices = list(range(start - 1, end))  # Convert to 0-based
    if SHUFFLE:
        random.shuffle(indices)
    selected_indices = indices[:available_videos]

    # Create playlist URLs
    playlist_urls = [f"https://www.youtube.com/watch?v={video_ids[i]}" for i in selected_indices]
    print(f"Generated playlist of {len(playlist_urls)} videos")

    # First video for initial playback
    youtube_url = playlist_urls[0]
    remaining_playlist = playlist_urls[1:] if len(playlist_urls) > 1 else []
else:
    # Single random video mode (original behavior)
    youtube_url = select_random_video(video_ids, start, end)
    remaining_playlist = []

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

print("YouTube video will play when ready.")
if PLAYLIST_SIZE:
    print(f"Playlist mode: {len(playlist_urls)} videos loaded")
    print("Use MPV controls: > for next video, < for previous video")
else:
    print("Single video mode: Press Ctrl+C to exit")

# Add remaining videos to playlist if in playlist mode
for url in remaining_playlist:
    mpv.command("loadfile", url, "append-play")

try:
    # Wait for user to interrupt
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting and cleaning up...")
finally:
    # Cleanup MPV and socket
    print("Cleaning up MPV...")
    mpv.terminate()
    if os.path.exists(SOCKET):
        os.remove(SOCKET)
    print(f"\nTo debug mpv, run:\n  tail -f {MPV_LOG}\n")
