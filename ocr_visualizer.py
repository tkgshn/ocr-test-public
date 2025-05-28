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
                elif ocr_result.get("source") == "openai":
                    self._draw_openai_highlights(draw, data, image.size)

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

    def _draw_openai_highlights(self,
                              draw: ImageDraw.Draw,
                              data: List[Dict[str, Any]],
                              image_size: Tuple[int, int]):
        """
        OpenAI の結果をハイライト表示（座標情報がないため、テキストボックスのみ）

        Args:
            draw: ImageDraw オブジェクト
            data: OpenAI の結果データ
            image_size: 画像サイズ
        """
        # OpenAI の結果には座標情報がないため、
        # テキスト情報のみを画像の下部に表示
        if isinstance(data, list) and data:
            y_offset = image_size[1] - 200

            for i, item in enumerate(data):
                if isinstance(item, dict):
                    text_info = []
                    for key, value in item.items():
                        if value and str(value).strip():
                            text_info.append(f"{key}: {value}")

                    if text_info:
                        text = " | ".join(text_info)
                        color = self.colors[i % len(self.colors)]

                        # テキストボックスを描画
                        self._draw_text_box(draw, (10, y_offset + i * 30), text, color)

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

    def _draw_text_box(self,
                      draw: ImageDraw.Draw,
                      position: Tuple[int, int],
                      text: str,
                      color: str):
        """
        テキストボックスを描画

        Args:
            draw: ImageDraw オブジェクト
            position: 描画位置
            text: 表示するテキスト
            color: 背景色
        """
        x, y = position

        try:
            font = ImageFont.load_default()

            # テキストサイズを取得
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # 背景を描画
            bg_color = self._hex_to_rgba(color, alpha=150)
            draw.rectangle([x, y, x + text_width + 10, y + text_height + 6],
                         fill=bg_color)

            # テキストを描画
            draw.text((x + 5, y + 3), text, fill=(0, 0, 0, 255), font=font)

        except Exception:
            # フォント関連のエラーが発生した場合はシンプルな描画
            draw.rectangle([x, y, x + 200, y + 20],
                         fill=self._hex_to_rgba(color, alpha=150))
            draw.text((x + 5, y + 3), text[:30], fill=(0, 0, 0, 255))

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
        st.subheader("📍 OCR結果のハイライト表示")

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

        # if highlighted_image:
        #     # 画像を表示
        #     # st.image(highlighted_image,
        #     #         caption=f"ハイライト表示 ({highlight_level})",
        #     #         use_column_width=True)

        #     # # 詳細情報を表示
        #     # self._display_detailed_results(ocr_result, highlight_level)
        # else:
        #     st.error("ハイライト画像の作成に失敗しました。")

    def _display_detailed_results(self,
                                ocr_result: Dict[str, Any],
                                highlight_level: str):
        """
        詳細なOCR結果を表示

        Args:
            ocr_result: OCR処理結果
            highlight_level: ハイライトレベル
        """
        if not ocr_result.get("success"):
            st.error(f"OCR処理に失敗しました: {ocr_result.get('error', '不明なエラー')}")
            return

        data = ocr_result.get("data", {})
        source = ocr_result.get("source", "unknown")

        if source == "document_ai":
            self._display_document_ai_details(data, highlight_level)
        elif source == "openai":
            self._display_openai_details(data)

    def _display_document_ai_details(self,
                                   data: Dict[str, Any],
                                   highlight_level: str):
        """
        Document AI の詳細結果を表示

        Args:
            data: Document AI の結果データ
            highlight_level: ハイライトレベル
        """
        # ページ情報
        if data.get("pages"):
            page = data["pages"][0]

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("ページ番号", page.get("page_number", 1))

            with col2:
                dimensions = page.get("dimensions", {})
                st.metric("幅", f"{dimensions.get('width', 0):.0f}px")

            with col3:
                st.metric("高さ", f"{dimensions.get('height', 0):.0f}px")

            # ↓↓↓ Paragraphs詳細や要素リストの表示は削除（何も表示しない）
            # ここには何も表示しない

    def _display_openai_details(self, data: List[Dict[str, Any]]):
        """
        OpenAI の詳細結果を表示

        Args:
            data: OpenAI の結果データ
        """
        if isinstance(data, list):
            st.subheader(f"📝 抽出された項目 ({len(data)}個)")

            for i, item in enumerate(data):
                st.markdown(f"### 項目 {i+1}")
                if isinstance(item, dict):
                    for j, (key, value) in enumerate(item.items()):
                        if value and str(value).strip():
                            # より一意性の高いキーを生成
                            unique_key = f"openai_detail_{i}_{j}_{key}_{int(time.time() * 1000000) % 1000000}"
                            # ASCII codec エラーを防ぐため、文字列をエンコード処理
                            try:
                                display_value = str(value)
                            except UnicodeEncodeError:
                                display_value = str(value).encode('utf-8', errors='ignore').decode('utf-8')
                            st.text_area(key, display_value, height=100, key=unique_key)
                else:
                    st.text(str(item))

                if i < len(data) - 1:  # 最後の項目以外は区切り線を追加
                    st.divider()
        else:
            st.json(data)

    def create_comparison_view(self,
                             image_file,
                             ocr_results: List[Dict[str, Any]]):
        """
        複数のOCR結果の比較表示

        Args:
            image_file: 元の画像ファイル
            ocr_results: OCR結果のリスト
        """
        st.subheader("🔍 OCR結果比較")

        if len(ocr_results) < 2:
            st.warning("比較するには2つ以上のOCR結果が必要です。")
            return

        # 結果を並べて表示
        cols = st.columns(len(ocr_results))

        for i, (col, result) in enumerate(zip(cols, ocr_results)):
            with col:
                source = result.get("source", f"結果{i+1}")
                st.subheader(f"{source.upper()}")

                if result.get("success"):
                    # ハイライト画像を作成
                    highlight_level = "paragraphs" if source == "document_ai" else "openai"
                    highlighted_image = self.create_highlighted_image(
                        image_file, result, highlight_level
                    )

                    if highlighted_image:
                        st.image(highlighted_image, use_column_width=True)

                    # テキスト抽出結果
                    data = result.get("data", {})
                    if isinstance(data, dict) and data.get("text"):
                        st.text_area("抽出テキスト", data["text"], height=150)
                    elif isinstance(data, list):
                        text_parts = []
                        for item in data:
                            if isinstance(item, dict):
                                for value in item.values():
                                    if value and str(value).strip():
                                        text_parts.append(str(value))
                        st.text_area("抽出テキスト", "\n".join(text_parts), height=150)
                else:
                    st.error(f"処理失敗: {result.get('error', '不明なエラー')}")
