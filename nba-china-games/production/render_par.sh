#!/bin/bash
# 并行分段渲染再拼接：./render_par.sh <h|v> <段数> <输出.mp4> <混音.wav>
# 分段文件留在 out/parts/，供 rerender_part.sh 局部重渲；交付压制用 deliver.sh。
set -e
shopt -s nullglob
cd "$(dirname "$0")"
mode=$1; parts=$2; out=$3; audio=$4
query=""; [[ $mode == v ]] && query="v=1"
total=$(node -e "const j=require('./scenes/film_${mode}.json');console.log(Math.round(j.duration*30))")
step=$(( (total + parts - 1) / parts ))
mkdir -p out/parts
rm -f out/parts/${mode}_*.mp4 out/parts/${mode}_list.txt
pids=()
for i in $(seq 0 $((parts - 1))); do
  a=$(( i * step )); b=$(( (i + 1) * step )); (( b > total )) && b=$total
  QUERY=$query JPEG=1 FRAMES=$a:$b node render.mjs scenes/film.html out/parts/${mode}_$i.mp4 > out/parts/${mode}_$i.log 2>&1 &
  pids+=($!)
  echo "file '${mode}_$i.mp4'" >> out/parts/${mode}_list.txt
done
for p in "${pids[@]}"; do wait "$p"; done
ffmpeg -y -loglevel error -f concat -safe 0 -i out/parts/${mode}_list.txt -i "$audio" -map 0:v -map 1:a -c:v copy \
  -ar 48000 -c:a aac -b:a 256k -shortest -movflags +faststart "$out"
echo "done $out ($total frames)"
