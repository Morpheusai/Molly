from celery.signals import task_prerun, task_postrun, task_failure
from src.db.task_queue_model import TaskQueueModel
from src.utils.session import with_sync_session
import datetime

@with_sync_session
def insert_or_update_task_queue(session, celery_task_id, status, started_at=False, completed_at=False):
    task = session.query(TaskQueueModel).filter_by(celery_task_id=celery_task_id).first()
    if not task:
        # 插入新记录
        task = TaskQueueModel(
            celery_task_id=celery_task_id,
            status=status,
            started_at=datetime.datetime.utcnow() if started_at else None,
            completed_at=datetime.datetime.utcnow() if completed_at else None
        )
        session.add(task)
    else:
        # 更新状态
        task.status = status
        if started_at:
            task.started_at = datetime.datetime.utcnow()
        if completed_at:
            task.completed_at = datetime.datetime.utcnow()
    session.commit()

@task_prerun.connect
def task_started_handler(sender=None, task_id=None, **kwargs):
    insert_or_update_task_queue(task_id, 'running', started_at=True)

@task_postrun.connect
def task_completed_handler(sender=None, task_id=None, **kwargs):
    insert_or_update_task_queue(task_id, 'completed', completed_at=True)

@task_failure.connect
def task_failed_handler(sender=None, task_id=None, **kwargs):
    insert_or_update_task_queue(task_id, 'failed') 