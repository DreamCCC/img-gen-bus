#!/bin/bash
# 重渲 render_par.sh 生成的某几段（每段拆成 SUBS 个进程，默认 4），写回 out/parts/<mode>_<段号>.mp4，再拼接成母版：
#   ./rerender_part.sh <h|v|f|vt|f_en|vt_en> "<段号> [段号 ...]" <段数> <输出.mp4> <混音.wav>
# 需要 out/parts/ 里其余各段还在；被清理过就直接重跑 render_par.sh。
set -e
shopt -s nullglob
cd "$(dirname "$0")"
mode=$1; idxs=$2; parts=$3; out=$4; audio=$5; subs=${SUBS:-4}
query=""; [[ $mode == v ]] && query="v=1"; [[ $mode == f ]] && query="m=f"; [[ $mode == vt ]] && query="m=vt"; [[ $mode == *_en ]] && query="m=${mode%_en}&lang=en"
total=$(node -e "const j=require('./scenes/film_${mode}.json');console.log(Math.round(j.duration*30))")
step=$(( (total + parts - 1) / parts ))
pids=()
for idx in $idxs; do
  a=$(( idx * step )); b=$(( (idx + 1) * step )); (( b > total )) && b=$total
  sub=$(( (b - a + subs - 1) / subs ))
  for k in $(seq 0 $((subs - 1))); do
    sa=$(( a + k * sub )); sb=$(( a + (k + 1) * sub )); (( sb > b )) && sb=$b
    QUERY=$query JPEG=1 FRAMES=$sa:$sb node render.mjs scenes/film.html out/parts/${mode}_${idx}_$k.mp4 > out/parts/${mode}_${idx}_$k.log 2>&1 &
    pids+=($!)
  done
done
for p in "${pids[@]}"; do wait "$p"; done
for idx in $idxs; do
  rm -f out/parts/${mode}_${idx}_list.txt
  for k in $(seq 0 $((subs - 1))); do echo "file '${mode}_${idx}_$k.mp4'" >> out/parts/${mode}_${idx}_list.txt; done
  ffmpeg -nostdin -y -loglevel error -f concat -safe 0 -i out/parts/${mode}_${idx}_list.txt -c copy out/parts/${mode}_$idx.mp4
  rm -f out/parts/${mode}_${idx}_*.mp4 out/parts/${mode}_${idx}_list.txt
done
rm -f out/parts/${mode}_list.txt
for i in $(seq 0 $((parts - 1))); do echo "file '${mode}_$i.mp4'" >> out/parts/${mode}_list.txt; done
ffmpeg -nostdin -y -loglevel error -f concat -safe 0 -i out/parts/${mode}_list.txt -i "$audio" -map 0:v -map 1:a -c:v copy \
  -ar 48000 -c:a aac -b:a 256k -shortest -movflags +faststart "$out"
echo "done $out"
