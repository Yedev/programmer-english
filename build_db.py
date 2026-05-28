#!/usr/bin/env python3
"""
程序员英语词典 SQLite 构建脚本

数据源:
  1. ECDICT (skywind3000) - 76万英汉词条主词典, MIT
     https://github.com/skywind3000/ECDICT
  2. Wei-Xia/most-frequent-technology-english-words - 260个程序员高频词标注
     https://github.com/Wei-Xia/most-frequent-technology-english-words

最终 SQLite 表结构:
  CREATE TABLE words (
      id              INTEGER PRIMARY KEY,
      word            TEXT NOT NULL UNIQUE COLLATE NOCASE, -- 单词
      sw              TEXT,        -- strip-word, 模糊匹配键
      phonetic        TEXT,        -- 音标 (英)
      definition      TEXT,        -- 英文释义
      translation     TEXT,        -- 中文释义
      pos             TEXT,        -- 词性占比 (e.g. n:46/v:54)
      collins         INTEGER,     -- 柯林斯星级 1-5
      oxford          INTEGER,     -- 是否牛津 3000 核心词 0/1
      tag             TEXT,        -- 考试标签: cet4 cet6 ky toefl ielts gre zk gk
      bnc             INTEGER,     -- BNC 词频排名
      frq             INTEGER,     -- 当代语料库词频排名
      exchange        TEXT,        -- 时态/复数变换
      is_programmer   INTEGER DEFAULT 0,  -- 是否程序员高频词 0/1
      prog_meaning    TEXT,        -- 程序员场景下的中文含义
      prog_note       TEXT,        -- 程序员场景下的用法注释
      prog_category   TEXT         -- 程序员场景词性分类
  );
  CREATE INDEX idx_sw ON words(sw);
  CREATE INDEX idx_tag ON words(tag);
  CREATE INDEX idx_collins ON words(collins);
  CREATE INDEX idx_bnc ON words(bnc);
  CREATE INDEX idx_frq ON words(frq);
  CREATE INDEX idx_programmer ON words(is_programmer);

  -- 标签透视表，便于按考试分类筛词
  CREATE TABLE word_tags (
      word_id INTEGER,
      tag     TEXT,
      PRIMARY KEY(word_id, tag)
  );
  CREATE INDEX idx_word_tags_tag ON word_tags(tag);
"""

import csv
import os
import re
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).parent
ECDICT_CSV = HERE / "ecdict.csv"
WEI_XIA_POSTS = HERE / "wei-xia" / "_posts"
# 在普通文件系统(/tmp)里构建, 完成后再复制到 outputs (bindfs 对 sqlite 的 VACUUM 等操作支持不佳)
BUILD_PATH = Path("/tmp/programmer_english.db")
DB_PATH = HERE / "programmer_english.db"

# CSV 字段较长时 Python csv 模块会报错，调大限制
csv.field_size_limit(sys.maxsize)


def strip_word(word: str) -> str:
    """ECDICT 模糊匹配键: 移除所有非字母数字字符并转小写"""
    return "".join(c for c in word if c.isalnum()).lower()


def to_int(value: str):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        try:
            return int(float(value))
        except ValueError:
            return None


def parse_wei_xia():
    """解析 Wei-Xia _posts/*.md 的 frontmatter, 返回 {word: {meaning, note, category}}"""
    if not WEI_XIA_POSTS.exists():
        print(f"[warn] {WEI_XIA_POSTS} 不存在, 跳过程序员词标注")
        return {}
    fm_re = re.compile(r"^([a-zA-Z_]+):\s*(.*)$")
    out = {}
    for md in sorted(WEI_XIA_POSTS.glob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        # 取头部 YAML front matter (--- ... ---)
        parts = text.split("---")
        if len(parts) < 3:
            continue
        front = parts[1].strip()
        data = {}
        for line in front.splitlines():
            m = fm_re.match(line.strip())
            if m:
                data[m.group(1).lower()] = m.group(2).strip()
        word = data.get("word", "").strip()
        if not word:
            # 从文件名 fallback
            stem = md.stem
            # 文件名形如 2020-01-01-accordion
            word = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)
        word = word.strip().strip('"').strip("'")
        if not word:
            continue
        out[word.lower()] = {
            "meaning": data.get("meaning", "").strip().strip('"').strip("'"),
            "note": data.get("note", "").strip().strip('"').strip("'"),
            "category": data.get("category", "").strip().strip('"').strip("'"),
        }
    return out


def main():
    if not ECDICT_CSV.exists():
        sys.exit(f"missing {ECDICT_CSV}; 请先下载 ECDICT")

    if BUILD_PATH.exists():
        BUILD_PATH.unlink()
    if DB_PATH.exists():
        DB_PATH.unlink()

    prog_words = parse_wei_xia()
    print(f"程序员高频词: {len(prog_words)} 个")

    conn = sqlite3.connect(BUILD_PATH)
    conn.execute("PRAGMA journal_mode = OFF")
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA temp_store = MEMORY")

    conn.executescript("""
        CREATE TABLE words (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            word          TEXT NOT NULL UNIQUE COLLATE NOCASE,
            sw            TEXT,
            phonetic      TEXT,
            definition    TEXT,
            translation   TEXT,
            pos           TEXT,
            collins       INTEGER,
            oxford        INTEGER,
            tag           TEXT,
            bnc           INTEGER,
            frq           INTEGER,
            exchange      TEXT,
            is_programmer INTEGER DEFAULT 0,
            prog_meaning  TEXT,
            prog_note     TEXT,
            prog_category TEXT
        );
        CREATE TABLE word_tags (
            word_id INTEGER NOT NULL,
            tag     TEXT NOT NULL,
            PRIMARY KEY(word_id, tag)
        );
        CREATE TABLE meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
    """)

    with open(ECDICT_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        BATCH = 5000
        total = 0
        for r in reader:
            w = (r.get("word") or "").strip()
            if not w:
                continue
            prog = prog_words.get(w.lower())
            rows.append((
                w,
                strip_word(w),
                r.get("phonetic") or None,
                r.get("definition") or None,
                r.get("translation") or None,
                r.get("pos") or None,
                to_int(r.get("collins")),
                to_int(r.get("oxford")),
                (r.get("tag") or "").strip() or None,
                to_int(r.get("bnc")),
                to_int(r.get("frq")),
                r.get("exchange") or None,
                1 if prog else 0,
                prog["meaning"] if prog else None,
                prog["note"] if prog else None,
                prog["category"] if prog else None,
            ))
            if len(rows) >= BATCH:
                conn.executemany(
                    "INSERT OR IGNORE INTO words(word,sw,phonetic,definition,translation,pos,collins,oxford,tag,bnc,frq,exchange,is_programmer,prog_meaning,prog_note,prog_category) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    rows,
                )
                total += len(rows)
                rows.clear()
                if total % 100000 == 0:
                    print(f"  已写入 {total} 条…")
        if rows:
            conn.executemany(
                "INSERT OR IGNORE INTO words(word,sw,phonetic,definition,translation,pos,collins,oxford,tag,bnc,frq,exchange,is_programmer,prog_meaning,prog_note,prog_category) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                rows,
            )
            total += len(rows)
        print(f"  共写入 {total} 条 ECDICT 词条")

    # 补录 Wei-Xia 里 ECDICT 没有的程序员词 (e.g. 'angle-brackets')
    missing = 0
    for w, info in prog_words.items():
        cur = conn.execute("SELECT id FROM words WHERE word = ? COLLATE NOCASE", (w,))
        if cur.fetchone() is None:
            conn.execute(
                "INSERT INTO words(word,sw,translation,is_programmer,prog_meaning,prog_note,prog_category) "
                "VALUES (?,?,?,?,?,?,?)",
                (w, strip_word(w), info["meaning"] or None, 1, info["meaning"] or None,
                 info["note"] or None, info["category"] or None),
            )
            missing += 1
    print(f"  补录 ECDICT 缺失的程序员词 {missing} 条")

    # 拆 tag 字段填充 word_tags 表
    cur = conn.execute("SELECT id, tag FROM words WHERE tag IS NOT NULL AND tag != ''")
    tag_rows = []
    for wid, tag in cur:
        for t in re.split(r"\s+", tag.strip()):
            if t:
                tag_rows.append((wid, t.lower()))
    conn.executemany("INSERT OR IGNORE INTO word_tags(word_id, tag) VALUES (?,?)", tag_rows)
    print(f"  word_tags 关联 {len(tag_rows)} 条")

    # 索引
    print("建立索引…")
    conn.executescript("""
        CREATE INDEX idx_sw            ON words(sw);
        CREATE INDEX idx_tag           ON words(tag);
        CREATE INDEX idx_collins       ON words(collins);
        CREATE INDEX idx_oxford        ON words(oxford);
        CREATE INDEX idx_bnc           ON words(bnc);
        CREATE INDEX idx_frq           ON words(frq);
        CREATE INDEX idx_programmer    ON words(is_programmer);
        CREATE INDEX idx_word_tags_tag ON word_tags(tag);
    """)

    # 元信息
    conn.executemany("INSERT INTO meta(key,value) VALUES (?,?)", [
        ("name", "程序员英语词典 / Programmer English Dictionary"),
        ("source_primary", "skywind3000/ECDICT (MIT)"),
        ("source_secondary", "Wei-Xia/most-frequent-technology-english-words"),
        ("schema_version", "1"),
        ("build_date", "2026-05-27"),
    ])

    conn.commit()
    # 收尾优化
    conn.execute("ANALYZE")
    conn.commit()
    conn.close()

    # 单独的 VACUUM 连接, 否则 journal_mode=OFF 下可能拒绝
    v = sqlite3.connect(BUILD_PATH)
    v.execute("VACUUM")
    v.close()

    # 复制到 outputs 目录 (bindfs)
    import shutil
    shutil.copy2(BUILD_PATH, DB_PATH)

    size_mb = DB_PATH.stat().st_size / 1024 / 1024
    print(f"\n生成完毕: {DB_PATH}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
