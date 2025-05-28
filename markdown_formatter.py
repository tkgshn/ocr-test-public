"""
Markdown出力クラス
整理されたデータをMarkdown形式で出力する
"""
import json
from typing import List, Dict, Any
from openai import OpenAI
import config


class MarkdownFormatter:
    """
    データをMarkdown形式で出力するクラス
    """

    def __init__(self):
        """
        初期化
        """
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

    def format_with_ai(self, organized_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        AIを使用してMarkdown形式に変換する

        Args:
            organized_data: 整理されたデータ

        Returns:
            Dict[str, Any]: Markdown変換結果
        """
        try:
            # データをJSON文字列に変換
            json_data = json.dumps(organized_data, indent=2, ensure_ascii=False)

            # OpenAI APIに送信
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL_TEXT,
                messages=[
                    {
                        "role": "system",
                        "content": config.MARKDOWN_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": f"以下のJSONデータをMarkdown形式に変換してください:\n\n{json_data}"
                    }
                ],
                temperature=0.3,
                max_tokens=4000
            )

            # レスポンスからテキストを抽出
            markdown_text = response.choices[0].message.content

            return {
                "success": True,
                "markdown": markdown_text,
                "input_data": json_data
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "markdown": "",
                "input_data": json_data if 'json_data' in locals() else ""
            }

    def format_manually(self, organized_data: List[Dict[str, Any]]) -> str:
        """
        手動でMarkdown形式に変換する（AIが失敗した場合のフォールバック）

        Args:
            organized_data: 整理されたデータ

        Returns:
            str: Markdown形式のテキスト
        """
        markdown_lines = []
        markdown_lines.append("# 地域課題と解決策の整理結果\n")

        for i, problem_data in enumerate(organized_data):
            # 課題タイトル
            problem_title = problem_data.get("problem", f"課題 {i+1}")
            markdown_lines.append(f"## {problem_title}\n")

            # 各カテゴリの処理
            categories = [
                ("personal", "個人としてできること"),
                ("community", "地域としてできること"),
                ("gov", "行政の役割"),
                ("others", "その他")
            ]

            for field, title in categories:
                markdown_lines.append(f"### {title}\n")

                content = problem_data.get(field, [])
                if isinstance(content, list):
                    if content:
                        for item in content:
                            if item and item.strip():
                                markdown_lines.append(f"- {item.strip()}")
                        markdown_lines.append("")
                    else:
                        markdown_lines.append("（該当なし）\n")
                elif isinstance(content, str):
                    if content.strip():
                        # 文字列の場合は改行で分割してリスト化
                        items = [item.strip() for item in content.split('\n') if item.strip()]
                        for item in items:
                            markdown_lines.append(f"- {item}")
                        markdown_lines.append("")
                    else:
                        markdown_lines.append("（該当なし）\n")
                else:
                    markdown_lines.append("（該当なし）\n")

            markdown_lines.append("---\n")

        return "\n".join(markdown_lines)

    def format_to_markdown(self, organized_data: List[Dict[str, Any]], use_ai: bool = True) -> Dict[str, Any]:
        """
        データをMarkdown形式に変換する

        Args:
            organized_data: 整理されたデータ
            use_ai: AIを使用するかどうか

        Returns:
            Dict[str, Any]: 変換結果
        """
        if use_ai:
            # まずAIで変換を試行
            ai_result = self.format_with_ai(organized_data)
            if ai_result["success"]:
                return ai_result
            else:
                # AIが失敗した場合は手動変換にフォールバック
                manual_markdown = self.format_manually(organized_data)
                return {
                    "success": True,
                    "markdown": manual_markdown,
                    "method": "manual_fallback",
                    "ai_error": ai_result.get("error", "")
                }
        else:
            # 手動変換を直接実行
            manual_markdown = self.format_manually(organized_data)
            return {
                "success": True,
                "markdown": manual_markdown,
                "method": "manual"
            }

    def add_metadata(self, markdown_content: str, metadata: Dict[str, Any]) -> str:
        """
        Markdownにメタデータを追加する

        Args:
            markdown_content: Markdownコンテンツ
            metadata: 追加するメタデータ

        Returns:
            str: メタデータ付きMarkdown
        """
        metadata_lines = [
            "---",
            "# 処理情報",
            f"- 処理日時: {metadata.get('timestamp', 'N/A')}",
            f"- 処理画像数: {metadata.get('image_count', 'N/A')}",
            f"- 識別された課題数: {metadata.get('problem_count', 'N/A')}",
            "---\n"
        ]

        return "\n".join(metadata_lines) + "\n" + markdown_content
