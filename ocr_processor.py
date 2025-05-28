"""
OCR処理クラス
OpenAI GPT-4 Visionを使用して画像から手書き文字を認識する
"""
import base64
import json
from typing import List, Dict, Any
from openai import OpenAI
from PIL import Image
import io
import config


class OCRProcessor:
    """
    OCR処理を行うクラス
    """

    def __init__(self):
        """
        初期化
        """
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

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

    def process_single_image(self, image_file) -> Dict[str, Any]:
        """
        単一の画像に対してOCR処理を実行する

        Args:
            image_file: 処理する画像ファイル

        Returns:
            Dict[str, Any]: OCR結果のJSON
        """
        try:
            # 画像をbase64エンコード
            base64_image = self.encode_image(image_file)

            # OpenAI APIに送信
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL_VISION,
                messages=[
                    {
                        "role": "system",
                        "content": config.OCR_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": config.VISION_DETAIL
                                }
                            }
                        ]
                    }
                ],
                temperature=config.TEMPERATURE_OCR,
                max_tokens=2000
            )

            # レスポンスからテキストを抽出
            result_text = response.choices[0].message.content

            # JSONとしてパース
            try:
                # コードブロックを除去
                clean_text = result_text.strip()
                if clean_text.startswith('```json'):
                    clean_text = clean_text[7:]  # ```json を除去
                if clean_text.endswith('```'):
                    clean_text = clean_text[:-3]  # ``` を除去
                clean_text = clean_text.strip()

                result_json = json.loads(clean_text)
                return {
                    "success": True,
                    "data": result_json,
                    "raw_text": result_text
                }
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"JSONパースエラー: {str(e)}",
                    "raw_text": result_text
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "raw_text": ""
            }

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
