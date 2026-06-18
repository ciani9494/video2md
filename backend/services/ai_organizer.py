from typing import Protocol

import httpx


SYSTEM_PROMPT = """你是一个技术文档整理助手。你的任务是将用户提供的视频转录文本整理为结构化的技术文档。

要求：
1. 提取核心技术点，去除口语化表达
2. 组织为清晰的章节结构（使用 Markdown 标题）
3. 保留代码片段并正确格式化
4. 添加关键要点总结
5. 如果有多个主题，分别整理
6. 输出纯 Markdown 格式
"""


class AiOrganizer(Protocol):
    def organize(self, transcript_text: str, api_key: str) -> str:
        """将原始转录文本转换为最终 Markdown。"""


class DeepSeekOrganizer:
    def organize(self, transcript_text: str, api_key: str) -> str:
        # DeepSeek 仅在最终整理时调用，原始音频保留在本地。
        response = httpx.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"请整理以下转录文本：\n\n{transcript_text}"},
                ],
                "temperature": 0.3,
                "max_tokens": 4000,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
