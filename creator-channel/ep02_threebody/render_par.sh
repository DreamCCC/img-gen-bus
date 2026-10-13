#!/bin/bash
# 并行分段渲染再拼接（无声母版）：./render_par.sh <段数> <输出.mp4>
# 分段文件留在 out/parts/，局部重渲：FRAMES=a:b JPEG=1 node render.mjs scenes/film.html out/parts/f_<i>.mp4
set -e
shopt -s nullglob
cd "$(dirname "$0")"
parts=$1; out=$2
total=$(node -e "const j=require('./scenes/film.json');console.log(Math.round(j.duration*30))")
step=$(( (total + parts - 1) / parts ))
mkdir -p out/parts
rm -f out/parts/f_*.mp4 out/parts/f_list.txt
pids=()
for i in $(seq 0 $((parts - 1))); do
  a=$(( i * step )); b=$(( (i + 1) * step )); (( b > total )) && b=$total
  JPEG=1 FRAMES=$a:$b node render.mjs scenes/film.html out/parts/f_$i.mp4 > out/parts/f_$i.log 2>&1 &
  pids+=($!)
  echo "file 'f_$i.mp4'" >> out/parts/f_list.txt
done
for p in "${pids[@]}"; do wait "$p"; done
ffmpeg -y -loglevel error -f concat -safe 0 -i out/parts/f_list.txt -c:v copy -movflags +faststart "$out"
echo "done $out ($total frames)"
