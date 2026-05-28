#!/usr/bin/env python3
"""把 programmer_english.db 瘦身到 GitHub Pages 单文件上限 (100MB) 以下。

策略:
  保留: 程序员高频词 / 各考试大纲词 (CET/考研/TOEFL/IELTS/GRE/中考/高考)
        / 牛津 3000 / 柯林斯星级词 / 当代词频前 5万 / BNC 前 5万
  丢弃: 长尾冷僻词条 (无任何标签、无星级、词频也很冷)
        + 整列 definition (英文释义) 节省 ~30MB
  结果: 大约 5-7 万词条 + 索引, 估计 30-50MB

用法:
  python3 slim_db.py         # 默认: 输入和输出都是 programmer_english.db (原地瘦身)
  python3 slim_db.py --keep  # 输出到 programmer_english.slim.db, 保留原 db
"""
import shutil
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "programmer_english.db"
KEEP = "--keep" in sys.argv
DST_FINAL = HERE / ("programmer_english.slim.db" if KEEP else "programmer_english.db")
TMP = Path("/tmp/programmer_english.slim.db")

if not SRC.exists():
    sys.exit(f"找不到 {SRC}; 先跑 build_db.py")

if TMP.exists():
    TMP.unlink()

print(f"读取: {SRC} ({SRC.stat().st_size/1024/1024:.1f} MB)")

con = sqlite3.connect(TMP)
con.execute("PRAGMA journal_mode = OFF")
con.execute("PRAGMA synchronous = OFF")
con.execute("PRAGMA temp_store = MEMORY")

# 新 schema: 没有 definition 列
con.executescript("""
    CREATE TABLE words (
        id            INTEGER PRIMARY KEY,
        word          TEXT NOT NULL UNIQUE COLLATE NOCASE,
        sw            TEXT,
        phonetic      TEXT,
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

con.execute("ATTACH DATABASE ? AS src", (str(SRC),))

# 学习用筛选: 任意一个条件就保留
print("筛选有价值的词条…")
con.execute("""
    INSERT INTO words(id, word, sw, phonetic, translation, pos, collins, oxford, tag, bnc, frq, exchange, is_programmer, prog_meaning, prog_note, prog_category)
    SELECT id, word, sw, phonetic, translation, pos, collins, oxford, tag, bnc, frq, exchange, is_programmer, prog_meaning, prog_note, prog_category
    FROM src.words
    WHERE translation IS NOT NULL AND translation != ''
      AND (
            is_programmer = 1
         OR (tag IS NOT NULL AND tag != '')
         OR oxford = 1
         OR (collins IS NOT NULL AND collins >= 1)
         OR (frq IS NOT NULL AND frq > 0 AND frq <= 50000)
         OR (bnc IS NOT NULL AND bnc > 0 AND bnc <= 50000)
      )
""")
kept = con.execute("SELECT COUNT(*) FROM words").fetchone()[0]
print(f"  保留词条: {kept}")

# word_tags 透视
con.execute("""
    INSERT INTO word_tags(word_id, tag)
    SELECT word_id, tag FROM src.word_tags
    WHERE word_id IN (SELECT id FROM words)
""")
tags = con.execute("SELECT COUNT(*) FROM word_tags").fetchone()[0]
print(f"  保留 word_tags: {tags}")

# meta
con.execute("INSERT INTO meta SELECT * FROM src.meta")
con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('variant','slim')")
con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('schema_version','2')")
con.execute("DELETE FROM meta WHERE key='source_secondary' AND value LIKE '%Wei-Xia%'")
con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('source_secondary','Wei-Xia/most-frequent-technology-english-words')")

# 索引
print("建立索引…")
con.executescript("""
    CREATE INDEX idx_sw            ON words(sw);
    CREATE INDEX idx_tag           ON words(tag);
    CREATE INDEX idx_collins       ON words(collins);
    CREATE INDEX idx_oxford        ON words(oxford);
    CREATE INDEX idx_bnc           ON words(bnc);
    CREATE INDEX idx_frq           ON words(frq);
    CREATE INDEX idx_programmer    ON words(is_programmer);
    CREATE INDEX idx_word_tags_tag ON word_tags(tag);
""")

con.commit()
con.execute("DETACH src")
con.execute("ANALYZE")
con.commit()
con.close()

# VACUUM 收紧
v = sqlite3.connect(TMP)
v.execute("VACUUM")
v.close()

# 复制回 outputs
shutil.copy2(TMP, DST_FINAL)
TMP.unlink()

mb = DST_FINAL.stat().st_size / 1024 / 1024
print(f"\n输出: {DST_FINAL}  ({mb:.1f} MB)")
if mb > 100:
    print("⚠ 超过 GitHub Pages 单文件 100MB 上限, 需要再砍")
elif mb > 50:
    print("✓ 在 GitHub Pages 上限内, 但较大, 移动端首次下载会久")
else:
    print("✓ 体积友好")
