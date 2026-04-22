import os
import sys
import random
import subprocess
import time
import signal
import argparse
from python_mpv_jsonipc import MPV

# Parse command line arguments
parser = argparse.ArgumentParser(description='Play random YouTube videos from a channel.')
parser.add_argument('channel_id', help='YouTube channel ID')
parser.add_argument('range', nargs='?', help='Range of videos (e.g., 1-100)')
parser.add_argument('--playlist', type=int, help='Create playlist of N random videos')
parser.add_argument('--shuffle', action='store_true', help='Shuffle the playlist')
parser.add_argument('--min-duration', type=int, help='Minimum video duration in seconds')
parser.add_argument('--max-duration', type=int, help='Maximum video duration in seconds')
parser.add_argument('--after-date', help='Only videos uploaded on or after this date (YYYYMMDD)')
parser.add_argument('--before-date', help='Only videos uploaded on or before this date (YYYYMMDD)')
parser.add_argument('--shorts', action='store_true', help='Only show Shorts (videos with #shorts in title)')
parser.add_argument('--no-shorts', action='store_true', help='Exclude Shorts')
parser.add_argument('--max-resolution', type=int,
    help='Maximum video height (e.g., 1080 to cap at 1080p)')
parser.add_argument('--sleep', type=int,
    help='Automatically close mpv after N seconds')
args = parser.parse_args()

CHANNEL_ID = args.channel_id
RANGE = args.range
PLAYLIST_SIZE = args.playlist
SHUFFLE = args.shuffle
LOADING_VIDEO = "loading.mp4"
CACHE_DIR = "cache"
CACHE_FILE = os.path.join(CACHE_DIR, f"{CHANNEL_ID}.txt")

os.makedirs(CACHE_DIR, exist_ok=True)

# Cache format: id\ttitle\tduration\ttimestamp\tupload_date
NUM_CACHE_COLUMNS = 5

if os.path.isfile(CACHE_FILE):
    with open(CACHE_FILE) as f:
        first_line = f.readline().strip()
        if first_line and '\t' in first_line:
            f.seek(0)
            video_data = [line.strip().split('\t') for line in f if line.strip()]
            # Pad short lines (old format upgrade) with empty values
            video_ids = [data[0] for data in video_data]
            video_titles = [data[1] if len(data) > 1 else '' for data in video_data]
            video_durations = [data[2] if len(data) > 2 else '' for data in video_data]
            video_timestamps = [data[3] if len(data) > 3 else '' for data in video_data]
            video_upload_dates = [data[4] if len(data) > 4 else '' for data in video_data]
        else:
            print(f"Cache file {CACHE_FILE} is in old format, deleting and regenerating...")
            os.remove(CACHE_FILE)
            video_ids = []
            video_titles = video_durations = video_timestamps = video_upload_dates = []
else:
    video_ids = []
    video_titles = video_durations = video_timestamps = video_upload_dates = []

if not video_ids:
    print(f"Fetching video metadata for channel {CHANNEL_ID}...")
    subprocess.run(
        f'yt-dlp --flat-playlist -j --extractor-args "youtubetab:approximate_date" "https://www.youtube.com/channel/{CHANNEL_ID}" | jq -r \'[.id, .title, .duration // empty, .timestamp // empty, .upload_date // empty] | @tsv\' > "{CACHE_FILE}"',
        shell=True,
        check=True
    )
    with open(CACHE_FILE) as f:
        video_data = [line.strip().split('\t') for line in f if line.strip()]
        video_ids = [data[0] for data in video_data]
        video_titles = [data[1] if len(data) > 1 else '' for data in video_data]
        video_durations = [data[2] if len(data) > 2 else '' for data in video_data]
        video_timestamps = [data[3] if len(data) > 3 else '' for data in video_data]
        video_upload_dates = [data[4] if len(data) > 4 else '' for data in video_data]
    print(f"Fetched {len(video_ids)} videos")

total = len(video_ids)
if RANGE:
    start, end = map(int, RANGE.split('-'))
else:
    start, end = 1, total

# Apply metadata filters
MIN_DURATION = args.min_duration
MAX_DURATION = args.max_duration
AFTER_DATE = args.after_date
BEFORE_DATE = args.before_date
SHORTS_ONLY = args.shorts
NO_SHORTS = args.no_shorts

def is_short(title):
    return '#shorts' in title.lower()

any_filters = MIN_DURATION or MAX_DURATION or AFTER_DATE or BEFORE_DATE or SHORTS_ONLY or NO_SHORTS
if any_filters:
    filtered_indices = []
    for i in range(start - 1, end):
        include = True
        if SHORTS_ONLY and not is_short(video_titles[i]):
            include = False
        if include and NO_SHORTS and is_short(video_titles[i]):
            include = False
        if include and MIN_DURATION and video_durations[i]:
            try:
                if float(video_durations[i]) < MIN_DURATION:
                    include = False
            except ValueError:
                pass
        if include and MAX_DURATION and video_durations[i]:
            try:
                if float(video_durations[i]) > MAX_DURATION:
                    include = False
            except ValueError:
                pass
        if include and AFTER_DATE and video_upload_dates[i]:
            if video_upload_dates[i] < AFTER_DATE:
                include = False
        if include and BEFORE_DATE and video_upload_dates[i]:
            if video_upload_dates[i] > BEFORE_DATE:
                include = False
        if include:
            filtered_indices.append(i)
    if not filtered_indices:
        print("No videos match the filter criteria. Exiting.")
        sys.exit(1)
    filtered_start = 1
    filtered_end = len(filtered_indices)
    print(f"Filtered: {len(filtered_indices)} videos match criteria out of {end - start + 1} in range")
else:
    filtered_indices = list(range(start - 1, end))
    filtered_start, filtered_end = start, end

# Generate playlist or single video
if PLAYLIST_SIZE:
    available_videos = min(PLAYLIST_SIZE, len(filtered_indices))
    if available_videos < PLAYLIST_SIZE:
        print(f"Warning: Only {available_videos} videos match criteria")

    if SHUFFLE:
        random.shuffle(filtered_indices)
        selected_indices = filtered_indices[:available_videos]
    else:
        selected_indices = random.sample(filtered_indices, available_videos)

    # Create playlist URLs and get metadata
    playlist_urls = []
    playlist_info = []
    for i in selected_indices:
        video_id = video_ids[i]
        video_title = video_titles[i] if i < len(video_titles) else ''
        duration = video_durations[i] if i < len(video_durations) else ''
        upload_date = video_upload_dates[i] if i < len(video_upload_dates) else ''
        playlist_urls.append(f"https://www.youtube.com/watch?v={video_id}")
        playlist_info.append((video_id, video_title, duration, upload_date))

    print(f"Generated playlist of {len(playlist_urls)} videos")
    # Format and align columns
    rows = []
    max_num_width = max(len(str(len(playlist_info))), 2)
    max_id_width = 11  # YouTube IDs are 11 chars
    max_date_width = 10  # YYYY-MM-DD is 10 chars
    max_dur_width = 5  # e.g. "XXXs" or "—"
    for idx, (vid, title, dur, date) in enumerate(playlist_info, 1):
        date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:8]}" if date else "—"
        dur_fmt = f"{int(float(dur))}s" if dur else "—"
        rows.append((idx, vid, date_fmt, dur_fmt, title))

    for num, vid, date, dur, title in rows:
        print(f"  {num:>{max_num_width}}. {vid}  {date:<{max_date_width}}  {dur:>{max_dur_width}}  {title}")

    # First video for initial playback
    youtube_url = playlist_urls[0]
    remaining_playlist = playlist_urls[1:] if len(playlist_urls) > 1 else []
else:
    # Single random video mode
    idx = random.choice(filtered_indices)
    video_id = video_ids[idx]
    video_title = video_titles[idx] if idx < len(video_titles) else ''
    duration = video_durations[idx] if idx < len(video_durations) else ''
    upload_date = video_upload_dates[idx] if idx < len(video_upload_dates) else ''
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    remaining_playlist = []
    date_fmt = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}" if upload_date else "—"
    dur_fmt = f"{int(float(duration))}s" if duration else "—"
    print(f"Selected: {video_id}  {date_fmt}  {dur_fmt:>4s}  {video_title}")

SOCKET = f"/tmp/mpv_socket_{os.getpid()}"
MPV_LOG = "mpv_scriptlog.txt"

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

# Apply resolution cap via mpv's built-in yt-dlp integration
if args.max_resolution:
    fmt = f"bestvideo[height<=?{args.max_resolution}]+bestaudio/best[height<=?{args.max_resolution}]"
    mpv.ytdl_format = fmt
    print(f"Resolution capped at {args.max_resolution}p")

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

sleep_end = time.time() + args.sleep if args.sleep else None
if sleep_end:
    remaining = int(sleep_end - time.time())
    print(f"Sleep timer: mpv will close in {remaining // 60}m{remaining % 60}s")

try:
    # Wait for user to interrupt or MPV to exit
    while True:
        time.sleep(0.5)
        # Check sleep timer
        if sleep_end and time.time() >= sleep_end:
            print("Sleep timer reached, closing mpv...")
            mpv.quit()
            break
        # Check if MPV process has terminated
        if mpv_proc.poll() is not None:
            print("MPV has exited, cleaning up...")
            break
except KeyboardInterrupt:
    print("Exiting and cleaning up...")
finally:
    # Cleanup MPV and socket
    print("Cleaning up MPV...")
    mpv.terminate()
    if os.path.exists(SOCKET):
        os.remove(SOCKET)
    print(f"\nTo debug mpv, run:\n  tail -f {MPV_LOG}\n")
