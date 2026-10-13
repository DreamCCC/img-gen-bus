#!/bin/bash
# 渲染静帧并拼成联系表：tools/qa.sh <名字> <t1,t2,...> [每行几张，默认 3]
set -e
cd "$(dirname "$0")/.."
name=$1; times=$2; cols=${3:-3}
dir=out/qa/$name
rm -rf "$dir"; mkdir -p "$dir"
node render.mjs scenes/film.html "$dir" --stills "$times" 2>&1 | grep -v "404 (Not Found)" || true
inputs=(); filters=""; i=0
for t in ${times//,/ }; do
  f=$(printf "%s/t%.2f.png" "$dir" "$t")
  inputs+=(-i "$f")
  filters+="[$i:v]scale=640:-1,drawtext=text='$t':x=8:y=8:fontsize=22:fontcolor=yellow:box=1:boxcolor=black@0.6[v$i];"
  i=$((i+1))
done
n=$i; rows=$(( (n + cols - 1) / cols ))
layout=""
for ((k=0; k<n; k++)); do layout+="$(( (k % cols) * 640 ))_$(( (k / cols) * 360 ))|"; done
for ((k=0; k<n; k++)); do filters+="[v$k]"; done
filters+="xstack=inputs=$n:layout=${layout%|}:fill=black"
[[ $n -eq 1 ]] && filters="[0:v]scale=640:-1"
ffmpeg -loglevel error -y "${inputs[@]}" -filter_complex "$filters" -frames:v 1 "out/qa/${name}.jpg"
echo "out/qa/${name}.jpg"
