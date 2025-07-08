#!/usr/bin/env python3
"""
Airtableの実際のフィールド名と変換ロジックの比較チェック
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agri_ai.utils.airtable_client import AirtableClient, AirtableToMongoMigrator


def analyze_field_mappings():
    """各テーブルのフィールドマッピングを詳細分析"""
    print("=== フィールドマッピング詳細分析 ===\n")
    
    try:
        # Airtableクライアント初期化
        client = AirtableClient()
        migrator = AirtableToMongoMigrator(client, None)
        
        # 各テーブルを分析
        tables = client.list_tables()
        
        for table_name in tables:
            print(f"📋 **{table_name}**")
            print("=" * 50)
            
            # 実際のフィールド取得
            schema = client.get_table_schema(table_name)
            actual_fields = schema.get('fields', [])
            sample_record = schema.get('sample')
            
            print(f"実際のAirtableフィールド ({len(actual_fields)}個):")
            for field in actual_fields:
                print(f"  - '{field}'")
            
            if sample_record:
                print(f"\nサンプルデータ:")
                fields_data = sample_record.get('fields', {})
                for field, value in fields_data.items():
                    display_value = str(value)
                    if len(display_value) > 50:
                        display_value = display_value[:47] + "..."
                    print(f"  {field}: {display_value}")
                
                # 変換テスト
                print(f"\n変換テスト:")
                try:
                    transformed = migrator._transform_airtable_record(sample_record, table_name)
                    print(f"変換後フィールド:")
                    for key, value in transformed.items():
                        if key in ['airtable_id', 'migrated_at', 'created_time', 'table_source']:
                            continue
                        if value is None:
                            print(f"  ⚠️  {key}: NULL (データなし)")
                        else:
                            display_value = str(value)
                            if len(display_value) > 50:
                                display_value = display_value[:47] + "..."
                            print(f"  ✓ {key}: {display_value}")
                
                except Exception as e:
                    print(f"  ❌ 変換エラー: {e}")
            
            print("\n" + "="*70 + "\n")
        
    except Exception as e:
        print(f"❌ 分析エラー: {e}")


if __name__ == "__main__":
    analyze_field_mappings()