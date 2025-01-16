import os
import sys
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

import logging
import logging.config as log_config
from config import g_config

cmd = "cat /proc/self/cgroup"
output = os.popen(cmd)
rests = output.readlines()
container_message = rests[0]
appendstr = ""
if container_message and "docker" in container_message:
    appendstr= container_message.strip().split("docker")[-1][1:]
elif container_message and "kubepods" in container_message and "/" in container_message:
    appendstr= container_message.strip().split("/")[-1][:12]

logger_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simpleFormater": {
            "format": "%(asctime)s.%(msecs)03d - %(filename)s[line:%(lineno)d] - %(levelname)7s: %(name)10s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simpleFormater",
            "level": "DEBUG"
        },
        "log_file_handler": {
            "filename": "./log.txt",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": "DEBUG",
            "formatter": "simpleFormater",
            "when": "d",
            "interval": 1,
            "backupCount": 10,
            "encoding": "utf8"
        }
    },
    "root": {
        "level": "DEBUG",
        "handlers": [
            "log_file_handler",
            "console"
        ]
    }
}

def config_logger(log_dir, log_level, name):
    # config logger

    if not log_level:
        log_level = "INFO"

    filename = os.path.join(log_dir, f'{appendstr}_{name}.log')
    logger_config['handlers']['log_file_handler']['filename'] = filename
    logger_config['handlers']['log_file_handler']['level'] = log_level
    logger_config['handlers']['console']['level'] = log_level
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    log_config.dictConfig(logger_config)

# 创建日志存储路径
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), g_config["log"]['log_path'])
if not os.path.exists(LOG_PATH):
    os.mkdir(LOG_PATH)

config_logger(g_config["log"]['log_path'], g_config["log"]['log_level'], f"server")

logger = logging.getLogger()



