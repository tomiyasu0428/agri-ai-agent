#!/usr/bin/env python3
"""
LINE Bot機能テストスクリプト
"""

import asyncio
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agri_ai.core.agent import AgentManager
from agri_ai.core.database import MongoDBClient, AgriDatabase
from agri_ai.line_bot.message_handler import LineMessageHandler
from agri_ai.line_bot.utils import (
    format_agent_response, 
    create_welcome_message, 
    create_error_message,
    parse_command,
    extract_field_name,
    extract_task_type,
    is_work_report
)


async def test_line_bot_components():
    """LINE Bot コンポーネントのテスト"""
    print("🤖 LINE Bot コンポーネントテスト開始")
    print("=" * 60)
    
    try:
        # MongoDB接続
        print("📊 MongoDB接続中...")
        mongo_client = MongoDBClient()
        await mongo_client.connect()
        
        # データベース初期化
        agri_db = AgriDatabase(mongo_client)
        
        # エージェントマネージャー初期化
        print("🧠 エージェントマネージャー初期化中...")
        agent_manager = AgentManager(agri_db)
        
        # LINE Bot API は実際のテストでは使用しないため、None を渡す
        print("📱 メッセージハンドラー初期化中...")
        message_handler = LineMessageHandler(agent_manager, None)
        
        print("✅ 初期化完了")
        
        return message_handler, agent_manager
        
    except Exception as e:
        print(f"❌ 初期化エラー: {e}")
        return None, None
    
    finally:
        if 'mongo_client' in locals():
            await mongo_client.disconnect()


async def test_message_processing():
    """メッセージ処理のテスト"""
    print(f"\n📝 メッセージ処理テスト")
    print("-" * 40)
    
    try:
        # MongoDB接続
        mongo_client = MongoDBClient()
        await mongo_client.connect()
        agri_db = AgriDatabase(mongo_client)
        agent_manager = AgentManager(agri_db)
        
        # テストメッセージ
        test_messages = [
            "こんにちは！",
            "今日の作業は何ですか？",
            "F14で大豆の防除を完了しました",
            "それの次回作業はいつですか？",
            "ヘルプ",
            "リセット"
        ]
        
        user_id = "test_line_user"
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n🗣️ テスト {i}: {message}")
            
            try:
                # エージェントでメッセージを処理
                response = await agent_manager.process_user_message(user_id, message)
                
                # LINE Bot用にフォーマット
                formatted_response = format_agent_response(response)
                
                print(f"🤖 応答: {formatted_response[:200]}...")
                
                # 少し待機
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ エラー: {e}")
        
        print(f"\n✅ メッセージ処理テスト完了")
        
    except Exception as e:
        print(f"❌ メッセージ処理テストエラー: {e}")
    
    finally:
        if 'mongo_client' in locals():
            await mongo_client.disconnect()


def test_utility_functions():
    """ユーティリティ関数のテスト"""
    print(f"\n🔧 ユーティリティ関数テスト")
    print("-" * 40)
    
    # ウェルカムメッセージテスト
    print("👋 ウェルカムメッセージテスト:")
    welcome_msg = create_welcome_message("田中太郎")
    print(f"結果: {welcome_msg[:100]}...")
    
    # エラーメッセージテスト
    print("\n❌ エラーメッセージテスト:")
    error_msg = create_error_message()
    print(f"結果: {error_msg[:100]}...")
    
    # コマンド解析テスト
    print("\n📋 コマンド解析テスト:")
    test_commands = ["ヘルプ", "リセット", "ステータス", "普通のメッセージ"]
    for cmd in test_commands:
        parsed = parse_command(cmd)
        print(f"  '{cmd}' -> {parsed}")
    
    # 圃場名抽出テスト
    print("\n🌾 圃場名抽出テスト:")
    field_tests = [
        "F14で大豆の防除",
        "鵡川 家裏での作業",
        "橋向こう③の状況",
        "普通のメッセージ"
    ]
    for text in field_tests:
        field = extract_field_name(text)
        print(f"  '{text}' -> {field}")
    
    # タスクタイプ抽出テスト
    print("\n📅 タスクタイプ抽出テスト:")
    task_tests = [
        "防除作業完了",
        "播種を実施",
        "収穫しました",
        "普通のメッセージ"
    ]
    for text in task_tests:
        task = extract_task_type(text)
        print(f"  '{text}' -> {task}")
    
    # 作業報告判定テスト
    print("\n📋 作業報告判定テスト:")
    report_tests = [
        "F14で防除完了",
        "作業を終了しました",
        "今日の作業は？",
        "こんにちは"
    ]
    for text in report_tests:
        is_report = is_work_report(text)
        print(f"  '{text}' -> {is_report}")
    
    print(f"\n✅ ユーティリティ関数テスト完了")


def test_response_formatting():
    """応答フォーマッティングのテスト"""
    print(f"\n📝 応答フォーマッティングテスト")
    print("-" * 40)
    
    # テスト用の応答データ
    test_responses = [
        "📋 作業報告を受付ました:\n作業: F14で大豆の防除 | 圃場: F14 | 状態: 完了",
        "❌ エラー: 圃場が見つかりません\n⚠️ 注意: 正しい圃場名を入力してください",
        "💡 提案: クプロシールドを1000倍希釈で使用してください\n🔮 次回作業提案: 7日後に再度防除",
        "a" * 2500,  # 長いメッセージのテスト
    ]
    
    for i, response in enumerate(test_responses, 1):
        print(f"\n🧪 テスト {i}:")
        print(f"入力: {response[:100]}...")
        
        formatted = format_agent_response(response)
        print(f"出力: {formatted[:200]}...")
        print(f"長さ: {len(formatted)} 文字")
    
    print(f"\n✅ 応答フォーマッティングテスト完了")


async def main():
    """メイン関数"""
    print("🚀 LINE Bot テスト開始")
    print("=" * 80)
    
    # コンポーネントテスト
    message_handler, agent_manager = await test_line_bot_components()
    
    if message_handler and agent_manager:
        print("✅ コンポーネントテスト成功")
    else:
        print("❌ コンポーネントテストに失敗")
        return
    
    # ユーティリティ関数テスト
    test_utility_functions()
    
    # 応答フォーマッティングテスト
    test_response_formatting()
    
    # メッセージ処理テスト
    await test_message_processing()
    
    print(f"\n{'='*80}")
    print("🎉 LINE Bot テスト完了！")
    print("\n次のステップ:")
    print("1. LINE Developer Consoleでチャンネルを作成")
    print("2. .envファイルにLINE_CHANNEL_ACCESS_TOKENとLINE_CHANNEL_SECRETを設定")
    print("3. scripts/run_line_bot.py でサーバーを起動")
    print("4. ngrok等でトンネルを作成してWebhook URLを設定")


if __name__ == "__main__":
    asyncio.run(main())