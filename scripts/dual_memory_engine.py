#!/usr/bin/env python3
"""
双记忆协同引擎 (Dual Memory Engine)
实现短期记忆与长期记忆的智能协同
"""

import os
import sys
import json
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

import numpy as np

# 配置
MEMORY_DIR = Path.home() / ".hermes" / "memory"
STM_DIR = MEMORY_DIR / "stm"
LTM_FILE = MEMORY_DIR.parent / "MEMORY.md"
COORDINATOR_FILE = MEMORY_DIR / "memory_coordinator.json"  # 协同状态

class ShortTermMemory:
    """短期记忆管理器"""
    
    def __init__(self, max_age_hours: int = 24, max_items: int = 1000):
        self.max_age = timedelta(hours=max_age_hours)
        self.max_items = max_items
        self.stm_dir = STM_DIR
        self.stm_dir.mkdir(exist_ok=True)
        
    def add(self, content: str, metadata: Optional[Dict] = None) -> str:
        """添加短期记忆"""
        item_id = hashlib.md5(f"{time.time()}_{content}".encode()).hexdigest()[:12]
        
        item = {
            "id": item_id,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
            "access_count": 0,
            "importance_score": 0.0
        }
        
        # 保存到文件
        file_path = self.stm_dir / f"{item_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(item, f, indent=2, ensure_ascii=False)
        
        # 清理过期项目
        self._cleanup()
        
        return item_id
    
    def get(self, item_id: str) -> Optional[Dict]:
        """获取短期记忆项"""
        file_path = self.stm_dir / f"{item_id}.json"
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            item = json.load(f)
        
        # 更新访问计数
        item["access_count"] = item.get("access_count", 0) + 1
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(item, f, indent=2, ensure_ascii=False)
        
        return item
    
    def query(self, keywords: List[str], limit: int = 10) -> List[Dict]:
        """查询短期记忆"""
        results = []
        cutoff = datetime.now() - self.max_age
        
        for file_path in self.stm_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    item = json.load(f)
                
                # 检查是否过期
                timestamp = datetime.fromisoformat(item["timestamp"])
                if timestamp < cutoff:
                    file_path.unlink()
                    continue
                
                # 关键词匹配
                content_lower = item["content"].lower()
                if any(kw.lower() in content_lower for kw in keywords):
                    results.append(item)
                    
            except Exception:
                continue
        
        # 按访问次数和时效性排序
        results.sort(
            key=lambda x: (
                x.get("access_count", 0),
                x["timestamp"]
            ),
            reverse=True
        )
        
        return results[:limit]
    
    def _cleanup(self):
        """清理过期和超出限制的项目"""
        items = []
        cutoff = datetime.now() - self.max_age
        
        for file_path in self.stm_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    item = json.load(f)
                
                timestamp = datetime.fromisoformat(item["timestamp"])
                if timestamp >= cutoff:
                    items.append((file_path, timestamp))
                else:
                    file_path.unlink()
                    
            except Exception:
                file_path.unlink()
        
        # 如果超出数量限制，删除最旧的项目
        if len(items) > self.max_items:
            items.sort(key=lambda x: x[1])
            for file_path, _ in items[:len(items) - self.max_items]:
                file_path.unlink()
    
    def get_all(self) -> List[Dict]:
        """获取所有短期记忆（用于协同分析）"""
        items = []
        cutoff = datetime.now() - self.max_age
        
        for file_path in self.stm_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    item = json.load(f)
                
                timestamp = datetime.fromisoformat(item["timestamp"])
                if timestamp >= cutoff:
                    items.append(item)
                    
            except Exception:
                continue
        
        return items


class LongTermMemory:
    """长期记忆管理器"""
    
    def __init__(self, ltm_file: Path = LTM_FILE):
        self.ltm_file = ltm_file
        self.sections = self._load_sections()
    
    def _load_sections(self) -> List[Dict]:
        """加载长期记忆的各个章节"""
        sections = []
        
        if not self.ltm_file.exists():
            return sections
        
        with open(self.ltm_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 按 ## 分割章节
        parts = content.split("\n## ")
        
        for i, part in enumerate(parts):
            if not part.strip():
                continue
            
            if not part.startswith("#"):
                part = "## " + part
            
            # 提取标题
            lines = part.strip().split("\n")
            title = lines[0].replace("#", "").strip() if lines else f"章节 {i}"
            
            sections.append({
                "id": f"ltm_section_{i}",
                "title": title,
                "content": part.strip(),
                "last_accessed": None,
                "access_count": 0
            })
        
        return sections
    
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """搜索长期记忆"""
        results = []
        query_lower = query.lower()
        
        for section in self.sections:
            # 计算相关性
            content_lower = section["content"].lower()
            
            # 简单的关键词匹配
            if query_lower in content_lower:
                # 计算匹配次数
                matches = content_lower.count(query_lower)
                
                # 考虑标题匹配
                title_bonus = 2.0 if query_lower in section["title"].lower() else 1.0
                
                # 计算相关性分数
                relevance = (matches * title_bonus) / len(section["content"]) * 1000
                
                results.append({
                    **section,
                    "relevance": min(relevance, 1.0),
                    "match_count": matches
                })
        
        # 按相关性排序
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:limit]
    
    def add_section(self, title: str, content: str) -> str:
        """添加新章节到长期记忆"""
        section_id = f"ltm_section_{len(self.sections)}"
        
        new_section = f"\n\n## {title}\n\n{content}"
        
        # 读取现有内容
        existing_content = ""
        if self.ltm_file.exists():
            with open(self.ltm_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        
        # 添加新章节
        updated_content = existing_content + new_section
        
        # 保存
        with open(self.ltm_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        # 重新加载章节
        self.sections = self._load_sections()
        
        return section_id
    
    def get_important_concepts(self, limit: int = 10) -> List[str]:
        """提取重要概念"""
        concepts = []
        
        for section in self.sections:
            # 查找包含核心概念的句子
            lines = section["content"].split("\n")
            for line in lines:
                line = line.strip()
                if len(line) > 20 and len(line) < 200:
                    # 检查是否包含重要关键词
                    important_keywords = [
                        "原则", "规则", "核心", "重要", "关键",
                        "必须", "应该", "建议", "教训", "经验"
                    ]
                    
                    if any(kw in line for kw in important_keywords):
                        concepts.append(line[:100])
        
        return concepts[:limit]


class MemoryCoordinator:
    """记忆协同引擎 - 管理短期↔长期记忆的协同"""
    
    def __init__(self):
        self.stm = ShortTermMemory()
        self.ltm = LongTermMemory()
        self.coordinator_file = COORDINATOR_FILE
        self.load_state()
    
    def load_state(self):
        """加载协同状态"""
        if self.coordinator_file.exists():
            with open(self.coordinator_file, 'r', encoding='utf-8') as f:
                self.state = json.load(f)
        else:
            self.state = {
                "total_transfers": 0,
                "last_coordination": None,
                "importance_threshold": 0.7
            }
    
    def save_state(self):
        """保存协同状态"""
        self.state["last_coordination"] = datetime.now().isoformat()
        
        with open(self.coordinator_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
    
    def calculate_importance(self, item: Dict) -> float:
        """计算记忆项的重要性分数"""
        score = 0.0
        
        # 访问次数加成
        access_count = item.get("access_count", 0)
        score += min(access_count * 0.1, 0.3)
        
        # 时效性加成（最近访问更重要）
        try:
            timestamp = datetime.fromisoformat(item["timestamp"])
            age_hours = (datetime.now() - timestamp).total_seconds() / 3600
            recency_score = max(0, 1 - age_hours / 24)  # 24小时内线性衰减
            score += recency_score * 0.3
        except Exception:
            pass
        
        # 元数据加成
        metadata = item.get("metadata", {})
        if metadata.get("important", False):
            score += 0.2
        if metadata.get("user_marked", False):
            score += 0.2
        
        # 长度加成（适当长度的内容更有价值）
        content_length = len(item.get("content", ""))
        if 50 < content_length < 1000:
            score += 0.2
        
        return min(score, 1.0)
    
    def evaluate_transfers(self) -> List[Dict]:
        """评估需要转移的短期记忆项目"""
        stm_items = self.stm.get_all()
        transfers = []
        
        for item in stm_items:
            importance = self.calculate_importance(item)
            item["importance_score"] = importance
            
            # 如果超过重要性阈值，建议转移
            if importance >= self.state["importance_threshold"]:
                transfers.append(item)
        
        # 按重要性排序
        transfers.sort(key=lambda x: x["importance_score"], reverse=True)
        return transfers
    
    def transfer_to_ltm(self, item_id: str, ltm_title: Optional[str] = None) -> bool:
        """将短期记忆项目转移到长期记忆"""
        item = self.stm.get(item_id)
        if not item:
            return False
        
        # 计算重要性
        importance = self.calculate_importance(item)
        
        # 生成长期记忆标题
        if not ltm_title:
            content_preview = item["content"][:50]
            ltm_title = f"重要记忆: {content_preview}..."
        
        # 添加到长期记忆
        metadata = item.get("metadata", {})
        metadata.update({
            "source": "stm_transfer",
            "stm_id": item_id,
            "transfer_time": datetime.now().isoformat(),
            "importance_score": importance
        })
        
        ltm_content = f"{item['content']}\n\n[元数据: {json.dumps(metadata, ensure_ascii=False, indent=2)}]"
        
        section_id = self.ltm.add_section(ltm_title, ltm_content)
        
        # 更新状态
        self.state["total_transfers"] += 1
        self.save_state()
        
        print(f"✅ 已转移项目 {item_id} 到长期记忆 (章节: {section_id})")
        return True
    
    def auto_transfer(self, max_transfers: int = 5) -> int:
        """自动转移重要短期记忆到长期记忆"""
        transfers = self.evaluate_transfers()
        transferred = 0
        
        print(f"\n🔄 自动转移评估: 发现 {len(transfers)} 个重要项目")
        
        for item in transfers[:max_transfers]:
            if self.transfer_to_ltm(item["id"]):
                transferred += 1
        
        if transferred > 0:
            print(f"✅ 已完成 {transferred} 个项目转移")
        else:
            print("ℹ 没有需要转移的项目")
        
        return transferred
    
    def search_across_memories(self, query: str, stm_limit: int = 5, ltm_limit: int = 5) -> Dict[str, List]:
        """跨短期和长期记忆搜索"""
        print(f"\n🔍 跨记忆搜索: '{query}'")
        
        # 搜索短期记忆
        stm_results = self.stm.query(query.split(), limit=stm_limit)
        
        # 搜索长期记忆
        ltm_results = self.ltm.search(query, limit=ltm_limit)
        
        return {
            "short_term": stm_results,
            "long_term": ltm_results
        }
    
    def print_search_results(self, results: Dict[str, List]):
        """打印搜索结果"""
        stm_results = results["short_term"]
        ltm_results = results["long_term"]
        
        print(f"\n{'='*70}")
        print(f"📊 搜索结果")
        print(f"{'='*70}\n")
        
        # 短期记忆结果
        if stm_results:
            print(f"🟢 短期记忆 ({len(stm_results)} 个结果):")
            print("-" * 50)
            for i, item in enumerate(stm_results, 1):
                importance = item.get("importance_score", 0)
                access_count = item.get("access_count", 0)
                print(f"{i}. 📌 {item['content'][:100]}...")
                print(f"   ⚡ 重要性: {importance:.2f} | 访问: {access_count}")
                print()
        
        # 长期记忆结果
        if ltm_results:
            print(f"📚 长期记忆 ({len(ltm_results)} 个结果):")
            print("-" * 50)
            for i, section in enumerate(ltm_results, 1):
                print(f"{i}. 🏷️  {section['title']}")
                print(f"   相关性: {section['relevance']:.3f}")
                # 显示内容预览
                content_preview = section['content'][:200]
                print(f"   📄 {content_preview}...")
                print()
        
        if not stm_results and not ltm_results:
            print("❌ 未找到相关结果")
    
    def get_coordination_report(self) -> Dict:
        """获取协同报告"""
        stm_items = self.stm.get_all()
        
        return {
            "short_term_count": len(stm_items),
            "long_term_sections": len(self.ltm.sections),
            "total_transfers": self.state["total_transfers"],
            "threshold": self.state["importance_threshold"],
            "pending_transfers": len(self.evaluate_transfers()),
            "stm_items": stm_items
        }
    
    def print_status(self):
        """打印系统状态"""
        print("\n📊 双记忆协同引擎状态")
        print("=" * 50)
        
        report = self.get_coordination_report()
        
        print(f"短期记忆项目: {report['short_term_count']}")
        print(f"长期记忆章节: {report['long_term_sections']}")
        print(f"已完成转移: {report['total_transfers']}")
        print(f"待转移项目: {report['pending_transfers']}")
        print(f"重要性阈值: {report['threshold']}")
        print(f"\n最后协调时间: {self.state['last_coordination'] or '从未'}")


def main():
    """主函数 - 演示双记忆协同系统"""
    print("🚀 双记忆协同引擎 v1.0")
    print("=" * 60)
    
    coordinator = MemoryCoordinator()
    
    # 命令行接口
    if len(sys.argv) < 2:
        print("\n使用方法:")
        print("  添加短期记忆:")
        print("    python3 dual_memory_engine.py add \"内容\"")
        print("\n  跨记忆搜索:")
        print("    python3 dual_memory_engine.py search \"查询\"")
        print("\n  自动转移:")
        print("    python3 dual_memory_engine.py transfer")
        print("\n  系统状态:")
        print("    python3 dual_memory_engine.py status")
        print("\n  协调报告:")
        print("    python3 dual_memory_engine.py report")
        return
    
    command = sys.argv[1]
    
    if command == "add" and len(sys.argv) > 2:
        content = " ".join(sys.argv[2:])
        item_id = coordinator.stm.add(content)
        print(f"✅ 已添加短期记忆: {item_id[:8]}...")
    
    elif command == "search" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        results = coordinator.search_across_memories(query)
        coordinator.print_search_results(results)
    
    elif command == "transfer":
        print("\n🔄 执行自动转移...")
        transferred = coordinator.auto_transfer()
        print(f"\n✅ 转移完成: {transferred} 个项目")
    
    elif command == "status":
        coordinator.print_status()
    
    elif command == "report":
        report = coordinator.get_coordination_report()
        print("\n📋 协同报告")
        print("=" * 50)
        for key, value in report.items():
            if key != "stm_items":
                print(f"{key}: {value}")
        
        if report["stm_items"]:
            print(f"\n短期记忆项目 ({len(report['stm_items'])}):")  
            for item in report["stm_items"][:5]:
                print(f"  - {item['content'][:60]}...")
    
    else:
        print("❌ 未知命令")


if __name__ == "__main__":
    main()
