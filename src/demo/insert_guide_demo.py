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
                "2025-03-07 14:31:00", "%Y-%m-%d %H:%M:%S")
        )
        #patient_case_mrna_research会话
        # patient_conversation_id = str(uuid.uuid4())
        # patient_conversation = ConversationModel(
        #     id=patient_conversation_id,
        #     user_id=user_id,
        #     session_title="患者个体化mRNA疫苗设计助手",
        #     chat_type="patient_case_mrna",  # config,
        #     create_time=datetime.strptime(
        #         "2025-03-07 14:33:00", "%Y-%m-%d %H:%M:%S")
        # )

        #neo_antigen_research会话
        neo_antigen_conversation_id = str(uuid.uuid4())
        neo_antigen_conversation = ConversationModel(
            id=neo_antigen_conversation_id,
            user_id=user_id,
            session_title="患者个体化antigen筛选设计助手",
            chat_type="neo_antigen",  # config,
            create_time=datetime.strptime(
                "2025-03-07 14:32:00", "%Y-%m-%d %H:%M:%S")
        )        

        session.add_all([pmhc_conversation, neo_antigen_conversation]) 



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
            file_type="neo_default_file",
            file_size=411,
            file_hash="ae840fb19516a28418991cf7f58f665b4fef79ba683f0ae9a2425197124484dd",
            file_status=True,
            file_origin=1,
            create_time=datetime.strptime(
                "2025-03-07 14:30:05", "%Y-%m-%d %H:%M:%S")

        )
        session.add(pmhc_uploaded_file)

# #patient_case_mrna_research会话相关信息插入
#         patient_response_text = \
#             """
# 🌟 欢迎来到患者个体化mRNA疫苗设计助手！ 🌟
# 我们致力于为每位患者定制高效、精准的mRNA疫苗方案，结合您的临床数据与AI预测，筛选最优抗原靶点，加速个性化治疗进程。
# 💡 操作流程指引：
# ✅ 1. 上传患者数据：
#     📊 临床病例数据：病人的基础病例信息
#     🧬 基因测序文件：病人的测试肽段序列
# ✅ 2. 智能分析与设计：
#     🧠 AI方案生成：结合专业知识库及案例，生成建议治疗方案
#     🛠️ 端到端运行：LLM驱动工具库调用，End to end生成结果

# 📥 我们提供了一个临床病例数据及其基因测序文件，您可以选择使用。
#             """


#         patient_messages = [
#             MessageModel(
#                 # "04abe03e-92d0-41d1-afc6-25de0b861e6b",
#                 id=str(uuid.uuid4()),
#                 conversation_id=patient_conversation_id,
#                 query="",
#                 response=patient_response_text,
#                 create_time=datetime.strptime(
#                     "2025-03-07 14:30:00", "%Y-%m-%d %H:%M:%S")
#             ),
#         ]
#         for message in patient_messages:
#             session.add(message)

#         patient_uploaded_file_one = UploadedFile(
#             id=str(uuid.uuid4()),
#             conversation_id=patient_conversation_id,
#             file_name="PancreaticCase.txt",
#             file_path="minio://molly/54d84f34-3917-4a9d-86f0-69f2f560933f_PancreaticCase.txt",
#             file_desc="胰腺癌病例分析",
#             file_type="neo_default_file",
#             file_size=1714,
#             file_hash="f1bf863f73245b3d6052338c6dee9ad3125e78906197b5e25dcfc16faac5c19d",
#             file_status=True,
#             file_origin=1,
#             create_time=datetime.strptime(
#                 "2025-03-07 14:30:10", "%Y-%m-%d %H:%M:%S")

#         )

#         patient_uploaded_file_two = UploadedFile(
#             id=str(uuid.uuid4()),
#             conversation_id=patient_conversation_id,
#             file_name="PancreaticSeq.fsa",
#             file_path="minio://molly/aa8d6981-a2b3-44c7-b9ab-db3f02e54a9f_PancreaticSeq.fsa",
#             file_desc="胰腺蛋白序列分析",
#             file_type="neo_default_file",
#             file_size=184,
#             file_hash="b2cc33f845e023c47462dd4cd6a452c38cd06b121dbd464182eb2311aaf81f38",
#             file_status=True,
#             file_origin=1,
#             create_time=datetime.strptime(
#                 "2025-03-07 14:30:05", "%Y-%m-%d %H:%M:%S")

#         )

#         session.add_all([patient_uploaded_file_two,patient_uploaded_file_one])

#neo_antigen_research会话相关信息插入
        neo_antigen_response_text = \
"""
## 🌟 欢迎使用 Neo 个体化 neoantigen 筛选助手 🌟
我们致力于帮助您从肿瘤相关的突变肽段中，筛选出具有潜力的个体化 neoantigen 候选，用于多肽疫苗或 mRNA 疫苗的后续设计。
平台已内置智能流程，支持从肽段切割、MHC结合亲和力预测，到免疫原性与TCR识别能力评估的一站式分析。

## 📥 您可以从以下方式开始：
### • 🧬 上传您自己的突变肽段（支持FASTA格式）
### • 🧪 点击预览并使用我们提供的示例数据进行体验
### • ❓ 获取引导，了解流程与所需输入内容
我们已为您准备了：
✔️ 模拟病例.txt文件
 • 👉 [PancreaticCase.txt]
✔️ 突变序列示例.fasta文件
 • 👉 [PancreaticSeq.fsa] 


## 👉 请选择您希望的操作：
### 了解预测流程与筛选逻辑
我想先搞清楚这个平台是如何进行neoantigen筛选的、都用了哪些工具、每一步是什么意思。
 （系统可展示：整体流程图、所用工具简介、评分含义、失败中止的条件等）
### 体验一个示例分析流程
我想看看平台分析一个标准病例的全过程和输出结果，了解候选肽段是如何被选出来的。
 （系统提供预置突变肽段+病历信息，展示从切割到免疫原性评分等完整过程和结果解读）
### 上传我的数据并开始分析
我已经准备好了突变肽段等数据，想直接开始一个真实的筛选分析流程。
 （系统引导上传数据 → 补充HLA/TCR → 启动分析）
        """

        patient_messages = [
            MessageModel(
                # "04abe03e-92d0-41d1-afc6-25de0b861e6b",
                id=str(uuid.uuid4()),
                conversation_id=neo_antigen_conversation_id,
                query="",
                response=neo_antigen_response_text,
                create_time=datetime.strptime(
                    "2025-03-07 14:30:00", "%Y-%m-%d %H:%M:%S")
            ),
        ]
        for message in patient_messages:
            session.add(message)

        patient_uploaded_file_one = UploadedFile(
            id=str(uuid.uuid4()),
            conversation_id=neo_antigen_conversation_id,
            file_name="PancreaticCase.txt",
            file_path="minio://molly/54d84f34-3917-4a9d-86f0-69f2f560933f_PancreaticCase.txt",
            file_desc="胰腺癌病例分析",
            file_type="neo_default_file",
            file_size=1714,
            file_hash="f1bf863f73245b3d6052338c6dee9ad3125e78906197b5e25dcfc16faac5c19d",
            file_status=True,
            file_origin=1,
            create_time=datetime.strptime(
                "2025-03-07 14:30:10", "%Y-%m-%d %H:%M:%S")

        )

        patient_uploaded_file_two = UploadedFile(
            id=str(uuid.uuid4()),
            conversation_id=neo_antigen_conversation_id,
            file_name="PancreaticSeq.fsa",
            file_path="minio://molly/aa8d6981-a2b3-44c7-b9ab-db3f02e54a9f_PancreaticSeq.fsa",
            file_desc="胰腺蛋白序列分析",
            file_type="neo_default_file",
            file_size=184,
            file_hash="b2cc33f845e023c47462dd4cd6a452c38cd06b121dbd464182eb2311aaf81f38",
            file_status=True,
            file_origin=1,
            create_time=datetime.strptime(
                "2025-03-07 14:30:05", "%Y-%m-%d %H:%M:%S")

        )

        session.add_all([patient_uploaded_file_two,patient_uploaded_file_one])

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
