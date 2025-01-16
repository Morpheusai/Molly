
import copy
import logging
from typing import List

from fastapi import BackgroundTasks
from config import g_config
from .protocols import *
from constants import CodeAgentState
from utils import init_tables, qeury_code_agent

init_tables()

def add_user(req: RunCodeAgentRequest, background_tasks: BackgroundTasks):
    """
    Asynchronously runs a code agent with the provided configuration and task description.
    Args:
        req (RunCodeAgentRequest): The request object containing task details and configuration overrides.
        background_tasks (BackgroundTasks): The background tasks manager to add the code agent task to.
    Returns:
        RunCodeAgentResponse: The response object containing the task ID of the initiated code agent task.
    The function performs the following steps:
    1. Creates a deep copy of the global configuration.
    2. Updates the task description with instance full path and project if provided in the request.
    3. Overrides the number of drafts, maximum steps, and maximum debug depth in the configuration if provided in the request.
    4. Initializes a CodeAgent with the updated configuration and task details.
    5. Adds the code agent's run method to the background tasks.
    6. Returns a response containing the task ID.
    """

def delete_specific_session(req: CheckCodeAgentTrackerRequest):
    """
    Asynchronously checks the code agent tracker and returns the corresponding HTML.
    Args:
        req (CheckCodeAgentTrackerRequest): The request object containing the task ID.
    Returns:
        CheckCodeAgentResponse: The response object containing the task ID and the HTML content of the tracker.
    """