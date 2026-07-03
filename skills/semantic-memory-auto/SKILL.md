---
name: semantic-memory-auto
description: |
  自动语义记忆检索。当用户问到涉及历史决策、配置偏好、项目进度等问题时，
  自动调用 semantic_search.py 搜索向量索引，将结果注入回答上下文。
---

# Semantic Memory Auto-Retrieval

## 使用规则

当用户的问题涉及以下内容时，**必须先执行语义检索**再回答：

1. **历史决策** — "为什么选择XX"、"我们之前讨论过…"
2. **个人配置** — "我的邮箱是"、"API配置"、"密码"
3. **项目进度** — "小说写到哪了"、"太初道果"
4. **用户偏好** — "我喜欢什么"、"主人在哪"
5. **已安装技能** — "我们有什么技能"、"简报怎么用"
6. **技术方案** — "之前怎么解决的"、"上次用什么方案"

## 检索命令

```bash
cd ~/.hermes/memory && python3 ~/.hermes/scripts/semantic_search.py search "用户的具体问题" 2>&1 | grep -E 'Rank|Relevance|Source|📄|📚' | head -10
```

## 索引维护

| 动作 | 命令 | 时机 |
|------|------|------|
| 状态检查 | `python3 ~/.hermes/scripts/semantic_search.py status` | 怀疑索引异常时 |
| 全量重建 | `cd ~/.hermes/memory && python3 ~/.hermes/scripts/build_full_index.py` | 手动触发 |
| 自动重建 | cron `0 3 * * *` 自动执行 | 每日凌晨3点 |

⚠️ **状态检查预期输出：** `✅ Index loaded: N chunks`（N > 0）

⚠️ 如果 Faiss 索引不存在或为空：`cd ~/.hermes/memory && python3 ~/.hermes/scripts/build_full_index.py`

## 索引数据源（2026-07-03 修复后）

| 来源 | 读取方式 | 范围 |
|------|---------|------|
| 核心文件 `SOUL.md`, `MEMORY.md`, `TOOLS.md`, `USER.md`, `IDENTITY.md` | 按 `## ` 分段 | 全部 |
| 当前会话 **`state.db`**（SQLite `messages` 表） | `extract_from_statedb()` | 最近 50 会话 |
| 旧文件系统 `sessions/*.json` / `*.jsonl` | 向后兼容读取 | 最近 30 文件 |

**修复前：** 只读文件系统 `.jsonl`/`.json`，但 Hermes 最新会话存在 SQLite 中，导致5周会话未被索引。修复后 `build_full_index.py` 加 `extract_from_statedb()` 直接从 `state.db` 读取。

**上限：** 500 chunks（按时间戳保留最新），重建耗时约 20s。

## 来源前缀解析

| 前缀 | 含义 | 新鲜度 |
|------|------|--------|
| `core/` | 核心记忆文件（SOUL.md等），稳定知识 | 基线 |
| `session/` | 旧文件系统会话（可能已过期） | 可能陈旧 |
| `statedb/` | 当前会话（来自 state.db） | **最新鲜** |

新鲜度排序：`statedb/` > `session/` > `core/`

## 结果使用

检索结果的 Top 3-5 条必须直接引用到回答中，标注来源前缀，确保有据可查。

## 相关性评分指南

| 评分 | 含义 | 应对 |
|------|------|------|
| 0.5+ | 强相关 | 直接引用到回答 |
| 0.3-0.5 | 中等相关 | 选择性引用 |
| <0.3 | 弱相关 | 可选引用或不引用 |

all-MiniLM-L6-v2 384维余弦相似度，0.3+ 对中文有意义。

**2026-07-03 更新后质量：**
- 索引从 83 → 500 chunks
- 覆盖范围从 5月 → 当前
- 近期话题搜索得分通常 0.5-0.7（先前 0.3-0.5）
- 核心文件稳定知识得分为 0.4-0.6

## 不触发条件

- 简单的聊天问候（"你好"、"在吗"）
- 即时命令（"发邮件"、"生成简报"）— 除非需要查配置
- 用户明确要求不用查
