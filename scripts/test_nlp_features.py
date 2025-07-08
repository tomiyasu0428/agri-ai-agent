#!/usr/bin/env python3
"""
自然言語処理機能のテストスクリプト
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agri_ai.nlp.agricultural_glossary import AgriculturalGlossary
from agri_ai.nlp.report_parser import WorkReportParser
from agri_ai.nlp.context_manager import ContextManager


def test_agricultural_glossary():
    """農業用語辞書のテスト"""
    print("=== 農業用語辞書テスト ===")
    glossary = AgriculturalGlossary()
    
    # 作物名の正規化テスト
    print("\n🌾 作物名の正規化:")
    crop_tests = ["だいず", "ブロッコリ", "トマト", "soybean"]
    for crop in crop_tests:
        normalized = glossary.normalize_crop_name(crop)
        print(f"  {crop} → {normalized}")
    
    # 作業名の正規化テスト  
    print("\n🚜 作業名の正規化:")
    task_tests = ["種まき", "薬剤散布", "weeding", "収穫"]
    for task in task_tests:
        normalized = glossary.normalize_task_name(task)
        print(f"  {task} → {normalized}")
    
    # 単位の正規化テスト
    print("\n📏 単位の正規化:")
    unit_tests = ["5.2ヘクタール", "100リットル", "50kg", "1000倍希釈"]
    for unit in unit_tests:
        normalized = glossary.normalize_units(unit)
        print(f"  {unit} → {normalized}")
    
    # 圃場名の抽出テスト
    print("\n🏡 圃場名の抽出:")
    field_tests = ["F14で防除しました", "石谷さん横の圃場", "鵡川家裏で作業"]
    for text in field_tests:
        field_name = glossary.extract_field_name(text)
        print(f"  '{text}' → {field_name}")
    
    # 包括的正規化テスト
    print("\n🔄 包括的正規化:")
    comprehensive_tests = [
        "だいずの種まきを5.2ヘクタールで完了しました",
        "ブロッコリに農薬を1000倍希釈で散布"
    ]
    for text in comprehensive_tests:
        normalized = glossary.comprehensive_normalize(text)
        print(f"  '{text}'\n  → '{normalized}'")


def test_report_parser():
    """作業報告解析のテスト"""
    print("\n=== 作業報告解析テスト ===")
    parser = WorkReportParser()
    
    # テスト用の作業報告
    test_reports = [
        "F14で大豆の防除を完了しました。クプロシールドを1000倍希釈で散布。9:00から11:30まで作業。天気は晴れでした。",
        "石谷さん横の圃場でブロッコリーの収穫をしました。今日の午前中に実施。",
        "鵡川家裏で播種作業を行いました。面積は2.5haです。",
        "畝立て作業を完了。明日は定植予定です。",
        "農薬散布を実施。希釈倍率は800倍。風が強かったので注意が必要。"
    ]
    
    for i, report_text in enumerate(test_reports, 1):
        print(f"\n📝 テスト報告 {i}:")
        print(f"入力: '{report_text}'")
        
        # 解析実行
        parsed = parser.parse_report(report_text)
        
        # 結果表示
        print(f"解析結果:")
        print(f"  作業名: {parsed.task_name}")
        print(f"  圃場名: {parsed.field_name}")
        print(f"  作物名: {parsed.crop_name}")
        print(f"  完了状況: {parsed.completion_status}")
        print(f"  作業日: {parsed.work_date}")
        print(f"  時間: {parsed.start_time} - {parsed.end_time}")
        print(f"  使用資材: {parsed.materials_used}")
        print(f"  数量: {parsed.quantity_applied}")
        print(f"  天候: {parsed.weather_condition}")
        print(f"  メモ: {parsed.notes}")
        print(f"  信頼度: {parsed.confidence_score:.2%}")
        
        # 要約表示
        summary = parser.format_report_summary(parsed)
        print(f"要約: {summary}")
        
        # 検証結果
        issues = parser.validate_report(parsed)
        if issues['errors']:
            print(f"エラー: {issues['errors']}")
        if issues['warnings']:
            print(f"警告: {issues['warnings']}")
        if issues['suggestions']:
            print(f"提案: {issues['suggestions']}")


def test_context_manager():
    """文脈管理のテスト"""
    print("\n=== 文脈管理テスト ===")
    context_manager = ContextManager()
    
    # テストユーザー
    user_id = "test_user_001"
    
    # 初期文脈の設定
    print(f"\n👤 ユーザー {user_id} の文脈管理:")
    context_manager.update_context(user_id, 
                                 current_task="防除",
                                 current_field="F14",
                                 current_crop="大豆",
                                 working_date="2025-07-08")
    
    # 文脈の取得
    context = context_manager.get_context(user_id)
    print(f"現在の文脈: {context_manager.get_context_summary(user_id)}")
    
    # 質問履歴の追加
    print(f"\n💬 質問履歴のテスト:")
    questions = [
        "今日のタスクは何ですか？",
        "F14の状況を教えてください",
        "防除の進捗はどうですか？",
        "それは完了しましたか？"
    ]
    
    for question in questions:
        context_manager.add_question_to_history(user_id, question)
        print(f"  追加: '{question}'")
    
    # 省略表現の解決テスト
    print(f"\n🔗 省略表現の解決:")
    ellipsis_tests = [
        "それは完了しましたか？",
        "あれの状況はどうですか？",
        "今日はどこで作業しますか？"
    ]
    
    for test_msg in ellipsis_tests:
        resolved = context_manager.resolve_ellipsis(user_id, test_msg)
        print(f"  '{test_msg}' → '{resolved}'")
    
    # 文脈推測テスト
    print(f"\n🤔 文脈推測:")
    inference_tests = [
        "播種作業はいつ行いますか？",
        "F15での作業を確認したい",
        "今日のブロッコリーの収穫について"
    ]
    
    for test_msg in inference_tests:
        inferred = context_manager.infer_context_from_message(user_id, test_msg)
        print(f"  '{test_msg}' → {inferred}")
    
    # 関連文脈の取得テスト
    print(f"\n🎯 関連文脈の取得:")
    relevance_tests = [
        "前回の作業はどうでしたか？",
        "どこで作業しますか？",
        "いつ実施予定ですか？"
    ]
    
    for test_msg in relevance_tests:
        relevant = context_manager.get_relevant_context(user_id, test_msg)
        print(f"  '{test_msg}' → {relevant}")
    
    # 次の質問提案
    print(f"\n💡 次の質問提案:")
    suggestions = context_manager.suggest_next_questions(user_id)
    for i, suggestion in enumerate(suggestions, 1):
        print(f"  {i}. {suggestion}")


def test_integrated_scenario():
    """統合シナリオのテスト"""
    print("\n=== 統合シナリオテスト ===")
    
    # 各モジュールの初期化
    glossary = AgriculturalGlossary()
    parser = WorkReportParser()
    context_manager = ContextManager()
    
    user_id = "farmer_tanaka"
    
    print(f"\n🎬 シナリオ: 田中さんの一日の作業")
    
    # シナリオ1: 朝の作業確認
    print(f"\n📅 朝の作業確認:")
    morning_query = "今日はF14で大豆の防除をやる予定です"
    
    # 文脈推測
    inferred_context = context_manager.infer_context_from_message(user_id, morning_query)
    print(f"推測された文脈: {inferred_context}")
    
    # 文脈更新
    context_manager.update_context(user_id, **inferred_context)
    context_manager.add_question_to_history(user_id, morning_query)
    
    # シナリオ2: 作業中の報告
    print(f"\n⏰ 作業中の報告:")
    work_report = "F14で防除作業を実施中。クプロシールドを1000倍で散布。9:00から開始。"
    
    # 報告解析
    parsed_report = parser.parse_report(work_report)
    print(f"解析結果: {parser.format_report_summary(parsed_report)}")
    
    # 作業履歴に追加
    work_info = {
        "task": parsed_report.task_name,
        "field": parsed_report.field_name,
        "status": "進行中",
        "materials": parsed_report.materials_used
    }
    context_manager.add_work_to_history(user_id, work_info)
    
    # シナリオ3: 完了報告
    print(f"\n✅ 完了報告:")
    completion_report = "それが完了しました。11:30に終了。天気は晴れでした。"
    
    # 省略表現解決
    resolved_report = context_manager.resolve_ellipsis(user_id, completion_report)
    print(f"解決後: '{resolved_report}'")
    
    # 完了報告解析
    parsed_completion = parser.parse_report(resolved_report)
    print(f"完了報告: {parser.format_report_summary(parsed_completion)}")
    
    # シナリオ4: 次の作業提案
    print(f"\n🔮 次の作業提案:")
    context = context_manager.get_context(user_id)
    suggestions = context_manager.suggest_next_questions(user_id)
    
    print(f"現在の文脈: {context_manager.get_context_summary(user_id)}")
    print(f"提案される質問:")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"  {i}. {suggestion}")


def main():
    """メイン関数"""
    print("🚀 農業AI自然言語処理機能テスト開始")
    print("=" * 60)
    
    try:
        # 各モジュールのテスト
        test_agricultural_glossary()
        test_report_parser()
        test_context_manager()
        test_integrated_scenario()
        
        print("\n" + "=" * 60)
        print("✅ すべてのテストが完了しました！")
        
    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 テスト終了")


if __name__ == "__main__":
    main()