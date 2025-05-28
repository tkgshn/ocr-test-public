"""
改善提案シート文字起こしツール - Document AI風UI
Streamlitアプリケーション
"""
import streamlit as st
import os
import json
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


def read_reference_files(uploaded_files: List) -> List[str]:
    """
    参考資料ファイルを読み取る

    Args:
        uploaded_files: アップロードされたファイルのリスト

    Returns:
        List[str]: 読み取ったテキストのリスト
    """
    texts = []

    for file in uploaded_files:
        try:
            # テキストファイルとして読み取り
            content = file.read().decode('utf-8')
            texts.append(f"[{file.name}]\n{content}")
        except Exception as e:
            st.warning(f"ファイル '{file.name}' の読み取りに失敗しました: {str(e)}")

    return texts


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


def display_image_ocr_result(image_file, ocr_result: Dict[str, Any], index: int):
    """
    画像とOCR結果を対応させて表示する

    Args:
        image_file: 画像ファイル
        ocr_result: OCR結果
        index: インデックス
    """
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader(f"📷 画像 {index + 1}: {image_file.name}")
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


def display_correction_results(corrected_results: List[Dict[str, Any]]):
    """
    修正結果を表示する

    Args:
        corrected_results: 修正結果のリスト
    """
    st.subheader("🔧 文字認識修正結果")

    successful_corrections = [r for r in corrected_results if r.get("success", False)]

    if successful_corrections:
        st.success(f"✅ 修正完了: {len(successful_corrections)} 件のデータを取得")

        for i, result in enumerate(successful_corrections):
            with st.expander(f"修正結果 {i + 1}"):
                if "data" in result:
                    try:
                        if isinstance(result["data"], str):
                            data = json.loads(result["data"])
                        else:
                            data = result["data"]
                        st.json(data)
                    except json.JSONDecodeError:
                        st.text(result.get("corrected_text", "修正テキストなし"))
                else:
                    st.text(result.get("corrected_text", "修正テキストなし"))
    else:
        st.error("❌ 修正処理に成功したデータがありません")


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

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status1 = "completed" if st.session_state.workflow_step > 0 else "pending"
        display_workflow_step(1, "OCR処理", status1)

    with col2:
        status2 = "completed" if st.session_state.workflow_step > 1 else "pending"
        display_workflow_step(2, "文字修正", status2)

    with col3:
        status3 = "completed" if st.session_state.workflow_step > 2 else "pending"
        display_workflow_step(3, "データ整理", status3)

    with col4:
        status4 = "completed" if st.session_state.workflow_step > 3 else "pending"
        display_workflow_step(4, "レポート生成", status4)

    st.markdown('</div>', unsafe_allow_html=True)

    # ファイルアップロード
    st.header("📁 ファイルアップロード")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("改善提案シート（必須）")
        uploaded_images = st.file_uploader(
            "手書きの改善提案シート画像をアップロード",
            type=['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'],
            accept_multiple_files=True,
            key="images"
        )

    with col2:
        st.subheader("議事録（オプション）")
        uploaded_minutes = st.file_uploader(
            "議事録ファイルをアップロード",
            type=['txt', 'md'],
            accept_multiple_files=True,
            key="minutes"
        )

    with col3:
        st.subheader("投影資料（オプション）")
        uploaded_materials = st.file_uploader(
            "投影資料ファイルをアップロード",
            type=['txt', 'md'],
            accept_multiple_files=True,
            key="materials"
        )

    # ファイル検証
    if uploaded_images:
        valid_images = validate_uploaded_files(uploaded_images, 'image')
        if not valid_images:
            st.error("有効な画像ファイルがありません。")
            st.stop()
    else:
        st.warning("改善提案シートの画像をアップロードしてください。")
        st.stop()

    # 参考資料の読み取り
    reference_texts = []
    if uploaded_minutes:
        valid_minutes = validate_uploaded_files(uploaded_minutes, 'document')
        reference_texts.extend(read_reference_files(valid_minutes))

    if uploaded_materials:
        valid_materials = validate_uploaded_files(uploaded_materials, 'document')
        reference_texts.extend(read_reference_files(valid_materials))

    # 処理ボタン群
    st.header("🚀 処理実行")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.button("1️⃣ OCR処理開始", type="primary"):
            st.session_state.workflow_step = 0

            # OCR処理
            with st.spinner("画像から手書き文字を認識中..."):
                ocr_processor = OCRProcessor()
                st.session_state.ocr_results = ocr_processor.process_multiple_images(valid_images)
                st.session_state.workflow_step = 1

            st.rerun()

    with col2:
        if st.button("2️⃣ 文字修正", disabled=st.session_state.workflow_step < 1):
            # 文字修正処理
            with st.spinner("認識結果を修正中..."):
                text_corrector = TextCorrector()
                st.session_state.corrected_results = text_corrector.correct_multiple_results(
                    st.session_state.ocr_results, reference_texts
                )
                st.session_state.workflow_step = 2

            st.rerun()

    with col3:
        if st.button("3️⃣ データ整理", disabled=st.session_state.workflow_step < 2):
            # データ整理処理
            with st.spinner("データを課題ごとに整理中..."):
                data_organizer = DataOrganizer()
                text_corrector = TextCorrector()
                successful_corrections = text_corrector.extract_successful_corrections(st.session_state.corrected_results)
                organization_result = data_organizer.organize_data(successful_corrections)

                if organization_result.get("success", False):
                    st.session_state.organized_data = organization_result["data"]
                    st.session_state.workflow_step = 3
                else:
                    st.error(f"データ整理に失敗しました: {organization_result.get('error', '')}")

            st.rerun()

    with col4:
        if st.button("4️⃣ レポート生成", disabled=st.session_state.workflow_step < 3):
            # Markdown変換処理
            with st.spinner("最終レポートを生成中..."):
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
                    st.session_state.workflow_step = 4
                else:
                    st.error(f"レポート生成に失敗しました: {markdown_result.get('error', '')}")

            st.rerun()

    with col5:
        if st.button("🔄 リセット"):
            st.session_state.workflow_step = 0
            st.session_state.ocr_results = None
            st.session_state.corrected_results = None
            st.session_state.organized_data = None
            st.session_state.final_markdown = None
            st.rerun()

    # 結果表示
    if st.session_state.workflow_step >= 1 and st.session_state.ocr_results:
        st.header("📷 ステップ1: OCR処理結果")

        successful_ocr = [r for r in st.session_state.ocr_results if r.get("success", False)]
        st.info(f"OCR処理完了: {len(successful_ocr)}/{len(valid_images)} 枚成功")

        # 各画像とOCR結果を表示
        for i, (image_file, ocr_result) in enumerate(zip(valid_images, st.session_state.ocr_results)):
            st.markdown("---")
            display_image_ocr_result(image_file, ocr_result, i)

    if st.session_state.workflow_step >= 2 and st.session_state.corrected_results:
        st.header("🔧 ステップ2: 文字認識修正結果")
        display_correction_results(st.session_state.corrected_results)

    if st.session_state.workflow_step >= 3 and st.session_state.organized_data:
        st.header("📊 ステップ3: 課題ドリブン整理結果")
        display_organization_results(st.session_state.organized_data)

    if st.session_state.workflow_step >= 4 and st.session_state.final_markdown:
        st.header("📝 ステップ4: 最終レポート")

        # 統計情報
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("処理画像数", len(valid_images))
        with col2:
            st.metric("識別課題数", len(st.session_state.organized_data))
        with col3:
            successful_ocr = [r for r in st.session_state.ocr_results if r.get("success", False)]
            st.metric("成功率", f"{len(successful_ocr)/len(valid_images)*100:.1f}%")
        with col4:
            solutions_count = sum(1 for item in st.session_state.organized_data
                                if any(item.get(field) for field in ["personal", "community", "gov", "others"]))
            st.metric("解決策有り", f"{solutions_count}/{len(st.session_state.organized_data)}")

        # Markdownプレビュー
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
