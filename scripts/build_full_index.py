#!/usr/bin/env python3
"""
嘟嘟记忆系统增强脚本 - 将所有历史会话与核心记忆编入向量索引
"""
import os, sys, json, re, time
from pathlib import Path
from datetime import datetime
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

HOME = Path.home()
MEMORY_DIR = HOME / ".hermes" / "memory"
SESSIONS_DIR = HOME / ".hermes" / "sessions"
INDEX_PATH = MEMORY_DIR / "semantic_index.faiss"
METADATA_PATH = MEMORY_DIR / "semantic_metadata.json"
MODEL_NAME = "all-MiniLM-L6-v2"

def extract_session_text():
    """从历史会话文件中提取有价值的内容"""
    chunks = []
    
    # 1. 核心记忆文件
    core_files = ["MEMORY.md", "SOUL.md", "TOOLS.md", "USER.md", "IDENTITY.md"]
    for name in core_files:
        fpath = HOME / ".hermes" / name
        if fpath.exists():
            text = fpath.read_text(encoding='utf-8')
            # 按 ## 分割
            sections = re.split(r'\n(?=#)', text)
            for i, sec in enumerate(sections):
                if len(sec.strip()) > 50:
                    chunks.append({
                        "id": f"core/{name}:{i}",
                        "text": sec.strip(),
                        "source": name,
                        "type": "core_memory",
                        "timestamp": datetime.now().isoformat()
                    })
    
    # 2. 历史会话文件
    session_files = sorted(SESSIONS_DIR.glob("*.jsonl")) + sorted(SESSIONS_DIR.glob("session_*.json"))
    seen = set()
    
    for sf in session_files[-30:]:  # 最近30个会话文件
        try:
            if sf.suffix == '.jsonl':
                with open(sf) as f:
                    for line in f:
                        try:
                            msg = json.loads(line)
                            role = msg.get('role', '')
                            content = msg.get('content', '')
                            if role in ('user', 'assistant') and content and len(content) > 30:
                                key = content[:50]
                                if key not in seen:
                                    seen.add(key)
                                    chunks.append({
                                        "id": f"session/{sf.stem}:{len(seen)}",
                                        "text": content.strip()[:1000],
                                        "source": f"session/{sf.name}",
                                        "type": "conversation",
                                        "role": role,
                                        "timestamp": msg.get('timestamp', datetime.now().isoformat())
                                    })
                        except:
                            pass
            elif sf.suffix == '.json':
                with open(sf) as f:
                    data = json.load(f)
                    for msg in data if isinstance(data, list) else data.values():
                        role = msg.get('role', '') if isinstance(msg, dict) else ''
                        content = msg.get('content', '') if isinstance(msg, dict) else ''
                        if role in ('user', 'assistant') and content and len(content) > 30:
                            key = content[:50]
                            if key not in seen:
                                seen.add(key)
                                chunks.append({
                                    "id": f"session/{sf.stem}:{len(seen)}",
                                    "text": content.strip()[:1000],
                                    "source": f"session/{sf.name}",
                                    "type": "conversation",
                                    "role": role,
                                    "timestamp": datetime.now().isoformat()
                                })
        except Exception as e:
            print(f"  ⚠ {sf.name}: {e}")
    
    print(f"  核心记忆: {sum(1 for c in chunks if c['type']=='core_memory')} 块")
    print(f"  历史会话: {sum(1 for c in chunks if c['type']=='conversation')} 条")
    return chunks

def build_index(chunks):
    """构建Faiss向量索引"""
    print(f"\n🧠 加载模型: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    
    texts = [c["text"] for c in chunks]
    print(f"📊 生成 {len(texts)} 个嵌入向量...")
    
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings.astype(np.float32))
    
    # 保存
    faiss.write_index(index, str(INDEX_PATH))
    with open(METADATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 索引构建完成!")
    print(f"   总块数: {len(chunks)}")
    print(f"   维度: {dimension}")
    print(f"   索引: {INDEX_PATH}")
    print(f"   元数据: {METADATA_PATH}")

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 嘟嘟记忆系统 - 全量索引构建")
    print("=" * 50)
    start = time.time()
    chunks = extract_session_text()
    build_index(chunks)
    elapsed = time.time() - start
    print(f"\n⏱️ 耗时: {elapsed:.1f}s")