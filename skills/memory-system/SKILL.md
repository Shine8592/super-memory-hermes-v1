---
name: memory-system
description: |
  Class-level memory architecture integrating semantic vector search (Faiss + sentence-transformers),
  dual memory engine (short-term ↔ long-term with importance scoring), and three-tier storage
  (hot/warm/cold with LRU eviction). Inspired by SuperMemo-Du architecture.
  Use when: designing or evaluating memory persistence, cross-session recall quality,
  semantic search, memory tiering, or knowledge retention strategies.
tags: [memory, semantic-search, vector-db, faiss, dual-memory, storage-tiers, persistence]
---

# Memory System — Semantic + Dual-Memory + Tiered Storage

## Overview

A production-grade memory architecture that combines three complementary systems:

| System | Function | Technology |
|--------|----------|-----------|
| **Semantic Vector Search** | Meaning-based retrieval (not keyword) | sentence-transformers + Faiss |
| **Dual Memory Engine** | STM ↔ LTM auto-transfer | JSON files + importance scoring |
| **Three-Tier Storage** | Hot/Warm/Cold auto-tiering | LRU cache + SSD + archive |

## 1. Semantic Vector Search

### Architecture

```
User Query → SentenceTransformer (all-MiniLM-L6-v2, 384-dim)
                ↓
         Faiss Flat Index
                ↓
       Top-K results by cosine similarity
                ↓
         Return {id, content, score, metadata}
```

### Key Components

| Component | File | Size | Notes |
|-----------|------|------|-------|
| Embedding model | `all-MiniLM-L6-v2` | ~80MB | 384-dim, fast CPU inference |
| Vector index | `semantic_index.faiss` | Varies | Faiss Flat (L2) or IVF |
| Metadata index | `semantic_metadata.json` | Varies | JSON array of {id, path, text, score} |

### When to Build/Update Index

| Trigger | Command |
|---------|---------|
| Fresh install | `python3 scripts/semantic_search.py build` |
| New memory files added | `cd ~/.hermes/memory && python3 ~/.hermes/scripts/semantic_search.py build` |
| Full rebuild (core + sessions) | `python3 ~/.hermes/scripts/build_full_index.py` |
| Scheduled rebuild (daily) | cron: `0 3 * * * python3 ~/.hermes/scripts/build_full_index.py` |
| Query | `python3 ~/.hermes/scripts/semantic_search.py search "what was that thing about..."` |

⚠️ `build_full_index.py` 会自动扫描 `~/.hermes/` 下的核心文件（SOUL.md, MEMORY.md, TOOLS.md, USER.md, IDENTITY.md）和最近30个会话文件，同时编入向量索引。

### Required Installation

```bash
pip install sentence-transformers faiss-cpu numpy
```

The model downloads on first run (~80MB). After that it caches locally.

## 2. Dual Memory Engine

### Architecture

```
      ┌─────────────────┐          ┌─────────────────┐
      │  Short-Term Mem  │ ◄──────►│  Long-Term Mem   │
      │  (STM)           │          │  (LTM)           │
      ├─────────────────┤          ├─────────────────┤
      │ 24h window      │          │ Permanent        │
      │ Raw conversation│          │ Distilled wisdom │
      │ JSON per item   │          │ MEMORY.md format │
      │ Max 1000 items  │          │ Structured by ## │
      └────────┬────────┘          └────────┬────────┘
               │                           │
               └──────────┬────────────────┘
                          │
              Importance Score ≥ 0.7
              → STM item promoted to LTM
              → Content summarized, filed under best ##
```

### STM Manager (ShortTermMemory)

```python
stm = ShortTermMemory(max_age_hours=24, max_items=1000)
stm.add("content string", metadata={"source": "chat", "topic": "memory"})
stm.query(["keyword1", "keyword2"])  # → ranked list
stm.get_all()  # → all non-expired items
```

- Items expire after `max_age_hours` (default: 24h)
- Excess items beyond `max_items` are LRU-evicted by timestamp
- Each item tracks: `id, content, timestamp, access_count, importance_score`
- Access count increments on read (favors frequently retrieved items)

### LTM Manager (LongTermMemory)

```python
ltm = LongTermMemory(ltm_file=Path("MEMORY.md"))
ltm.search("query string")  # keyword-matched sections
ltm.add_section("## New Topic", "content")
```

- Parses MEMORY.md by `## ` headers into sections
- Keyword-based search within each section
- Sections tracked: `id, title, content, last_accessed, access_count`

### STM → LTM Transfer (importance scoring)

```python
def calculate_importance(item):
    score = 0.0
    score += min(item.access_count / 10, 0.3)        # Frequency (max 0.3)
    score += min(1.0 - (age_hours / 24), 0.3)         # Recency (max 0.3)
    score += 0.2 if item.metadata.get("important") else 0  # Explicit flag
    score += 0.2 if len(item.content) > 100 else 0    # Substance heuristic
    return min(score, 1.0)
```

When `score >= 0.7`, the item is:
1. Summarized (first 200 chars + key metadata)
2. Appended to LTM under an appropriate `## ` section
3. Flagged in STM as "promoted" (not deleted until natural expiry)

## 3. Three-Tier Storage

### Tier Definitions

| Tier | Medium | Capacity | TTL | Latency | Eviction Policy |
|------|--------|----------|-----|---------|-----------------|
| 🔥 **Hot** | Python dict (LRU cache) | 1000 items | 7 days idle | <1ms | score = priority / (1 + age_hours) |
| 🟡 **Warm** | SSD filesystem (JSON) | Unlimited | 30 days | <10ms | mtime > 30d → Cold |
| 🧊 **Cold** | Archive (compressed) | Unlimited | Permanent | <1min | Never evicted |

### Hot Storage (LRUCache)

```python
cache = LRUCache(max_size=1000)
cache.put("key", value, priority=1.0)
value = cache.get("key")  # Updates access_time
cold = cache.get_cold_items(days=7)  # Idle > 7 days
```

Eviction score: `priority / (1 + age_hours)` — lowest score removed first.

### Warm → Cold Transition

Files in warm storage (`memory/stm/`) older than 30 days with zero access:
1. Compressed (gzip)
2. Moved to `memory/archive/YYYY-MM/`
3. Manifest updated in `memory/archive/manifest.json`

## Deployment (实际部署步骤)

### 依赖安装
```bash
pip install sentence-transformers faiss-cpu numpy
# 模型约80MB，首次运行自动下载
```

### 脚本目录结构
```
~/.hermes/
├── scripts/
│   ├── semantic_search.py        # 语义检索核心（构建+搜索+状态）
│   ├── dual_memory_engine.py     # 双记忆协同（STM + LTM）
│   ├── storage_tiers.py          # 三层存储实现
│   ├── build_full_index.py       # 全量索引构建（含历史会话）
│   ├── init_dual_memory.py       # 初始化STM目录+协调器
│   └── memory_maintain.py        # 定期维护（清理+转移）
├── memory/
│   ├── stm/                      # 短期记忆（JSON文件）
│   ├── archive/                  # 冷存储归档
│   ├── semantic_index.faiss      # Faiss向量索引
│   └── semantic_metadata.json    # 索引元数据
├── SOUL.md                       # 核心性格文件（用户提供）
├── MEMORY.md                     # 长期记忆文件（用户提供）
└── skills/                       # Hermes技能
```

### 初始化流程
```bash
# 1. 初始化双记忆引擎
python3 ~/.hermes/scripts/init_dual_memory.py
# 输出: ✅ 双记忆引擎初始化完成

# 2. 构建向量索引（从 ~/.hermes/*.md 和会话数据）
cd ~/.hermes/memory
python3 ~/.hermes/scripts/build_full_index.py
# 输出: ✅ INDEX BUILT SUCCESSFULLY! Total chunks: N

# 3. 测试搜索
python3 ~/.hermes/scripts/semantic_search.py search "测试查询"
```

### 路径规则
- 所有脚本使用 `Path.home() / ".hermes" / "memory"` 定位存储目录
- 核心记忆文件（SOUL.md, MEMORY.md 等）放在 `~/.hermes/` 根目录
- 即为用户提供, 部署脚本, 不包含用户个人数据

### 发布到GitHub（公开仓库，不含个人数据）
```bash
# 只发布 scripts/ + skills/ + install.sh + README
# 核心记忆文件（*.md）通过 .gitignore 排除
git clone <repo>
cp scripts/*.py repo/scripts/
cp -r skills/* repo/skills/
git add -A && git commit -m "initial release"
git push
```

## 4. Hermes Integration Patterns

### 自动语义检索（回答问题时触发）
每次用户询问涉及历史记忆、配置、偏好、项目进度的问题时，**先执行语义检索再回答**：

```bash
cd ~/.hermes/memory && python3 ~/.hermes/scripts/semantic_search.py search "用户的问题" 2>&1 | tail -30
```

检索结果的 Top 3-5 条必须直接引用到回答中，标注来源（如"来自 SOUL.md"、"来自5月14日会话"）。

### Cron 定时任务（Hermes cronjob 工具）

| 任务 | 调度 | 命令 |
|------|------|------|
| 每日GitHub备份 | `0 2 * * *` | `cd dudu-backup && git add -A && git commit && git push` |
| 向量索引重建 | `0 3 * * *` | `python3 ~/.hermes/scripts/build_full_index.py` |
| 记忆维护 | `0 */6 * * *` | `python3 ~/.hermes/scripts/memory_maintain.py` |

使用 Hermes cronjob tool 创建：
```
cronjob action=create name="任务名" schedule="0 2 * * *" prompt="执行的命令和步骤"
```

### Loading Memory at Session Start

```python
# On each session:
# 1. Search semantic index for recent topics
semantic_search("recent topics")  # → top 5 memories

# 2. Check LTM for relevant background
ltm.search("[current context keywords]")  # → matching sections

# 3. Review today's STM entries
stm.query(["today"])  # → recent context
```

### Saving Memory During Session

```python
# Significant event → save to STM
stm.add(event_description, metadata={"source": "user", "topic": "project-X"})

# End of session → auto-transfer if score ≥ 0.7
for item in stm.get_all():
    score = calculate_importance(item)
    if score >= 0.7:
        ltm.add_section(f"## {item.metadata.get('topic', 'General')}", item.content)
```

## 5. Backup & Recovery

| Mechanism | Frequency | Target |
|-----------|-----------|--------|
| Git push (full repo) | Daily | GitHub private repo |
| Email backup (core files) | On upgrade | SMTP → backup email |
| Index rebuild | Daily @ 08:00, 20:00 | Faiss index refresh |
| Archive rotation | Monthly | Warm → Cold compression |

## References

- `references/tavily-setup.md` — Tavily API config (for search-based memory retrieval)
- `references/qq-mail-setup.md` — Email backup setup (for memory email archiving)
- `references/deployment-guide.md` — 完整部署步骤、Cron配置、维护命令、故障排查

## Related Skills

- **china-briefing** — Uses semantic search for briefing generation
- **himalaya** — Email backup transport layer