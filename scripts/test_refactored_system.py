#!/usr/bin/env python3
"""
リファクタリングされたシステムのテストスクリプト
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agri_ai.core.database_pool import get_database_pool, close_database_pool
from agri_ai.core.optimized_database import OptimizedAgriDatabase
from agri_ai.core.agent_pool import get_agent_pool, shutdown_agent_pool
from agri_ai.core.agent import OptimizedAgentManager
from agri_ai.line_bot.message_handler import OptimizedLineMessageHandler
from agri_ai.exceptions import AgriAIException
from agri_ai.utils.config import get_settings
from agri_ai.utils.error_handling import error_handler


async def test_database_pool():
    """データベースプールのテスト"""
    print("🗄️ データベースプールテスト")
    print("-" * 40)
    
    try:
        # データベースプールを取得
        db_pool = await get_database_pool()
        optimized_db = OptimizedAgriDatabase(db_pool)
        
        # 基本的なクエリテスト
        print("📊 基本クエリテスト中...")
        start_time = time.time()
        
        # 今日のタスクを取得
        tasks = await optimized_db.get_today_tasks("test_user", "2025-07-09")
        print(f"✅ タスク取得完了: {len(tasks)}件 ({time.time() - start_time:.2f}s)")
        
        # 圃場ステータスを取得
        start_time = time.time()
        field_status = await optimized_db.get_field_status("F14")
        print(f"✅ 圃場ステータス取得完了 ({time.time() - start_time:.2f}s)")
        
        # キャッシュテスト
        print("🔄 キャッシュテスト中...")
        start_time = time.time()
        tasks2 = await optimized_db.get_today_tasks("test_user", "2025-07-09")
        print(f"✅ キャッシュされたタスク取得完了 ({time.time() - start_time:.2f}s)")
        
        # 統計情報を取得
        stats = await optimized_db.get_database_stats()
        print(f"📈 データベース統計: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ データベースプールテストエラー: {e}")
        return False


async def test_agent_pool():
    """エージェントプールのテスト"""
    print("\n🤖 エージェントプールテスト")
    print("-" * 40)
    
    try:
        # エージェントプールを取得
        agent_pool = await get_agent_pool()
        
        # 複数のエージェントを作成
        print("🔧 複数エージェント作成テスト中...")
        agents = []
        for i in range(5):
            user_id = f"test_user_{i}"
            agent = await agent_pool.get_agent(user_id)
            agents.append((user_id, agent))
            print(f"✅ エージェント {i+1} 作成完了")
        
        # エージェント統計を取得
        stats = agent_pool.get_pool_stats()
        print(f"📊 エージェントプール統計: {stats}")
        
        # エージェント情報を取得
        for user_id, agent in agents[:2]:  # 最初の2つのエージェントのみ
            agent_info = agent_pool.get_agent_info(user_id)
            print(f"📋 エージェント {user_id} 情報: {agent_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ エージェントプールテストエラー: {e}")
        return False


async def test_optimized_agent_manager():
    """最適化されたエージェントマネージャーのテスト"""
    print("\n⚡ 最適化エージェントマネージャーテスト")
    print("-" * 40)
    
    try:
        # エージェントプールを取得
        agent_pool = await get_agent_pool()
        agent_manager = OptimizedAgentManager(agent_pool)
        
        # メッセージ処理テスト
        test_messages = [
            "こんにちは！",
            "今日の作業を教えてください",
            "F14で大豆の防除を完了しました",
            "それの次回作業はいつですか？",
        ]
        
        for i, message in enumerate(test_messages):
            print(f"📨 メッセージ {i+1}: {message}")
            start_time = time.time()
            
            response = await agent_manager.process_user_message(f"test_user_{i}", message)
            processing_time = time.time() - start_time
            
            print(f"🤖 応答 ({processing_time:.2f}s): {response[:100]}...")
        
        # 統計情報を取得
        stats = agent_manager.get_agent_stats()
        print(f"📊 エージェントマネージャー統計: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ エージェントマネージャーテストエラー: {e}")
        return False


async def test_message_handler():
    """メッセージハンドラーのテスト"""
    print("\n💬 メッセージハンドラーテスト")
    print("-" * 40)
    
    try:
        # エージェントマネージャーを作成
        agent_pool = await get_agent_pool()
        agent_manager = OptimizedAgentManager(agent_pool)
        
        # メッセージハンドラーを作成
        message_handler = OptimizedLineMessageHandler(agent_manager, None)
        await message_handler.initialize()
        
        # 基本機能テスト
        print("🔧 基本機能テスト中...")
        
        # セッション管理テスト
        user_id = "test_message_user"
        message_handler._initialize_user_session(user_id, "テストユーザー")
        
        # レート制限テスト
        rate_limit_ok = message_handler._check_rate_limit(user_id)
        print(f"✅ レート制限チェック: {'OK' if rate_limit_ok else 'NG'}")
        
        # メッセージ検証テスト
        valid_message = message_handler._validate_message("こんにちは")
        invalid_message = message_handler._validate_message("")
        print(f"✅ メッセージ検証: 有効={valid_message}, 無効={invalid_message}")
        
        # キャッシュテスト
        test_response = "テストレスポンス"
        message_handler._cache_response(user_id, "テストメッセージ", test_response)
        cached_response = message_handler._get_cached_response(user_id, "テストメッセージ")
        print(f"✅ キャッシュテスト: {'OK' if cached_response == test_response else 'NG'}")
        
        # 統計情報を取得
        stats = message_handler.get_processing_stats()
        print(f"📊 メッセージハンドラー統計: {stats}")
        
        # クリーンアップ
        await message_handler.shutdown()
        
        return True
        
    except Exception as e:
        print(f"❌ メッセージハンドラーテストエラー: {e}")
        return False


async def test_error_handling():
    """エラーハンドリングのテスト"""
    print("\n🚨 エラーハンドリングテスト")
    print("-" * 40)
    
    try:
        # カスタム例外のテスト
        from agri_ai.exceptions import DatabaseQueryError, AgentProcessingError
        
        # エラーハンドリングデコレータのテスト
        @error_handler.handle_async_error("test operation", print, return_error_message=True)
        async def test_function():
            raise DatabaseQueryError("テストエラー")
        
        result = await test_function()
        print(f"✅ エラーハンドリング結果: {result}")
        
        # エラーレスポンス作成テスト
        error_response = error_handler.create_error_response(
            AgentProcessingError("テスト処理エラー"), 
            "test_operation", 
            print
        )
        print(f"✅ エラーレスポンス作成: {error_response}")
        
        return True
        
    except Exception as e:
        print(f"❌ エラーハンドリングテストエラー: {e}")
        return False


async def test_configuration():
    """設定管理のテスト"""
    print("\n⚙️ 設定管理テスト")
    print("-" * 40)
    
    try:
        # 設定を取得
        settings = get_settings()
        
        # 設定プロパティのテスト
        print(f"✅ 環境: {settings.environment}")
        print(f"✅ デバッグモード: {settings.debug}")
        print(f"✅ 本番環境: {settings.is_production}")
        print(f"✅ LINE Bot有効: {settings.is_line_bot_enabled}")
        
        # AIモデル設定のテスト
        ai_config = settings.get_ai_model_config()
        print(f"✅ AIモデル設定: {ai_config}")
        
        return True
        
    except Exception as e:
        print(f"❌ 設定管理テストエラー: {e}")
        return False


async def performance_test():
    """パフォーマンステスト"""
    print("\n⚡ パフォーマンステスト")
    print("-" * 40)
    
    try:
        # データベースプールを取得
        db_pool = await get_database_pool()
        optimized_db = OptimizedAgriDatabase(db_pool)
        
        # エージェントプールを取得
        agent_pool = await get_agent_pool()
        agent_manager = OptimizedAgentManager(agent_pool)
        
        # 並列処理テスト
        print("🔥 並列処理テスト中...")
        
        async def process_message(user_id: str, message: str):
            start_time = time.time()
            response = await agent_manager.process_user_message(user_id, message)
            return time.time() - start_time
        
        # 10並列でメッセージ処理
        tasks = []
        for i in range(10):
            user_id = f"perf_user_{i}"
            message = f"テストメッセージ {i}"
            task = process_message(user_id, message)
            tasks.append(task)
        
        start_time = time.time()
        processing_times = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        print(f"✅ 10並列処理完了: {total_time:.2f}s")
        print(f"📊 平均処理時間: {sum(processing_times) / len(processing_times):.2f}s")
        print(f"📊 最大処理時間: {max(processing_times):.2f}s")
        print(f"📊 最小処理時間: {min(processing_times):.2f}s")
        
        # プール統計を取得
        pool_stats = agent_pool.get_pool_stats()
        print(f"📊 プール統計: {pool_stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ パフォーマンステストエラー: {e}")
        return False


async def main():
    """メイン関数"""
    print("🚀 リファクタリングされたシステムのテスト開始")
    print("=" * 80)
    
    # テスト実行
    tests = [
        ("設定管理", test_configuration),
        ("エラーハンドリング", test_error_handling),
        ("データベースプール", test_database_pool),
        ("エージェントプール", test_agent_pool),
        ("エージェントマネージャー", test_optimized_agent_manager),
        ("メッセージハンドラー", test_message_handler),
        ("パフォーマンス", performance_test),
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
        print("\n🚀 リファクタリング完了！")
        print("主な改善点:")
        print("- エラーハンドリングの統一化")
        print("- データベースコネクションプールとキャッシュ")
        print("- エージェントプールとライフサイクル管理")
        print("- メッセージ処理の最適化（キュー、レート制限、キャッシュ）")
        print("- 包括的な統計とモニタリング")
        print("- 型安全性の向上")
    else:
        print("⚠️ いくつかのテストが失敗しました。")
    
    # クリーンアップ
    print("\n🧹 クリーンアップ中...")
    await shutdown_agent_pool()
    await close_database_pool()
    
    print("🏁 テスト完了")


if __name__ == "__main__":
    asyncio.run(main())