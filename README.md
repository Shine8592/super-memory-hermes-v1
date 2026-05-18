# Super‑Memory‑Hermes‑V1 (Iterated)

## What is new in this iteration?

- **custom_scripts/** – a set of helper scripts that implement:
  - `post_process_log.py` – automatically persist each assistant turn into the SQLite `logs` table.
  - `generate_mermaid.py` – converts short‑term STM JSON logs into a compact Mermaid graph for LLM context.
  - `upgrade_memory.py` – promotes important logs to `MEMORY.md` with a Markdown‑style promotion summary.
  - `backup_sqlite.sh` – creates a SQL dump of the memory database.
  - `backup_and_sync.sh` – archives the dump, emails it via Himalaya (to `yaner_zf@126.com`) and pushes the archive to a backup repository. **No secrets are stored in the repo**; the GitHub token must be supplied at runtime (e.g. via `GIT_ASKPASS`).
- **skills/memory-system/** – the full memory‑system Skill (SKILL.md and references) is now part of the repo for easy loading with `skill_view(name="memory-system")`.
- **.gitignore** – explicitly excludes all private data files.

---
# 🧠 嘟嘟超级记忆系统 - Hermes 版本 V1

> 基于 SuperMemo-Du 架构的语义向量记忆系统，专门为 Hermes Agent 设计。
> 让 AI 助手拥有"真正理解语义"的长期记忆能力。

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🔍 **语义向量检索** | 基于 `sentence-transformers`（all-MiniLM-L6-v2）+ `Faiss` 384维向量索引 |
| 🔄 **双记忆协同** | 短期记忆（STM 24h窗口）→ 长期记忆（LTM 永久）自动转移 |
| 🗄️ **三层存储** | 热存储（内存LRU）/ 温存储（SSD）/ 冷存储（归档） |
| ⏰ **自动维护** | 6小时一次记忆清理+转移，每日自动重建向量索引 |
| 🔌 **Hermes 原生集成** | 通过 SKILL.md 实现自动语义检索触发 |
| 🔐 **隐私安全** | 核心记忆与系统代码分离，用户数据不会被发布 |

## 📂 项目结构

```
super-memory-hermes-v1/
├── README.md               # 本文件
├── install.sh              # 一键安装脚本
├── requirements.txt        # Python依赖
├── config/
│    └── example.yaml       # 配置文件模板
├── scripts/
│    ├── semantic_search.py      # 语义向量检索核心
│    ├── dual_memory_engine.py   # 双记忆协同引擎
│    ├── storage_tiers.py        # 三层存储实现
│    ├── build_full_index.py     # 全量索引构建
│    ├── auto_index_updater.py   # 自动索引更新
│    ├── init_dual_memory.py     # 双记忆引擎初始化
│    └── memory_maintain.py      # 记忆自动维护
├── skills/
│    ├── memory-system/          # Hermes 记忆系统技能
│    └── semantic-memory-auto/   # 自动语义检索技能
└── templates/
     └── memory_coordinator.json.template  # 协调器配置模板
```

## 🚀 快速安装

```bash
# 1. 克隆仓库
git clone https://github.com/Shine8592/嘟嘟超级记忆系统hermes版本V1.git
cd 嘟嘟超级记忆系统hermes版本V1

# 2. 一键安装
chmod +x install.sh && ./install.sh

# 3. 构建初始索引
cd ~/.hermes/memory
python3 ~/.hermes/scripts/build_full_index.py

# 4. 验证
python3 ~/.hermes/scripts/semantic_search.py search "测试查询"
```

## 🔧 手动安装

### 安装依赖
```bash
pip install sentence-transformers faiss-cpu numpy
```

### 部署脚本
```bash
mkdir -p ~/.hermes/scripts
cp scripts/*.py ~/.hermes/scripts/
cp -r skills/* ~/.hermes/skills/
chmod +x ~/.hermes/scripts/*.py
```

### 配置记忆系统
```bash
# 初始化双记忆引擎
python3 ~/.hermes/scripts/init_dual_memory.py

# 构建向量索引（将你的核心记忆文件放入 ~/.hermes/ 目录）
# 支持的文件：SOUL.md, IDENTITY.md, USER.md, MEMORY.md, TOOLS.md
python3 ~/.hermes/scripts/build_full_index.py
```

## 📖 使用指南

### 语义搜索
```bash
cd ~/.hermes/memory
python3 ~/.hermes/scripts/semantic_search.py search "你的问题"
```

### 查看索引状态
```bash
python3 ~/.hermes/scripts/semantic_search.py status
```

### 记忆维护
```bash
# 手动执行记忆维护（清理STM + 自动转移）
python3 ~/.hermes/scripts/memory_maintain.py
```

## ⏰ 建议的 Cron 设置

| 时间 | 命令 | 用途 |
|------|------|------|
| 每天 03:00 | `python3 ~/.hermes/scripts/build_full_index.py` | 重建向量索引 |
| 每 6 小时 | `python3 ~/.hermes/scripts/memory_maintain.py` | STM清理+转移 |
| 每天 02:00 | `cd ~/dudu-backup && git add -A && git commit -m "backup" && git push` | GitHub备份 |

## 📋 质量门禁

每次记忆检索后自动执行：
- ✅ 相关性评分（0-1，>0.3 为有效结果）
- ✅ 来源标注（标注具体文件/会话）
- ✅ 内容长度检查（<50字符的结果自动过滤）
- ✅ 时效性排序（最近内容权重更高）

## 🔒 安全说明

- **系统代码不包含任何用户数据**
- API 密钥需通过 `~/.hermes/.env` 单独配置
- 用户的核心记忆文件（SOUL.md, MEMORY.md 等）**不会**随本仓库发布
- 见 `config/example.yaml` 了解配置项

## 📜 许可证

MIT License - 自由使用、修改、分发

## 🙏 致谢

- 基于 [SuperMemo-Du](https://github.com/Shine8592/SuperMemo-Du) 架构设计
- [sentence-transformers](https://www.sbert.net/) 提供语义嵌入模型
- [Faiss](https://faiss.ai/) 提供向量检索引擎
- [Hermes Agent](https://hermes-agent.nousresearch.com/) 提供 AI Agent 运行平台

---

> 🌸 嘟嘟出品 - 让每个AI助手都有好记性