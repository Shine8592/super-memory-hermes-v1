
# 🧠 嘟嘟超级记忆系统 - Hermes 版本 V2.0

> 基于 SuperMemo-Du 架构的语义向量记忆系统，专门为 Hermes Agent 设计。
> 让 AI 助手拥有"真正理解语义"的长期记忆能力。

## 🆕 v2.0 更新亮点

| 改进 | 说明 |
|------|------|
| **state.db 原生读取** | `build_full_index.py` 新增 `extract_from_statedb()`，直接读取 Hermes SQLite 会话库 |
| **索引覆盖当前会话** | 修复前只读文件系统，最新会话从未进入索引。修复后索引从 83→500 chunks |
| **500 上限保护** | 自动按时间戳保留最新的 500 条，避免索引无限膨胀 |
| **性能优化** | 单次重建约 20s，增量去重避免消息重复索引 |

## 迭代新增 (2026-06)

| 组件 | 说明 |
|------|------|
| `custom_scripts/post_process_log.py` | 自动将每次助手回复持久化到 SQLite `logs` 表 |
| `custom_scripts/generate_mermaid.py` | 将 STM 原子日志转为 Mermaid 图 |
| `custom_scripts/upgrade_memory.py` | 将重要日志提升到 `MEMORY.md` |
| `custom_scripts/backup_sqlite.sh` | 内存 SQLite 数据库 SQL dump |
| `custom_scripts/backup_and_sync.sh` | 归档 dump → Himalaya 邮件发送 → GitHub 备份推送 |
| `skills/memory-system/` | 完整记忆系统技能（含 SKILL.md + 引用文件） |
| `.gitignore` | 显式排除所有私人数据文件 |

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🔍 **语义向量检索** | 基于 `sentence-transformers`（all-MiniLM-L6-v2）+ `Faiss` 384维向量索引 |
| 🔄 **双记忆协同** | 短期记忆（STM 24h窗口）→ 长期记忆（LTM 永久）自动转移 |
| 🗄️ **三层存储** | 热存储（内存LRU）/ 温存储（SSD）/ 冷存储（归档） |
| 🎯 **state.db 原生支持** | 直接读取 Hermes SQLite 会话库，告别文件系统滞后（**v2.0 新增**） |
| ⏰ **自动维护** | 6小时一次记忆清理+转移，每日自动重建向量索引 |
| 🔌 **Hermes 原生集成** | 通过 SKILL.md 实现自动语义检索触发 |
| 🔐 **隐私安全** | 核心记忆与系统代码分离，用户数据不会被发布 |

## 📂 项目结构

```
super-memory-hermes-v1/
├── README.md                # 本文件
├── install.sh               # 一键安装脚本
├── requirements.txt         # Python依赖
├── .gitignore               # 排除私人数据
├── config/
│    └── example.yaml        # 配置模板
├── scripts/
│    ├── semantic_search.py       # 语义向量检索核心
│    ├── dual_memory_engine.py    # 双记忆协同引擎
│    ├── storage_tiers.py         # 三层存储实现
│    ├── build_full_index.py      # 全量索引构建（v2.0: 支持 state.db）
│    ├── auto_index_updater.py    # 自动索引更新
│    ├── init_dual_memory.py      # 双记忆引擎初始化
│    └── memory_maintain.py       # 记忆自动维护
├── custom_scripts/
│    ├── post_process_log.py      # 日志持久化
│    ├── upgrade_memory.py        # 日志→MEMORY.md 提升
│    ├── generate_mermaid.py      # Mermaid 图生成
│    ├── backup_sqlite.sh         # SQLite dump
│    └── backup_and_sync.sh       # 归档+邮件+GitHub
├── skills/
│    ├── memory-system/           # Hermes 记忆系统技能
│    └── semantic-memory-auto/    # 自动语义检索技能
└── templates/
     └── memory_coordinator.json.template  # 协调器模板
```

## 🚀 快速安装

```bash
# 1. 克隆仓库
git clone https://github.com/Shine8592/super-memory-hermes-v1.git
cd super-memory-hermes-v1

# 2. 一键安装
chmod +x install.sh && ./install.sh

# 3. 构建初始索引（自动读取核心文件 + state.db 最新会话）
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
mkdir -p ~/.hermes/scripts ~/.hermes/custom_scripts
cp scripts/*.py ~/.hermes/scripts/
cp custom_scripts/* ~/.hermes/custom_scripts/
cp -r skills/* ~/.hermes/skills/
chmod +x ~/.hermes/scripts/*.py ~/.hermes/custom_scripts/*.sh
```

### 配置
```bash
# 初始化双记忆引擎
python3 ~/.hermes/scripts/init_dual_memory.py

# 构建向量索引（将你的核心记忆文件放入 ~/.hermes/ 目录）
# 支持的文件：SOUL.md, IDENTITY.md, USER.md, MEMORY.md, TOOLS.md
# v2.0: 自动从 state.db 读取 Hermes 最新会话
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

# 日志提升（重要日志 → MEMORY.md）
python3 ~/.hermes/custom_scripts/upgrade_memory.py
```

## ⏰ 建议的 Cron 设置

| 时间 | 命令 | 用途 |
|------|------|------|
| 每天 03:00 | `python3 ~/.hermes/scripts/build_full_index.py` | 重建向量索引 |
| 每 6 小时 | `python3 ~/.hermes/scripts/memory_maintain.py` | STM清理+转移 |
| 每天 04:00 | `python3 ~/.hermes/custom_scripts/upgrade_memory.py && python3 ~/.hermes/scripts/build_full_index.py` | 记忆升级 |

## 📋 质量门禁

每次记忆检索后自动执行：
- ✅ 相关性评分（0-1，>0.3 为有效结果）
- ✅ **来源前缀识别**（`core/` 核心文件 / `statedb/` 当前会话 / `session/` 旧会话）
- ✅ 内容长度检查（<50字符的结果自动过滤）
- ✅ 时效性排序（最近内容权重更高）

## 🔒 安全说明

- **系统代码不包含任何用户数据**
- API 密钥需通过 `~/.hermes/.env` 或环境变量单独配置
- 用户的核心记忆文件（SOUL.md, MEMORY.md 等）**不会**随本仓库发布
- 见 `config/example.yaml` 了解配置项
- **v2.0 建议：** 不要将 API Key 明文写入任何 .md 文件

## 📜 许可证

MIT License - 自由使用、修改、分发

## 🙏 致谢

- 基于 [SuperMemo-Du](https://github.com/Shine8592/SuperMemo-Du) 架构设计
- [sentence-transformers](https://www.sbert.net/) 提供语义嵌入模型
- [Faiss](https://faiss.ai/) 提供向量检索引擎
- [Hermes Agent](https://hermes-agent.nousresearch.com/) 提供 AI Agent 运行平台

---

> 🌸 嘟嘟出品 - 让每个AI助手都有好记性
