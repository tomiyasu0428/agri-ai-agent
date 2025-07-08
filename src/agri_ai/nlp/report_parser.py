"""
作業報告の自然言語解析機能
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from .agricultural_glossary import AgriculturalGlossary

logger = logging.getLogger(__name__)


@dataclass
class ParsedWorkReport:
    """解析された作業報告データ"""
    task_name: Optional[str] = None
    field_name: Optional[str] = None
    crop_name: Optional[str] = None
    worker_name: Optional[str] = None
    completion_status: Optional[str] = None
    work_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    materials_used: List[Dict[str, Any]] = None
    quantity_applied: Optional[str] = None
    weather_condition: Optional[str] = None
    notes: Optional[str] = None
    next_task_suggestion: Optional[str] = None
    confidence_score: float = 0.0
    
    def __post_init__(self):
        if self.materials_used is None:
            self.materials_used = []


class WorkReportParser:
    """作業報告の自然言語を構造化データに変換するクラス"""
    
    def __init__(self):
        self.glossary = AgriculturalGlossary()
        
        # 報告パターンの定義
        self.report_patterns = {
            "completion": [
                r"(.+?)(?:を|の)?(?:完了|終了|終わり|できた|やった|実施した|行った)",
                r"(.+?)(?:が|は)?(?:完了|終了|終わり|できた|やった|実施した|行った)",
                r"(.+?)(?:しました|した|完了しました)"
            ],
            "field_work": [
                r"(.+?)(?:圃場|畑|ハウス|で)(.+?)(?:を|の)?(.+?)(?:完了|実施|行った)",
                r"(.+?)(?:の|で)(.+?)(?:作業|を|の)(.+?)(?:完了|実施|行った)"
            ],
            "material_usage": [
                r"(.+?)(?:を|に)(.+?)(?:散布|使用|撒いた|かけた)",
                r"(.+?)(?:で|に)(.+?)(?:を|の)(.+?)(?:散布|使用|撒いた|かけた)"
            ],
            "time_info": [
                r"(\d{1,2}:\d{2})\s*(?:から|より)\s*(\d{1,2}:\d{2})\s*(?:まで|迄)",
                r"(\d{1,2}:\d{2})\s*(?:～|〜|−|ー)\s*(\d{1,2}:\d{2})",
                r"(\d{1,2}時\d{1,2}分)\s*(?:から|より)\s*(\d{1,2}時\d{1,2}分)\s*(?:まで|迄)"
            ],
            "weather": [
                r"(?:天気|天候|気候)(?:は|:)?(.+?)(?:でした|だった|です|だ)",
                r"(.+?)(?:でした|だった|です|だ)(?:ので|から|が、)"
            ]
        }
        
        # 文脈キーワード
        self.context_keywords = {
            "urgency": ["急いで", "至急", "すぐに", "早急に", "緊急"],
            "difficulty": ["難しい", "困難", "大変", "苦労", "問題"],
            "quality": ["良い", "悪い", "問題ない", "順調", "うまく"],
            "weather_concern": ["雨", "風", "暑い", "寒い", "曇り", "晴れ"]
        }
        
        # 日付パターン
        self.date_patterns = [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})日?",
            r"(\d{1,2})[月/-](\d{1,2})日?",
            r"今日|きょう|本日",
            r"昨日|きのう",
            r"明日|あした|あす"
        ]
    
    def parse_report(self, text: str, context: Optional[Dict[str, Any]] = None) -> ParsedWorkReport:
        """作業報告テキストを解析して構造化データに変換"""
        # 前処理
        normalized_text = self.glossary.comprehensive_normalize(text)
        
        # 基本情報の抽出
        report = ParsedWorkReport()
        
        # 作業名の抽出
        report.task_name = self._extract_task_name(normalized_text)
        
        # 圃場名の抽出
        report.field_name = self._extract_field_name(normalized_text)
        
        # 作物名の抽出
        report.crop_name = self._extract_crop_name(normalized_text)
        
        # 完了ステータスの抽出
        report.completion_status = self._extract_completion_status(normalized_text)
        
        # 日付・時間の抽出
        report.work_date = self._extract_date(normalized_text, context)
        report.start_time, report.end_time = self._extract_time_range(normalized_text)
        
        # 使用資材の抽出
        report.materials_used = self._extract_materials(normalized_text)
        
        # 数量情報の抽出
        report.quantity_applied = self._extract_quantity(normalized_text)
        
        # 天候情報の抽出
        report.weather_condition = self._extract_weather(normalized_text)
        
        # 備考・メモの抽出
        report.notes = self._extract_notes(normalized_text)
        
        # 次回作業提案の抽出
        report.next_task_suggestion = self._extract_next_task_suggestion(normalized_text)
        
        # 信頼度スコアの計算
        report.confidence_score = self._calculate_confidence_score(report, normalized_text)
        
        logger.info(f"Parsed report with confidence {report.confidence_score:.2f}")
        return report
    
    def _extract_task_name(self, text: str) -> Optional[str]:
        """作業名を抽出"""
        # 完了パターンから作業名を抽出
        for pattern in self.report_patterns["completion"]:
            match = re.search(pattern, text)
            if match:
                task_candidate = match.group(1).strip()
                normalized_task = self.glossary.normalize_task_name(task_candidate)
                if normalized_task != task_candidate:
                    return normalized_task
                return task_candidate
        
        # 直接的な作業名を検索
        for task_name in self.glossary.task_synonyms.keys():
            if task_name in text:
                return task_name
        
        return None
    
    def _extract_field_name(self, text: str) -> Optional[str]:
        """圃場名を抽出"""
        return self.glossary.extract_field_name(text)
    
    def _extract_crop_name(self, text: str) -> Optional[str]:
        """作物名を抽出"""
        for crop_name in self.glossary.crop_synonyms.keys():
            if crop_name in text:
                return crop_name
        
        # 作物名の候補を検索
        for crop_name, synonyms in self.glossary.crop_synonyms.items():
            for synonym in synonyms:
                if synonym in text.lower():
                    return crop_name
        
        return None
    
    def _extract_completion_status(self, text: str) -> Optional[str]:
        """完了ステータスを抽出"""
        completion_indicators = ["完了", "終了", "終わり", "できた", "やった", "実施した", "行った"]
        pending_indicators = ["未完了", "未実施", "未着手", "途中", "継続中"]
        
        for indicator in completion_indicators:
            if indicator in text:
                return "完了"
        
        for indicator in pending_indicators:
            if indicator in text:
                return "未完了"
        
        return None
    
    def _extract_date(self, text: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """日付を抽出"""
        today = datetime.now()
        
        # 相対日付の処理
        if any(word in text for word in ["今日", "きょう", "本日"]):
            return today.strftime("%Y-%m-%d")
        elif any(word in text for word in ["昨日", "きのう"]):
            return (today - timedelta(days=1)).strftime("%Y-%m-%d")
        elif any(word in text for word in ["明日", "あした", "あす"]):
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 具体的な日付パターン
        for pattern in self.date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:  # 年月日
                        year, month, day = groups
                        return f"{year}-{int(month):02d}-{int(day):02d}"
                    elif len(groups) == 2:  # 月日（今年として扱う）
                        month, day = groups
                        return f"{today.year}-{int(month):02d}-{int(day):02d}"
                except:
                    continue
        
        # コンテキストから日付を推測
        if context and "default_date" in context:
            return context["default_date"]
        
        return None
    
    def _extract_time_range(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """時間範囲を抽出"""
        for pattern in self.report_patterns["time_info"]:
            match = re.search(pattern, text)
            if match:
                start_time = self.glossary.normalize_time(match.group(1))
                end_time = self.glossary.normalize_time(match.group(2))
                return start_time, end_time
        
        return None, None
    
    def _extract_materials(self, text: str) -> List[Dict[str, Any]]:
        """使用資材を抽出"""
        materials = []
        
        # 資材使用パターンを検索
        for pattern in self.report_patterns["material_usage"]:
            match = re.search(pattern, text)
            if match:
                material_name = match.group(1).strip()
                normalized_material = self.glossary.normalize_material_name(material_name)
                
                # 希釈倍率の検出
                dilution_match = re.search(r"(\d+)\s*倍", text)
                dilution = dilution_match.group(1) + "倍" if dilution_match else None
                
                materials.append({
                    "name": normalized_material,
                    "original_name": material_name,
                    "dilution": dilution
                })
        
        return materials
    
    def _extract_quantity(self, text: str) -> Optional[str]:
        """数量情報を抽出"""
        quantities = self.glossary.extract_quantities(text)
        if quantities:
            return quantities[0]["normalized"]
        return None
    
    def _extract_weather(self, text: str) -> Optional[str]:
        """天候情報を抽出"""
        weather_keywords = ["晴れ", "曇り", "雨", "雪", "風", "暑い", "寒い", "湿度", "乾燥"]
        
        for keyword in weather_keywords:
            if keyword in text:
                return keyword
        
        # 天候パターンを検索
        for pattern in self.report_patterns["weather"]:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_notes(self, text: str) -> Optional[str]:
        """備考・メモを抽出"""
        # 特定のキーワード後のテキストを備考として抽出
        note_keywords = ["備考", "メモ", "注意", "問題", "課題", "その他"]
        
        for keyword in note_keywords:
            pattern = f"{keyword}[：:]\\s*(.+)"
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        # 文脈から重要な情報を抽出
        context_info = []
        for category, keywords in self.context_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    context_info.append(f"{category}: {keyword}")
        
        if context_info:
            return "; ".join(context_info)
        
        return None
    
    def _extract_next_task_suggestion(self, text: str) -> Optional[str]:
        """次回作業提案を抽出"""
        suggestion_patterns = [
            r"次(?:回|に)(?:は|の)?(.+?)(?:が|を|は)(?:必要|やる|する|実施)",
            r"今度(.+?)(?:が|を|は)(?:必要|やる|する|実施)",
            r"(?:次|今度)(.+?)(?:してください|した方がよい|すべき)"
        ]
        
        for pattern in suggestion_patterns:
            match = re.search(pattern, text)
            if match:
                suggestion = match.group(1).strip()
                return self.glossary.normalize_task_name(suggestion)
        
        return None
    
    def _calculate_confidence_score(self, report: ParsedWorkReport, text: str) -> float:
        """信頼度スコアを計算"""
        score = 0.0
        max_score = 10.0
        
        # 基本情報の存在チェック
        if report.task_name:
            score += 2.0
        if report.field_name:
            score += 1.5
        if report.completion_status:
            score += 1.5
        if report.work_date:
            score += 1.0
        if report.materials_used:
            score += 1.0
        if report.quantity_applied:
            score += 1.0
        if report.weather_condition:
            score += 0.5
        if report.notes:
            score += 0.5
        
        # テキストの長さと構造化の程度
        if len(text) > 50:
            score += 1.0
        
        # 正規化された用語の使用
        normalized_terms = 0
        for term in text.split():
            if (self.glossary.normalize_crop_name(term) != term or
                self.glossary.normalize_task_name(term) != term or
                self.glossary.normalize_material_name(term) != term):
                normalized_terms += 1
        
        if normalized_terms > 0:
            score += min(normalized_terms * 0.2, 1.0)
        
        return min(score / max_score, 1.0)
    
    def validate_report(self, report: ParsedWorkReport) -> Dict[str, List[str]]:
        """解析結果の検証"""
        issues = {
            "warnings": [],
            "errors": [],
            "suggestions": []
        }
        
        # 必須フィールドのチェック
        if not report.task_name:
            issues["errors"].append("作業名が特定できませんでした")
        
        if not report.field_name:
            issues["warnings"].append("圃場名が特定できませんでした")
        
        if not report.completion_status:
            issues["warnings"].append("完了ステータスが不明です")
        
        # 論理的整合性のチェック
        if report.start_time and report.end_time:
            try:
                start = datetime.strptime(report.start_time, "%H:%M")
                end = datetime.strptime(report.end_time, "%H:%M")
                if start >= end:
                    issues["warnings"].append("開始時刻が終了時刻より遅いです")
            except:
                issues["warnings"].append("時刻の形式が正しくありません")
        
        # 改善提案
        if report.confidence_score < 0.7:
            issues["suggestions"].append("より詳細な情報を提供してください")
        
        if not report.materials_used and report.task_name in ["防除", "施肥"]:
            issues["suggestions"].append("使用した資材を明記してください")
        
        return issues
    
    def format_report_summary(self, report: ParsedWorkReport) -> str:
        """解析結果の要約を生成"""
        summary_parts = []
        
        if report.task_name:
            summary_parts.append(f"作業: {report.task_name}")
        
        if report.field_name:
            summary_parts.append(f"圃場: {report.field_name}")
        
        if report.completion_status:
            summary_parts.append(f"状態: {report.completion_status}")
        
        if report.work_date:
            summary_parts.append(f"日付: {report.work_date}")
        
        if report.start_time and report.end_time:
            summary_parts.append(f"時間: {report.start_time} - {report.end_time}")
        
        if report.materials_used:
            materials = ", ".join([mat["name"] for mat in report.materials_used])
            summary_parts.append(f"使用資材: {materials}")
        
        if report.quantity_applied:
            summary_parts.append(f"数量: {report.quantity_applied}")
        
        summary = " | ".join(summary_parts)
        summary += f" (信頼度: {report.confidence_score:.1%})"
        
        return summary