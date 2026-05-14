#!/bin/bash
# 嘟嘟超级记忆系统 - 一键安装脚本
set -e

echo "========================================"
echo "  🧠 嘟嘟超级记忆系统 Hermes V1 安装"
echo "========================================"
echo ""

# 1. 安装Python依赖
echo "📦 安装Python依赖..."
pip install sentence-transformers faiss-cpu numpy 2>&1 | tail -1

# 2. 创建目录
echo "📁 创建目录结构..."
mkdir -p ~/.hermes/scripts
mkdir -p ~/.hermes/memory/stm
mkdir -p ~/.hermes/memory/archive
mkdir -p ~/.hermes/skills

# 3. 部署脚本
echo "📋 部署脚本..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp -r "$SCRIPT_DIR/scripts/"* ~/.hermes/scripts/
cp -r "$SCRIPT_DIR/skills/"* ~/.hermes/skills/
chmod +x ~/.hermes/scripts/*.py

# 4. 初始化双记忆引擎
echo "⚙️ 初始化双记忆引擎..."
python3 ~/.hermes/scripts/init_dual_memory.py

# 5. 验证安装
echo ""
echo "🔍 验证安装..."
python3 -c "
from sentence_transformers import SentenceTransformer
import faiss
print('✅ sentence-transformers:', SentenceTransformer.__module__)
print('✅ faiss:', faiss.__version__)
"

echo ""
echo "========================================"
echo "  ✅ 安装完成！"
echo "========================================"
echo ""
echo "下一步："
echo "  1. 将你的核心记忆文件放入 ~/.hermes/"
echo "     (SOUL.md, IDENTITY.md, USER.md, MEMORY.md, TOOLS.md)"
echo "  2. 构建向量索引："
echo "     cd ~/.hermes/memory && python3 ~/.hermes/scripts/build_full_index.py"
echo "  3. 测试搜索："
echo "     python3 ~/.hermes/scripts/semantic_search.py search \"你的查询\""
echo ""