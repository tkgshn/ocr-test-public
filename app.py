"""
改善提案シート文字起こしツール
Streamlitアプリケーション
"""
import streamlit as st
import os
from datetime import datetime
from typing import List, Optional
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


def display_processing_status(step: str, current: int, total: int):
    """
    処理状況を表示する

    Args:
        step: 処理ステップ名
        current: 現在の進行状況
        total: 全体の数
    """
    progress = current / total if total > 0 else 0
    st.progress(progress)
    st.text(f"{step}: {current}/{total}")


def main():
    """
    メイン関数
    """
    st.set_page_config(
        page_title="改善提案シート文字起こしツール",
        page_icon="🤖",
        layout="wide"
    )

    st.title("🤖 改善提案シート文字起こしツール")
    st.markdown("住民会議で回収された改善提案シートの手書き文字をOCRで読み取り、地域の課題ごとに整理します。")

    # APIキーの確認
    if not check_api_key():
        st.error("OpenAI APIキーが設定されていません。.envファイルにOPENAI_API_KEYを設定してください。")
        st.stop()

    # サイドバーでの設定
    st.sidebar.header("設定")
    use_ai_markdown = st.sidebar.checkbox("AIでMarkdown変換", value=True, help="AIを使用してMarkdown形式に変換します")

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

    # 処理実行ボタン
    if st.button("🚀 処理開始", type="primary"):

        # 処理開始
        st.header("⚙️ 処理状況")

        # 各処理クラスのインスタンス化
        ocr_processor = OCRProcessor()
        text_corrector = TextCorrector()
        data_organizer = DataOrganizer()
        markdown_formatter = MarkdownFormatter()

        try:
            # ステップ1: OCR処理
            st.subheader("1. 画像文字認識処理")
            with st.spinner("画像から手書き文字を認識中..."):
                ocr_results = ocr_processor.process_multiple_images(valid_images)

            # OCR結果の表示
            successful_ocr = [r for r in ocr_results if r.get("success", False)]
            st.success(f"OCR処理完了: {len(successful_ocr)}/{len(valid_images)} 枚成功")

            if not successful_ocr:
                st.error("OCR処理に成功した画像がありません。")
                st.stop()

            # ステップ2: 文字認識修正
            st.subheader("2. 文字認識修正処理")
            with st.spinner("認識結果を修正中..."):
                corrected_results = text_corrector.correct_multiple_results(ocr_results, reference_texts)
                successful_corrections = text_corrector.extract_successful_corrections(corrected_results)

            st.success(f"修正処理完了: {len(successful_corrections)} 件のデータを取得")

            if not successful_corrections:
                st.error("修正処理に成功したデータがありません。")
                st.stop()

            # ステップ3: データ整理
            st.subheader("3. 課題ドリブン整理処理")
            with st.spinner("データを課題ごとに整理中..."):
                organization_result = data_organizer.organize_data(successful_corrections)

            if not organization_result.get("success", False):
                st.error(f"データ整理に失敗しました: {organization_result.get('error', '')}")
                st.stop()

            organized_data = organization_result["data"]
            st.success(f"整理処理完了: {len(organized_data)} 件の課題を識別")

            # データ検証
            validation_result = data_organizer.validate_organized_data(organized_data)
            if not validation_result["is_valid"]:
                st.warning("データ検証で問題が見つかりました:")
                for issue in validation_result["issues"]:
                    st.warning(f"- {issue}")

            # ステップ4: Markdown変換
            st.subheader("4. Markdown形式変換")
            with st.spinner("Markdown形式に変換中..."):
                markdown_result = markdown_formatter.format_to_markdown(organized_data, use_ai_markdown)

            if not markdown_result.get("success", False):
                st.error(f"Markdown変換に失敗しました: {markdown_result.get('error', '')}")
                st.stop()

            # メタデータの追加
            metadata = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "image_count": len(valid_images),
                "problem_count": len(organized_data)
            }

            final_markdown = markdown_formatter.add_metadata(
                markdown_result["markdown"],
                metadata
            )

            st.success("Markdown変換完了")

            # 結果表示
            st.header("📊 処理結果")

            # 統計情報
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("処理画像数", len(valid_images))
            with col2:
                st.metric("識別課題数", len(organized_data))
            with col3:
                st.metric("成功率", f"{len(successful_ocr)/len(valid_images)*100:.1f}%")
            with col4:
                solutions_count = sum(1 for item in organized_data
                                    if any(item.get(field) for field in ["personal", "community", "gov", "others"]))
                st.metric("解決策有り", f"{solutions_count}/{len(organized_data)}")

            # Markdownプレビュー
            st.subheader("📝 結果プレビュー")
            st.markdown(final_markdown)

            # ダウンロードボタン
            st.subheader("💾 ダウンロード")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"改善提案シート_整理結果_{timestamp}.md"

            st.download_button(
                label="📥 Markdownファイルをダウンロード",
                data=final_markdown,
                file_name=filename,
                mime="text/markdown"
            )

            # デバッグ情報（展開可能）
            with st.expander("🔍 詳細情報"):
                st.subheader("OCR結果")
                st.json(ocr_results)

                st.subheader("修正結果")
                st.json(corrected_results)

                st.subheader("整理結果")
                st.json(organized_data)

                st.subheader("検証結果")
                st.json(validation_result)

        except Exception as e:
            st.error(f"処理中にエラーが発生しました: {str(e)}")
            st.exception(e)


if __name__ == "__main__":
    main()
