# 程序员英语背单词

闪卡式背单词 Web App，浏览器里跑 SQLite，无后端。

## 跑起来

```bash
# 本地预览
python3 serve.py        # 自动开浏览器

# 部署到 GitHub Pages
./deploy.sh             # 见 DEPLOY.md
```

## 功能

- 9 个词集快速切换：程序员高频 / CET4 / CET6 / 考研 / TOEFL / IELTS / GRE / 牛津 3000 / 柯林斯 5★
- 词频范围二次筛选（如「当代词频前 5000 的 CET6 词」）
- 闪卡翻面：正面 = 单词 + 音标 + 标签，反面 = 中文释义 + 程序员场景注释 + 时态变形
- 三态评分（不熟悉 / 跳过 / 已掌握），进度存 `localStorage`，自动跳过已掌握的词
- 键盘：空格翻面 · J 不熟悉 · K 跳过 · L 已掌握 · S 朗读
- Web Speech API 朗读单词，可选「翻卡自动朗读」
- IndexedDB 缓存词库，首次下载后秒开
- 暗色 UI，自适应手机

## 数据来源

| 来源 | 用途 | 许可证 |
| --- | --- | --- |
| [skywind3000/ECDICT](https://github.com/skywind3000/ECDICT) | 英汉词条主体（音标、中英释义、词性、词频、考试标签、时态变化） | MIT |
| [Wei-Xia/most-frequent-technology-english-words](https://github.com/Wei-Xia/most-frequent-technology-english-words) | 260 个程序员高频词的中文含义与场景注释 | MIT |

## 词库内容

部署用的 `programmer_english.db`（瘦身版，~13MB）保留有学习价值的词：

```
总词条       59,181        程序员高频     260
有翻译       59,181        牛津 3000     3,461
有音标       47,823        柯林斯 5★      630

考试覆盖
  CET4       3,849    考研      4,801
  CET6       5,407    TOEFL     6,974
  IELTS      5,040    GRE       7,504
```

## 文件

| 文件 | 说明 |
| --- | --- |
| `index.html` | 单文件背单词 Web App（sql.js + 内联 CSS/JS） |
| `programmer_english.db` | 13MB 的瘦身 SQLite，部署用 |
| `serve.py` | 一键本地启动 HTTP 服务并打开浏览器 |
| `build_db.py` | 从 `ecdict.csv` 重建 770K 词全量 db |
| `slim_db.py` | 把全量 db 瘦身到 GitHub Pages 可托管的体积 |
| `deploy.sh` | 一键部署到 GitHub Pages |
| `.github/workflows/deploy.yml` | Pages 自动构建工作流 |
| `DEPLOY.md` | 部署详细步骤 |

## 完整重建

```bash
python3 build_db.py    # 从 ecdict.csv 生成 770K 词全量 db (~153MB, 不可部署)
python3 slim_db.py     # 瘦身到 13MB, 覆盖原 db
./deploy.sh            # 推到 GitHub Pages
```

## 表结构

`words` 主表（`word`, `phonetic`, `translation`, `pos`, `collins`, `oxford`, `tag`, `bnc`, `frq`, `exchange`, `is_programmer`, `prog_meaning`, `prog_note`, `prog_category`）

`word_tags` 标签透视表（`word_id`, `tag`）

`meta` 元数据

索引：`sw / tag / collins / oxford / bnc / frq / is_programmer / word_tags.tag`

## 示例查询

```sql
-- 按词查
SELECT word, phonetic, translation FROM words WHERE word = 'deploy';

-- 模糊匹配 (long time / long-time / longtime)
SELECT word FROM words WHERE sw = 'longtime';

-- 程序员高频词
SELECT word, prog_meaning, prog_note FROM words WHERE is_programmer = 1 ORDER BY word;

-- CET6 按词频排
SELECT w.word, w.translation, w.frq
FROM words w JOIN word_tags t ON t.word_id = w.id
WHERE t.tag = 'cet6' ORDER BY w.frq LIMIT 100;
```
