#!/bin/bash
# 新建一个宣传片项目骨架：目录、脚本、模板、依赖清单。
#   bash <skill>/scripts/init_project.sh <项目目录> [--install]
# --install：顺便建 .venv 并安装 Python / Node 依赖（需要网络）。
set -euo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
DST=${1:?usage: init_project.sh <dir> [--install]}
mkdir -p "$DST"/{tools,audio/vo,audio/vo_v,scenes/clips,assets/footage,assets/music,assets/gen,out}
cd "$DST"

cp -n "$SKILL"/scripts/{render.mjs,render_par.sh,rerender_part.sh,deliver.sh} .
chmod +x render_par.sh rerender_part.sh deliver.sh
cp -n "$SKILL"/scripts/sfxlib.py audio/
for f in "$SKILL"/scripts/*.py; do
  [[ $(basename "$f") == sfxlib.py ]] || cp -n "$f" tools/
done

# 参考实现当模板：改完内容再用，别原样渲染
cp -n "$SKILL"/templates/{timeline_h.py,timeline_v.py} tools/
cp -n "$SKILL"/templates/{mix_film.py,mix_film_v.py,vo_lines.json,vo_lines_v.json} audio/
cp -n "$SKILL"/templates/film.html scenes/
cp -n "$SKILL"/templates/clips_h.json .
cp -n "$SKILL"/templates/CREDITS.md assets/CREDITS.template.md

cp -n "$SKILL"/templates/project/requirements.txt .
cp -n "$SKILL"/templates/project/package.json .
[[ -f .env ]] || cp "$SKILL"/templates/project/env.example .env.example
[[ -f .gitignore ]] || cp "$SKILL"/templates/project/gitignore .gitignore

if [[ ${2:-} == --install ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
  npm install --silent
fi

cat <<EOF
项目骨架已建好：$DST
下一步：
  1. cp .env.example .env 并填写密钥（不要回显）
  2. 没加 --install 的话：python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && npm install
  3. 确认本机有 ffmpeg 和 Google Chrome（装在非默认位置时 export CHROME_PATH=...）
  4. 按 SKILL.md 的流程，从需求确认开始
EOF
