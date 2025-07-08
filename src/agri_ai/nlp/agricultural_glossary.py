"""
農業専門用語の辞書と正規化機能
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AgriculturalGlossary:
    """農業専門用語の辞書と正規化を行うクラス"""
    
    def __init__(self):
        self.crop_synonyms = {
            # 作物の同義語
            "大豆": ["だいず", "ダイズ", "soybean", "soybeans"],
            "ブロッコリー": ["ブロッコリ", "broccoli"],
            "キャベツ": ["cabbage", "きゃべつ"],
            "トマト": ["tomato", "とまと"],
            "きゅうり": ["cucumber", "キュウリ", "胡瓜"],
            "なす": ["eggplant", "ナス", "茄子"],
            "ピーマン": ["pepper", "ピーマン"],
            "レタス": ["lettuce", "れたす"]
        }
        
        self.task_synonyms = {
            # 作業の同義語
            "播種": ["はしゅ", "種まき", "タネまき", "seeding", "sowing"],
            "定植": ["ていしょく", "植え付け", "transplanting"],
            "防除": ["ぼうじょ", "農薬散布", "薬剤散布", "pest control"],
            "収穫": ["しゅうかく", "harvest", "harvesting"],
            "施肥": ["せひ", "肥料やり", "fertilizing"],
            "除草": ["じょそう", "草取り", "weeding"],
            "畝立て": ["うねたて", "畝作り", "ridging"],
            "耕耘": ["こううん", "耕起", "tillage"],
            "灌水": ["かんすい", "水やり", "irrigation"],
            "剪定": ["せんてい", "枝切り", "pruning"]
        }
        
        self.material_synonyms = {
            # 資材の同義語
            "農薬": ["のうやく", "薬剤", "pesticide", "chemical"],
            "肥料": ["ひりょう", "fertilizer"],
            "種子": ["しゅし", "タネ", "seed", "seeds"],
            "苗": ["なえ", "seedling", "seedlings"],
            "マルチ": ["マルチフィルム", "mulch", "mulching"]
        }
        
        self.field_synonyms = {
            # 圃場の同義語パターン
            "圃場": ["ほじょう", "畑", "field", "圃場"],
            "ハウス": ["温室", "greenhouse", "house"]
        }
        
        self.status_synonyms = {
            # ステータスの同義語
            "完了": ["かんりょう", "終了", "完成", "done", "finished", "completed"],
            "未完了": ["みかんりょう", "未実施", "未着手", "todo", "pending"],
            "進行中": ["しんこうちゅう", "作業中", "実施中", "in progress", "working"]
        }
        
        # 数量・単位の正規化
        self.unit_patterns = {
            "面積": [
                (r"(\d+(?:\.\d+)?)\s*(?:ha|ヘクタール|ヘクター)", r"\1 ha"),
                (r"(\d+(?:\.\d+)?)\s*(?:a|アール)", r"\1 a"),
                (r"(\d+(?:\.\d+)?)\s*(?:㎡|平方メートル|平米)", r"\1 ㎡")
            ],
            "容量": [
                (r"(\d+(?:\.\d+)?)\s*(?:L|リットル|ℓ)", r"\1 L"),
                (r"(\d+(?:\.\d+)?)\s*(?:ml|mL|ミリリットル)", r"\1 ml"),
                (r"(\d+(?:\.\d+)?)\s*(?:cc)", r"\1 cc")
            ],
            "重量": [
                (r"(\d+(?:\.\d+)?)\s*(?:kg|キログラム|キロ)", r"\1 kg"),
                (r"(\d+(?:\.\d+)?)\s*(?:g|グラム)", r"\1 g"),
                (r"(\d+(?:\.\d+)?)\s*(?:t|トン)", r"\1 t")
            ]
        }
        
        # 時間・日付の正規化
        self.time_patterns = [
            (r"(\d{1,2})\s*時\s*(\d{1,2})\s*分", r"\1:\2"),
            (r"(\d{1,2})\s*時", r"\1:00"),
            (r"午前\s*(\d{1,2}:\d{2})", r"\1 AM"),
            (r"午後\s*(\d{1,2}:\d{2})", r"\1 PM")
        ]
        
        # 農薬希釈倍率の正規化
        self.dilution_patterns = [
            (r"(\d+)\s*倍", r"\1倍"),
            (r"(\d+)\s*(?:倍希釈|倍に希釈)", r"\1倍"),
            (r"(\d+)\s*(?:分の1|/1)", r"\1倍")
        ]
    
    def normalize_crop_name(self, text: str) -> str:
        """作物名を正規化する"""
        text = text.strip()
        
        for standard_name, synonyms in self.crop_synonyms.items():
            for synonym in synonyms:
                if synonym in text.lower():
                    return standard_name
        
        return text
    
    def normalize_task_name(self, text: str) -> str:
        """作業名を正規化する"""
        text = text.strip()
        
        for standard_name, synonyms in self.task_synonyms.items():
            for synonym in synonyms:
                if synonym in text.lower():
                    return standard_name
        
        return text
    
    def normalize_material_name(self, text: str) -> str:
        """資材名を正規化する"""
        text = text.strip()
        
        for standard_name, synonyms in self.material_synonyms.items():
            for synonym in synonyms:
                if synonym in text.lower():
                    return standard_name
        
        return text
    
    def normalize_status(self, text: str) -> str:
        """ステータスを正規化する"""
        text = text.strip()
        
        for standard_status, synonyms in self.status_synonyms.items():
            for synonym in synonyms:
                if synonym in text.lower():
                    return standard_status
        
        return text
    
    def normalize_units(self, text: str) -> str:
        """単位を正規化する"""
        normalized_text = text
        
        for category, patterns in self.unit_patterns.items():
            for pattern, replacement in patterns:
                normalized_text = re.sub(pattern, replacement, normalized_text, flags=re.IGNORECASE)
        
        return normalized_text
    
    def normalize_time(self, text: str) -> str:
        """時間表記を正規化する"""
        normalized_text = text
        
        for pattern, replacement in self.time_patterns:
            normalized_text = re.sub(pattern, replacement, normalized_text, flags=re.IGNORECASE)
        
        return normalized_text
    
    def normalize_dilution(self, text: str) -> str:
        """希釈倍率を正規化する"""
        normalized_text = text
        
        for pattern, replacement in self.dilution_patterns:
            normalized_text = re.sub(pattern, replacement, normalized_text, flags=re.IGNORECASE)
        
        return normalized_text
    
    def extract_field_name(self, text: str) -> Optional[str]:
        """テキストから圃場名を抽出する"""
        # 既知の圃場名パターンを検索
        field_patterns = [
            r"([^\s]+(?:圃場|畑|ハウス|温室))",
            r"([A-Z]\d+)",  # F14, A1 などの形式
            r"([^\s]+(?:家裏|家前|横|北|南|東|西))",  # 石谷さん横 などの形式
            r"(鵡川[^\s]*)",  # 鵡川関連
            r"(豊糠[^\s]*)"   # 豊糠関連
        ]
        
        for pattern in field_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_quantities(self, text: str) -> List[Dict[str, str]]:
        """テキストから数量情報を抽出する"""
        quantities = []
        
        # 数量パターンを検索
        quantity_patterns = [
            r"(\d+(?:\.\d+)?)\s*(ha|ヘクタール|a|アール|㎡|平方メートル|平米)",
            r"(\d+(?:\.\d+)?)\s*(L|リットル|ml|mL|ミリリットル|cc)",
            r"(\d+(?:\.\d+)?)\s*(kg|キログラム|キロ|g|グラム|t|トン)",
            r"(\d+)\s*(倍|倍希釈)"
        ]
        
        for pattern in quantity_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                quantities.append({
                    "value": match.group(1),
                    "unit": match.group(2),
                    "normalized": self.normalize_units(match.group(0))
                })
        
        return quantities
    
    def comprehensive_normalize(self, text: str) -> str:
        """包括的な正規化を実行する"""
        # 基本的な正規化
        normalized = text.strip()
        
        # 各種正規化を適用
        normalized = self.normalize_units(normalized)
        normalized = self.normalize_time(normalized)
        normalized = self.normalize_dilution(normalized)
        
        # 用語の正規化
        for word in normalized.split():
            crop = self.normalize_crop_name(word)
            if crop != word:
                normalized = normalized.replace(word, crop)
            
            task = self.normalize_task_name(word)
            if task != word:
                normalized = normalized.replace(word, task)
            
            material = self.normalize_material_name(word)
            if material != word:
                normalized = normalized.replace(word, material)
        
        return normalized
    
    def get_suggestions(self, partial_text: str) -> List[str]:
        """部分的なテキストに対する候補を提供する"""
        suggestions = []
        partial_lower = partial_text.lower()
        
        # 作物名の候補
        for crop, synonyms in self.crop_synonyms.items():
            if any(partial_lower in syn.lower() for syn in synonyms) or partial_lower in crop.lower():
                suggestions.append(crop)
        
        # 作業名の候補
        for task, synonyms in self.task_synonyms.items():
            if any(partial_lower in syn.lower() for syn in synonyms) or partial_lower in task.lower():
                suggestions.append(task)
        
        # 資材名の候補
        for material, synonyms in self.material_synonyms.items():
            if any(partial_lower in syn.lower() for syn in synonyms) or partial_lower in material.lower():
                suggestions.append(material)
        
        return list(set(suggestions))