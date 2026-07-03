#!/usr/bin/env python3
"""
嘟嘟记忆系统增强脚本 - 将所有历史会话与核心记忆编入向量索引
"""
import os, sys, json, re, time, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

HOME = Path.home()
MEMORY_DIR = HOME / ".hermes" / "memory"
SESSIONS_DIR = HOME / ".hermes" / "sessions"
STATE_DB = HOME / ".hermes" / "state.db"
INDEX_PATH = MEMORY_DIR / "semantic_index.faiss"
METADATA_PATH = MEMORY_DIR / "semantic_metadata.json"
MODEL_NAME = "all-MiniLM-L6-v2"

# 每条消息最大字符数（截断以控制索引大小）
MAX_CHUNK_CHARS = 1200

def extract_from_statedb(max_sessions=30):
    """从 state.db SQLite 提取最近会话的消息作为向量块"""
    chunks = []
    if not STATE_DB.exists():
        print("  ⚠ state.db 不存在，跳过")
        return chunks

    try:
        conn = sqlite3.connect(str(STATE_DB))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 获取最近的会话（排除 tool/系统角色）
        cur.execute("""
            SELECT m.id, m.session_id, m.role, m.content, m.timestamp, s.title
            FROM messages m
            JOIN sessions s ON s.id = m.session_id
            WHERE m.role IN ('user', 'assistant')
              AND m.content IS NOT NULL
              AND length(m.content) > 30
            ORDER BY m.id DESC
            LIMIT ?
        """, (max_sessions * 200,))  # 取宽裕量，后面去重

        rows = cur.fetchall()
        conn.close()

        seen = set()
        count = 0
        for row in rows:
            content = row["content"].strip()
            if not content:
                continue
            # 去重（取前60字符作为指纹）
            key = content[:60]
            if key in seen:
                continue
            seen.add(key)

            ts = row["timestamp"]
            if isinstance(ts, (int, float)):
                ts_str = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            else:
                ts_str = datetime.now().isoformat()

            # 截断长消息
            text = content[:MAX_CHUNK_CHARS]

            session_title = row["title"] or row["session_id"]
            chunks.append({
                "id": f"statedb/{row['id']}",
                "text": text,
                "source": f"statedb/{row['session_id']}",
                "type": "conversation",
                "role": row["role"],
                "title": session_title,
                "timestamp": ts_str
            })
            count += 1

        print(f"  state.db 会话: {count} 条")
    except Exception as e:
        print(f"  ⚠ state.db 读取失败: {e}")

    return chunks

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
                if isinstance(data, list):
                    messages = data
                elif isinstance(data, dict):
                    messages = data.get('messages') or []
                    if not messages and isinstance(data.get('request'), dict) and isinstance(data['request'].get('body'), dict):
                        messages = data['request']['body'].get('messages') or []
                else:
                    messages = []
                for msg in messages:
                    role = msg.get('role', '') if isinstance(msg, dict) else ''
                    content = msg.get('content', '') if isinstance(msg, dict) else ''
                    if not isinstance(content, str):
                        content = ''
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
                                "timestamp": data.get('last_updated') if isinstance(data, dict) else datetime.now().isoformat()
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

    # 1. 从旧文件系统提取
    chunks = extract_session_text()

    # 2. 从 state.db 提取最新会话（补充文件系统缺失的当前会话）
    statedb_chunks = extract_from_statedb(max_sessions=50)
    chunks.extend(statedb_chunks)

    # 只保留最近 N 条避免无限膨胀
    MAX_CHUNKS = 500
    if len(chunks) > MAX_CHUNKS:
        # 按时间戳排序，保留最新的
        def sort_key(c):
            ts = c.get('timestamp', '')
            return ts if isinstance(ts, str) else str(ts)
        chunks.sort(key=sort_key, reverse=True)
        chunks = chunks[:MAX_CHUNKS]
        print(f"  📐 压缩至 {MAX_CHUNKS} 条（保留最新）")

    build_index(chunks)
    elapsed = time.time() - start
    print(f"\n⏱️ 耗时: {elapsed:.1f}s")