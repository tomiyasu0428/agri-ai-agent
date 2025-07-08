#!/usr/bin/env python3
"""
修正されたフィールドマッピングでデータを再移行
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agri_ai.core.database import MongoDBClient
from agri_ai.utils.airtable_client import AirtableClient, AirtableToMongoMigrator


async def clear_and_remigrate():
    """既存データをクリアして再移行"""
    print("=== 修正されたデータマッピングで再移行 ===\n")
    
    try:
        # MongoDB接続
        print("1. MongoDB Atlas接続中...")
        mongo_client = MongoDBClient()
        await mongo_client.connect()
        
        # 既存コレクションの削除
        print("2. 既存データをクリア中...")
        db = mongo_client.database
        collections = await db.list_collection_names()
        
        for collection_name in collections:
            if collection_name not in ['sample_mflix']:  # サンプルデータは残す
                await db[collection_name].drop()
                print(f"   ✓ {collection_name} を削除")
        
        # Airtable初期化
        print("\n3. Airtableクライアント初期化中...")
        airtable_client = AirtableClient()
        
        # 再移行実行
        print("4. 修正されたマッピングで再移行実行中...")
        migrator = AirtableToMongoMigrator(airtable_client, mongo_client)
        result = await migrator.migrate_all_tables()
        
        # 結果表示
        print(f"\n=== 再移行結果 ===")
        print(f"移行完了時刻: {result.get('migration_completed', 'N/A')}")
        print(f"成功テーブル数: {result['tables_migrated']}")
        print(f"総レコード数: {result['total_records']}")
        
        # 圃場データの確認
        print(f"\n5. 圃場データの確認...")
        field_collection = await mongo_client.get_collection("圃場データ")
        sample_field = await field_collection.find_one()
        
        if sample_field:
            print(f"   ✓ サンプル圃場データ:")
            print(f"     圃場ID: {sample_field.get('圃場ID', 'N/A')}")
            print(f"     圃場名: {sample_field.get('圃場名', 'N/A')}")
            print(f"     エリア: {sample_field.get('エリア', 'N/A')}")
            print(f"     面積(ha): {sample_field.get('面積(ha)', 'N/A')} ha")
            print(f"     面積: {sample_field.get('面積', 'N/A')} ha")
            
            if sample_field.get('面積(ha)') is not None:
                print(f"   🎉 面積データが正常に移行されました！")
            else:
                print(f"   ⚠️  まだ面積データがnullです")
        
        if result['errors']:
            print(f"\nエラー:")
            for error in result['errors']:
                print(f"  - {error}")
        
        print(f"\n✅ 再移行完了！")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    finally:
        if 'mongo_client' in locals():
            await mongo_client.disconnect()


if __name__ == "__main__":
    asyncio.run(clear_and_remigrate())