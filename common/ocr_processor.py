"""
OCR処理クラス
Google Document AI 専用
"""
import base64
import json
import os
from typing import List, Dict, Any, Optional
# from openai import OpenAI  # OpenAIは使用しない
from PIL import Image
import io
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Google Document AI imports
try:
    from google.api_core.client_options import ClientOptions
    from google.cloud import documentai
    from google.oauth2 import service_account
    DOCUMENTAI_AVAILABLE = True
except ImportError:
    DOCUMENTAI_AVAILABLE = False
    print("Error: Google Document AI not available. Install with: pip install google-cloud-documentai google-auth")
    raise ImportError("Google Document AI is required for this application")


class OCRProcessor:
    """
    OCR処理を行うクラス
    Google Document AI 専用
    """

    def __init__(self, use_document_ai: bool = True):
        """
        初期化

        Args:
            use_document_ai: Google Document AIを使用するかどうか（常にTrue）
        """
        if not DOCUMENTAI_AVAILABLE:
            raise RuntimeError("Google Document AI is not available. Please install required packages.")

        self.use_document_ai = True

        # OpenAI client は使用しない
        # self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

        # Google Document AI client
        self._setup_document_ai()

    def _setup_document_ai(self):
        """Google Document AI クライアントのセットアップ"""
        try:
            # 環境変数から設定を取得
            self.project_id = config.GOOGLE_CLOUD_PROJECT_ID
            self.location = config.GOOGLE_CLOUD_LOCATION
            self.processor_id = config.GOOGLE_CLOUD_PROCESSOR_ID

            if not all([self.project_id, self.processor_id]):
                raise ValueError("Google Cloud credentials not configured. Please set GOOGLE_CLOUD_PROJECT_ID and GOOGLE_CLOUD_PROCESSOR_ID")

            # 認証設定
            credentials = None
            
            # Streamlit secretsからサービスアカウント情報を取得
            try:
                import streamlit as st
                if hasattr(st, 'secrets') and 'google_service_account' in st.secrets:
                    # st.secretsからサービスアカウント情報を作成
                    service_account_info = dict(st.secrets["google_service_account"])
                    credentials = service_account.Credentials.from_service_account_info(
                        service_account_info
                    )
                    print("Using credentials from Streamlit secrets")
            except Exception as e:
                print(f"Could not load credentials from st.secrets: {e}")
            
            # 環境変数のファイルパスから読み込み
            if not credentials and config.GOOGLE_APPLICATION_CREDENTIALS:
                if os.path.exists(config.GOOGLE_APPLICATION_CREDENTIALS):
                    credentials = service_account.Credentials.from_service_account_file(
                        config.GOOGLE_APPLICATION_CREDENTIALS
                    )
                    print(f"Using credentials from file: {config.GOOGLE_APPLICATION_CREDENTIALS}")
                else:
                    print(f"Warning: Service account file not found: {config.GOOGLE_APPLICATION_CREDENTIALS}")
            
            if not credentials:
                print("Warning: No credentials found. Attempting to use Application Default Credentials.")

            # Document AI client の初期化
            endpoint = config.GOOGLE_CLOUD_DOCUMENTAI_ENDPOINT
            # エンドポイントURLを正しく構築（httpsプロトコルは含めない）
            opts = ClientOptions(api_endpoint=endpoint)

            if credentials:
                self.documentai_client = documentai.DocumentProcessorServiceClient(
                    client_options=opts,
                    credentials=credentials
                )
            else:
                # ADCを使用
                self.documentai_client = documentai.DocumentProcessorServiceClient(
                    client_options=opts
                )

            # プロセッサーのフルパス
            self.processor_name = self.documentai_client.processor_path(
                self.project_id, self.location, self.processor_id
            )

            print(f"Document AI initialized: {self.processor_name}")

        except Exception as e:
            raise RuntimeError(f"Failed to setup Document AI: {e}")

    def encode_image(self, image_file) -> str:
        """
        画像をbase64エンコードする

        Args:
            image_file: アップロードされた画像ファイル

        Returns:
            str: base64エンコードされた画像データ
        """
        # PILで画像を開く
        image = Image.open(image_file)

        # RGBAモードの場合はRGBに変換
        if image.mode == 'RGBA':
            # 白い背景を作成
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])  # アルファチャンネルをマスクとして使用
            image = background
        elif image.mode != 'RGB':
            # その他のモードもRGBに変換
            image = image.convert('RGB')

        # 画像をJPEG形式でバイト配列に変換
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        # base64エンコード
        return base64.b64encode(img_byte_arr).decode('utf-8')

    def process_with_document_ai(self, image_file) -> Dict[str, Any]:
        """
        Google Document AIを使用してOCR処理を実行する

        Args:
            image_file: 処理する画像ファイル

        Returns:
            Dict[str, Any]: OCR結果（座標情報付き）
        """
        try:
            # ファイルを読み込み
            if hasattr(image_file, 'read'):
                image_content = image_file.read()
                image_file.seek(0)  # ファイルポインタをリセット
            else:
                with open(image_file, "rb") as f:
                    image_content = f.read()

            # MIMEタイプを推定
            mime_type = "image/jpeg"
            if hasattr(image_file, 'name'):
                if image_file.name.lower().endswith('.png'):
                    mime_type = "image/png"
                elif image_file.name.lower().endswith('.pdf'):
                    mime_type = "application/pdf"

            # Document AI リクエストを作成
            raw_document = documentai.RawDocument(
                content=image_content,
                mime_type=mime_type
            )

            # OCR設定（座標情報を含む詳細な結果を取得）
            process_options = documentai.ProcessOptions(
                ocr_config=documentai.OcrConfig(
                    enable_native_pdf_parsing=True,
                    enable_image_quality_scores=True,
                    enable_symbol=True,
                    premium_features=documentai.OcrConfig.PremiumFeatures(
                        compute_style_info=True,
                        enable_selection_mark_detection=True,
                    ),
                )
            )

            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document,
                process_options=process_options
            )

            # Document AI で処理
            result = self.documentai_client.process_document(request=request)
            document = result.document

            # 結果を構造化
            structured_result = self._structure_document_ai_result(document)

            return {
                "success": True,
                "data": structured_result,
                "raw_document": document,
                "source": "document_ai"
            }

        except Exception as e:
            print(f"Document AI error: {e}")
            return {
                "success": False,
                "error": f"Document AI processing error: {str(e)}",
                "source": "document_ai"
            }

    def _structure_document_ai_result(self, document) -> Dict[str, Any]:
        """
        Document AI の結果を構造化する

        Args:
            document: Document AI の Document オブジェクト

        Returns:
            Dict[str, Any]: 構造化された結果
        """
        result = {
            "text": document.text,
            "pages": [],
            "entities": [],
            "bounding_boxes": []
        }

        # ページ情報を処理
        for page in document.pages:
            page_info = {
                "page_number": page.page_number,
                "dimensions": {
                    "width": page.dimension.width,
                    "height": page.dimension.height,
                    "unit": page.dimension.unit
                },
                "blocks": [],
                "paragraphs": [],
                "lines": [],
                "tokens": []
            }

            # ブロック、段落、行、トークンの座標情報を抽出
            for block in page.blocks:
                if block.layout.bounding_poly:
                    page_info["blocks"].append(self._extract_layout_info(block.layout, document.text))

            for paragraph in page.paragraphs:
                if paragraph.layout.bounding_poly:
                    page_info["paragraphs"].append(self._extract_layout_info(paragraph.layout, document.text))

            for line in page.lines:
                if line.layout.bounding_poly:
                    page_info["lines"].append(self._extract_layout_info(line.layout, document.text))

            for token in page.tokens:
                if token.layout.bounding_poly:
                    page_info["tokens"].append(self._extract_layout_info(token.layout, document.text))

            result["pages"].append(page_info)

        # エンティティ情報を処理
        for entity in document.entities:
            entity_info = {
                "type": entity.type_,
                "text": entity.text_anchor.content if entity.text_anchor else "",
                "confidence": entity.confidence,
                "bounding_box": None
            }

            if entity.page_anchor and entity.page_anchor.page_refs:
                # ページアンカーから座標情報を取得
                page_ref = entity.page_anchor.page_refs[0]
                if hasattr(page_ref, 'bounding_poly') and page_ref.bounding_poly:
                    entity_info["bounding_box"] = self._extract_bounding_poly(page_ref.bounding_poly)

            result["entities"].append(entity_info)

        return result

    def _extract_layout_info(self, layout, full_text: str) -> Dict[str, Any]:
        """
        レイアウト情報から座標とテキストを抽出

        Args:
            layout: Document AI の Layout オブジェクト
            full_text: ドキュメント全体のテキスト

        Returns:
            Dict[str, Any]: 座標とテキスト情報
        """
        info = {
            "text": "",
            "bounding_box": None,
            "confidence": layout.confidence if hasattr(layout, 'confidence') else 0.0
        }

        # テキストを抽出
        if layout.text_anchor and layout.text_anchor.text_segments:
            text_segments = []
            for segment in layout.text_anchor.text_segments:
                start_idx = int(segment.start_index) if segment.start_index else 0
                end_idx = int(segment.end_index) if segment.end_index else len(full_text)
                text_segments.append(full_text[start_idx:end_idx])
            info["text"] = "".join(text_segments)

        # 座標を抽出
        if layout.bounding_poly:
            info["bounding_box"] = self._extract_bounding_poly(layout.bounding_poly)

        return info

    def _extract_bounding_poly(self, bounding_poly) -> Dict[str, Any]:
        """
        バウンディングポリゴンから座標情報を抽出

        Args:
            bounding_poly: Document AI の BoundingPoly オブジェクト

        Returns:
            Dict[str, Any]: 座標情報
        """
        vertices = []
        normalized_vertices = []

        # 通常の座標
        if bounding_poly.vertices:
            for vertex in bounding_poly.vertices:
                vertices.append({
                    "x": vertex.x if hasattr(vertex, 'x') else 0,
                    "y": vertex.y if hasattr(vertex, 'y') else 0
                })

        # 正規化座標 (0-1の範囲)
        if bounding_poly.normalized_vertices:
            for vertex in bounding_poly.normalized_vertices:
                normalized_vertices.append({
                    "x": vertex.x if hasattr(vertex, 'x') else 0,
                    "y": vertex.y if hasattr(vertex, 'y') else 0
                })

        return {
            "vertices": vertices,
            "normalized_vertices": normalized_vertices
        }

    # OpenAI関連のメソッドはコメントアウト
    # def process_with_openai(self, image_file) -> Dict[str, Any]:
    #     """
    #     OpenAI GPT-4 Visionを使用してOCR処理を実行する（フォールバック）
    #
    #     Args:
    #         image_file: 処理する画像ファイル
    #
    #     Returns:
    #         Dict[str, Any]: OCR結果のJSON
    #     """
    #     try:
    #         # 画像をbase64エンコード
    #         base64_image = self.encode_image(image_file)
    #
    #         # OpenAI APIに送信
    #         response = self.openai_client.chat.completions.create(
    #             model=config.OPENAI_MODEL_VISION,
    #             messages=[
    #                 {
    #                     "role": "system",
    #                     "content": config.OCR_SYSTEM_PROMPT
    #                 },
    #                 {
    #                     "role": "user",
    #                     "content": [
    #                         {
    #                             "type": "image_url",
    #                             "image_url": {
    #                                 "url": f"data:image/jpeg;base64,{base64_image}",
    #                                 "detail": config.VISION_DETAIL
    #                             }
    #                         }
    #                     ]
    #                 }
    #             ],
    #             temperature=config.TEMPERATURE_OCR,
    #             max_tokens=2000
    #         )
    #
    #         # レスポンスからテキストを抽出
    #         result_text = response.choices[0].message.content
    #
    #         # JSONとしてパース
    #         try:
    #             # コードブロックを除去
    #             clean_text = result_text.strip()
    #             if clean_text.startswith('```json'):
    #                 clean_text = clean_text[7:]  # ```json を除去
    #             if clean_text.endswith('```'):
    #                 clean_text = clean_text[:-3]  # ``` を除去
    #             clean_text = clean_text.strip()
    #
    #             result_json = json.loads(clean_text)
    #             return {
    #                 "success": True,
    #                 "data": result_json,
    #                 "raw_text": result_text,
    #                 "source": "openai"
    #             }
    #         except json.JSONDecodeError as e:
    #             return {
    #                 "success": False,
    #                 "error": f"JSONパースエラー: {str(e)}",
    #                 "raw_text": result_text,
    #                 "source": "openai"
    #             }
    #
    #     except Exception as e:
    #         return {
    #             "success": False,
    #             "error": str(e),
    #             "raw_text": "",
    #             "source": "openai"
    #         }

    def process_single_image(self, image_file) -> Dict[str, Any]:
        """
        単一の画像に対してOCR処理を実行する
        Google Document AI のみを使用

        Args:
            image_file: 処理する画像ファイル

        Returns:
            Dict[str, Any]: OCR結果のJSON
        """
        # Document AI のみを使用
        return self.process_with_document_ai(image_file)

    def process_multiple_images(self, image_files: List) -> List[Dict[str, Any]]:
        """
        複数の画像に対してOCR処理を実行する

        Args:
            image_files: 処理する画像ファイルのリスト

        Returns:
            List[Dict[str, Any]]: OCR結果のリスト
        """
        results = []

        for i, image_file in enumerate(image_files):
            print(f"画像 {i+1}/{len(image_files)} を処理中...")
            result = self.process_single_image(image_file)
            result["image_index"] = i + 1
            result["filename"] = image_file.name if hasattr(image_file, 'name') else f"image_{i+1}"
            results.append(result)

        return results
