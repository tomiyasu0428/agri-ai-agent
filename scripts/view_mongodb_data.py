#!/usr/bin/env python3
"""
MongoDB データベース内容確認ツール
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agri_ai.core.database import MongoDBClient


async def show_database_overview():
    """データベース概要を表示"""
    print("=== MongoDB データベース概要 ===\n")
    
    try:
        # MongoDB接続
        client = MongoDBClient()
        await client.connect()
        
        # データベース統計
        db = client.database
        stats = await db.command("dbStats")
        
        print(f"データベース名: {stats['db']}")
        print(f"コレクション数: {stats['collections']}")
        print(f"総ドキュメント数: {stats['objects']}")
        print(f"データサイズ: {stats['dataSize']:,} bytes")
        print()
        
        # 各コレクションの詳細
        print("=== コレクション一覧 ===")
        collections = await db.list_collection_names()
        
        for collection_name in sorted(collections):
            collection = db[collection_name]
            count = await collection.count_documents({})
            
            # サンプルドキュメントを取得
            sample = await collection.find_one()
            fields = list(sample.keys()) if sample else []
            
            print(f"\n📁 {collection_name}")
            print(f"   レコード数: {count}")
            print(f"   フィールド数: {len(fields)}")
            
            if fields:
                # 主要フィールドを表示（システムフィールドを除く）
                main_fields = [f for f in fields if not f.startswith('_') and f not in ['airtable_id', 'migrated_at']]
                print(f"   主要フィールド: {', '.join(main_fields[:5])}")
                if len(main_fields) > 5:
                    print(f"   その他: {len(main_fields) - 5}個のフィールド")
        
        print("\n=== サンプルデータ ===")
        
        # 作業者マスターのサンプル
        worker_collection = db["worker_master"]
        worker = await worker_collection.find_one()
        if worker:
            print(f"\n👥 作業者マスター (サンプル):")
            print(f"   名前: {worker.get('作業者名', 'N/A')}")
            print(f"   役割: {worker.get('役割', 'N/A')}")
            print(f"   所属: {worker.get('所属', 'N/A')}")
        
        # 圃場データのサンプル
        field_collection = db["圃場データ"]
        field = await field_collection.find_one()
        if field:
            print(f"\n🌾 圃場データ (サンプル):")
            print(f"   圃場ID: {field.get('圃場ID', 'N/A')}")
            print(f"   圃場名: {field.get('圃場名', 'N/A')}")
            print(f"   エリア: {field.get('エリア', 'N/A')}")
            print(f"   面積: {field.get('面積(ha)', 'N/A')}")
        
        # 作業タスクのサンプル
        task_collection = db["作業タスク"]
        task = await task_collection.find_one()
        if task:
            print(f"\n📋 作業タスク (サンプル):")
            print(f"   タスク名: {task.get('タスク名', 'N/A')}")
            print(f"   ステータス: {task.get('ステータス', 'N/A')}")
            print(f"   予定日: {task.get('予定日', 'N/A')}")
        
        print(f"\n✅ データベース確認完了！")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    finally:
        if 'client' in locals():
            await client.disconnect()


async def show_collection_details(collection_name):
    """特定のコレクションの詳細を表示"""
    print(f"=== {collection_name} 詳細データ ===\n")
    
    try:
        client = MongoDBClient()
        await client.connect()
        
        collection = client.database[collection_name]
        
        # 全ドキュメントを取得（最大10件）
        cursor = collection.find().limit(10)
        documents = await cursor.to_list(length=10)
        
        for i, doc in enumerate(documents, 1):
            print(f"--- レコード {i} ---")
            for key, value in doc.items():
                if key.startswith('_'):
                    continue
                
                # 値を表示用に整形
                display_value = str(value)
                if len(display_value) > 50:
                    display_value = display_value[:47] + "..."
                
                print(f"{key}: {display_value}")
            print()
        
        total_count = await collection.count_documents({})
        if total_count > 10:
            print(f"... 他 {total_count - 10} 件のレコードがあります")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    finally:
        if 'client' in locals():
            await client.disconnect()


async def main():
    """メイン関数"""
    if len(sys.argv) > 1:
        collection_name = sys.argv[1]
        await show_collection_details(collection_name)
    else:
        await show_database_overview()


if __name__ == "__main__":
    asyncio.run(main())