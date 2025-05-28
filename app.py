"""
改善提案シート文字起こしツール - Document AI風UI
Streamlitアプリケーション
"""
import sys
import os
import streamlit as st
import json
import difflib
from datetime import datetime
from typing import List, Optional, Dict, Any
import config
from common.ocr_processor import OCRProcessor
from phase1.text_corrector import TextCorrector
from phase1.data_organizer import DataOrganizer
from phase1.markdown_formatter import MarkdownFormatter
from common.ocr_visualizer import OCRVisualizer
from phase2.multi_section_processor import MultiSectionProcessor
import time
import hashlib
from PIL import Image
import io

# Streamlit Cloud環境ではst.secretsからenvをセット
if hasattr(st, "secrets") and st.secrets:
    # 環境変数をセット
    for key in ["GOOGLE_CLOUD_PROJECT_ID", "GOOGLE_CLOUD_LOCATION", 
                "GOOGLE_CLOUD_PROCESSOR_ID", "GOOGLE_CLOUD_DOCUMENTAI_ENDPOINT", 
                "OPENAI_API_KEY"]:
        if key in st.secrets:
            os.environ[key] = str(st.secrets[key])
    
    # Google Service Account JSONを一時ファイルとして作成
    if "google_service_account" in st.secrets:
        import tempfile
        service_account_info = dict(st.secrets["google_service_account"])
        # 必要なフィールドを確実に含める
        service_account_info["type"] = "service_account"
        
        # 一時ファイルに書き込み
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(service_account_info, f)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def check_api_key() -> bool:
    """
    Google Document AI設定の確認

    Returns:
        bool: Document AI設定が正しく設定されているかどうか
    """
    return bool(config.GOOGLE_CLOUD_PROJECT_ID and config.GOOGLE_CLOUD_PROCESSOR_ID)


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


def correct_and_organize_text(edited_data: dict) -> Dict[str, Any]:
    """
    編集されたテキストをAIで修正・整理する

    Args:
        edited_data: 編集されたテキストデータ

    Returns:
        修正・整理された結果
    """
    try:
        # TextCorrector と DataOrganizer のインスタンス化
        corrector = TextCorrector()
        organizer = DataOrganizer()

        # テキストを一つの辞書として整形
        ocr_data = {
            "text": "\n".join([f"{k}: {v}" for k, v in edited_data.items() if v]),
            "categories": edited_data
        }

        # OCR結果として整形
        ocr_result = {
            "success": True,
            "data": ocr_data,
            "source": "manual_edit"
        }

        # テキスト修正
        correction_result = corrector.correct_single_result(ocr_result)

        if correction_result.get("success"):
            # 修正されたデータを整理
            corrected_data = correction_result.get("data", {})

            # データを適切な形式に変換
            if isinstance(corrected_data, dict):
                items_to_organize = [corrected_data]
            else:
                items_to_organize = corrected_data if isinstance(corrected_data, list) else [corrected_data]

            # 課題ベースで整理
            organization_result = organizer.organize_data(items_to_organize)
            if organization_result.get("success"):
                organized_data = organization_result["data"]
            else:
                organized_data = []

            return {
                "success": True,
                "corrected_data": corrected_data,
                "organized_data": organized_data,
                "original_data": edited_data
            }
        else:
            return {
                "success": False,
                "error": correction_result.get("error", "修正処理に失敗しました"),
                "original_data": edited_data
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "original_data": edited_data
        }


def display_image_ocr_correction_result(image_file, ocr_result: Dict[str, Any], correction_result: Dict[str, Any], index: int):
    """
    画像、OCR結果、修正結果を並べて表示

    Args:
        image_file: 画像ファイル
        ocr_result: OCR処理結果
        correction_result: 修正処理結果
        index: インデックス（一意のキー生成用）
    """
    # 印刷されたラベルのリスト
    PRINTED_LABELS = [
        "あなたが考える現状の課題",
        "この課題を解決する方法",
        "その課題を解決する方法",
        "（住民の役割）",
        "住民の役割",
        "・個人としてできること",
        "個人としてできること",
        "・地域としてできること",
        "地域としてできること",
        "（行政の役割）",
        "行政の役割",
        "（その他）",
        "その他"
    ]

    # ラベルとカテゴリのマッピング
    LABEL_MAPPING = {
        "あなたが考える現状の課題": "あなたが考える現状の課題",
        "個人としてできること": "個人としてできること",
        "地域としてできること": "地域としてできること",
        "行政の役割": "行政の役割",
        "その他": "その他"
    }

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📷 元画像とハイライト")

        # OCR結果がある場合はハイライト表示
        if ocr_result and ocr_result.get("success", False):
            visualizer = OCRVisualizer()
            # ハイライト表示（デフォルトでparagraphsレベル）
            visualizer.display_ocr_results_with_highlights(image_file, ocr_result)
        else:
            st.error("OCR処理が失敗したため、ハイライト表示できません")
            st.image(image_file, caption="元画像", use_column_width=True)

    with col2:
        st.subheader("📝 手書き内容の読み取り結果")

        # OCR結果の表示（段落ごと）
        if ocr_result.get("success", False):
            # OCRデータの表示
            if "data" in ocr_result and ocr_result["data"]:
                try:
                    # JSONデータをパースして表示
                    if isinstance(ocr_result["data"], str):
                        ocr_data = json.loads(ocr_result["data"])
                    else:
                        ocr_data = ocr_result["data"]

                    # データの種類に応じて表示
                    source = ocr_result.get("source", "unknown")
                    if source == "document_ai":
                        # Document AI の結果表示 - paragraphsレベルのみ
                        if ocr_data.get("pages") and ocr_data["pages"]:
                            page = ocr_data["pages"][0]
                            paragraphs = page.get("paragraphs", [])

                            if paragraphs:
                                st.info("各項目の手書き内容を確認し、必要に応じて修正してください。")

                                # 段落を分類して表示
                                current_category = None
                                categorized_paragraphs = []

                                for i, paragraph in enumerate(paragraphs):
                                    if isinstance(paragraph, dict) and 'text' in paragraph:
                                        text = paragraph['text'].strip()

                                        # 印刷されたラベルかどうかチェック
                                        is_label = False
                                        for label in PRINTED_LABELS:
                                            if label in text or text in label:
                                                is_label = True
                                                # カテゴリを更新
                                                for key, value in LABEL_MAPPING.items():
                                                    if key in text:
                                                        current_category = value
                                                        break
                                                break

                                        if not is_label and text:
                                            # 手書き内容として処理
                                            categorized_paragraphs.append({
                                                'category': current_category or '未分類',
                                                'text': text,
                                                'confidence': paragraph.get('confidence', 0),
                                                'index': i
                                            })

                                # カテゴリごとにグループ化
                                category_groups = {}
                                for item in categorized_paragraphs:
                                    category = item['category']
                                    if category not in category_groups:
                                        category_groups[category] = []
                                    category_groups[category].append(item)

                                # カテゴリアイコン
                                category_icons = {
                                    "あなたが考える現状の課題": "🎯",
                                    "個人としてできること": "👤",
                                    "地域としてできること": "👥",
                                    "行政の役割": "🏛️",
                                    "その他": "📌",
                                    "未分類": "❓"
                                }

                                # 定義されたカテゴリの順序
                                category_order = [
                                    "あなたが考える現状の課題",
                                    "個人としてできること",
                                    "地域としてできること",
                                    "行政の役割",
                                    "その他"
                                ]

                                # カテゴリごとに表示（定義された順序で、空でも必ず表示）
                                for category in category_order:
                                    icon = category_icons.get(category, "❓")
                                    if category in category_groups:
                                        items = category_groups[category]
                                        # 複数項目がある場合は改行で結合
                                        combined_text = "\n".join([item['text'] for item in items])
                                        # 最高信頼度を表示
                                        max_confidence = max([item['confidence'] for item in items])
                                        confidence_info = ""
                                        if max_confidence > 0:
                                            confidence_info = f" (信頼度: {max_confidence:.2%})"
                                        # 一意のキーを生成
                                        paragraph_key = f"paragraph_{index}_{category}"
                                        # 編集可能なテキストエリア
                                        edited_text = st.text_area(
                                            f"{icon} {category}{confidence_info}",
                                            combined_text,
                                            height=100,
                                            key=paragraph_key,
                                            help="このテキストを直接編集できます"
                                        )
                                        # 編集されたテキストを保存（セッション状態に）
                                        if f"edited_paragraphs_{index}" not in st.session_state:
                                            st.session_state[f"edited_paragraphs_{index}"] = {}
                                        st.session_state[f"edited_paragraphs_{index}"][category] = {
                                            'text': edited_text,
                                            'category': category,
                                            'items': items
                                        }
                                    else:
                                        # 空のテキストエリア
                                        paragraph_key = f"paragraph_{index}_{category}_empty"
                                        edited_text = st.text_area(
                                            f"{icon} {category}",
                                            "",
                                            height=100,
                                            key=paragraph_key,
                                            help="このテキストを直接編集できます",
                                            placeholder="（未入力）"
                                        )
                                        # 編集されたテキストを保存
                                        if f"edited_paragraphs_{index}" not in st.session_state:
                                            st.session_state[f"edited_paragraphs_{index}"] = {}
                                        if edited_text:  # 空でない場合のみ保存
                                            st.session_state[f"edited_paragraphs_{index}"][category] = {
                                                'text': edited_text,
                                                'category': category,
                                                'items': []
                                            }
                            else:
                                st.warning("段落データが見つかりません")
                    elif isinstance(ocr_data, list):
                        # OpenAI の結果表示（構造化されたデータ）
                        field_mapping = [
                            ('problem', '🎯 あなたが考える現状の課題'),
                            ('personal', '👤 個人としてできること'),
                            ('community', '👥 地域としてできること'),
                            ('gov', '🏛️ 行政の役割'),
                            ('others', '📌 その他')
                        ]
                        for i, item in enumerate(ocr_data):
                            if isinstance(item, dict):
                                # すべてのフィールドを表示（空のフィールドも含む、順序通り）
                                for field_key, display_label in field_mapping:
                                    # 一意のキーを生成
                                    unique_key = f"ocr_{index}_{i}_{field_key}"
                                    # 値を取得（存在しない場合は空文字）
                                    display_value = ""
                                    if field_key in item:
                                        try:
                                            display_value = str(item[field_key]) if item[field_key] else ""
                                        except UnicodeEncodeError:
                                            display_value = str(item[field_key]).encode('utf-8', errors='ignore').decode('utf-8') if item[field_key] else ""
                                    # 編集可能なテキストエリア（空でも表示）
                                    edited_value = st.text_area(
                                        display_label,
                                        display_value,
                                        height=80,
                                        key=unique_key,
                                        help="このテキストを直接編集できます",
                                        placeholder="（未入力）" if not display_value else None
                                    )
                                    # 編集されたテキストを保存
                                    if f"edited_items_{index}" not in st.session_state:
                                        st.session_state[f"edited_items_{index}"] = {}
                                    if i not in st.session_state[f"edited_items_{index}"]:
                                        st.session_state[f"edited_items_{index}"][i] = {}
                                    st.session_state[f"edited_items_{index}"][i][field_key] = edited_value
                            else:
                                st.text(str(item))
                            if i < len(ocr_data) - 1:
                                st.markdown("---")
                    else:
                        st.json(ocr_data)

                except json.JSONDecodeError as e:
                    st.error(f"OCR結果のJSONパースに失敗しました: {str(e)}")
                    if "raw_text" in ocr_result:
                        raw_key = f"raw_ocr_{index}"
                        st.text_area("生のOCR結果", ocr_result["raw_text"], height=200, key=raw_key)
            else:
                st.warning("OCRデータが見つかりません")
        else:
            st.error(f"❌ OCR処理失敗: {ocr_result.get('error', '不明なエラー')}")

        # AI修正結果の表示は削除（エラーのみ表示）
        if correction_result and not correction_result.get("success", False):
            error_msg = correction_result.get('error', '不明なエラー')
            try:
                display_error = str(error_msg)
            except UnicodeEncodeError:
                display_error = str(error_msg).encode('utf-8', errors='ignore').decode('utf-8')
            st.error(f"❌ AI修正処理失敗: {display_error}")

        # --- 文字修正と整理 ---
        st.markdown("---")
        st.subheader("📝 文字修正・整理")

        # 編集内容を収集する関数
        def get_edited_data():
            edited_data = {}
            # Document AI
            if ocr_result.get("source", "") == "document_ai":
                for category in [
                    "あなたが考える現状の課題",
                    "個人としてできること",
                    "地域としてできること",
                    "行政の役割",
                    "その他"
                ]:
                    key = f"edited_paragraphs_{index}"
                    if key in st.session_state and category in st.session_state[key]:
                        edited_data[category] = st.session_state[key][category]['text']
            # OpenAI
            elif ocr_result.get("source", "") == "openai":
                key = f"edited_items_{index}"
                if key in st.session_state:
                    for i, item in st.session_state[key].items():
                        for field_key, field_label in [
                            ('problem', 'あなたが考える現状の課題'),
                            ('personal', '個人としてできること'),
                            ('community', '地域としてできること'),
                            ('gov', '行政の役割'),
                            ('others', 'その他')
                        ]:
                            if field_key in item:
                                edited_data[field_label] = item[field_key]
            return edited_data

        # 保存ボタン
        if st.button("💾 編集内容を保存して文字修正する", key=f"save_and_correct_{index}"):
            # 編集内容の取得
            edited_data = get_edited_data()

            # 処理中の表示
            with st.spinner("🔄 テキストを修正・整理しています..."):
                correction_organized_result = correct_and_organize_text(edited_data)
                st.session_state[f"correction_result_{index}"] = correction_organized_result

        # 結果の表示
        correction_key = f"correction_result_{index}"
        if correction_key in st.session_state:
            result = st.session_state[correction_key]

            if result.get("success"):
                # 成功時の表示
                st.success("✅ 文字修正が完了しました")

                # 修正結果の表示（ハイライト付き）
                st.markdown("### 🔍 修正結果")

                corrected_data = result.get("corrected_data", {})
                original_data = result.get("original_data", {})

                # カテゴリごとに修正結果を表示
                for category in [
                    "あなたが考える現状の課題",
                    "個人としてできること",
                    "地域としてできること",
                    "行政の役割",
                    "その他"
                ]:
                    if category in original_data and original_data[category]:
                        # 修正後のテキストを取得
                        if isinstance(corrected_data, dict) and "categories" in corrected_data:
                            corrected_text = corrected_data.get("categories", {}).get(category, original_data[category])
                        else:
                            corrected_text = original_data[category]

                        # 変更がある場合のみ表示
                        if corrected_text != original_data[category]:
                            display_field_comparison(category, original_data[category], corrected_text)
                        else:
                            st.markdown(f"**{category}:** {corrected_text}")

                # 整理されたデータの表示
                organized_data = result.get("organized_data", [])
                if organized_data:
                    st.markdown("### 📊 課題ベースでの整理結果")

                    for i, problem_data in enumerate(organized_data):
                        with st.container():
                            st.markdown(f"#### 課題 {i + 1}: {problem_data.get('problem', '不明な課題')}")
                            col1, col2 = st.columns(2)

                            with col1:
                                st.markdown("**個人としてできること:**")
                                personal = problem_data.get('personal', [])
                                if isinstance(personal, list):
                                    for item in personal:
                                        st.markdown(f"- {item}")
                                elif personal:
                                    for item in str(personal).split("\n"):
                                        if item.strip():
                                            st.markdown(f"- {item.strip()}")
                                else:
                                    st.markdown("- なし")

                                st.markdown("**地域としてできること:**")
                                community = problem_data.get('community', [])
                                if isinstance(community, list):
                                    for item in community:
                                        st.markdown(f"- {item}")
                                elif community:
                                    for item in str(community).split("\n"):
                                        if item.strip():
                                            st.markdown(f"- {item.strip()}")
                                else:
                                    st.markdown("- なし")

                            with col2:
                                st.markdown("**行政の役割:**")
                                gov = problem_data.get('gov', [])
                                if isinstance(gov, list):
                                    for item in gov:
                                        st.markdown(f"- {item}")
                                elif gov:
                                    for item in str(gov).split("\n"):
                                        if item.strip():
                                            st.markdown(f"- {item.strip()}")
                                else:
                                    st.markdown("- なし")

                                st.markdown("**その他:**")
                                others = problem_data.get('others', [])
                                if isinstance(others, list):
                                    for item in others:
                                        st.markdown(f"- {item}")
                                elif others:
                                    for item in str(others).split("\n"):
                                        if item.strip():
                                            st.markdown(f"- {item.strip()}")
                                else:
                                    st.markdown("- なし")

            else:
                # エラー時の表示
                st.error(f"❌ 修正・整理処理でエラーが発生しました: {result.get('error', '不明なエラー')}")
                st.info("編集内容はそのまま保持されています。")


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
                        for item in str(personal).split("\n"):
                            if item.strip():
                                st.markdown(f"- {item.strip()}")
                    else:
                        st.markdown("- なし")

                    st.markdown("**地域としてできること:**")
                    community = problem.get('community', [])
                    if isinstance(community, list):
                        for item in community:
                            st.markdown(f"- {item}")
                    elif community:
                        for item in str(community).split("\n"):
                            if item.strip():
                                st.markdown(f"- {item.strip()}")
                    else:
                        st.markdown("- なし")

                with col2:
                    st.markdown("**行政の役割:**")
                    gov = problem.get('gov', [])
                    if isinstance(gov, list):
                        for item in gov:
                            st.markdown(f"- {item}")
                    elif gov:
                        for item in str(gov).split("\n"):
                            if item.strip():
                                st.markdown(f"- {item.strip()}")
                    else:
                        st.markdown("- なし")

                    st.markdown("**その他:**")
                    others = problem.get('others', [])
                    if isinstance(others, list):
                        for item in others:
                            st.markdown(f"- {item}")
                    elif others:
                        for item in str(others).split("\n"):
                            if item.strip():
                                st.markdown(f"- {item.strip()}")
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
    .mode-selector {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #2196f3;
    }
    </style>
    """, unsafe_allow_html=True)

    # ヘッダー
    st.markdown("""
    <div class="main-header">
        <h1>🤖 改善提案シート文字起こしツール</h1>
    </div>
    """, unsafe_allow_html=True)

    # ここに処理モード選択をすぐ続けて配置
    # st.markdown('<div class="mode-selector">', unsafe_allow_html=True)
    st.subheader("🎯 処理モード選択")
    processing_mode = st.radio(
        "処理モードを選択してください:",
        [
            "🟢 通常モード（1枚画像=1提案）",
            "🧪 ベータ: 複数セクション画像対応（1枚画像=複数提案）"
        ],
        help="🟢 通常モード: 1by1データ用。1枚の画像に1つの提案が書かれている場合はこちらを選択してください。\n🧪 ベータ: 1personデータ用。1枚の画像に複数の提案（セクション）が含まれている場合はこちらを選択してください。"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # APIキーの確認
    if not check_api_key():
        st.error("Google Document AI設定が正しく設定されていません。.envファイルにGOOGLE_CLOUD_PROJECT_IDとGOOGLE_CLOUD_PROCESSOR_IDを設定してください。")
        st.stop()

    if processing_mode == "🧪 ベータ: 複数セクション画像対応（1枚画像=複数提案）":
        # Phase 2: 複数セクション処理モード
        display_multi_section_mode()
    else:
        # Phase 1: 単一セクション処理モード（既存の処理）
        display_single_section_mode()


def display_multi_section_mode():
    """複数セクション処理モードの表示"""
    st.header("📑 1枚の画像に複数の提案が含まれた画像を受け付けます")


    if 'multi_processor' not in st.session_state:
        st.session_state.multi_processor = MultiSectionProcessor()
    if 'multi_processing_complete' not in st.session_state:
        st.session_state.multi_processing_complete = False

    # ファイルアップロード
    # st.subheader("📁 複数セクション画像アップロード")
    uploaded_image = st.file_uploader(
        "複数セクションが含まれた改善提案シート画像をアップロード",
        type=['jpg', 'jpeg', 'png', 'gif', 'webp'],
        help="1personディレクトリのような複数セクションが含まれた画像をアップロードしてください"
    )

    if uploaded_image:
        st.success(f"✅ 画像ファイル '{uploaded_image.name}' が準備完了")

        # 処理実行ボタン
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🚀 複数セクション処理を開始", type="primary"):
                with st.spinner("複数セクション処理を実行中..."):
                    result = st.session_state.multi_processor.process_multi_section_image(uploaded_image)
                    if result.get("success", False):
                        st.session_state.multi_processing_complete = True
                        st.rerun()

        with col2:
            if st.button("🔄 処理結果をリセット"):
                st.session_state.multi_processor._reset_processing_state()
                st.session_state.multi_processing_complete = False
                st.success("処理結果をリセットしました。")
                st.rerun()

        # 処理結果の表示
        if st.session_state.multi_processing_complete:
            st.markdown("---")

            # タブで結果表示を切り替え
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "🔍 セクション分析",
                "📝 OCR結果",
                "✏️ 修正",
                "📊 サマリー",
                "💾 エクスポート"
            ])

            with tab1:
                st.session_state.multi_processor.display_section_analysis_results()

            with tab2:
                st.session_state.multi_processor.display_section_ocr_results()

            with tab3:
                st.session_state.multi_processor.display_section_correction_interface()

            with tab4:
                st.session_state.multi_processor.display_category_summary()

            with tab5:
                st.session_state.multi_processor.display_export_options()

    else:
        st.warning("複数セクションが含まれた改善提案シートの画像をアップロードしてください。")

        # サンプル画像の説明
        with st.expander("📖 複数セクション処理について"):
            st.markdown("""
            **Phase 2: 複数セクション処理機能**

            この機能は、1つの画像に複数のセクション（課題、提案、対象など）が含まれた
            改善提案シートを自動的に分析・処理します。

            **主な機能:**
            - 🔍 **自動セクション検出**: 画像内の複数セクションを自動検出
            - ✂️ **セクション分割**: 検出されたセクションを個別に切り出し
            - 📝 **一括OCR処理**: 各セクションに対してOCR処理を実行
            - 🏷️ **自動カテゴリ分類**: セクション内容に基づいて自動分類
            - ✏️ **個別修正機能**: セクションごとの内容修正
            - 📊 **カテゴリ別サマリー**: 分類されたセクションの統計表示
            - 💾 **構造化エクスポート**: JSON/Markdownでの結果出力

            **対象データ:** `kaizen_teian_sheets/1person/` のような複数セクション画像
            """)


def display_single_section_mode():
    """単一セクション処理モードの表示（既存の処理）"""
    st.header("📄 1画像1提案の画像をアップロードしてください")

    # サンプル画像の表示
    import os
    sample_dir = os.path.join(os.path.dirname(__file__), "kaizen_teian_sheets", "1by1")
    image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")
    sample_images = [f for f in os.listdir(sample_dir) if f.lower().endswith(image_extensions)]

    if sample_images:
        st.markdown("#### 以下のような画像を添付してください")
        # 1行あたりのカラム数
        cols_per_row = 4
        # 画像をグループ化して表示
        for i in range(0, len(sample_images), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, img_name in enumerate(sample_images[i:i+cols_per_row]):
                img_path = os.path.join(sample_dir, img_name)
                with cols[j]:
                    st.image(img_path, caption=img_name, width=200)
    else:
        st.info("サンプル画像が見つかりませんでした。1by1ディレクトリに画像があるか確認してください。")

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

    # # ワークフロー表示
    # st.markdown('<div class="workflow-container">', unsafe_allow_html=True)
    # st.subheader("📋 処理ワークフロー")

    # col1, col2 = st.columns(2)

    # with col1:
    #     status1 = "completed" if st.session_state.workflow_step > 0 else "pending"
    #     display_workflow_step(1, "OCR処理 + 文字修正", status1)

    # with col2:
    #     status2 = "completed" if st.session_state.workflow_step > 1 else "pending"
    #     display_workflow_step(2, "データ整理 + レポート生成", status2)

    # st.markdown('</div>', unsafe_allow_html=True)

    # ファイルアップロード（改善提案シートのみ）
    # st.subheader("📁 ファイルアップロード")

    # st.write("改善提案シート（必須）")
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

        # --- ここから自動実行ロジック追加 ---
        # ファイル名リストでアップロード内容の変化を検知
        uploaded_names = [f.name for f in valid_images]
        prev_uploaded_names = st.session_state.get('prev_uploaded_names', None)
        # すでに処理済みかどうか判定
        already_processed = (
            st.session_state.get('ocr_results') is not None and
            st.session_state.get('corrected_results') is not None and
            st.session_state.get('workflow_step', 0) >= 1 and
            st.session_state.get('prev_uploaded_names') == uploaded_names
        )
        # ファイルが新しくアップロードされた場合のみ自動実行
        if not already_processed:
            st.session_state.workflow_step = 0
            reference_texts = []  # 参考資料は使用しない
            with st.spinner("自動でOCR処理と文字修正を実行中..."):
                ocr_results, corrected_results = process_ocr_and_correction(valid_images, reference_texts)
                st.session_state.ocr_results = ocr_results
                st.session_state.corrected_results = corrected_results
                st.session_state.workflow_step = 1
                st.session_state.prev_uploaded_names = uploaded_names
            st.rerun()
    else:
        st.warning("サンプル画像と同じフォーマットの改善提案シートの画像をアップロードしてください。")
        st.stop()

    # 処理ボタン群
    st.subheader("🚀 処理実行")

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
            st.subheader("📷 ステップ1: OCR処理 + 文字修正結果")

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

        # 整理されたデータの表示
        display_organization_results(st.session_state.organized_data)

        # 最終レポートの表示とダウンロード
        st.subheader("📄 最終レポート")

        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(st.session_state.final_markdown)

        with col2:
            st.download_button(
                label="📥 Markdownファイルをダウンロード",
                data=st.session_state.final_markdown,
                file_name=f"kaizen_teian_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )

            # JSONデータのダウンロード
            json_data = json.dumps(st.session_state.organized_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 JSONファイルをダウンロード",
                data=json_data,
                file_name=f"kaizen_teian_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )


def summarize_with_openai(edited_data: dict) -> str:
    """
    編集内容をOpenAIの要約プロンプトに投げて要約を取得する関数。
    """
    from openai import OpenAI
    import os
    import json

    # APIキー取得
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        st.error("OpenAI APIキーが設定されていません。環境変数 OPENAI_API_KEY を設定してください。")
        return "APIキー未設定"

    client = OpenAI(api_key=openai_api_key)

    # プロンプト作成
    prompt = """
あなたは日本語の要約AIです。以下の各項目の内容を簡潔にまとめてください。

"""
    for k, v in edited_data.items():
        prompt += f"【{k}】\n{v}\n"
    prompt += "\n全体を200文字以内で要約してください。"

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは日本語の要約AIです。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=256,
            temperature=0.3
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        st.error(f"OpenAI API呼び出しでエラー: {e}")
        return f"要約失敗: {e}"


if __name__ == "__main__":
    main()
