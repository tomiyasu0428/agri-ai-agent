#!/usr/bin/env python3
"""
統合されたAIエージェントのテストスクリプト
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agri_ai.core.agent import AgriAIAgent
from agri_ai.core.database import MongoDBClient, AgriDatabase


async def test_integrated_agent():
    """統合されたエージェントのテスト"""
    print("🤖 統合エージェントテスト開始")
    print("=" * 60)
    
    try:
        # MongoDB接続
        print("📊 MongoDB接続中...")
        mongo_client = MongoDBClient()
        await mongo_client.connect()
        
        # データベースオブジェクト作成
        agri_db = AgriDatabase(mongo_client)
        
        # エージェント作成
        print("🧠 AIエージェント初期化中...")
        agent = AgriAIAgent(agri_db)
        
        # テストユーザー
        user_id = "test_farmer_001"
        
        # テストシナリオ
        test_scenarios = [
            {
                "scenario": "初回挨拶",
                "message": "こんにちは！今日の作業を確認したいです。",
                "expected_features": ["挨拶応答", "文脈初期化"]
            },
            {
                "scenario": "作業確認",
                "message": "F14での大豆の防除作業はどうすればいいですか？",
                "expected_features": ["文脈推測", "データベース検索", "作業提案"]
            },
            {
                "scenario": "作業報告",
                "message": "F14で大豆の防除を完了しました。クプロシールドを1000倍希釈で散布。9:00から11:30まで作業。",
                "expected_features": ["作業報告解析", "データ抽出", "文脈更新"]
            },
            {
                "scenario": "省略表現",
                "message": "それの次回作業はいつですか？",
                "expected_features": ["省略表現解決", "文脈活用"]
            },
            {
                "scenario": "状況確認",
                "message": "今日の作業状況を教えてください",
                "expected_features": ["履歴参照", "状況まとめ"]
            }
        ]
        
        # 各シナリオを実行
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n🎬 シナリオ {i}: {scenario['scenario']}")
            print("-" * 40)
            print(f"💬 入力: {scenario['message']}")
            
            # エージェントに問い合わせ
            response = await agent.process_message(scenario['message'], user_id)
            print(f"🤖 応答: {response}")
            
            # 期待される機能の確認
            print(f"✅ 期待される機能: {', '.join(scenario['expected_features'])}")
            
            # 文脈の確認
            context_summary = agent.context_manager.get_context_summary(user_id)
            print(f"📝 現在の文脈: {context_summary}")
            
            # 少し待機
            await asyncio.sleep(1)
        
        # 統計情報の表示
        print(f"\n📊 統計情報:")
        context_stats = agent.context_manager.get_statistics()
        print(f"  - 総文脈数: {context_stats['total_contexts']}")
        print(f"  - アクティブ文脈数: {context_stats['active_contexts_24h']}")
        print(f"  - 平均質問数: {context_stats['average_questions_per_user']}")
        print(f"  - 平均作業履歴数: {context_stats['average_work_history_per_user']}")
        
        # 文脈の詳細表示
        print(f"\n🔍 文脈詳細:")
        context = agent.context_manager.get_context(user_id)
        print(f"  - 現在のタスク: {context.current_task}")
        print(f"  - 現在の圃場: {context.current_field}")
        print(f"  - 現在の作物: {context.current_crop}")
        print(f"  - 作業日: {context.working_date}")
        print(f"  - 質問履歴数: {len(context.recent_questions)}")
        print(f"  - 作業履歴数: {len(context.work_history)}")
        
        # 提案される質問
        print(f"\n💡 提案される質問:")
        suggestions = agent.context_manager.suggest_next_questions(user_id)
        for j, suggestion in enumerate(suggestions, 1):
            print(f"  {j}. {suggestion}")
        
        print(f"\n✅ 統合エージェントテスト完了！")
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 接続を閉じる
        if 'mongo_client' in locals():
            await mongo_client.disconnect()


async def test_nlp_agent_integration():
    """NLP機能とエージェントの統合テスト"""
    print("\n🔬 NLP統合テスト開始")
    print("=" * 60)
    
    try:
        # MongoDB接続
        mongo_client = MongoDBClient()
        await mongo_client.connect()
        agri_db = AgriDatabase(mongo_client)
        agent = AgriAIAgent(agri_db)
        
        user_id = "nlp_test_user"
        
        # NLP機能の詳細テスト
        nlp_tests = [
            {
                "name": "自然な作業報告",
                "input": "今日はF14で大豆の防除作業やりました。朝9時から11時半まで。農薬はクプロシールド使って1000倍で薄めました。天気は晴れで風も弱かったです。",
                "expected_extractions": ["作業名", "圃場名", "作物名", "時間", "資材", "天候"]
            },
            {
                "name": "短縮表現",
                "input": "F14防除完了",
                "expected_extractions": ["作業名", "圃場名", "完了状況"]
            },
            {
                "name": "曖昧な表現",
                "input": "さっきの作業、うまくいきました",
                "expected_extractions": ["文脈参照", "完了状況"]
            },
            {
                "name": "質問形式",
                "input": "明日はどの圃場で何をすればいいですか？",
                "expected_extractions": ["日付推測", "作業提案"]
            }
        ]
        
        for test in nlp_tests:
            print(f"\n🧪 テスト: {test['name']}")
            print(f"入力: {test['input']}")
            
            # エージェントの応答を取得
            response = await agent.process_message(test['input'], user_id)
            print(f"応答: {response}")
            
            # 期待される抽出項目
            print(f"期待される抽出: {', '.join(test['expected_extractions'])}")
            
            # 文脈更新の確認
            context = agent.context_manager.get_context(user_id)
            print(f"文脈更新: タスク={context.current_task}, 圃場={context.current_field}")
        
        print(f"\n✅ NLP統合テスト完了！")
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if 'mongo_client' in locals():
            await mongo_client.disconnect()


async def main():
    """メイン関数"""
    print("🚀 統合エージェントテスト開始")
    
    # 基本的な統合テスト
    await test_integrated_agent()
    
    # NLP機能の詳細テスト
    await test_nlp_agent_integration()
    
    print("\n🎉 全てのテストが完了しました！")


if __name__ == "__main__":
    asyncio.run(main())