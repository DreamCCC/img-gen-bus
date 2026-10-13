#!/bin/bash
# 交付压制：测混音整体响度 → 固定增益 + 过采样限幅 → H.264/AAC → 复测
#   ./deliver.sh <母版.mp4> <混音.wav> <交付.mp4> <maxrate，横版 22M / 竖版 16M> [目标 LUFS，默认 -16]
# 不用 loudnorm：单遍 loudnorm 是动态增益，人声和音乐会忽大忽小。
set -euo pipefail
master=$1; mix=$2; out=$3; maxrate=$4; target=${5:--16}
I=$(ffmpeg -nostats -i "$mix" -af ebur128 -f null - 2>&1 | awk '/^ *I:/{v=$2} END{print v}')
gain=$(awk -v t="$target" -v i="$I" 'BEGIN{printf "%.1f", t - i + 0.3}')
echo "mix I=${I} LUFS -> gain ${gain} dB"
ffmpeg -y -loglevel error -i "$master" -i "$mix" -map 0:v -map 1:a \
  -c:v libx264 -preset slow -crf 19 -maxrate "$maxrate" -bufsize "$(( ${maxrate%M} * 2 ))M" -pix_fmt yuv420p \
  -af "volume=${gain}dB,aresample=192000,alimiter=limit=0.75:attack=2:release=60:level=false,aresample=48000" \
  -c:a aac -b:a 256k -shortest -movflags +faststart "$out"
ffmpeg -nostats -i "$out" -af ebur128=peak=true -f null - 2>&1 | grep -E "^ +(I|LRA|Peak):" | tail -3
