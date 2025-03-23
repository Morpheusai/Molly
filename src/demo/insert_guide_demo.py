import asyncio
import uuid

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.db.conversation_model import ConversationModel
from src.db.message_model import MessageModel
from src.db.tool_msg_model import ToolModel
from src.db.uploadfiles_model import UploadedFile
from src.utils.base import Base, async_engine
from src.utils.log import logger
#TODO 优化 加 config json data
async def insert_conversation_data(session: AsyncSession, user_id: str) -> dict:
    """
    将硬编码的 JSON 数据插入到数据库中，并返回与原始 JSON 一致的响应。
    
    Args:
        session: SQLAlchemy AsyncSession 对象
        user_id: 用户的 unionid
    
    Returns:
        与原始 JSON 格式一致的字典

    ***示例中的响应时间并不是真实系统的响应时间***
    """
    try:
        new_conversation_id = str(uuid.uuid4())
        conversation = ConversationModel(
            id=new_conversation_id,
            user_id=user_id,
            session_title="MHC-I分子结合亲和力预测AI助手",
            chat_type="demo",#config,
            create_time=datetime.strptime("2025-03-07 14:30:00", "%Y-%m-%d %H:%M:%S")
        )
        session.add(conversation)

        response_text = \
"""
🌟 **欢迎来到个性化疫苗 AI 预测助手！** 🌟
我们可以帮助您**从候选抗原序列中筛选出与MHC-I 分子结合亲和力最强的肽段**，以便更好地评估它们的免疫潜力。 
💡 **简单操作流程**：
✅ *1.* 提供您候选的抗原序列文件，我们将进行**默认筛选策略**的预测。
✅ *2.* 后续您可以尝试不同的筛选策略：
 - 选择合适的HLA 分型，我们将计算不同肽段的结合能力。
 - 调整预测参数，探索不同的筛选策略。
 - 展示筛选出来的亲和力最强的肽段三维结构。

📥 我们提供了一个示例抗原序列文件，您可以选择使用。
"""

        messages = [
            MessageModel(
                id=str(uuid.uuid4()),#"04abe03e-92d0-41d1-afc6-25de0b861e6b",
                conversation_id=new_conversation_id,
                query="",
                response=response_text,
                create_time=datetime.strptime("2025-03-07 14:30:00", "%Y-%m-%d %H:%M:%S")
            ),
        ]
        for message in messages:
            session.add(message)

        uploaded_file = UploadedFile(
            id=str(uuid.uuid4()),
            conversation_id=new_conversation_id,
            file_name="B0702.fsa",
            file_path="minio://molly/8e81f329-a602-4b0c-bc69-2b110033d594_B0702.fsa",
            file_desc="mRNA疫苗序列分析",
            file_type="application/octet-stream",
            file_size=373,
            file_hash="6ba6e3e00aabaa3b83395a0afbc213e78837d1ba904d2233e42e3e76c45cdfda",
            file_status=True,
            file_origin=0,
            create_time=datetime.strptime("2025-03-07 14:30:05", "%Y-%m-%d %H:%M:%S")
            
        )
        session.add(uploaded_file)            

        # 提交事务
        await session.commit()

        return {
            "ok": 0,
            "failed": "",
            "session_id": new_conversation_id,  
            "session_title": "DEMO",
        }

    except Exception as e:
        await session.rollback()
        return {
            "ok": 1,
            "failed": str(e),
            "session_id": new_conversation_id,
            "session_title": None,
            "chats": [],
            "files": []
        }
async def insert_guide_demo(user_id: str):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables ensured to exist.")
    # 创建异步会话工厂
    async_session_factory = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    # 使用会话执行插入操作
    async with async_session_factory() as session:
        try:
            await insert_conversation_data(session, user_id)
            # logger.info(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}", exc_info=True)
if __name__ == "__main__":
    asyncio.run(insert_guide_demo())
