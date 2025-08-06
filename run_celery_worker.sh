#!/bin/bash
# 启动 Celery worker 的脚本，自动设置 IS_CELERY_WORKER 环境变量
# 默认后台运行（--detach），如需前台运行请参考注释

# 设置环境变量，确保 Celery worker 进程识别为 worker 环境
export IS_CELERY_WORKER=1

# 启动 Celery worker，后台运行（--detach）
celery -A src.utils.celery_task_agent worker --loglevel=info --concurrency=1 --prefetch-multiplier=1 --detach --logfile=/var/log/celery/stg/celery.log

# 如果你想在前台运行（调试用），请注释掉上面一行，取消下面一行的注释：
# celery -A src.utils.celery_task_agent worker --loglevel=info --time-limit=21600 --soft-time-limit=21600 