"""
改善提案シート文字起こしツール - Document AI風UI
Streamlitアプリケーション
"""
import streamlit as st
import os
import json
import difflib
from datetime import datetime
from typing import List, Optional, Dict, Any
import config
from ocr_processor import OCRProcessor
from text_corrector import TextCorrector
from data_organizer import DataOrganizer
from markdown_formatter import MarkdownFormatter


def check_api_key() -> bool:
    """
    OpenAI APIキーの存在確認

    Returns:
        bool: APIキーが設定されているかどうか
    """
    return bool(config.OPENAI_API_KEY)


def validate_uploaded_files(uploaded_files: List, file_type: str) -> List:
    """
    アップロードされたファイルの検証

    Args:
        uploaded_files: アップロードされたファイルのリスト
        file_type: ファイルタイプ（'image' or 'document'）

    Returns:
        List: 有効なファイルのリスト
    """
    valid_files = []

    if file_type == 'image':
        allowed_extensions = config.ALLOWED_IMAGE_EXTENSIONS
    else:
        allowed_extensions = config.ALLOWED_DOCUMENT_EXTENSIONS

    for file in uploaded_files:
        # ファイル拡張子の確認
        file_extension = os.path.splitext(file.name)[1].lower()
        if file_extension not in allowed_extensions:
            st.warning(f"ファイル '{file.name}' は対応していない形式です。対応形式: {', '.join(allowed_extensions)}")
            continue

        # ファイルサイズの確認
        if file.size > config.MAX_FILE_SIZE_MB * 1024 * 1024:
            st.warning(f"ファイル '{file.name}' のサイズが大きすぎます。最大サイズ: {config.MAX_FILE_SIZE_MB}MB")
            continue

        valid_files.append(file)

    return valid_files


def display_workflow_step(step_number: int, title: str, status: str = "pending"):
    """
    ワークフローステップを表示する

    Args:
        step_number: ステップ番号
        title: ステップタイトル
        status: ステップ状態 ("pending", "processing", "completed", "error")
    """
    status_icons = {
        "pending": "⏳",
        "processing": "🔄",
        "completed": "✅",
        "error": "❌"
    }

    status_colors = {
        "pending": "#gray",
        "processing": "#blue",
        "completed": "#green",
        "error": "#red"
    }

    icon = status_icons.get(status, "⏳")
    color = status_colors.get(status, "#gray")

    st.markdown(f"""
    <div style="
        border: 2px solid {color};
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        background-color: {'#f0f8f0' if status == 'completed' else '#f8f8f8'};
    ">
        <h4>{icon} ステップ {step_number}: {title}</h4>
    </div>
    """, unsafe_allow_html=True)


def highlight_differences(original: str, corrected: str) -> str:
    """
    テキストの差分をハイライト表示する

    Args:
        original: 元のテキスト
        corrected: 修正されたテキスト

    Returns:
        str: ハイライト表示用のHTML
    """
    if original == corrected:
        return corrected

    # 文字レベルでの差分を計算
    diff = difflib.SequenceMatcher(None, original, corrected)
    result = []

    for tag, i1, i2, j1, j2 in diff.get_opcodes():
        if tag == 'equal':
            # 変更されていない部分は通常表示
            result.append(corrected[j1:j2])
        elif tag == 'replace':
            # 変更された部分をハイライト
            result.append(f'<mark style="background-color: #ffeb3b; padding: 1px 2px; border-radius: 2px;">{corrected[j1:j2]}</mark>')
        elif tag == 'insert':
            # 追加された部分をハイライト
            result.append(f'<mark style="background-color: #c8e6c9; padding: 1px 2px; border-radius: 2px;">{corrected[j1:j2]}</mark>')
        elif tag == 'delete':
            # 削除された部分は表示しない（修正後のテキストなので）
            pass

    return ''.join(result)


def display_field_comparison(field_name: str, original_text: str, corrected_text: str):
    """
    フィールドの比較表示を行う

    Args:
        field_name: フィールド名
        original_text: 元のテキスト
        corrected_text: 修正されたテキスト
    """
    if original_text == corrected_text:
        # 変更がない場合は通常表示
        st.markdown(f"**{field_name}:** {corrected_text}")
    else:
        # 変更がある場合はハイライト表示
        highlighted_text = highlight_differences(original_text, corrected_text)
        st.markdown(f"**{field_name}:** {highlighted_text}", unsafe_allow_html=True)

        # 変更内容を小さく表示（expanderの代わりにdetailsタグを使用）
        details_html = f"""
        <details style="margin-top: 5px; margin-bottom: 10px;">
            <summary style="cursor: pointer; font-size: 0.8em; color: #666;">📝 {field_name}の変更詳細</summary>
            <div style="margin-top: 10px; padding: 10px; background-color: #f8f9fa; border-radius: 5px;">
                <div style="margin-bottom: 10px;">
                    <strong>修正前:</strong><br>
                    <span style="font-family: monospace; background-color: #fff; padding: 5px; border-radius: 3px; display: inline-block; margin-top: 5px;">{original_text}</span>
                </div>
                <div>
                    <strong>修正後:</strong><br>
                    <span style="font-family: monospace; background-color: #fff; padding: 5px; border-radius: 3px; display: inline-block; margin-top: 5px;">{corrected_text}</span>
                </div>
            </div>
        </details>
        """
        st.markdown(details_html, unsafe_allow_html=True)


def display_image_ocr_correction_result(image_file, ocr_result: Dict[str, Any], correction_result: Dict[str, Any], index: int):
    """
    画像、OCR結果、修正結果を横並びで表示する

    Args:
        image_file: 画像ファイル
        ocr_result: OCR結果
        correction_result: 修正結果
        index: インデックス
    """
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        st.subheader(f"📷 画像 {index + 1}")
        st.text(f"ファイル名: {image_file.name}")
        st.image(image_file, use_column_width=True)

    with col2:
        st.subheader(f"📝 OCR結果 {index + 1}")

        if ocr_result.get("success", False):
            st.success("✅ OCR処理成功")

            # OCRデータの表示
            if "data" in ocr_result and ocr_result["data"]:
                try:
                    # JSONデータをパースして表示
                    if isinstance(ocr_result["data"], str):
                        data = json.loads(ocr_result["data"])
                    else:
                        data = ocr_result["data"]

                    if isinstance(data, list) and len(data) > 0:
                        item = data[0]
                        st.markdown("**認識された内容:**")
                        st.markdown(f"**課題:** {item.get('problem', 'なし')}")
                        st.markdown(f"**個人:** {item.get('personal', 'なし')}")
                        st.markdown(f"**地域:** {item.get('community', 'なし')}")
                        st.markdown(f"**行政:** {item.get('gov', 'なし')}")
                        st.markdown(f"**その他:** {item.get('others', 'なし')}")
                    else:
                        st.json(data)

                except (json.JSONDecodeError, KeyError) as e:
                    st.warning(f"データ表示エラー: {str(e)}")
                    st.text(ocr_result.get("raw_text", "テキストなし"))
            else:
                st.text(ocr_result.get("raw_text", "テキストなし"))
        else:
            st.error("❌ OCR処理失敗")
            st.error(ocr_result.get("error", "不明なエラー"))

    with col3:
        st.subheader(f"🔧 修正結果 {index + 1}")

        if correction_result and correction_result.get("success", False):
            st.success("✅ 修正処理成功")

            # 修正データの表示
            if "data" in correction_result and correction_result["data"]:
                try:
                    # JSONデータをパースして表示
                    if isinstance(correction_result["data"], str):
                        corrected_data = json.loads(correction_result["data"])
                    else:
                        corrected_data = correction_result["data"]

                    if isinstance(corrected_data, list) and len(corrected_data) > 0:
                        corrected_item = corrected_data[0]

                        # OCR結果と修正結果を比較してハイライト表示
                        if ocr_result.get("success", False) and "data" in ocr_result:
                            try:
                                if isinstance(ocr_result["data"], str):
                                    original_data = json.loads(ocr_result["data"])
                                else:
                                    original_data = ocr_result["data"]

                                if isinstance(original_data, list) and len(original_data) > 0:
                                    original_item = original_data[0]

                                    st.markdown("**修正された内容:**")

                                    # 各フィールドの差分をハイライト表示
                                    for field in ["problem", "personal", "community", "gov", "others"]:
                                        original_text = str(original_item.get(field, 'なし'))
                                        corrected_text = str(corrected_item.get(field, 'なし'))

                                        field_names = {
                                            "problem": "課題",
                                            "personal": "個人",
                                            "community": "地域",
                                            "gov": "行政",
                                            "others": "その他"
                                        }

                                        display_field_comparison(field_names[field], original_text, corrected_text)
                                else:
                                    st.json(corrected_data)
                            except (json.JSONDecodeError, KeyError):
                                st.json(corrected_data)
                        else:
                            st.json(corrected_data)
                    else:
                        st.json(corrected_data)

                except (json.JSONDecodeError, KeyError) as e:
                    st.warning(f"データ表示エラー: {str(e)}")
                    st.text(correction_result.get("corrected_text", "修正テキストなし"))
            else:
                st.text(correction_result.get("corrected_text", "修正テキストなし"))
        else:
            if correction_result:
                st.error("❌ 修正処理失敗")
                st.error(correction_result.get("error", "不明なエラー"))
            else:
                st.info("⏳ 修正処理待機中")


def display_organization_results(organized_data: List[Dict[str, Any]]):
    """
    整理結果を表示する

    Args:
        organized_data: 整理されたデータ
    """
    st.subheader("📊 課題ドリブン整理結果")

    if organized_data:
        st.success(f"✅ 整理完了: {len(organized_data)} 件の課題を識別")

        for i, problem in enumerate(organized_data):
            with st.expander(f"課題 {i + 1}: {problem.get('problem', '不明な課題')}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**個人としてできること:**")
                    personal = problem.get('personal', [])
                    if isinstance(personal, list):
                        for item in personal:
                            st.markdown(f"- {item}")
                    elif personal:
                        st.markdown(f"- {personal}")
                    else:
                        st.markdown("- なし")

                    st.markdown("**地域としてできること:**")
                    community = problem.get('community', [])
                    if isinstance(community, list):
                        for item in community:
                            st.markdown(f"- {item}")
                    elif community:
                        st.markdown(f"- {community}")
                    else:
                        st.markdown("- なし")

                with col2:
                    st.markdown("**行政の役割:**")
                    gov = problem.get('gov', [])
                    if isinstance(gov, list):
                        for item in gov:
                            st.markdown(f"- {item}")
                    elif gov:
                        st.markdown(f"- {gov}")
                    else:
                        st.markdown("- なし")

                    st.markdown("**その他:**")
                    others = problem.get('others', [])
                    if isinstance(others, list):
                        for item in others:
                            st.markdown(f"- {item}")
                    elif others:
                        st.markdown(f"- {others}")
                    else:
                        st.markdown("- なし")
    else:
        st.error("❌ 整理されたデータがありません")


def process_ocr_and_correction(valid_images: List, reference_texts: List[str]):
    """
    OCR処理と文字修正を一連で実行する

    Args:
        valid_images: 有効な画像ファイルのリスト
        reference_texts: 参考資料テキストのリスト

    Returns:
        tuple: (ocr_results, corrected_results)
    """
    total_images = len(valid_images)

    # プログレスバーとステータス表示
    progress_bar = st.progress(0)
    status_text = st.empty()

    # OCR処理
    status_text.text("📷 画像文字認識処理を開始...")
    ocr_processor = OCRProcessor()
    ocr_results = []

    for i, image_file in enumerate(valid_images):
        progress = (i + 0.5) / (total_images * 2)  # OCRは全体の50%
        progress_bar.progress(progress)
        status_text.text(f"📷 画像 {i + 1}/{total_images} をOCR処理中...")

        result = ocr_processor.process_single_image(image_file)
        ocr_results.append(result)

    # 文字修正処理
    status_text.text("🔧 文字認識修正処理を開始...")
    text_corrector = TextCorrector()
    corrected_results = []

    for i, ocr_result in enumerate(ocr_results):
        progress = (total_images + i + 1) / (total_images * 2)  # 修正は全体の50%
        progress_bar.progress(progress)
        status_text.text(f"🔧 OCR結果 {i + 1}/{total_images} を修正中...")

        if ocr_result.get("success", False):
            correction_result = text_corrector.correct_single_result(ocr_result, reference_texts)
            corrected_results.append(correction_result)
        else:
            corrected_results.append(None)

    progress_bar.progress(1.0)
    status_text.text("✅ OCR処理と文字修正が完了しました！")

    return ocr_results, corrected_results


def main():
    """
    メイン関数
    """
    st.set_page_config(
        page_title="改善提案シート文字起こしツール - Document AI",
        page_icon="🤖",
        layout="wide"
    )

    # カスタムCSS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .workflow-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    mark {
        padding: 2px 4px;
        border-radius: 3px;
    }
    </style>
    """, unsafe_allow_html=True)

    # ヘッダー
    st.markdown("""
    <div class="main-header">
        <h1>🤖 改善提案シート文字起こしツール</h1>
        <p>Document AI風ワークフロー - 段階的処理確認</p>
    </div>
    """, unsafe_allow_html=True)

    # APIキーの確認
    if not check_api_key():
        st.error("OpenAI APIキーが設定されていません。.envファイルにOPENAI_API_KEYを設定してください。")
        st.stop()

    # セッション状態の初期化
    if 'workflow_step' not in st.session_state:
        st.session_state.workflow_step = 0
    if 'ocr_results' not in st.session_state:
        st.session_state.ocr_results = None
    if 'corrected_results' not in st.session_state:
        st.session_state.corrected_results = None
    if 'organized_data' not in st.session_state:
        st.session_state.organized_data = None
    if 'final_markdown' not in st.session_state:
        st.session_state.final_markdown = None

    # ワークフロー表示
    st.markdown('<div class="workflow-container">', unsafe_allow_html=True)
    st.subheader("📋 処理ワークフロー")

    col1, col2 = st.columns(2)

    with col1:
        status1 = "completed" if st.session_state.workflow_step > 0 else "pending"
        display_workflow_step(1, "OCR処理 + 文字修正", status1)

    with col2:
        status2 = "completed" if st.session_state.workflow_step > 1 else "pending"
        display_workflow_step(2, "データ整理 + レポート生成", status2)

    st.markdown('</div>', unsafe_allow_html=True)

    # ファイルアップロード（改善提案シートのみ）
    st.header("📁 ファイルアップロード")

    st.subheader("改善提案シート（必須）")
    uploaded_images = st.file_uploader(
        "手書きの改善提案シート画像をアップロード",
        type=['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'],
        accept_multiple_files=True,
        key="images",
        help="複数の画像ファイルを同時にアップロードできます"
    )

    # ファイル検証
    if uploaded_images:
        valid_images = validate_uploaded_files(uploaded_images, 'image')
        if not valid_images:
            st.error("有効な画像ファイルがありません。")
            st.stop()

        st.success(f"✅ {len(valid_images)} 枚の画像ファイルが準備完了")
    else:
        st.warning("改善提案シートの画像をアップロードしてください。")
        st.stop()

    # 処理ボタン群
    st.header("🚀 処理実行")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("1️⃣ OCR処理 + 文字修正開始", type="primary"):
            st.session_state.workflow_step = 0

            # OCR処理と文字修正を一連で実行
            reference_texts = []  # 参考資料は使用しない
            ocr_results, corrected_results = process_ocr_and_correction(valid_images, reference_texts)

            st.session_state.ocr_results = ocr_results
            st.session_state.corrected_results = corrected_results
            st.session_state.workflow_step = 1

            st.rerun()

    with col2:
        if st.button("2️⃣ データ整理 + レポート生成", disabled=st.session_state.workflow_step < 1):
            # データ整理とレポート生成を一連で実行
            with st.spinner("データを課題ごとに整理し、レポートを生成中..."):
                # データ整理処理
                data_organizer = DataOrganizer()
                text_corrector = TextCorrector()
                successful_corrections = text_corrector.extract_successful_corrections(st.session_state.corrected_results)
                organization_result = data_organizer.organize_data(successful_corrections)

                if organization_result.get("success", False):
                    st.session_state.organized_data = organization_result["data"]

                    # レポート生成処理
                    markdown_formatter = MarkdownFormatter()
                    markdown_result = markdown_formatter.format_to_markdown(st.session_state.organized_data, True)

                    if markdown_result.get("success", False):
                        # メタデータの追加
                        metadata = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "image_count": len(valid_images),
                            "problem_count": len(st.session_state.organized_data)
                        }

                        st.session_state.final_markdown = markdown_formatter.add_metadata(
                            markdown_result["markdown"], metadata
                        )
                        st.session_state.workflow_step = 2
                    else:
                        st.error(f"レポート生成に失敗しました: {markdown_result.get('error', '')}")
                else:
                    st.error(f"データ整理に失敗しました: {organization_result.get('error', '')}")

            st.rerun()

    with col3:
        if st.button("🔄 リセット"):
            st.session_state.workflow_step = 0
            st.session_state.ocr_results = None
            st.session_state.corrected_results = None
            st.session_state.organized_data = None
            st.session_state.final_markdown = None
            st.rerun()

    # 結果表示
    if st.session_state.workflow_step >= 1 and st.session_state.ocr_results and st.session_state.corrected_results:
        # 処理2が完了している場合は、処理1の結果を折りたたみ表示
        if st.session_state.workflow_step >= 2:
            with st.expander("📷 ステップ1: OCR処理 + 文字修正結果を表示", expanded=False):
                successful_ocr = [r for r in st.session_state.ocr_results if r.get("success", False)]
                successful_corrections = [r for r in st.session_state.corrected_results if r and r.get("success", False)]

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("OCR成功", f"{len(successful_ocr)}/{len(valid_images)}")
                with col2:
                    st.metric("修正成功", f"{len(successful_corrections)}/{len(valid_images)}")

                # 各画像、OCR結果、修正結果を表示
                for i, (image_file, ocr_result, correction_result) in enumerate(zip(valid_images, st.session_state.ocr_results, st.session_state.corrected_results)):
                    st.markdown("---")
                    display_image_ocr_correction_result(image_file, ocr_result, correction_result, i)
        else:
            # 処理2が未完了の場合は通常表示
            st.header("📷 ステップ1: OCR処理 + 文字修正結果")

            successful_ocr = [r for r in st.session_state.ocr_results if r.get("success", False)]
            successful_corrections = [r for r in st.session_state.corrected_results if r and r.get("success", False)]

            col1, col2 = st.columns(2)
            with col1:
                st.metric("OCR成功", f"{len(successful_ocr)}/{len(valid_images)}")
            with col2:
                st.metric("修正成功", f"{len(successful_corrections)}/{len(valid_images)}")

            # 各画像、OCR結果、修正結果を表示
            for i, (image_file, ocr_result, correction_result) in enumerate(zip(valid_images, st.session_state.ocr_results, st.session_state.corrected_results)):
                st.markdown("---")
                display_image_ocr_correction_result(image_file, ocr_result, correction_result, i)

    if st.session_state.workflow_step >= 2 and st.session_state.organized_data and st.session_state.final_markdown:
        st.header("📊 ステップ2: データ整理 + レポート生成結果")

        # 整理結果の表示
        display_organization_results(st.session_state.organized_data)

        st.markdown("---")

        # 統計情報
        st.subheader("📈 処理統計")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("処理画像数", len(valid_images))
        with col2:
            st.metric("識別課題数", len(st.session_state.organized_data))
        with col3:
            successful_ocr = [r for r in st.session_state.ocr_results if r.get("success", False)]
            st.metric("OCR成功率", f"{len(successful_ocr)/len(valid_images)*100:.1f}%")
        with col4:
            solutions_count = sum(1 for item in st.session_state.organized_data
                                if any(item.get(field) for field in ["personal", "community", "gov", "others"]))
            st.metric("解決策有り", f"{solutions_count}/{len(st.session_state.organized_data)}")

        # 最終レポートプレビュー
        st.subheader("📄 最終レポートプレビュー")
        st.markdown(st.session_state.final_markdown)

        # ダウンロードボタン
        st.subheader("💾 ダウンロード")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"改善提案シート_整理結果_{timestamp}.md"

        st.download_button(
            label="📥 Markdownファイルをダウンロード",
            data=st.session_state.final_markdown,
            file_name=filename,
            mime="text/markdown"
        )


if __name__ == "__main__":
    main()
