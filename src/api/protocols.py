
from typing import  Any, Optional, Union,Dict,List
from pydantic  import BaseModel
from code_knowledge_base.openmmlab_config import OpenmmlabInstance


class BaseResponse(BaseModel):
    """
    BaseResponse is a model that represents the response structure for API protocols.
    Attributes:
        result_code (int): The result code indicating the status of the response.
        result_message (Optional[str]): An optional message providing additional information about the result. Defaults to an empty string.
    """
    result_code:int = 0
    result_message:Optional[str] = "OK"

class BaseTask(BaseModel):
    """
    BaseRequest is a data model representing a request with a task ID and an optional task name.
    Attributes:
        task_id (str): The unique identifier for the task.
        task_name (Optional[str]): The name of the task. Defaults to an empty string.
    """

    task_id:str
    task_name:Optional[str] = ""

class RetrieveInstancesRequest(BaseModel):
    """
    RetrieveInstancesRequest is a data model for handling requests to retrieve instances.
    Attributes:
        query (str): The query string used to retrieve instances.
        project_name (Optional[str]): The name of the project. Defaults to None.
    """

    query:str
    project_name:Optional[str] = None

class RetrieveInstancesResponse(BaseResponse):
    """
    RetrieveInstancesResponse is a response model for retrieving instance details.
    Attributes:
        instance_full_path (str): The full path of the instance.
        instance_name (str): The name of the instance.
        project_name (str): The name of the project to which the instance belongs.
        description (Optional[str]): A brief description of the instance. Defaults to None.
        summary (Optional[str]): A summary of the instance. Defaults to None.
    """
    instance_full_path: str
    instance_name: str
    project_name: str
    description: Optional[str] = None
    summary: Optional[str] = None

class GenerateCodeRequest(BaseTask):
    """
    GenerateCodeRequest is a Pydantic model representing a request to generate code.
    Attributes:
        task_desc (Dict[str, Any]): A dictionary containing the task description.
        project (Optional[str]): The name of the project. Defaults to None.
        instance_full_path (Optional[str]): The full path to the instance. Defaults to None.
        previous_plan (Optional[str]): The previous plan associated with the task. Defaults to None.
        previous_code (Optional[str]): The previous code associated with the task. Defaults to None.
        previous_is_buggy (Optional[bool]): Indicates if the previous code was buggy. Defaults to None.
        previous_analysis (Optional[str]): The previous analysis associated with the task. Defaults to None.
    """
    task_desc: Dict[str, Any]
    project: Optional[str] = None
    instance_full_path: Optional[str] = None
    previous_plan: Optional[str] = None
    previous_code: Optional[str] = None
    previous_is_buggy: Optional[bool] = None
    previous_analysis: Optional[str] = None

class GenerateCodeResponse(BaseTask, BaseResponse):
    """
    GenerateCodeResponse is a response model for the code generation task.
    Attributes:
        task_id (str): The unique identifier for the code generation task.
        plan (str): The plan or strategy used for generating the code.
        code (str): The generated code as a string.
    """
    plan: str
    code: str

class RunAndEvaluateCodeRequest(BaseTask):
    """
    RunAndEvaluateCodeRequest is a data model for handling requests to run and evaluate code.

    Attributes:
        code (str): The code to be executed and evaluated.
        project (Optional[str]): The name of the project, if applicable.
        instance_full_path (Optional[str]): The full path to the instance, if applicable.
    """
    task_desc: Dict[str, Any]
    code: str
    project: Optional[str] = None
    instance_full_path: Optional[str] = None

class RunAndEvaluateCodeResponse(BaseTask, BaseResponse):
    """
    RunAndEvaluateCodeResponse is a response model for the run and evaluate code API.
    Attributes:
        term_out (str): The terminal output of the code execution.
        is_buggy (bool): Indicates whether the code is buggy.
        analysis (str): The analysis of the code execution.
        metric (Optional[float]): An optional metric related to the code execution.
    """
    term_out: str
    is_buggy: bool
    analysis:str
    metric: Optional[float] = None

class RunCodeAgentRequest(BaseTask):
    """
    RunCodeAgentRequest is a data model for a request to run a code agent.
    Attributes:
        task_desc (Dict[str, Any]): A dictionary containing the task description.
        project (Optional[str]): The name of the project. Defaults to None.
        instance_full_path (Optional[str]): The full path to the instance. Defaults to None.
        num_drafts (Optional[int]): The number of drafts. Defaults to None.
        max_debug_depth (Optional[int]): The maximum depth for debugging. Defaults to None.
        max_steps (Optional[int]): The maximum number of steps. Defaults to None.
    """
    task_desc: Dict[str, Any]
    project: Optional[str] = None
    instance_full_path: Optional[str] = None
    num_drafts: Optional[int] = None
    max_debug_depth: Optional[int] = None
    max_steps: Optional[int] = None

class RunCodeAgentResponse(BaseTask,BaseResponse):
    pass

class CheckCodeAgentTrackerRequest(BaseTask):
    """
    CheckCodeAgentTrackerRequest is a request model for tracking the agent's code check task.
    Attributes:
        task_id (str): The unique identifier for the task to be tracked.
    """
    pass

class CheckCodeAgentResponse(BaseTask, BaseResponse):
    """
    Response model for the CheckCodeAgent API.
    Attributes:
        html (str): The HTML content returned by the CheckCodeAgent.
    """
    html: str
    queue_position: int
    state: str