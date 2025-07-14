import asyncio

from celery import Celery
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import func, select

from src.db.workflows_model import WorkflowModel
from src.config import g_config
from src.utils.log import logger
from src.utils.base import get_async_session_local
from src.model.predict_openai_engine import predict_proxy_stream_generator
from src.api.protocols import PredictUserInputAgentRequest

# 导入信号监听模块，确保信号监听生效
import src.utils.celery_task_signals

agent_broker_url = g_config["url"]["agent_broker_url"]

celery_agent_app = Celery("worker", broker=agent_broker_url, backend=None)

@celery_agent_app.task(soft_time_limit=600, ignore_result=True)
def run_and_consume_generator(agent_request_dict, conversation_id, patient_id, unionid):
    """
    Celery任务入口，必须是同步def。参数agent_request_dict为dict，conversation_id为str。
    增加异常捕获，防止worker崩溃。
    """
    try:
        asyncio.run(_run(agent_request_dict, conversation_id, patient_id, unionid))
    except Exception as e:
        logger.error(f"Celery任务run_and_consume_generator执行异常: {e}", exc_info=True)

async def _run(agent_request_dict, conversation_id, patient_id, unionid):
    """
    真正的异步主逻辑，消费异步生成器，并在结束后执行回调。
    增加异常捕获，保证流程健壮。
    """
    try:
        if isinstance(agent_request_dict, dict):
            agent_request = PredictUserInputAgentRequest(**agent_request_dict)
        else:
            agent_request = agent_request_dict
        async for _ in predict_proxy_stream_generator(agent_request, conversation_id):
            pass
        await on_complete(patient_id, unionid)
    except Exception as e:
        logger.error(f"异步主逻辑_run执行异常: {e}", exc_info=True)

async def on_complete(patient_id, unionid):
    try:
        logger.info(f"开始执行on_complete回调，patient_id: {patient_id}")
        AsyncSessionLocal = get_async_session_local()
        async with AsyncSessionLocal() as session:
            try:
                workflow_result = await session.execute(
                    select(WorkflowModel)
                    .where(WorkflowModel.patient_id == int(patient_id))
                    .where(WorkflowModel.stage == '新抗原预测')
                    .where(WorkflowModel.rank == 3)
                )
                workflow_record = workflow_result.scalar_one_or_none()
                
                if workflow_record:
                    logger.info(f"找到工作流记录，当前状态: {workflow_record.status}")
                    workflow_record.status = 'completed'
                    workflow_record.completed_at = func.now()
                    workflow_record.completed_by = unionid
                    logger.info(f"设置状态为completed，准备提交...")
                    await session.commit()
                    logger.info(f"数据库提交完成")
                    logger.info(f"工作流状态已更新为completed，patient_id: {patient_id}")
                else:
                    logger.warning(f"未找到工作流记录，patient_id: {patient_id}")
            except Exception as db_e:
                logger.error(f"on_complete数据库操作异常: {db_e}", exc_info=True)
    except Exception as e:
        logger.error(f"on_complete回调执行失败: {e}", exc_info=True)