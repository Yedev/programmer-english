#!/usr/bin/env bash
# 一键部署到 GitHub Pages
#
# 前置 (一次):
#   brew install gh        # macOS, 或见 https://cli.github.com
#   gh auth login          # 浏览器走 OAuth, 一次完事
#
# 用法:
#   ./deploy.sh

set -euo pipefail

GH_USER="yechanghong"
GH_REPO="programmer-english"
DB_FILE="programmer_english.db"
DB_MAX_MB=100   # GitHub 单文件硬上限

cd "$(dirname "$0")"

bold() { printf "\n\033[1m%s\033[0m\n" "$*"; }
ok()   { printf "\033[32m✓\033[0m %s\n" "$*"; }
warn() { printf "\033[33m!\033[0m %s\n" "$*"; }
die()  { printf "\033[31m✗\033[0m %s\n" "$*" >&2; exit 1; }

bold "→ [1/4] 检查依赖和文件"
command -v gh  >/dev/null || die "缺少 GitHub CLI, 装: brew install gh"
command -v git >/dev/null || die "缺少 git"
gh auth status >/dev/null 2>&1 || die "未登录 GitHub CLI, 先跑: gh auth login"
[[ -f "$DB_FILE" ]] || die "找不到 $DB_FILE, 先跑: python3 build_db.py && python3 slim_db.py"

DB_BYTES=$(stat -f%z "$DB_FILE" 2>/dev/null || stat -c%s "$DB_FILE")
DB_MB=$(( DB_BYTES / 1024 / 1024 ))
if (( DB_MB >= DB_MAX_MB )); then
  die "$DB_FILE 体积 ${DB_MB}MB, 超过 GitHub 单文件 ${DB_MAX_MB}MB 上限. 先跑: python3 slim_db.py"
fi
ok "依赖齐全, db = ${DB_MB}MB (在 ${DB_MAX_MB}MB 上限内)"

bold "→ [2/4] git 初始化 + commit"
if [[ ! -d .git ]]; then
  git init -q -b main
  ok "git init"
fi
git config user.email >/dev/null 2>&1 || git config user.email "$GH_USER@users.noreply.github.com"
git config user.name  >/dev/null 2>&1 || git config user.name  "$GH_USER"

git add -A
if ! git diff --cached --quiet; then
  git commit -q -m "Deploy programmer english flashcards"
  ok "commit 完成"
else
  ok "无新改动"
fi

bold "→ [3/4] 创建/确认仓库 $GH_USER/$GH_REPO 并 push"
if gh repo view "$GH_USER/$GH_REPO" >/dev/null 2>&1; then
  git remote get-url origin >/dev/null 2>&1 || \
    git remote add origin "https://github.com/$GH_USER/$GH_REPO.git"
  git branch -M main >/dev/null 2>&1 || true
  git push -u origin main
  ok "push 到现有仓库"
else
  gh repo create "$GH_USER/$GH_REPO" --public \
    --description "程序员英语背单词 · 闪卡 · ECDICT + 程序员高频词" \
    --source=. --remote=origin --push
  ok "仓库已创建并 push"
fi

bold "→ [4/4] 启用 GitHub Pages (Actions 模式)"
gh api -X POST "repos/$GH_USER/$GH_REPO/pages" \
  -F "build_type=workflow" 2>/dev/null && ok "已开启 Pages" || {
  gh api -X PUT "repos/$GH_USER/$GH_REPO/pages" \
    -F "build_type=workflow" >/dev/null 2>&1 && ok "Pages 已是 Actions 模式" || \
    warn "无法自动开启 Pages, 请手动到 https://github.com/$GH_USER/$GH_REPO/settings/pages 选 'GitHub Actions'"
}

bold "→ 完成"
cat <<EOF

  网站:    https://$GH_USER.github.io/$GH_REPO/
  Actions: https://github.com/$GH_USER/$GH_REPO/actions

  ( 首次部署等 GitHub Actions 跑完, 约 1-3 分钟, 等绿勾 ✓ 后访问网址 )

EOF
