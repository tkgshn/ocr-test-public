"""
OCR結果の可視化コンポーネント
座標データ付きハイライト表示機能
"""
import streamlit as st
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from typing import Dict, List, Any, Optional, Tuple
import json
import time


class OCRVisualizer:
    """
    OCR結果の可視化を行うクラス
    """

    def __init__(self):
        """初期化"""
        self.colors = [
            "#FF6B6B",  # 赤
            "#4ECDC4",  # ティール
            "#45B7D1",  # 青
            "#96CEB4",  # 緑
            "#FFEAA7",  # 黄
            "#DDA0DD",  # プラム
            "#98D8C8",  # ミント
            "#F7DC6F",  # ゴールド
            "#BB8FCE",  # ラベンダー
            "#85C1E9"   # スカイブルー
        ]

    def create_highlighted_image(self,
                                image_file,
                                ocr_result: Dict[str, Any],
                                highlight_level: str = "paragraphs") -> Optional[Image.Image]:
        """
        OCR結果をハイライト表示した画像を作成

        Args:
            image_file: 元の画像ファイル
            ocr_result: OCR処理結果
            highlight_level: ハイライトレベル ("blocks", "paragraphs", "lines", "tokens")

        Returns:
            PIL.Image: ハイライト表示された画像
        """
        try:
            # 画像を読み込み
            if hasattr(image_file, 'read'):
                image_file.seek(0)
                image = Image.open(image_file)
            else:
                image = Image.open(image_file)

            # RGBAモードに変換（透明度を扱うため）
            if image.mode != 'RGBA':
                image = image.convert('RGBA')

            # 描画用のオーバーレイを作成
            overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)

            # OCR結果からハイライト情報を抽出
            if ocr_result.get("success") and ocr_result.get("data"):
                data = ocr_result["data"]

                if ocr_result.get("source") == "document_ai":
                    self._draw_document_ai_highlights(draw, data, highlight_level, image.size)
                # OpenAIの場合は何も描画しない（streamlit側でテキストのみ表示）

            # オーバーレイを元画像に合成
            highlighted_image = Image.alpha_composite(image, overlay)

            # RGBモードに変換（表示用）
            return highlighted_image.convert('RGB')

        except Exception as e:
            st.error(f"ハイライト画像の作成に失敗しました: {e}")
            return None

    def _draw_document_ai_highlights(self,
                                   draw: ImageDraw.Draw,
                                   data: Dict[str, Any],
                                   highlight_level: str,
                                   image_size: Tuple[int, int]):
        """
        Document AI の結果をハイライト表示

        Args:
            draw: ImageDraw オブジェクト
            data: Document AI の結果データ
            highlight_level: ハイライトレベル
            image_size: 画像サイズ (width, height)
        """
        if "pages" not in data or not data["pages"]:
            return

        page = data["pages"][0]  # 最初のページを処理

        # ハイライトレベルに応じて描画
        if highlight_level in page:
            elements = page[highlight_level]

            for i, element in enumerate(elements):
                if element.get("bounding_box"):
                    color_idx = i % len(self.colors)
                    color = self.colors[color_idx]

                    # 座標を取得
                    bbox = element["bounding_box"]

                    # 正規化座標を使用（利用可能な場合）
                    if bbox.get("normalized_vertices"):
                        vertices = self._convert_normalized_vertices(
                            bbox["normalized_vertices"], image_size
                        )
                    elif bbox.get("vertices"):
                        vertices = [(v["x"], v["y"]) for v in bbox["vertices"]]
                    else:
                        continue

                    # ポリゴンを描画
                    self._draw_polygon_highlight(draw, vertices, color, element.get("text", ""))

    def _convert_normalized_vertices(self,
                                   normalized_vertices: List[Dict[str, float]],
                                   image_size: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        正規化座標を実際の画像座標に変換

        Args:
            normalized_vertices: 正規化座標のリスト
            image_size: 画像サイズ (width, height)

        Returns:
            実際の座標のリスト
        """
        width, height = image_size
        vertices = []

        for vertex in normalized_vertices:
            x = int(vertex.get("x", 0) * width)
            y = int(vertex.get("y", 0) * height)
            vertices.append((x, y))

        return vertices

    def _draw_polygon_highlight(self,
                              draw: ImageDraw.Draw,
                              vertices: List[Tuple[int, int]],
                              color: str,
                              text: str = ""):
        """
        ポリゴンハイライトを描画

        Args:
            draw: ImageDraw オブジェクト
            vertices: 頂点座標のリスト
            color: ハイライト色
            text: 表示するテキスト
        """
        if len(vertices) < 3:
            return

        # 半透明の塗りつぶし
        fill_color = self._hex_to_rgba(color, alpha=50)
        draw.polygon(vertices, fill=fill_color)

        # 境界線
        outline_color = self._hex_to_rgba(color, alpha=200)
        draw.polygon(vertices, outline=outline_color, width=2)

        # テキストラベルは豆腐フォント問題を避けるために削除
        # 日本語フォントが正しく読み込めない环境でも動作するように

    def _hex_to_rgba(self, hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
        """
        16進数カラーをRGBAに変換

        Args:
            hex_color: 16進数カラー文字列 (例: "#FF6B6B")
            alpha: 透明度 (0-255)

        Returns:
            RGBA タプル
        """
        hex_color = hex_color.lstrip('#')

        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (r, g, b, alpha)
        else:
            return (255, 0, 0, alpha)  # デフォルトは赤

    def display_ocr_results_with_highlights(self,
                                          image_file,
                                          ocr_result: Dict[str, Any]):
        """
        OCR結果をハイライト付きで表示

        Args:
            image_file: 元の画像ファイル
            ocr_result: OCR処理結果
        """
        # st.subheader("📍 OCR結果のハイライト表示")

        # デフォルトのハイライトレベルを設定
        if ocr_result.get("source") == "document_ai":
            highlight_level = "paragraphs"  # デフォルトでparagraphsを使用
        else:
            highlight_level = "openai"
            st.info("OpenAI の結果には座標情報がないため、テキスト情報のみ表示されます。")

        # ハイライト画像を作成
        highlighted_image = self.create_highlighted_image(
            image_file, ocr_result, highlight_level
        )

        if highlighted_image:
            # 画像を表示
            st.image(highlighted_image)

        #     # # 詳細情報を表示
        #     # self._display_detailed_results(ocr_result, highlight_level)
        # else:
        #     st.error("ハイライト画像の作成に失敗しました。")
