#!/bin/bash
# 并行分段渲染再拼接：./render_par.sh <段数> <输出.mp4> <混音.wav> [场景名，默认 film；英文版 film_en]
# 分段留在 out/parts/；交付压制用 deliver.sh。
set -e
shopt -s nullglob
cd "$(dirname "$0")"
parts=$1; out=$2; audio=$3; scene=${4:-film}
total=$(node -e "const j=require('./scenes/'+process.argv[1]+'.json');console.log(Math.round(j.duration*30))" "$scene")
step=$(( (total + parts - 1) / parts ))
mkdir -p out/parts
rm -f out/parts/p_*.mp4 out/parts/list.txt
pids=()
for i in $(seq 0 $((parts - 1))); do
  a=$(( i * step )); b=$(( (i + 1) * step )); (( b > total )) && b=$total
  JPEG=1 FRAMES=$a:$b node render.mjs scenes/$scene.html out/parts/p_$i.mp4 > out/parts/p_$i.log 2>&1 &
  pids+=($!)
  echo "file 'p_$i.mp4'" >> out/parts/list.txt
done
for p in "${pids[@]}"; do wait "$p"; done
ffmpeg -nostdin -y -loglevel error -f concat -safe 0 -i out/parts/list.txt -i "$audio" -map 0:v -map 1:a -c:v copy \
  -ar 48000 -c:a aac -b:a 256k -shortest -movflags +faststart "$out"
echo "done $out ($total frames)"
