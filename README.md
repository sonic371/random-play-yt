# random-play-yt

Play random YouTube videos from a channel using `mpv` with seamless transitions.

## Requirements

- Python 3 + `python-mpv-jsonipc`
- `yt-dlp`, `jq`, `mpv`
- `loading.mp4` in the script directory (placeholder video while YouTube loads)

```bash
pip install python-mpv-jsonipc
# Arch Linux
sudo pacman -S yt-dlp jq mpv
# Ubuntu/Debian
sudo apt install yt-dlp jq mpv
```

## Usage

```bash
python random_play.py CHANNEL_ID
```

Videos are cached locally after the first run, so subsequent runs are instant.

## Examples

**Basic — play a random video from a channel:**
```bash
python random_play.py UCq6VFHwMzcMXbuKyG7SQYIg
```

**Playlist mode — queue multiple videos:**
```bash
# Sequential (oldest first from cache)
python random_play.py UCq6VFHwMzcMXbuKyG7SQYIg --playlist 10

# Shuffled
python random_play.py UCq6VFHwMzcMXbuKyG7SQYIg --playlist 10 --shuffle
```

**Filter by duration:**
```bash
# Only videos longer than 5 minutes
python random_play.py UCq6VFHwMzcMXbuKyG7SQYIg --min-duration 300

# Only videos shorter than 10 minutes
python random_play.py UCq6VFHwMzcMXbuKyG7SQYIg --max-duration 600

# Between 3 and 8 minutes
python random_play.py UCq6VFHwMzcMXbuKyG7SQYIg --min-duration 180 --max-duration 480
```

**Filter by upload date:**
```bash
# Only videos from 2025 onwards
python random_play.py UCq6VFHwMzcMXbuKyG7SQYIg --after-date 20250101

# Only videos before 2023
python random_play.py UCq6VFHwMzcMXbuKyG7SQYIg --before-date 20230101

# Videos uploaded in 2024-2025
python random_play.py UCq6VFHwMzcMXbuKyG7SQYIg --after-date 20240101 --before-date 20251231
```

**Filter shorts:**
```bash
# Only Shorts (videos with #shorts in title)
python random_play.py UC7kW7V4IHduc6aqxmR91CWQ --shorts

# Exclude Shorts
python random_play.py UC7kW7V4IHduc6aqxmR91CWQ --no-shorts
```

**Combine filters:**
```bash
# Shuffled playlist of 5, 3-10 min, from 2024 onward, no shorts
python random_play.py UCq6VFHwMzcMXbuKyG7SQYIg --playlist 5 --shuffle \
    --min-duration 180 --max-duration 600 --after-date 20240101 --no-shorts
```

**Limit to a range of cache indices:**
```bash
# Only consider videos 1-100 in the cache
python random_play.py UCq6VFHwMzcMXbuKyG7SQYIg 1-100 --playlist 5 --shuffle
```

**Cap video resolution:**
```bash
# Don't stream higher than 1080p
python random_play.py UCq6VFHwMzcMXbuKyG7SQYIg --max-resolution 1080

# Cap at 720p (good for slower connections)
python random_play.py UCq6VFHwMzcMXbuKyG7SQYIg --max-resolution 720
```

**Sleep timer — auto-close mpv after a set time:**
```bash
# Close mpv after 30 minutes
python random_play.py UCq6VFHwMzcMXbuKyG7SQYIg --sleep 1800

# Close after 1 hour with playlist
python random_play.py UCq6VFHwMzcMXbuKyG7SQYIg --playlist 10 --shuffle --sleep 3600
```

## How it works

1. Fetches and caches video metadata (ID, title, duration, upload date) from the channel using `yt-dlp`
2. Applies any filter flags and selects videos
3. Starts `mpv` with an IPC socket, plays a loading video on loop
4. Queues the YouTube video — plays seamlessly once loaded
5. Exits when `mpv` is closed or Ctrl+C is pressed

Use `>` / `<` in mpv to skip between playlist items.
