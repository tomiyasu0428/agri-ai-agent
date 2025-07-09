#!/usr/bin/env python3
"""
LangChainエージェントの動作テストスクリプト
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agri_ai.core.agent import AgriAIAgent
from agri_ai.core.database import MongoDBClient, AgriDatabase
from agri_ai.utils.config import get_settings


async def test_basic_agent_functionality():
    """基本的なエージェント機能のテスト"""
    print("🤖 LangChainエージェント基本機能テスト")
    print("=" * 60)
    
    # 設定の確認
    settings = get_settings()
    print(f"📝 設定確認:")
    print(f"  OpenAI API Key: {'✅ 設定済み' if settings.openai_api_key else '❌ 未設定'}")
    print(f"  MongoDB URI: {'✅ 設定済み' if settings.mongodb_uri else '❌ 未設定'}")
    
    if not settings.openai_api_key:
        print("❌ OpenAI API Keyが設定されていません。")
        print("   .envファイルにOPENAI_API_KEYを設定してください。")
        return False
    
    try:
        # MongoDB接続テスト
        print(f"\n📊 MongoDB接続テスト:")
        mongo_client = MongoDBClient()
        await mongo_client.connect()
        print(f"  ✅ MongoDB接続成功")
        
        # データベースの確認
        agri_db = AgriDatabase(mongo_client)
        print(f"  ✅ AgriDatabase初期化成功")
        
        # エージェントの初期化
        print(f"\n🧠 エージェント初期化テスト:")
        agent = AgriAIAgent(agri_db)
        print(f"  ✅ AgriAIAgent初期化成功")
        print(f"  📱 利用可能ツール数: {len(agent.tools)}")
        
        # ツールの確認
        print(f"\n🔧 利用可能ツール:")
        for i, tool in enumerate(agent.tools, 1):
            print(f"  {i}. {tool.name}: {tool.description}")
        
        return True
        
    except Exception as e:
        print(f"❌ 初期化エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'mongo_client' in locals():
            await mongo_client.disconnect()


async def test_simple_conversation():
    """シンプルな対話テスト"""
    print(f"\n💬 シンプルな対話テスト")
    print("=" * 60)
    
    try:
        # エージェント初期化
        mongo_client = MongoDBClient()
        await mongo_client.connect()
        agri_db = AgriDatabase(mongo_client)
        agent = AgriAIAgent(agri_db)
        
        user_id = "test_user"
        
        # 基本的な質問
        simple_questions = [
            "こんにちは！",
            "今日は何をすればいいですか？",
            "圃場の状況を教えてください",
            "ありがとうございました"
        ]
        
        for i, question in enumerate(simple_questions, 1):
            print(f"\n🗣️ 質問 {i}: {question}")
            try:
                response = await agent.process_message(question, user_id)
                print(f"🤖 応答: {response}")
            except Exception as e:
                print(f"❌ エラー: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 対話テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'mongo_client' in locals():
            await mongo_client.disconnect()


async def test_database_tools():
    """データベースツールのテスト"""
    print(f"\n🗄️ データベースツールテスト")
    print("=" * 60)
    
    try:
        # エージェント初期化
        mongo_client = MongoDBClient()
        await mongo_client.connect()
        agri_db = AgriDatabase(mongo_client)
        agent = AgriAIAgent(agri_db)
        
        user_id = "test_user"
        
        # データベース関連の質問
        db_questions = [
            "今日のタスクを教えてください",
            "F14の圃場情報を教えてください",
            "大豆の防除について教えてください",
            "使用できる資材は何がありますか？"
        ]
        
        for i, question in enumerate(db_questions, 1):
            print(f"\n📊 データベース質問 {i}: {question}")
            try:
                response = await agent.process_message(question, user_id)
                print(f"🤖 応答: {response}")
                
                # 少し待機
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ エラー: {e}")
                import traceback
                traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ データベースツールテストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'mongo_client' in locals():
            await mongo_client.disconnect()


async def test_work_report_processing():
    """作業報告処理のテスト"""
    print(f"\n📋 作業報告処理テスト")
    print("=" * 60)
    
    try:
        # エージェント初期化
        mongo_client = MongoDBClient()
        await mongo_client.connect()
        agri_db = AgriDatabase(mongo_client)
        agent = AgriAIAgent(agri_db)
        
        user_id = "test_farmer"
        
        # 作業報告のテスト
        work_reports = [
            "F14で大豆の防除を完了しました",
            "播種作業を今日の午前中に実施しました",
            "クプロシールドを1000倍希釈で散布完了",
            "石谷さん横の圃場での収穫作業を終えました"
        ]
        
        for i, report in enumerate(work_reports, 1):
            print(f"\n📝 作業報告 {i}: {report}")
            try:
                response = await agent.process_message(report, user_id)
                print(f"🤖 応答: {response}")
                
                # 文脈の確認
                context_summary = agent.context_manager.get_context_summary(user_id)
                print(f"📊 文脈更新: {context_summary}")
                
                # 少し待機
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ エラー: {e}")
                import traceback
                traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ 作業報告処理テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'mongo_client' in locals():
            await mongo_client.disconnect()


async def test_context_and_ellipsis():
    """文脈と省略表現のテスト"""
    print(f"\n🔗 文脈と省略表現テスト")
    print("=" * 60)
    
    try:
        # エージェント初期化
        mongo_client = MongoDBClient()
        await mongo_client.connect()
        agri_db = AgriDatabase(mongo_client)
        agent = AgriAIAgent(agri_db)
        
        user_id = "test_context_user"
        
        # 文脈を構築する会話
        context_building = [
            "F14で大豆の防除作業を予定しています",
            "それはいつ実施すればいいですか？",
            "作業を完了しました",
            "それの次回作業はいつですか？"
        ]
        
        for i, message in enumerate(context_building, 1):
            print(f"\n💭 文脈メッセージ {i}: {message}")
            try:
                response = await agent.process_message(message, user_id)
                print(f"🤖 応答: {response}")
                
                # 文脈の確認
                context_summary = agent.context_manager.get_context_summary(user_id)
                print(f"📊 現在の文脈: {context_summary}")
                
                # 少し待機
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ エラー: {e}")
                import traceback
                traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ 文脈テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'mongo_client' in locals():
            await mongo_client.disconnect()


async def interactive_test():
    """対話型テスト"""
    print(f"\n🎮 対話型テスト")
    print("=" * 60)
    print("エージェントと対話してみましょう！")
    print("'quit'または'exit'で終了します。")
    
    try:
        # エージェント初期化
        mongo_client = MongoDBClient()
        await mongo_client.connect()
        agri_db = AgriDatabase(mongo_client)
        agent = AgriAIAgent(agri_db)
        
        user_id = "interactive_user"
        
        while True:
            try:
                # ユーザー入力
                user_input = input("\n👤 あなた: ")
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("対話を終了します。")
                    break
                
                if not user_input.strip():
                    continue
                
                # エージェントの応答
                print("🤖 考え中...")
                response = await agent.process_message(user_input, user_id)
                print(f"🤖 エージェント: {response}")
                
                # 文脈の確認（オプション）
                context_summary = agent.context_manager.get_context_summary(user_id)
                print(f"📊 文脈: {context_summary}")
                
            except KeyboardInterrupt:
                print("\n対話を中断しました。")
                break
            except Exception as e:
                print(f"❌ エラー: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 対話型テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'mongo_client' in locals():
            await mongo_client.disconnect()


async def main():
    """メイン関数"""
    print("🚀 LangChainエージェント総合テスト開始")
    print("=" * 80)
    
    # 各テストの実行
    tests = [
        ("基本機能", test_basic_agent_functionality),
        ("シンプル対話", test_simple_conversation),
        ("データベースツール", test_database_tools),
        ("作業報告処理", test_work_report_processing),
        ("文脈と省略表現", test_context_and_ellipsis)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = await test_func()
            results.append((test_name, result))
            print(f"✅ {test_name}: {'成功' if result else '失敗'}")
        except Exception as e:
            print(f"❌ {test_name}: エラー - {e}")
            results.append((test_name, False))
    
    # 結果サマリー
    print(f"\n{'='*80}")
    print(f"📊 テスト結果サマリー:")
    successful_tests = sum(1 for _, result in results if result)
    total_tests = len(results)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"  {status} {test_name}")
    
    print(f"\n成功: {successful_tests}/{total_tests}")
    
    if successful_tests == total_tests:
        print("🎉 すべてのテストが成功しました！")
        
        # 対話型テストの提案
        interactive_choice = input("\n対話型テストを実行しますか？ (y/n): ")
        if interactive_choice.lower() in ['y', 'yes']:
            await interactive_test()
    else:
        print("⚠️ いくつかのテストが失敗しました。設定を確認してください。")
    
    print("\n🏁 テスト完了")


if __name__ == "__main__":
    asyncio.run(main())