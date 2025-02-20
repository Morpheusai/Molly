import httpx
from src.api.protocols import UserInput
import json
from typing import AsyncGenerator, Any, List, Dict
from src.utils.mysql_db import process_messages


async def proxy_stream_generator(user_input: UserInput, msg_id: str) -> AsyncGenerator[str, None]:
    """
    代理生成器，转发远程服务器的 SSE 流，并在流结束后进行数据库操作。
    """
    # 目标服务器地址
    target_url = "http://52.74.25.27:17070/stream"
    
    # 构造请求参数
    json_data = user_input.dict()

    # 用于存储收集到的 AI 和 Tool 消息
    ai_messages: List[Dict] = []  # 存储所有 AI 类型消息
    tool_messages: List[Dict] = []  # 存储所有 Tool 类型消息

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout=300.0)) as client:
        try:
            async with client.stream(
                "POST",
                target_url,
                json=json_data
            ) as response:
                # 检查响应状态
                if response.status_code != 200:
                    error = await response.aread()
                    yield f"data: {json.dumps({'type': 'error', 'content': f'Upstream error: {response.status_code} {error.decode()}'})}\n\n"
                    return

                # 流式转发数据并收集 AI 和 Tool 消息
                async for chunk in response.aiter_text():
                    # print(chunk)
                    yield chunk

                    # 解析 chunk 并判断是否为 AI 或 Tool 类型
                    if chunk.startswith("data:"):
                        try:
                            data = json.loads(chunk[5:].strip())
                            if data.get("type") == "message":
                                
                                content = data.get("content", {})
                                msg_type = content.get("type")
                                if msg_type == "ai":
                                    ai_messages.append(data)
                                elif msg_type == "tool":
                                    tool_messages.append(data)
                        except json.JSONDecodeError:
                            pass

        except httpx.ConnectError:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Connection failed'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Unexpected error1: {str(e)}'})}\n\n"
    # 处理消息
    await process_messages(msg_id, ai_messages, tool_messages)            


