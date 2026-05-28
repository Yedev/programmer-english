# 部署到 GitHub Pages

最终架构非常简单：HTML + 13MB SQLite 一起进 GitHub Pages，浏览器在客户端跑 sql.js 查询。无后端、无外部依赖。

## 一次性准备

```bash
brew install gh        # macOS, 没装的话; 或见 https://cli.github.com
gh auth login          # 浏览器一次 OAuth
```

## 一键部署

```bash
cd <outputs 目录>
./deploy.sh
```

跑完会打印两个 URL：
- 网站：`https://yechanghong.github.io/programmer-english/`
- Actions 进度：`https://github.com/yechanghong/programmer-english/actions`

GitHub Actions 首次构建 1-3 分钟，等绿勾后访问网址。

## 脚本做了什么

| 步骤 | 内容 |
| --- | --- |
| 1 | 检查 `gh` / `git` 已装且 `gh auth status` 通过；db 文件存在且 ≤ 100MB |
| 2 | `git init` + 初次 commit (`.gitignore` 已把 65MB ecdict.csv 排除) |
| 3 | `gh repo create yechanghong/programmer-english --public --push` 建仓 + push |
| 4 | 调 GitHub API 启用 Pages 的 "GitHub Actions" 模式 |
| 5 | 仓库里的 `.github/workflows/deploy.yml` 接管，把根目录所有文件作为 Pages 站点发布 |

## 为什么不是 153MB 的完整 db

- GitHub 单文件硬上限 100MB（push 时直接被拒）
- GitHub Releases 能存 2GB，但下载链不带 CORS 头，浏览器没法 fetch
- 所以走 `slim_db.py` 瘦身策略：保留所有有学习价值的词、丢掉冷僻词条 + 整列 `definition`(英文释义)
- 结果：59,181 词条 / 13MB，覆盖 100% 程序员高频词 + 100% 所有考试大纲 + 牛津 3000 + 柯林斯星级 + BNC 和当代词频前 5 万

如果之后想要回到完整 770K 词的版本：`python3 build_db.py`（但这版本无法部署到 GitHub Pages）

## 后续更新

```bash
./deploy.sh
```

- 改了 HTML / CSS / JS：自动 commit + push，GitHub Actions 几十秒重新部署
- 重建了 db：脚本会一起推上去
- 想让访问者重新下载 db：把 `index.html` 里的 `CACHE_KEY` 从 `v2-slim` 改成 `v3-slim`

## 手动备选

如果不想用 `gh` CLI：

```bash
# 1. 浏览器去 https://github.com/new 建 programmer-english 仓库
# 2. 本机
git init -b main
git add .
git commit -m "Init"
git remote add origin https://github.com/yechanghong/programmer-english.git
git push -u origin main
# 3. 仓库 Settings → Pages → Source 选 "GitHub Actions"
```

## 常见问题

**Q: Push 报 `file too large`？**
A: 检查 `programmer_english.db` 是否超过 100MB。如果之前跑了 `python3 build_db.py`（生成 153MB 全量版），再跑一次 `python3 slim_db.py` 瘦身到 13MB。

**Q: Pages Action 红叉？**
A: 看 `https://github.com/yechanghong/programmer-english/actions` 日志。最常见原因：Settings → Pages 没切到 "GitHub Actions" 模式。手动切一下重新触发 workflow。

**Q: 网页打开后报 "Failed to fetch"？**
A: 确认 `programmer_english.db` 已经在仓库根目录里（`git ls-files | grep db`）。如果没有，是因为 `.gitignore` 误把它排除了。

**Q: 想用别的托管 (Cloudflare Pages / Netlify / Vercel)？**
A: 这些都支持 git 仓库直连，把这个 repo 连过去即可，HTML 用相对路径读 db 也都能跑。

**Q: 国内访问速度？**
A: GitHub Pages 国内偶尔抽风，可以考虑 Cloudflare Pages 或 Vercel 作为镜像，repo 不变。
