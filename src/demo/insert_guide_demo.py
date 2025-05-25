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
        patient_conversation_id = str(uuid.uuid4())
        patient_conversation = ConversationModel(
            id=patient_conversation_id,
            user_id=user_id,
            session_title="患者个体化mRNA疫苗设计助手",
            chat_type="patient_case_mrna",  # config,
            create_time=datetime.strptime(
                "2025-03-07 14:33:00", "%Y-%m-%d %H:%M:%S")
        )

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

        session.add_all([pmhc_conversation, patient_conversation,neo_antigen_conversation]) 



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

#patient_case_mrna_research会话相关信息插入
        patient_response_text = \
            """
🌟 欢迎来到患者个体化mRNA疫苗设计助手！ 🌟
我们致力于为每位患者定制高效、精准的mRNA疫苗方案，结合您的临床数据与AI预测，筛选最优抗原靶点，加速个性化治疗进程。
💡 操作流程指引：
✅ 1. 上传患者数据：
    📊 临床病例数据：病人的基础病例信息
    🧬 基因测序文件：病人的测试肽段序列
✅ 2. 智能分析与设计：
    🧠 AI方案生成：结合专业知识库及案例，生成建议治疗方案
    🛠️ 端到端运行：LLM驱动工具库调用，End to end生成结果

📥 我们提供了一个临床病例数据及其基因测序文件，您可以选择使用。
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

        patient_uploaded_file_one = UploadedFile(
            id=str(uuid.uuid4()),
            conversation_id=patient_conversation_id,
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
            conversation_id=patient_conversation_id,
            file_name="PancreaticSeq.fsa",
            file_path="minio://molly/a3173986-f964-43a1-95dd-694fa93ee150_PancreaticSeq.fsa",
            file_desc="胰腺蛋白序列分析",
            file_type="neo_default_file",
            file_size=573,
            file_hash="4e3a006c929b9b9c326fca34a26ea450cba37da46c2563bb6eed5bc12472a08a",
            file_status=True,
            file_origin=1,
            create_time=datetime.strptime(
                "2025-03-07 14:30:05", "%Y-%m-%d %H:%M:%S")

        )

        session.add_all([patient_uploaded_file_two,patient_uploaded_file_one])

#neo_antigen_research会话相关信息插入
        neo_antigen_response_text = \
"""
🌟 欢迎来到个体化neo-antigen筛选设计助手！ 🌟
我们专注于为肿瘤患者定制高效、安全的mRNA疫苗方案，通过整合患者特异性突变数据与多维度AI预测工具，筛选高免疫原性新抗原（neo-antigen），助力精准免疫治疗。  
### 📥 输入信息要求
请确保提供以下数据（**肽段序列为必填**）：

#### 🧬 肽段序列数据
- 包含突变位点的肽段（例如：`FAKEA123T`，需明确突变位置）
- *若无此数据，将无法继续，请立即补充！*

#### 🩺 MHC分型数据（可选）
- 默认使用 `HLA-A*02:01`
- 若需其他分型请明确提供（例如：`HLA-B*07:02`）

#### 🔬 TCR序列数据（可选）
- 若需分析 pMHC-TCR 相互作用：
  - 至少提供 CDR3 区域（`A3`/`B3` 序列）
  - 示例格式：`CASSLGQGNQPQHF`
### ⚙️ 工具与流程
#### 📌 可用工具集
- **蛋白切割**  
  `NetChop`  
- **抗原递呈**  
  `NetCTLpan`  
- **pMHC结合预测**  
  `NetMHCPan`, `TransPHLA`, `BigMHC_EL`, `ImmuneApp_PP`  
- **免疫原性预测**  
  `BigMHC_IM`, `PRIME`, `ImmuneApp_IM`  
- **TCR相互作用**  
  `pMTnet`, `PISTE`, `NetTCR`（需CDR3数据）  
- **结构建模**  
  `UniPMT`  

#### 🔄 默认工作流 `NeoAntigenSelection`
1. 肽段切割  
2. pMHC亲和力筛选  
3. 免疫原性评估  
4. TCR相互作用预测（若有数据）  
   *若无高评分候选，流程将提前终止并反馈原因*  

### 📌 操作指引
1. **上传数据**  
   - 上传文件（如`.fasta`）  
   - 补充MHC/TCR数据（非必需但建议）  
2. **启动分析**  
   - 默认调用 `NeoAntigenSelection` 工作流  
   - 或根据需求定制工具组合  
3. **获取结果**  
   - 候选肽段列表  
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
