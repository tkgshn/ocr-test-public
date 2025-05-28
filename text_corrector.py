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
        # APIキーが非ASCII文字を含む可能性があるため、安全に処理
        api_key = config.OPENAI_API_KEY
        if api_key:
            # APIキーをUTF-8でエンコード可能か確認
            try:
                api_key.encode('utf-8')
            except UnicodeEncodeError:
                # エンコードエラーがある場合は無視
                api_key = api_key.encode('utf-8', errors='ignore').decode('utf-8')
        
        # カスタムHTTPヘッダーを設定して日本語問題を回避
        import httpx
        http_client = httpx.Client(
            headers={"Accept-Charset": "utf-8"}
        )
        
        self.client = OpenAI(
            api_key=api_key,
            http_client=http_client
        )

    def correct_single_result(self, ocr_result: Dict[str, Any], reference_texts: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        単一のOCR結果を修正する

        Args:
            ocr_result: 修正対象のOCR結果（Dict形式）
            reference_texts: 参考資料のテキストリスト

        Returns:
            Dict[str, Any]: 修正結果
        """
        try:
            # OCRが成功していない場合は修正しない
            if not ocr_result.get("success", False):
                return {
                    "success": False,
                    "error": "OCR処理が失敗しているため修正できません",
                    "corrected_text": "",
                    "original_text": ""
                }

            # OCRデータからテキスト部分のみを抽出（座標データを除外）
            ocr_data = ocr_result.get("data", {})
            print(f"[DEBUG] OCRデータの型: {type(ocr_data)}")

            # テキストのみを抽出する関数
            def extract_text_only(data):
                if isinstance(data, dict):
                    # Document AIの場合
                    if "text" in data:
                        return {"text": data["text"]}
                    # OpenAIの場合
                    elif "pages" in data:
                        text_only_data = {"text": data.get("text", "")}
                        return text_only_data
                    else:
                        # その他の辞書型データ
                        text_data = {}
                        for key, value in data.items():
                            if key in ["text", "content"] or (isinstance(value, str) and len(value) > 0):
                                if not key.startswith(("bounding_box", "confidence", "normalized_vertices", "dimensions")):
                                    text_data[key] = value
                        return text_data
                elif isinstance(data, list):
                    # リスト形式のデータ（OpenAIの構造化結果など）
                    text_only_list = []
                    for item in data:
                        if isinstance(item, dict):
                            text_item = {}
                            for key, value in item.items():
                                if isinstance(value, str) and len(value.strip()) > 0:
                                    text_item[key] = value
                            if text_item:
                                text_only_list.append(text_item)
                        elif isinstance(item, str):
                            text_only_list.append(item)
                    return text_only_list
                else:
                    return data

            # テキストのみを抽出
            text_only_data = extract_text_only(ocr_data)
            print(f"[DEBUG] テキストのみのデータ: {str(text_only_data)[:200]}")

            # JSON文字列として変換（座標データなしなのでエラーが起きにくい）
            try:
                raw_text = json.dumps(text_only_data, ensure_ascii=False, indent=2)
                print(f"[DEBUG] JSON変換成功、長さ: {len(raw_text)}")
            except Exception as e:
                print(f"[DEBUG] JSON変換エラー: {str(e)}")
                # フォールバック: 単純な文字列として処理
                if isinstance(text_only_data, dict) and "text" in text_only_data:
                    raw_text = text_only_data["text"]
                else:
                    raw_text = str(text_only_data)
                print(f"[DEBUG] フォールバック処理、長さ: {len(raw_text)}")

            # 参考資料の情報を含めたプロンプトを作成
            reference_info = ""
            if reference_texts:
                safe_references = []
                for ref in reference_texts:
                    try:
                        safe_ref = str(ref)
                    except UnicodeEncodeError:
                        safe_ref = str(ref).encode('utf-8', errors='ignore').decode('utf-8')
                    safe_references.append(safe_ref)
                reference_info = f"\n参考資料:\n{chr(10).join(safe_references)}"

            # プロンプトを安全に処理
            try:
                prompt = config.CORRECTION_SYSTEM_PROMPT.format(
                    ocr_result=raw_text
                ) + reference_info
            except Exception as e:
                print(f"[DEBUG] プロンプト生成エラー: {str(e)}")
                # フォールバック: シンプルなプロンプト
                prompt = f"以下のOCR結果を修正してください:\n{raw_text}"

            print(f"[DEBUG] OpenAI APIに送信するプロンプト長: {len(prompt)}")

            # OpenAI APIに送信
            try:
                # メッセージをUTF-8でエンコード可能な形式に変換
                system_content = prompt
                user_content = f"以下のOCR結果を修正してください:\n{raw_text}"
                
                # ASCIIでエンコードできない文字をエスケープ
                try:
                    system_content.encode('ascii')
                    user_content.encode('ascii')
                except UnicodeEncodeError:
                    # 日本語が含まれている場合は、UTF-8でエンコード可能か確認
                    system_content = system_content.encode('utf-8', errors='replace').decode('utf-8')
                    user_content = user_content.encode('utf-8', errors='replace').decode('utf-8')
                
                response = self.client.chat.completions.create(
                    model=config.OPENAI_MODEL_TEXT,
                    messages=[
                        {
                            "role": "system",
                            "content": system_content
                        },
                        {
                            "role": "user",
                            "content": user_content
                        }
                    ],
                    temperature=config.TEMPERATURE_CORRECTION,
                    max_tokens=2000
                )
            except Exception as e:
                print(f"[DEBUG] OpenAI API呼び出しエラー: {str(e)}")
                print(f"[DEBUG] エラータイプ: {type(e)}")
                # エラーの詳細を確認
                import traceback
                traceback.print_exc()

                return {
                    "success": False,
                    "error": f"OpenAI API呼び出しエラー: {str(e)}",
                    "corrected_text": "",
                    "original_text": raw_text
                }

            # レスポンスからテキストを抽出
            corrected_text = response.choices[0].message.content
            print(f"[DEBUG] OpenAI応答長: {len(corrected_text)}")
            print(f"[DEBUG] OpenAI応答の最初の200文字: {corrected_text[:200]}")

            # JSONとしてパース
            try:
                # コードブロックを除去
                clean_text = corrected_text.strip()
                print(f"[DEBUG] 清理前のテキスト開始: {clean_text[:50]}")

                if clean_text.startswith('```json'):
                    clean_text = clean_text[7:]  # ```json を除去
                    print("[DEBUG] ```json を除去")
                if clean_text.endswith('```'):
                    clean_text = clean_text[:-3]  # ``` を除去
                    print("[DEBUG] ``` を除去")
                clean_text = clean_text.strip()

                print(f"[DEBUG] 清理後のテキスト開始: {clean_text[:50]}")
                print(f"[DEBUG] 清理後のテキスト終了: {clean_text[-50:]}")

                corrected_json = json.loads(clean_text)
                print(f"[DEBUG] JSON解析成功、型: {type(corrected_json)}")

                return {
                    "success": True,
                    "data": corrected_json,
                    "corrected_text": corrected_text,
                    "original_text": raw_text
                }
            except json.JSONDecodeError as e:
                print(f"[DEBUG] JSON解析エラー: {str(e)}")
                print(f"[DEBUG] エラー位置: line {e.lineno}, column {e.colno}")
                print(f"[DEBUG] 解析対象テキスト: {clean_text}")

                return {
                    "success": False,
                    "error": f"修正結果のJSONパースエラー: {str(e)} (位置: line {e.lineno}, col {e.colno})",
                    "corrected_text": corrected_text,
                    "original_text": raw_text,
                    "clean_text": clean_text  # デバッグ用
                }

        except Exception as e:
            print(f"[DEBUG] 予期しないエラー: {str(e)}")
            print(f"[DEBUG] エラータイプ: {type(e)}")

            # エラーメッセージも安全に処理
            try:
                error_msg = str(e)
            except UnicodeEncodeError:
                error_msg = str(e).encode('utf-8', errors='ignore').decode('utf-8')

            return {
                "success": False,
                "error": f"修正処理中の予期しないエラー: {error_msg}",
                "corrected_text": "",
                "original_text": ocr_result.get("raw_text", "")
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
                correction_result = self.correct_single_result(ocr_result, reference_texts)
                corrected_results.append(correction_result)
            else:
                # OCRが失敗した場合は失敗結果を返す
                corrected_results.append({
                    "success": False,
                    "error": "OCR処理が失敗しているため修正できません",
                    "corrected_text": "",
                    "original_text": ""
                })

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
            if result.get("success", False):
                correction_data = result.get("data", [])
                # リスト形式でない場合はリストに変換
                if isinstance(correction_data, list):
                    successful_data.extend(correction_data)
                else:
                    successful_data.append(correction_data)

        return successful_data
