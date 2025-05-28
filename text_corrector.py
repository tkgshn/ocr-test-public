"""
文字認識修正クラス
OCR結果の誤認識を修正する
"""
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
import config


class TextCorrector:
    """
    文字認識結果の修正を行うクラス
    """

    def __init__(self):
        """
        初期化
        """
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

    def correct_single_result(self, ocr_result: str, reference_texts: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        単一のOCR結果を修正する

        Args:
            ocr_result: 修正対象のOCR結果（JSON文字列）
            reference_texts: 参考資料のテキストリスト

        Returns:
            Dict[str, Any]: 修正結果
        """
        try:
            # 参考資料の情報を含めたプロンプトを作成
            reference_info = ""
            if reference_texts:
                reference_info = f"\n参考資料:\n{chr(10).join(reference_texts)}"

            prompt = config.CORRECTION_SYSTEM_PROMPT.format(
                ocr_result=ocr_result
            ) + reference_info

            # OpenAI APIに送信
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL_TEXT,
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": f"以下のOCR結果を修正してください:\n{ocr_result}"
                    }
                ],
                temperature=config.TEMPERATURE_CORRECTION,
                max_tokens=2000
            )

            # レスポンスからテキストを抽出
            corrected_text = response.choices[0].message.content

            # JSONとしてパース
            try:
                # コードブロックを除去
                clean_text = corrected_text.strip()
                if clean_text.startswith('```json'):
                    clean_text = clean_text[7:]  # ```json を除去
                if clean_text.endswith('```'):
                    clean_text = clean_text[:-3]  # ``` を除去
                clean_text = clean_text.strip()

                corrected_json = json.loads(clean_text)
                return {
                    "success": True,
                    "data": corrected_json,
                    "corrected_text": corrected_text,
                    "original_text": ocr_result
                }
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"修正結果のJSONパースエラー: {str(e)}",
                    "corrected_text": corrected_text,
                    "original_text": ocr_result
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "corrected_text": "",
                "original_text": ocr_result
            }

    def correct_multiple_results(self, ocr_results: List[Dict[str, Any]], reference_texts: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        複数のOCR結果を修正する

        Args:
            ocr_results: OCR結果のリスト
            reference_texts: 参考資料のテキストリスト

        Returns:
            List[Dict[str, Any]]: 修正結果のリスト
        """
        corrected_results = []

        for i, ocr_result in enumerate(ocr_results):
            print(f"OCR結果 {i+1}/{len(ocr_results)} を修正中...")

            if ocr_result.get("success", False):
                # OCRが成功した場合のみ修正処理を実行
                # OCRデータをJSON文字列として取得
                ocr_data = ocr_result.get("data", [])
                raw_text = json.dumps(ocr_data, ensure_ascii=False, indent=2)

                correction_result = self.correct_single_result(raw_text, reference_texts)

                # 元のOCR結果に修正結果を追加
                result = ocr_result.copy()
                result["correction"] = correction_result
                corrected_results.append(result)
            else:
                # OCRが失敗した場合はそのまま追加
                corrected_results.append(ocr_result)

        return corrected_results

    def extract_successful_corrections(self, corrected_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        修正に成功した結果のみを抽出する

        Args:
            corrected_results: 修正結果のリスト

        Returns:
            List[Dict[str, Any]]: 成功した修正結果のデータ部分のリスト
        """
        successful_data = []

        for result in corrected_results:
            if (result.get("success", False) and
                result.get("correction", {}).get("success", False)):

                correction_data = result["correction"]["data"]
                # リスト形式でない場合はリストに変換
                if isinstance(correction_data, list):
                    successful_data.extend(correction_data)
                else:
                    successful_data.append(correction_data)

        return successful_data
