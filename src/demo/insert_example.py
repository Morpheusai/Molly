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
            session_title="DEMO",
            chat_type="demo",#config,
            create_time=datetime.strptime("2025-03-07 14:30:00", "%Y-%m-%d %H:%M:%S")
        )
        session.add(conversation)

        msg_id_tool_1 = str(uuid.uuid4())
        msg_id_tool_2 = str(uuid.uuid4())
        msg_id_tool_3 = str(uuid.uuid4())

        messages = [
            MessageModel(
                id=str(uuid.uuid4()),#"04abe03e-92d0-41d1-afc6-25de0b861e6b",
                conversation_id=new_conversation_id,
                query="你好，我想筛选出与 MHC-I 分子结合亲和力强的肽段，能帮我分析吗？",
                response="您好！请提供肿瘤变异蛋白序列的FASTA格式文件，以便我们进行分析。您可以通过上传文件的方式提供该信息。",
                create_time=datetime.strptime("2025-03-07 14:30:00", "%Y-%m-%d %H:%M:%S")
            ),
            MessageModel(
                id=str(uuid.uuid4()),#"7a684ae7-0e6b-4c8a-92b3-f5a7cbefd3b3",
                conversation_id=new_conversation_id,
                query="请帮我分析这个文件中的肽段序列",
                response="好的，我已经看到您上传的文件。接下来，我需要确认一些参数信息：\n\n1. **HLA分型数据**：您是否有特定的HLA分型数据需要使用？如果没有，我将使用默认值HLA-A02:01。\n2. **肽段预测长度**：默认使用9-mer肽段长度进行筛选，您是否需要修改？\n3. **弱结合阈值**：默认值为2.0，您是否需要修改？\n4. **强结合阈值**：默认值为0.5，您是否需要修改？\n\n请您逐一确认或提供这些信息。",
                create_time=datetime.strptime("2025-03-07 14:30:10", "%Y-%m-%d %H:%M:%S")
            ),
            MessageModel(
                id=str(uuid.uuid4()),#"77fbfa55-bbc3-4bdd-ad62-c0f8469f6c43",
                conversation_id=new_conversation_id,
                query="我是中国人，你有什么建议的HLA分型数据",
                response="对于中国人群，常见的HLA分型包括HLA-A02:01和HLA-A24:02。您可以选择使用这两个分型进行分析。\n\n请确认您希望使用的HLA分型数据，以及是否需要调整其他参数（如肽段长度、弱结合阈值、强结合阈值）。",
                create_time=datetime.strptime("2025-03-07 14:30:20", "%Y-%m-%d %H:%M:%S")
            ),
            MessageModel(
                id= msg_id_tool_1,#"1e059843-7294-4a34-88d3-deb54542abb9",#
                conversation_id=new_conversation_id,
                query="好的，使用HLA-A02:01",
                response="感谢您的确认。接下来，我们将使用以下参数进行分析：\n\n- **HLA分型数据**: HLA-A02:01\n- **肽段预测长度**: 9-mer（默认）\n- **弱结合阈值**: 2.0（默认）\n- **强结合阈值**: 0.5（默认）\n\n在进行分析之前，我将先验证您上传的FASTA文件格式是否正确。请稍等片刻。",
                create_time=datetime.strptime("2025-03-07 14:30:30", "%Y-%m-%d %H:%M:%S")
            ),
            MessageModel(
                id=str(uuid.uuid4()),#"083cddec-f725-40fa-bb72-e480e1aa86d3",
                conversation_id=new_conversation_id,
                query="亲和力强和弱是怎么定义的？我不太清楚这些指标是什么意思。",
                response="在NetMHCpan工具中，肽段与MHC分子的结合亲和力通过预测的结合亲和力值（binding affinity）来衡量。以下是一些关键指标的解释：\n\n1. **强结合阈值（Strong Binding Threshold）**：\n   - 这是一个数值阈值，用于定义肽段与MHC分子之间的强结合。\n   - 如果预测的结合亲和力值低于这个阈值，则认为肽段与MHC分子具有强结合能力。\n   - 默认值为0.5。\n\n2. **弱结合阈值（Weak Binding Threshold）**：\n   - 这是一个数值阈值，用于定义肽段与MHC分子之间的弱结合。\n   - 如果预测的结合亲和力值低于这个阈值但高于强结合阈值，则认为肽段与MHC分子具有弱结合能力。\n   - 默认值为2.0。\n\n3. **结合亲和力值（Binding Affinity Value）**：\n   - 这是一个预测值，表示肽段与MHC分子结合的强度。\n   - 数值越低，表示结合亲和力越强。\n\n通过这些指标，我们可以筛选出与MHC分子结合亲和力强的肽段，以便用于后续的疫苗设计和个性化免疫治疗。\n\n如果您还有其他问题或需要进一步调整参数，请随时告知！如果没有问题，我将继续进行分析。",
                create_time=datetime.strptime("2025-03-07 14:31:00", "%Y-%m-%d %H:%M:%S")
            ),
            MessageModel(
                id=msg_id_tool_2,#"0337064c-faa0-42b8-a39f-b083e1fb5907",#
                conversation_id=new_conversation_id,
                query="好的，继续",
                response="",
                create_time=datetime.strptime("2025-03-07 14:31:10", "%Y-%m-%d %H:%M:%S")
            ),
            MessageModel(
                id=str(uuid.uuid4()),#"5b45fc6a-5cd1-41d0-8438-d044113804bc",
                conversation_id=new_conversation_id,
                query="有意思，其中VMAPRTVLL并没有达到阈值，为什么是SB等级",
                response="在NetMHCpan工具中，肽段与MHC分子的结合亲和力不仅仅依赖于数值阈值，还可能受到其他因素的影响，如算法的预测模型和特定的结合位点特性。\n\n在您的结果中，肽段 **VMAPRTVLL** 被标记为 **SB（Strong Binder）**，即使其亲和力值为56.54 nM，这可能是因为：\n\n1. **预测模型的特性**：NetMHCpan的预测模型可能会根据特定的序列特征或结合位点的特性，将某些肽段标记为强结合。\n2. **结合位点的特性**：某些肽段可能在特定的结合位点上表现出更强的结合能力，即使整体亲和力值不在最强范围内。\n\n这些因素可能导致某些肽段被标记为强结合，即使其亲和力值略高于通常的强结合阈值。\n\n如果您对某个特定肽段的预测结果有疑问，可以进一步通过实验验证或使用其他工具进行交叉验证。\n\n接下来，我可以对 **LLLSAALAL** 进行结构预测，您是否希望继续？",
                create_time=datetime.strptime("2025-03-07 14:31:40", "%Y-%m-%d %H:%M:%S")
            ),
            MessageModel(
                id=msg_id_tool_3,#"ef354450-64a4-47ef-97cf-1cd55824f6fe",#
                conversation_id=new_conversation_id,
                query="那就预测VMAPRTVLL这个序列的结构吧",
                response="",
                create_time=datetime.strptime("2025-03-07 14:31:50", "%Y-%m-%d %H:%M:%S")
            )
        ]
        for message in messages:
            session.add(message)

        tools = [
            ToolModel(
                id=str(uuid.uuid4()),
                message_id=msg_id_tool_1,#"1e059843-7294-4a34-88d3-deb54542abb9",
                conversation_id=new_conversation_id,
                tool_id=f"tool_{uuid.uuid4().hex[:8]}",
                tool_name="ValidateFastaFile",
                tool_args='{"input_file": "minio://molly/8e81f329-a602-4b0c-bc69-2b110033d594_B0702.fsa"}',
                tool_result='{"type": "text", "content": "文件格式已完成验证，符合标准格式，请问是否继续？"}',
                create_time=datetime.strptime("2025-03-07 14:30:35", "%Y-%m-%d %H:%M:%S")
            ),
            ToolModel(
                id=str(uuid.uuid4()),
                message_id=msg_id_tool_2,#"0337064c-faa0-42b8-a39f-b083e1fb5907",
                conversation_id=new_conversation_id,
                tool_id=f"tool_{uuid.uuid4().hex[:8]}",
                tool_name="NetMHCpan",
                tool_args='{"input_file": "minio://molly/8e81f329-a602-4b0c-bc69-2b110033d594_B0702.fsa", "mhc_allele": "HLA-A02:01", "peptide_length": "9", "high_threshold_of_bp": 0.5, "low_threshold_of_bp": 2.0}',
                tool_result='{"type": "link", "url": "minio://netmhcpan-results/336537a209b543b19c2bb7162b99a838_netmhcpan_result.txt", "content": "**Protein B_070201. Allele HLA-A*02:01. Number of high binders 2. Number of weak binders 12. Number of peptides 354**\\n\\n| Peptide Sequence | HLA Allele | Bind Level | Affinity (nM) |\\n|------------------|------------|------------|---------------|\\n| RADPPKTHV | HLA-A*02:01 | WB | 11070.41 |\\n| YLENGKDKL | HLA-A*02:01 | WB | 1962.26 |\\n| VVIGAVVAA | HLA-A*02:01 | WB | 656.49 |\\n| RTFQKWAAV | HLA-A*02:01 | WB | 501.69 |\\n| GIVAGLAVL | HLA-A*02:01 | WB | 416.02 |\\n| YAYDGKDYI | HLA-A*02:01 | WB | 275.95 |\\n| VLAVVVIGA | HLA-A*02:01 | WB | 200.18 |\\n| MLVMAPRTV | HLA-A*02:01 | WB | 165.71 |\\n| GLAVLAVVV | HLA-A*02:01 | WB | 161.21 |\\n| ALGFYPAEI | HLA-A*02:01 | WB | 67.2 |\\n| VIGAVVAAV | HLA-A*02:01 | WB | 59.05 |\\n| VMAPRTVLL | HLA-A*02:01 | SB | 56.54 |\\n| VLLLLSAAL | HLA-A*02:01 | WB | 48.18 |\\n| LLLSAALAL | HLA-A*02:01 | SB | 17.32 |\\n\\n**当前结果**: 已完成亲和力强的肽段的筛选，我可以对LLLSAALAL进行结构的预测，请问是否继续？"}',
                create_time=datetime.strptime("2025-03-07 14:31:20", "%Y-%m-%d %H:%M:%S")
            ),
            ToolModel(
                id=str(uuid.uuid4()),
                message_id=msg_id_tool_3,#"ef354450-64a4-47ef-97cf-1cd55824f6fe",
                conversation_id=new_conversation_id,
                tool_id=f"tool_{uuid.uuid4().hex[:8]}",
                tool_name="ESM3",
                tool_args='{"protein_sequence": "VMAPRTVLL"}',
                tool_result='{"type": "link", "url": "minio://esm-results/68dde8d6ae48465086d7530372a51f04_esm3_result.pdb", "content": "已完成肽段序列的三维结构预测，并生成输出 PDB 文件。"}',
                create_time=datetime.strptime("2025-03-07 14:32:00", "%Y-%m-%d %H:%M:%S")
            )
        ]
        for tool in tools:
            session.add(tool)

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
async def insert_demo(user_id: str):
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
    asyncio.run(insert_demo())