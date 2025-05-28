"""
複数セクション処理統合管理
改善提案シートの複数セクションを一括処理する
"""
import streamlit as st
from PIL import Image
from typing import List, Dict, Any, Optional, Tuple
import logging
import json
from datetime import datetime
import io
import time

from section_analyzer import SectionAnalyzer, SectionInfo, SectionBounds
from ocr_processor import OCRProcessor
from text_corrector import TextCorrector
from ocr_visualizer import OCRVisualizer

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiSectionProcessor:
    """
    複数セクション処理統合管理クラス
    """

    def __init__(self):
        """初期化"""
        self.section_analyzer = SectionAnalyzer()
        self.ocr_processor = OCRProcessor()
        self.text_corrector = TextCorrector()
        self.ocr_visualizer = OCRVisualizer()

        # 処理状態
        self.current_image: Optional[Image.Image] = None
        self.section_bounds: List[SectionBounds] = []
        self.section_images: List[Image.Image] = []
        self.section_infos: List[SectionInfo] = []
        self.processing_results: Dict[str, Any] = {}

    def process_multi_section_image(self, image_file) -> Dict[str, Any]:
        """
        複数セクション画像を処理

        Args:
            image_file: アップロードされた画像ファイル

        Returns:
            Dict[str, Any]: 処理結果
        """
        try:
            # 画像を読み込み
            self.current_image = Image.open(image_file)

            # ステップ1: セクション分析
            st.info("🔍 ステップ1: セクション分析を実行中...")
            self.section_bounds = self.section_analyzer.analyze_image_layout(self.current_image)

            # ステップ2: セクション画像抽出
            st.info("✂️ ステップ2: セクション画像を抽出中...")
            self.section_images = self.section_analyzer.extract_sections(
                self.current_image, self.section_bounds
            )

            # ステップ3: 各セクションのOCR処理
            st.info("📝 ステップ3: 各セクションのOCR処理中...")
            section_ocr_results = []

            progress_bar = st.progress(0)
            for i, section_image in enumerate(self.section_images):
                # OCR実行
                ocr_result = self._process_section_ocr(section_image, i)
                section_ocr_results.append(ocr_result)

                # プログレスバー更新
                progress_bar.progress((i + 1) / len(self.section_images))

            # ステップ4: セクション情報作成
            st.info("📊 ステップ4: セクション情報を構造化中...")
            self.section_infos = []
            for i, (bounds, ocr_result) in enumerate(zip(self.section_bounds, section_ocr_results)):
                section_info = self.section_analyzer.create_section_info(
                    section_id=str(i + 1),
                    bounds=bounds,
                    ocr_result=ocr_result
                )
                self.section_infos.append(section_info)

            # 処理結果をまとめる
            self.processing_results = {
                "success": True,
                "total_sections": len(self.section_infos),
                "sections": self.section_infos,
                "section_bounds": self.section_bounds,
                "section_images": self.section_images,
                "processing_timestamp": datetime.now().isoformat()
            }

            st.success(f"✅ 処理完了！{len(self.section_infos)}個のセクションを検出しました。")
            return self.processing_results

        except Exception as e:
            logger.error(f"複数セクション処理エラー: {str(e)}")
            st.error(f"処理中にエラーが発生しました: {str(e)}")
            return {"success": False, "error": str(e)}

    def _process_section_ocr(self, section_image: Image.Image, section_index: int) -> Dict[str, Any]:
        """
        個別セクションのOCR処理

        Args:
            section_image: セクション画像
            section_index: セクションインデックス

        Returns:
            Dict[str, Any]: OCR結果
        """
        try:
            # 画像をバイト形式に変換してファイルライクオブジェクトを作成
            img_byte_arr = io.BytesIO()
            section_image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            # ファイル名属性を追加
            img_byte_arr.name = f"section_{section_index + 1}.png"

            # OCR実行（process_single_imageメソッドを使用）
            ocr_result = self.ocr_processor.process_single_image(img_byte_arr)

            return ocr_result

        except Exception as e:
            logger.error(f"セクション{section_index + 1}のOCR処理エラー: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "source": "error"
            }

    def display_section_analysis_results(self):
        """セクション分析結果を表示"""
        if not self.current_image or not self.section_bounds:
            st.warning("セクション分析結果がありません。")
            return

        st.subheader("🔍 セクション分析結果")

        # タブで表示切り替え
        tab1, tab2, tab3 = st.tabs(["📷 元画像", "🎯 セクション境界", "📊 分析詳細"])

        with tab1:
            st.image(self.current_image, caption="元画像", use_column_width=True)

        with tab2:
            # セクション境界を可視化
            visualized_image = self.section_analyzer.visualize_sections(
                self.current_image, self.section_bounds
            )
            st.image(visualized_image, caption="セクション境界", use_column_width=True)

        with tab3:
            # 分析詳細
            st.write(f"**検出セクション数:** {len(self.section_bounds)}")

            for i, bounds in enumerate(self.section_bounds):
                st.markdown(f"#### セクション {i + 1} 詳細")
                with st.container():
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**境界情報:**")
                        st.write(f"- X座標: {bounds.x}")
                        st.write(f"- Y座標: {bounds.y}")
                        st.write(f"- 幅: {bounds.width}")
                        st.write(f"- 高さ: {bounds.height}")
                        st.write(f"- 信頼度: {bounds.confidence:.2f}")

                    with col2:
                        if i < len(self.section_images):
                            st.image(self.section_images[i], caption=f"セクション {i + 1}", use_column_width=True)

                if i < len(self.section_bounds) - 1:
                    st.divider()

    def display_section_ocr_results(self):
        """セクションOCR結果を表示"""
        if not self.section_infos:
            st.warning("セクションOCR結果がありません。")
            return

        st.subheader("📝 セクションOCR結果")

        # カテゴリ別フィルタ
        categories = list(set([section.category for section in self.section_infos]))
        selected_categories = st.multiselect(
            "表示するカテゴリを選択:",
            categories,
            default=categories
        )

        # フィルタされたセクションを表示
        filtered_sections = [
            section for section in self.section_infos
            if section.category in selected_categories
        ]

        for section in filtered_sections:
            st.markdown(f"### {section.title} - {section.category}")
            with st.container():
                col1, col2 = st.columns([1, 2])

                with col1:
                    # セクション画像
                    section_index = int(section.id) - 1
                    if section_index < len(self.section_images):
                        st.image(
                            self.section_images[section_index],
                            caption=f"セクション {section.id}",
                            use_column_width=True
                        )

                with col2:
                    # OCR結果
                    st.write("**OCR結果:**")
                    if section.content:
                        # 一意のキーを生成
                        text_key = f"section_text_{section.id}_{int(time.time() * 1000000) % 1000000}"
                        st.text_area(
                            f"テキスト内容 (セクション {section.id})",
                            value=section.content,
                            height=150,
                            key=text_key
                        )
                    else:
                        st.write("テキストが検出されませんでした。")

                    # OCR詳細情報
                    if section.ocr_result:
                        st.markdown("**OCR詳細情報:**")
                        with st.container():
                            st.json(section.ocr_result)

            st.divider()

    def display_section_correction_interface(self):
        """セクション修正インターフェース"""
        if not self.section_infos:
            st.warning("修正対象のセクションがありません。")
            return

        st.subheader("✏️ セクション修正")

        # セクション選択
        section_options = [f"セクション {s.id}: {s.category}" for s in self.section_infos]
        selected_section_index = st.selectbox(
            "修正するセクションを選択:",
            range(len(section_options)),
            format_func=lambda x: section_options[x]
        )

        if selected_section_index is not None:
            selected_section = self.section_infos[selected_section_index]

            col1, col2 = st.columns([1, 1])

            with col1:
                # セクション画像とハイライト
                st.write("**元画像:**")
                section_index = int(selected_section.id) - 1
                if section_index < len(self.section_images):
                    st.image(
                        self.section_images[section_index],
                        caption=f"セクション {selected_section.id}",
                        use_column_width=True
                    )

                # OCRハイライト表示
                if selected_section.ocr_result and selected_section.ocr_result.get("success", False):
                    st.write("**OCRハイライト:**")
                    # ここでOCRVisualizerを使用してハイライト表示
                    # 注意: セクション画像用に座標を調整する必要がある

            with col2:
                # テキスト修正インターフェース
                st.write("**テキスト修正:**")

                # 元のテキスト
                original_text = selected_section.content or ""

                # 修正テキスト入力
                corrected_text = st.text_area(
                    "修正されたテキスト:",
                    value=original_text,
                    height=200,
                    key=f"correction_{selected_section.id}_{int(time.time() * 1000000) % 1000000}"
                )

                # カテゴリ修正
                new_category = st.selectbox(
                    "カテゴリ:",
                    ['課題', '提案', '対象', '効果', '実現性', 'その他'],
                    index=['課題', '提案', '対象', '効果', '実現性', 'その他'].index(selected_section.category)
                    if selected_section.category in ['課題', '提案', '対象', '効果', '実現性', 'その他'] else 5,
                    key=f"category_{selected_section.id}_{int(time.time() * 1000000) % 1000000}"
                )

                # 修正適用ボタン
                if st.button(f"セクション {selected_section.id} の修正を適用", key=f"apply_{selected_section.id}"):
                    # 修正を適用
                    selected_section.content = corrected_text
                    selected_section.category = new_category
                    selected_section.title = f"セクション {selected_section.id} ({new_category})"

                    st.success(f"セクション {selected_section.id} の修正を適用しました！")
                    st.rerun()

    def display_category_summary(self):
        """カテゴリ別サマリー表示"""
        if not self.section_infos:
            st.warning("サマリー対象のデータがありません。")
            return

        st.subheader("📊 カテゴリ別サマリー")

        # カテゴリ別にグループ化
        category_groups = {}
        for section in self.section_infos:
            category = section.category
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(section)

        # カテゴリ別表示
        for category, sections in category_groups.items():
            st.markdown(f"### 📋 {category} ({len(sections)}件)")
            with st.container():
                for i, section in enumerate(sections):
                    st.write(f"**{i + 1}. セクション {section.id}:**")
                    if section.content:
                        # 内容を要約表示（最初の100文字）
                        content_preview = section.content[:100] + "..." if len(section.content) > 100 else section.content
                        st.write(f"　{content_preview}")
                    else:
                        st.write("　（内容なし）")
                    st.write("")
                st.divider()

    def export_results(self) -> Dict[str, Any]:
        """処理結果をエクスポート"""
        if not self.section_infos:
            return {"error": "エクスポート対象のデータがありません"}

        # セクションデータをエクスポート
        export_data = self.section_analyzer.export_sections_data(self.section_infos)

        # 追加情報
        export_data.update({
            "image_info": {
                "width": self.current_image.width if self.current_image else 0,
                "height": self.current_image.height if self.current_image else 0
            },
            "processing_summary": {
                "total_sections": len(self.section_infos),
                "categories": list(set([s.category for s in self.section_infos])),
                "success_rate": len([s for s in self.section_infos if s.content]) / len(self.section_infos) if self.section_infos else 0
            }
        })

        return export_data

    def display_export_options(self):
        """エクスポートオプション表示"""
        if not self.section_infos:
            st.warning("エクスポート対象のデータがありません。")
            return

        st.subheader("💾 エクスポート")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📄 JSON形式でダウンロード", key=f"export_json_btn_{int(time.time() * 1000000) % 1000000}"):
                export_data = self.export_results()
                json_str = json.dumps(export_data, ensure_ascii=False, indent=2)

                st.download_button(
                    label="📥 JSONファイルをダウンロード",
                    data=json_str,
                    file_name=f"multi_section_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    key=f"download_json_btn_{int(time.time() * 1000000) % 1000000}"
                )

        with col2:
            if st.button("📊 サマリーレポート生成", key=f"generate_report_btn_{int(time.time() * 1000000) % 1000000}"):
                # サマリーレポートを生成
                report = self._generate_summary_report()

                st.download_button(
                    label="📥 レポートをダウンロード",
                    data=report,
                    file_name=f"section_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                    key=f"download_report_btn_{int(time.time() * 1000000) % 1000000}"
                )

        with col3:
            if st.button("🔄 処理結果をリセット", key=f"reset_multi_btn_{int(time.time() * 1000000) % 1000000}"):
                self._reset_processing_state()
                st.success("処理結果をリセットしました。")
                st.rerun()

    def _generate_summary_report(self) -> str:
        """サマリーレポートを生成"""
        if not self.section_infos:
            return "# エラー\n\nレポート生成対象のデータがありません。"

        # カテゴリ別統計
        category_stats = {}
        for section in self.section_infos:
            category = section.category
            if category not in category_stats:
                category_stats[category] = 0
            category_stats[category] += 1

        # レポート生成
        report = f"""# 改善提案シート 複数セクション分析レポート

## 処理概要
- **処理日時:** {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
- **総セクション数:** {len(self.section_infos)}
- **画像サイズ:** {self.current_image.width if self.current_image else 0} x {self.current_image.height if self.current_image else 0}

## カテゴリ別統計
"""

        for category, count in category_stats.items():
            percentage = (count / len(self.section_infos)) * 100
            report += f"- **{category}:** {count}件 ({percentage:.1f}%)\n"

        report += "\n## セクション詳細\n\n"

        for section in self.section_infos:
            report += f"### セクション {section.id}: {section.category}\n\n"
            if section.content:
                report += f"**内容:**\n{section.content}\n\n"
            else:
                report += "**内容:** （検出されませんでした）\n\n"
            report += "---\n\n"

        return report

    def _reset_processing_state(self):
        """処理状態をリセット"""
        self.current_image = None
        self.section_bounds = []
        self.section_images = []
        self.section_infos = []
        self.processing_results = {}
