"""
セクション分析・分割機能
改善提案シート内の複数セクションを自動検出・分割する
"""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import streamlit as st
from typing import List, Dict, Tuple, Any, Optional
import logging
from dataclasses import dataclass
import json

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SectionBounds:
    """セクション境界情報"""
    x: int
    y: int
    width: int
    height: int
    section_type: str  # 'header', 'content', 'example'
    confidence: float
    text_content: Optional[str] = None


@dataclass
class SectionInfo:
    """セクション情報"""
    id: str
    bounds: SectionBounds
    title: str
    content: str
    category: str  # '課題', '提案', '対象' など
    ocr_result: Optional[Dict[str, Any]] = None


class SectionAnalyzer:
    """
    改善提案シートのセクション分析・分割クラス
    """

    def __init__(self):
        """初期化"""
        self.sections: List[SectionInfo] = []
        self.image_height = 0
        self.image_width = 0

        # セクション検出パラメータ
        self.min_section_height = 50  # 最小セクション高さ
        self.horizontal_line_threshold = 0.7  # 水平線検出閾値
        self.text_density_threshold = 0.1  # テキスト密度閾値

        # カテゴリキーワード
        self.category_keywords = {
            '課題': ['課題', '問題', 'もんだい', 'かだい'],
            '提案': ['提案', '改善', 'ていあん', 'かいぜん', 'アイデア'],
            '対象': ['対象', 'たいしょう', '行政', '住民', 'ぎょうせい', 'じゅうみん'],
            '効果': ['効果', 'こうか', 'メリット', '利益'],
            '実現性': ['実現', 'じつげん', '可能', 'かのう', '実行']
        }

    def analyze_image_layout(self, image: Image.Image) -> List[SectionBounds]:
        """
        画像のレイアウトを解析してセクション境界を検出

        Args:
            image: PIL画像オブジェクト

        Returns:
            List[SectionBounds]: 検出されたセクション境界のリスト
        """
        try:
            # PIL画像をOpenCV形式に変換
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

            self.image_height, self.image_width = gray.shape

            # 水平線検出によるセクション分割
            horizontal_sections = self._detect_horizontal_sections(gray)

            # テキスト密度による分割補完
            density_sections = self._detect_text_density_sections(gray)

            # 結果をマージ
            merged_sections = self._merge_section_detections(horizontal_sections, density_sections)

            # セクション境界を作成
            section_bounds = []
            for i, (start_y, end_y) in enumerate(merged_sections):
                bounds = SectionBounds(
                    x=0,
                    y=start_y,
                    width=self.image_width,
                    height=end_y - start_y,
                    section_type='content',
                    confidence=0.8
                )
                section_bounds.append(bounds)

            logger.info(f"検出されたセクション数: {len(section_bounds)}")
            return section_bounds

        except Exception as e:
            logger.error(f"レイアウト解析エラー: {str(e)}")
            # フォールバック: 画像を等分割
            return self._fallback_equal_division(image)

    def _detect_horizontal_sections(self, gray_image: np.ndarray) -> List[Tuple[int, int]]:
        """
        水平線検出によるセクション分割

        Args:
            gray_image: グレースケール画像

        Returns:
            List[Tuple[int, int]]: (開始Y座標, 終了Y座標)のリスト
        """
        # 水平線検出
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines = cv2.morphologyEx(gray_image, cv2.MORPH_OPEN, horizontal_kernel)

        # 水平線の位置を取得
        horizontal_sum = np.sum(horizontal_lines, axis=1)
        line_positions = []

        for i, intensity in enumerate(horizontal_sum):
            if intensity > self.image_width * 255 * self.horizontal_line_threshold:
                line_positions.append(i)

        # 連続する線をグループ化
        if not line_positions:
            return [(0, self.image_height)]

        grouped_lines = []
        current_group = [line_positions[0]]

        for pos in line_positions[1:]:
            if pos - current_group[-1] <= 5:  # 5ピクセル以内は同じ線とみなす
                current_group.append(pos)
            else:
                grouped_lines.append(int(np.mean(current_group)))
                current_group = [pos]

        if current_group:
            grouped_lines.append(int(np.mean(current_group)))

        # セクション境界を作成
        sections = []
        start_y = 0

        for line_y in grouped_lines:
            if line_y - start_y > self.min_section_height:
                sections.append((start_y, line_y))
                start_y = line_y

        # 最後のセクション
        if self.image_height - start_y > self.min_section_height:
            sections.append((start_y, self.image_height))

        return sections

    def _detect_text_density_sections(self, gray_image: np.ndarray) -> List[Tuple[int, int]]:
        """
        テキスト密度によるセクション検出

        Args:
            gray_image: グレースケール画像

        Returns:
            List[Tuple[int, int]]: (開始Y座標, 終了Y座標)のリスト
        """
        # エッジ検出
        edges = cv2.Canny(gray_image, 50, 150)

        # 水平方向の密度を計算
        row_density = np.sum(edges, axis=1) / self.image_width

        # 密度の変化点を検出
        density_diff = np.diff(row_density)

        # 閾値を超える変化点を検出
        threshold = np.std(density_diff) * 2
        change_points = []

        for i, diff in enumerate(density_diff):
            if abs(diff) > threshold:
                change_points.append(i)

        # セクション境界を作成
        if not change_points:
            return [(0, self.image_height)]

        sections = []
        start_y = 0

        for point in change_points:
            if point - start_y > self.min_section_height:
                sections.append((start_y, point))
                start_y = point

        # 最後のセクション
        if self.image_height - start_y > self.min_section_height:
            sections.append((start_y, self.image_height))

        return sections

    def _merge_section_detections(self, horizontal_sections: List[Tuple[int, int]],
                                 density_sections: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """
        複数の検出結果をマージ

        Args:
            horizontal_sections: 水平線検出結果
            density_sections: 密度検出結果

        Returns:
            List[Tuple[int, int]]: マージされたセクション境界
        """
        # すべての境界点を収集
        all_boundaries = set()

        for start, end in horizontal_sections:
            all_boundaries.add(start)
            all_boundaries.add(end)

        for start, end in density_sections:
            all_boundaries.add(start)
            all_boundaries.add(end)

        # ソートして連続するセクションを作成
        sorted_boundaries = sorted(all_boundaries)

        merged_sections = []
        for i in range(len(sorted_boundaries) - 1):
            start = sorted_boundaries[i]
            end = sorted_boundaries[i + 1]

            if end - start > self.min_section_height:
                merged_sections.append((start, end))

        return merged_sections if merged_sections else [(0, self.image_height)]

    def _fallback_equal_division(self, image: Image.Image) -> List[SectionBounds]:
        """
        フォールバック: 画像を等分割

        Args:
            image: PIL画像オブジェクト

        Returns:
            List[SectionBounds]: 等分割されたセクション境界
        """
        height = image.height
        width = image.width

        # 4つのセクションに等分割（改善提案シートの一般的な構造）
        section_height = height // 4
        sections = []

        for i in range(4):
            start_y = i * section_height
            end_y = (i + 1) * section_height if i < 3 else height

            bounds = SectionBounds(
                x=0,
                y=start_y,
                width=width,
                height=end_y - start_y,
                section_type='content',
                confidence=0.5  # 低い信頼度
            )
            sections.append(bounds)

        return sections

    def extract_sections(self, image: Image.Image, section_bounds: List[SectionBounds]) -> List[Image.Image]:
        """
        セクション境界に基づいて画像を分割

        Args:
            image: 元画像
            section_bounds: セクション境界リスト

        Returns:
            List[Image.Image]: 分割された画像リスト
        """
        section_images = []

        for bounds in section_bounds:
            # 画像を切り出し
            section_image = image.crop((
                bounds.x,
                bounds.y,
                bounds.x + bounds.width,
                bounds.y + bounds.height
            ))
            section_images.append(section_image)

        return section_images

    def classify_section_content(self, ocr_text: str) -> str:
        """
        OCRテキストからセクションのカテゴリを分類

        Args:
            ocr_text: OCR結果テキスト

        Returns:
            str: 分類されたカテゴリ
        """
        if not ocr_text:
            return 'unknown'

        text_lower = ocr_text.lower()

        # カテゴリキーワードとのマッチング
        category_scores = {}

        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            category_scores[category] = score

        # 最高スコアのカテゴリを返す
        if category_scores and max(category_scores.values()) > 0:
            return max(category_scores, key=category_scores.get)

        return 'その他'

    def create_section_info(self, section_id: str, bounds: SectionBounds,
                           ocr_result: Dict[str, Any]) -> SectionInfo:
        """
        セクション情報を作成

        Args:
            section_id: セクションID
            bounds: セクション境界
            ocr_result: OCR結果

        Returns:
            SectionInfo: セクション情報
        """
        # OCRテキストを取得
        text_content = ""
        if ocr_result.get("success", False):
            if "text" in ocr_result:
                text_content = ocr_result["text"]
            elif "extracted_text" in ocr_result:
                text_content = ocr_result["extracted_text"]

        # カテゴリを分類
        category = self.classify_section_content(text_content)

        # タイトルを生成
        title = f"セクション {section_id} ({category})"

        return SectionInfo(
            id=section_id,
            bounds=bounds,
            title=title,
            content=text_content,
            category=category,
            ocr_result=ocr_result
        )

    def visualize_sections(self, image: Image.Image, section_bounds: List[SectionBounds]) -> Image.Image:
        """
        セクション境界を可視化

        Args:
            image: 元画像
            section_bounds: セクション境界リスト

        Returns:
            Image.Image: 境界が描画された画像
        """
        # 画像をコピー
        vis_image = image.copy()
        draw = ImageDraw.Draw(vis_image)

        # 色のリスト
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']

        for i, bounds in enumerate(section_bounds):
            color = colors[i % len(colors)]

            # 境界を描画
            draw.rectangle([
                bounds.x, bounds.y,
                bounds.x + bounds.width, bounds.y + bounds.height
            ], outline=color, width=3)

            # セクション番号を描画
            draw.text((bounds.x + 10, bounds.y + 10), f"Section {i+1}",
                     fill=color, stroke_width=2, stroke_fill='white')

        return vis_image

    def export_sections_data(self, sections: List[SectionInfo]) -> Dict[str, Any]:
        """
        セクションデータをエクスポート

        Args:
            sections: セクション情報リスト

        Returns:
            Dict[str, Any]: エクスポート用データ
        """
        export_data = {
            "total_sections": len(sections),
            "analysis_timestamp": str(np.datetime64('now')),
            "sections": []
        }

        for section in sections:
            section_data = {
                "id": section.id,
                "title": section.title,
                "category": section.category,
                "content": section.content,
                "bounds": {
                    "x": section.bounds.x,
                    "y": section.bounds.y,
                    "width": section.bounds.width,
                    "height": section.bounds.height,
                    "confidence": section.bounds.confidence
                }
            }
            export_data["sections"].append(section_data)

        return export_data
