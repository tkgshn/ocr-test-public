"""
データ整理クラス
修正されたOCR結果を課題ドリブンで整理する
"""
import json
from typing import List, Dict, Any
from openai import OpenAI
import config


class DataOrganizer:
    """
    データを課題ドリブンで整理するクラス
    """

    def __init__(self):
        """
        初期化
        """
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

    def format_input_data(self, corrected_data: List[Dict[str, Any]]) -> str:
        """
        修正されたデータを整理用の入力形式にフォーマットする

        Args:
            corrected_data: 修正済みのOCRデータリスト

        Returns:
            str: フォーマットされた入力データ
        """
        formatted_entries = []

        for i, entry in enumerate(corrected_data):
            formatted_entry = f"[image{i+1}]\n{json.dumps(entry, indent=2, ensure_ascii=False)}"
            formatted_entries.append(formatted_entry)

        return "\n\n".join(formatted_entries)

    def organize_data(self, corrected_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        修正されたデータを課題ドリブンで整理する

        Args:
            corrected_data: 修正済みのOCRデータリスト

        Returns:
            Dict[str, Any]: 整理結果
        """
        try:
            # 入力データをフォーマット
            formatted_input = self.format_input_data(corrected_data)

            # OpenAI APIに送信
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL_TEXT,
                messages=[
                    {
                        "role": "system",
                        "content": config.ORGANIZATION_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": f"以下のデータを課題ドリブンで整理してください:\n\n{formatted_input}"
                    }
                ],
                temperature=config.TEMPERATURE_ORGANIZATION,
                max_tokens=3000
            )

            # レスポンスからテキストを抽出
            organized_text = response.choices[0].message.content

            # JSONとしてパース
            try:
                # コードブロックを除去
                clean_text = organized_text.strip()
                if clean_text.startswith('```json'):
                    clean_text = clean_text[7:]  # ```json を除去
                if clean_text.endswith('```'):
                    clean_text = clean_text[:-3]  # ``` を除去
                clean_text = clean_text.strip()

                organized_json = json.loads(clean_text)
                return {
                    "success": True,
                    "data": organized_json,
                    "organized_text": organized_text,
                    "input_data": formatted_input
                }
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"整理結果のJSONパースエラー: {str(e)}",
                    "organized_text": organized_text,
                    "input_data": formatted_input
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "organized_text": "",
                "input_data": formatted_input if 'formatted_input' in locals() else ""
            }

    def validate_organized_data(self, organized_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        整理されたデータの妥当性を検証する

        Args:
            organized_data: 整理されたデータ

        Returns:
            Dict[str, Any]: 検証結果
        """
        validation_result = {
            "is_valid": True,
            "issues": [],
            "statistics": {
                "total_problems": 0,
                "problems_with_solutions": 0,
                "empty_categories": []
            }
        }

        if not isinstance(organized_data, list):
            validation_result["is_valid"] = False
            validation_result["issues"].append("データがリスト形式ではありません")
            return validation_result

        validation_result["statistics"]["total_problems"] = len(organized_data)

        for i, problem_data in enumerate(organized_data):
            # 必須フィールドの確認
            required_fields = ["problem", "personal", "community", "gov", "others"]
            missing_fields = [field for field in required_fields if field not in problem_data]

            if missing_fields:
                validation_result["is_valid"] = False
                validation_result["issues"].append(f"問題 {i+1}: 必須フィールドが不足 - {missing_fields}")

            # 解決策があるかどうかの確認
            has_solutions = any(
                problem_data.get(field) and
                (isinstance(problem_data[field], list) and len(problem_data[field]) > 0 or
                 isinstance(problem_data[field], str) and problem_data[field].strip())
                for field in ["personal", "community", "gov", "others"]
            )

            if has_solutions:
                validation_result["statistics"]["problems_with_solutions"] += 1

            # 空のカテゴリの確認
            for field in ["personal", "community", "gov", "others"]:
                if (not problem_data.get(field) or
                    (isinstance(problem_data[field], list) and len(problem_data[field]) == 0) or
                    (isinstance(problem_data[field], str) and not problem_data[field].strip())):
                    validation_result["statistics"]["empty_categories"].append(f"問題 {i+1}: {field}")

        return validation_result
