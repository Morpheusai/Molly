import httpx
import json
import asyncio

from collections import deque
from typing import AsyncGenerator, Any, List, Dict

from src.api.protocols import UserInput
from src.utils.mysql_db import process_messages
from src.utils.log import logger
from src.config import g_config

async def proxy_stream_generator(user_input: UserInput, msg_id: str, conversation_id: str, stop_event: asyncio.Event, stop_events: Dict[str, asyncio.Event]) -> AsyncGenerator[str, None]:
    """
    代理生成器，转发远程服务器的 SSE 流，并在流结束后进行数据库操作。
    """
    if user_input.conversation_chat_type == "normal":
        # 目标服务器地址
        target_url = g_config["url"]["target_stream_url"]
    else:
        target_url = g_config["url"]["target_demo_stream_url"]  
    # 构造请求参数
    json_data = user_input.dict()

    logger.info(f"发送到目标服务器的数据: {json.dumps(json_data, ensure_ascii=False)}")

    # 用于存储收集到的 AI 和 Tool 消息
    ai_messages: List[Dict] = []  # 存储所有 AI 类型消息
    tool_messages: List[Dict] = []  # 存储所有 Tool 类型消息
    #用来将流式的消息进行分割
    current_response = None
    # 初始化 
    msg_response = ""
    flag_i=0
    flag_j=0
    tool_result_analysis_list = []
    content_dict={}
    content=""
    chunk_queue = deque()
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
                # tool_result_analysis_list = ""
                # 流式转发数据并收集 AI 和 Tool 消息

                buffer = ""  # 缓冲区，存储未处理完的分块数据
                async for chunk in response.aiter_text():
                    # 检查是否停止
                    if stop_event.is_set():  # 使用 stop_event 检查
                        break
                    buffer += chunk  # 将新数据加入缓冲区
                    # 检查缓冲区是否包含完整的 SSE 消息（以 \n\n 结尾）
                    while "\n\n" in buffer:
                        # 提取第一条完整消息（包括 "data: {...}\n\n"）
                        
                        message, buffer = buffer.split("\n\n", 1)
                        # 补回分隔符，保持 SSE 格式   
                        message += "\n\n"  
                        # 跳过 [DONE] 消息不入队列
                        if "data: [DONE]" not in message:
                            # 存入队列（完整的 SSE 消息） 
                            chunk_queue.append(message)                        
                    yield chunk
        except httpx.ConnectError as e:
            logger.error(f"Connection error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': 'Connection failed'})}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': f'Unexpected error: {str(e)}'})}\n\n"
        finally:
            # 清理 stop_events 字典
            if conversation_id in stop_events:
                del stop_events[conversation_id]  

        # 处理缓冲的 chunk
        while chunk_queue:
            chunk = chunk_queue.popleft()
            # 解析 chunk 并判断是否为 AI 或 Tool 类型
            if chunk.startswith("data:"):
                try:
                    data = json.loads(chunk[5:].strip())
                    if data.get("type") == "message":
                        content_dict = data.get("content", {})
                        msg_type = content_dict.get("type")
                        if msg_type == "ai":
                            ai_messages.append(data)
                        elif msg_type == "tool":
                            flag_j+=1
                            tool_messages.append(data)
                    elif data.get("type") == "token":  
                        #添加response信息  
                        if flag_i == flag_j and flag_i == 0:  
                            content = data.get("content", "")  
                            msg_response +=  content
                        elif flag_i == flag_j :   
                            content = data.get("content", "")
                            current_response = (current_response or "") + content                                    
                        else:
                            flag_i+=1
                            #多个工具调用
                            if current_response is not None and flag_i != flag_j:
                                tool_result_analysis_list.append(current_response)
                                while flag_i < flag_j:
                                    flag_i+=1
                                    tool_result_analysis_list.append("")
                                
                                current_response=None
                                content = data.get("content", "")
                                current_response = (current_response or "") + content                                            
                                    
                            elif current_response is not None and flag_i == flag_j:
                                tool_result_analysis_list.append(current_response)
                                current_response=None
                                content = data.get("content", "")
                                current_response = (current_response or "") + content      
                            #解决开头token丢失问题
                            elif current_response is None and flag_i == flag_j:   
                                content = data.get("content", "")
                                current_response = (current_response or "") + content 

                            elif current_response is None and flag_i != flag_j:   
                                while flag_i < flag_j:
                                    flag_i+=1
                                    tool_result_analysis_list.append("")                                    
                                content = data.get("content", "")
                                current_response = (current_response or "") + content  
                except json.JSONDecodeError as e:
                    # 记录错误信息和出错的内容
                    logger.error(f"JSONDecodeError encountered: {e}")
                    logger.error(f"Failed to parse chunk: {chunk[5:].strip()}")
            if current_response is not None:
                tool_result_analysis_list.append(current_response)
                    # tool_result_analysis_list+=current_response      
    # 处理消息
    await process_messages(msg_id, conversation_id, ai_messages, tool_messages, tool_result_analysis_list, msg_response)            

