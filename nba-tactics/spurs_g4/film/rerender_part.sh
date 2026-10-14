#!/bin/bash
# 重渲 render_par.sh 生成的某一段（拆成 4 个进程），再拼接成母版：
#   ./rerender_part.sh <h|v|f|vt> <段号> <段数> <输出.mp4> <混音.wav>
# 需要 out/parts/ 里其余各段还在；被清理过就直接重跑 render_par.sh。
set -e
shopt -s nullglob
cd "$(dirname "$0")"
mode=$1; idx=$2; parts=$3; out=$4; audio=$5
query=""; [[ $mode == v ]] && query="v=1"; [[ $mode == f ]] && query="m=f"; [[ $mode == vt ]] && query="m=vt"
total=$(node -e "const j=require('./scenes/film_${mode}.json');console.log(Math.round(j.duration*30))")
step=$(( (total + parts - 1) / parts ))
a=$(( idx * step )); b=$(( (idx + 1) * step )); (( b > total )) && b=$total
sub=$(( (b - a + 3) / 4 ))
pids=()
for k in 0 1 2 3; do
  sa=$(( a + k * sub )); sb=$(( a + (k + 1) * sub )); (( sb > b )) && sb=$b
  QUERY=$query JPEG=1 FRAMES=$sa:$sb node render.mjs scenes/film.html out/parts/${mode}_${idx}_$k.mp4 > out/parts/${mode}_${idx}_$k.log 2>&1 &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
rm -f out/parts/${mode}_list.txt
for i in $(seq 0 $((parts - 1))); do
  if (( i == idx )); then
    for k in 0 1 2 3; do echo "file '${mode}_${idx}_$k.mp4'" >> out/parts/${mode}_list.txt; done
  else
    echo "file '${mode}_$i.mp4'" >> out/parts/${mode}_list.txt
  fi
done
ffmpeg -y -loglevel error -f concat -safe 0 -i out/parts/${mode}_list.txt -i "$audio" -map 0:v -map 1:a -c:v copy \
  -ar 48000 -c:a aac -b:a 256k -shortest -movflags +faststart "$out"
echo "done $out"
