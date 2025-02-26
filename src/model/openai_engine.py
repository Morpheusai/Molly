import httpx
from src.api.protocols import UserInput
import json
import asyncio
from typing import AsyncGenerator, Any, List, Dict
from src.utils.mysql_db import process_messages
from src.utils.log import logger
from src.config import g_config

async def proxy_stream_generator(user_input: UserInput, msg_id: str, conversation_id: str, stop_event: asyncio.Event, stop_events: Dict[str, asyncio.Event]) -> AsyncGenerator[str, None]:
    """
    代理生成器，转发远程服务器的 SSE 流，并在流结束后进行数据库操作。
    """
    # 目标服务器地址
    target_url= g_config["url"]["target_url"]
    target_url = target_url
    
    # 构造请求参数
    json_data = user_input.dict()
    logger.info(f"发送到目标服务器的数据: {json.dumps(json_data, ensure_ascii=False)}")

    # 用于存储收集到的 AI 和 Tool 消息
    ai_messages: List[Dict] = []  # 存储所有 AI 类型消息
    tool_messages: List[Dict] = []  # 存储所有 Tool 类型消息
    # 初始化 full_response
    full_response = ""

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

                # # 用于存储 AI 的完整回复
                # full_response = ""
                # 流式转发数据并收集 AI 和 Tool 消息
                async for chunk in response.aiter_text():
                    # 检查是否停止
                    if stop_event.is_set():  # 使用 stop_event 检查
                        break
                    #将 chunk 拼接到 full_response 中
                    # full_response += chunk
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
                            else:        
                                content = data.get("content", {})
                                full_response += content
                                
                        except json.JSONDecodeError:
                            pass
        except httpx.ConnectError as e:
            logger.error(f"Connection error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': 'Connection failed'})}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': f'Unexpected error1: {str(e)}'})}\n\n"
        finally:
            # 清理 stop_events 字典
            if conversation_id in stop_events:
                del stop_events[conversation_id]            
    # 处理消息
    await process_messages(msg_id, conversation_id, ai_messages, tool_messages, full_response)            

