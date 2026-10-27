#!/usr/bin/env bash
# "Watch" a Blender tutorial: transcript + reference frames, ready for a shot plan.
#
# Usage: study_tutorial.sh <youtube-url | local-video> <out_dir> [dense_seconds=30] [sheet_every=20]
#   transcript.vtt / transcript.txt  full transcript (captions via yt-dlp; local files need Whisper)
#   dense/                           every frame of the first N seconds (shot breakdown: lens, height, speed)
#   sheets/sheet_XX.jpg              timestamped contact sheets of the whole tutorial (one frame / sheet_every s)
#   frames/                          the same frames as single PNGs, to use as per-step references
#
# If YouTube blocks the download (CAPTCHA / bot check), run it on your own machine with a browser
# session: add  --cookies-from-browser chrome  to the yt-dlp lines, or download manually and pass the file.
set -euo pipefail
src="$1"; out="$2"; dense="${3:-30}"; every="${4:-20}"
mkdir -p "$out"/{dense,sheets,frames}

if [[ -f "$src" ]]; then
  video="$src"
else
  yt-dlp --skip-download --write-subs --write-auto-subs --sub-langs "en.*,en" --sub-format vtt \
         -o "$out/transcript.%(ext)s" "$src" || echo "no captions downloaded"
  yt-dlp -f "bv*[height<=1080]+ba/b[height<=1080]" --merge-output-format mp4 -o "$out/tutorial.%(ext)s" "$src"
  video="$out/tutorial.mp4"
  vtt=$(ls "$out"/transcript*.vtt 2>/dev/null | head -1 || true)
  if [[ -n "${vtt}" ]]; then
    # strip VTT timing/markup and duplicate rolling-caption lines into plain text
    sed -e '/-->/d' -e '/^WEBVTT/d' -e '/^Kind:/d' -e '/^Language:/d' -e 's/<[^>]*>//g' "$vtt" \
      | awk 'NF && $0!=prev {print; prev=$0}' > "$out/transcript.txt"
  fi
fi

fps=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$video")
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$video")
ffmpeg -y -loglevel error -t "$dense" -i "$video" -vf "scale=960:-2" "$out/dense/f_%05d.jpg"
ffmpeg -y -loglevel error -i "$video" -vf "fps=1/${every},scale=1280:-2" "$out/frames/t_%04d.png"
ffmpeg -y -loglevel error -i "$video" \
  -vf "fps=1/${every},scale=384:-2,drawtext=text='%{pts\:hms}':x=6:y=6:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6,tile=5x4:padding=4:margin=4" \
  "$out/sheets/sheet_%02d.jpg"
echo "video ${dur}s @ ${fps} fps"
echo "dense frames: $(ls "$out/dense" | wc -l) (first ${dense}s) | step frames: $(ls "$out/frames" | wc -l) | sheets: $(ls "$out/sheets" | wc -l)"
[[ -f "$out/transcript.txt" ]] && echo "transcript: $(wc -w < "$out/transcript.txt") words" || echo "transcript: none (use the video-cut skill's transcribe.py on the video)"
