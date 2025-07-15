from celery.signals import task_prerun, task_postrun, task_failure
from src.db.task_queue_model import TaskQueueModel
from src.utils.session import with_sync_session
from datetime import datetime, timezone

@with_sync_session
def insert_or_update_task_queue(session, task_queue_id, status, started_at=False, completed_at=False):
    task = session.get(TaskQueueModel, task_queue_id)
    if not task:
        print(f"[celery_task_signals] Warning: task_queue 里找不到 task_queue_id={task_queue_id}，不做插入。")
        return
    # 更新状态
    task.status = status
    if started_at:
        task.started_at = datetime.now(timezone.utc)
    if completed_at:
        task.completed_at = datetime.now(timezone.utc)
    session.commit()

@with_sync_session
def update_task_queue_celery_id_and_start(session, task_queue_id: int, celery_task_id: str, status: str):
    """
    根据主键id更新 celery_task_id、status 和 started_at。
    """
    task = session.get(TaskQueueModel, task_queue_id)
    if task:
        task.celery_task_id = celery_task_id
        task.status = status
        # started_at 统一为无时区 datetime
        task.started_at = datetime.now()
        session.commit()

@with_sync_session
def update_task_queue_celery_id_and_complete(session, task_queue_id: int, celery_task_id: str, status: str):
    """
    根据主键id更新 celery_task_id、status 和 completed_at。
    """
    task = session.get(TaskQueueModel, task_queue_id)
    if task:
        task.celery_task_id = celery_task_id
        task.status = status
        task.completed_at = datetime.now(timezone.utc)
        session.commit()

@task_prerun.connect
def task_started_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **other):
    task_queue_id = None
    if kwargs and 'task_queue_id' in kwargs:
        task_queue_id = kwargs['task_queue_id']
    update_task_queue_celery_id_and_start(task_queue_id, task_id, 'running')    

@task_postrun.connect
def task_completed_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **other):
    task_queue_id = None
    if kwargs and 'task_queue_id' in kwargs:
        task_queue_id = kwargs['task_queue_id']
    update_task_queue_celery_id_and_complete(task_queue_id, task_id, 'completed')

@task_failure.connect
def task_failed_handler(sender=None, task_id=None, **kwargs):
    insert_or_update_task_queue(task_id, 'failed') 