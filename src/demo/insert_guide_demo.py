import asyncio
import uuid

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.db.conversation_model import ConversationModel
from src.db.message_model import MessageModel
from src.db.uploadfiles_model import UploadedFile
from src.utils.base import Base, async_engine
from src.utils.log import logger


# TODO 优化 加 config json data
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
        #pmhc_affinity_prediction会话
        pmhc_conversation_id = str(uuid.uuid4())
        pmhc_conversation = ConversationModel(
            id=pmhc_conversation_id,
            user_id=user_id,
            session_title="肽段-MHC亲和力智能筛选助手",
            chat_type="pmhc_affinity_prediction",  # config,
            create_time=datetime.strptime(
                "2025-03-07 14:30:00", "%Y-%m-%d %H:%M:%S")
        )
        #patient_case_mrna_research会话
        patient_conversation_id = str(uuid.uuid4())
        patient_conversation = ConversationModel(
            id=patient_conversation_id,
            user_id=user_id,
            session_title="患者个体化mRNA疫苗设计助手",
            chat_type="patient_case_mrna",  # config,
            create_time=datetime.strptime(
                "2025-03-07 14:30:00", "%Y-%m-%d %H:%M:%S")
        )

        session.add_all([pmhc_conversation, patient_conversation]) 



        #pmhc_affinity_prediction会话相关信息插入
        pmhc_response_text = \
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

        pmhc_messages = [
            MessageModel(
                # "04abe03e-92d0-41d1-afc6-25de0b861e6b",
                id=str(uuid.uuid4()),
                conversation_id=pmhc_conversation_id,
                query="",
                response=pmhc_response_text,
                create_time=datetime.strptime(
                    "2025-03-07 14:30:00", "%Y-%m-%d %H:%M:%S")
            ),
        ]
        for message in pmhc_messages:
            session.add(message)

        pmhc_uploaded_file = UploadedFile(
            id=str(uuid.uuid4()),
            conversation_id=pmhc_conversation_id,
            file_name="testSeq.fsa",
            file_path="minio://molly/6b5a0a9b-4dc3-420d-b53d-a4ca375c51d1_testSeq.fsa",
            file_desc="mRNA疫苗序列分析",
            file_type="application/octet-stream",
            file_size=411,
            file_hash="ae840fb19516a28418991cf7f58f665b4fef79ba683f0ae9a2425197124484dd",
            file_status=True,
            file_origin=0,
            create_time=datetime.strptime(
                "2025-03-07 14:30:05", "%Y-%m-%d %H:%M:%S")

        )
        session.add(pmhc_uploaded_file)

    #patient_case_mrna_research会话相关信息插入
        patient_response_text = \
            """
🌟 欢迎来到患者个体化mRNA疫苗设计助手！ 🌟
我们致力于为每位患者定制高效、精准的mRNA疫苗方案，结合您的临床数据与AI预测，筛选最优抗原靶点，加速个性化治疗进程。
💡 操作流程指引：
✅ 1. 上传患者数据（支持多模态输入）：
    临床资料（病理分型、PD-L1表达等）
    基因组文件（WES测序结果、TMB数据）
    HLA分型报告（NGS格式优先）
    免疫组库数据（可选TCR/BCR测序）
✅ 2. 智能分析与设计：
    🧬 AI驱动：自动筛选高免疫原性突变（结合MHC亲和力+克隆性分析）
    🛠️ 序列优化：密码子调整、二级结构稳定化、TLR激动剂规避
    📊 方案生成：输出包含4-20个优先表位的mRNA疫苗核心序列（5'/3'UTR架构）
✅ 3. 结果应用与迭代：
    💉 佐剂推荐：基于患者免疫微环境匹配
    🔬 验证建议：ELISpot/流式实验设计方案
    🔄 动态更新：支持随访数据导入重新优化
📥 示例数据包（含模拟临床报告+FASTA序列）已就绪，点击即可快速体验！
🚀 从数据到疫苗，我们为每位患者点亮精准医疗的曙光
            """

        patient_messages = [
            MessageModel(
                # "04abe03e-92d0-41d1-afc6-25de0b861e6b",
                id=str(uuid.uuid4()),
                conversation_id=patient_conversation_id,
                query="",
                response=patient_response_text,
                create_time=datetime.strptime(
                    "2025-03-07 14:30:00", "%Y-%m-%d %H:%M:%S")
            ),
        ]
        for message in patient_messages:
            session.add(message)

        patient_uploaded_file = UploadedFile(
            id=str(uuid.uuid4()),
            conversation_id=patient_conversation_id,
            file_name="testSeq.fsa",
            file_path="minio://molly/6b5a0a9b-4dc3-420d-b53d-a4ca375c51d1_testSeq.fsa",
            file_desc="mRNA疫苗序列分析",
            file_type="application/octet-stream",
            file_size=411,
            file_hash="ae840fb19516a28418991cf7f58f665b4fef79ba683f0ae9a2425197124484dd",
            file_status=True,
            file_origin=0,
            create_time=datetime.strptime(
                "2025-03-07 14:30:05", "%Y-%m-%d %H:%M:%S")

        )
        session.add(patient_uploaded_file)



        # 提交事务
        await session.commit()

        # return {
        #     "ok": 0,
        #     "failed": "",
        #     "conversation_id": pmhc_conversation_id,
        #     "session_title": "DEMO",
        # }

    except Exception as e:
        await session.rollback()
        return {
            "ok": 1,
            "failed": str(e),
            # "conversation_id": pmhc_conversation_id,
            # "session_title": None,
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
