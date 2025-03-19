from pydantic import BaseModel
from typing import Optional,List,Dict,Any
from datetime import datetime

from pydantic import BaseModel, Field, SerializeAsAny
from typing_extensions import TypedDict

from src.model.models import AllModelEnum, OpenAIModelName

#基础响应模型
class  BaseResponse(BaseModel):
    ok: int = 0              # 0 表示成功，非 0 表示失败
    failed: str = ""         # 出错信息，默认为空

#创建用户请求模型
class AddUserRequest(BaseModel):
    unionid: str  # 用户统一标识（必填）
    openid: str  # 普通用户的标识（必填）
    nickname: Optional[str] = None  # 普通用户昵称（可选）
    sex: Optional[int] = None  # 普通用户性别，1为男性，2为女性（可选）
    province: Optional[str] = None  # 普通用户个人资料填写的省份（可选）
    city: Optional[str] = None  # 普通用户个人资料填写的城市（可选）
    country: Optional[str] = None  # 国家，如中国为CN（可选）
    headimgurl: Optional[str] = None  # 用户头像 URL（可选）
    privilege: Optional[str] = None  # 用户特权信息（可选）
    phone:Optional[str] = None #用户手机号（可选）
    email:Optional[str] = None #用户邮箱（可选）

#查询用户信息请求模型    
class QueryUserInfoRequest(BaseModel):
    openid : str  # 普通用户的标识，对当前开发者账号唯一
    unionid: str     # 用户统一标识。针对一个微信开放平台账号下的应用，同一用户的unionid是唯一的    

#查询用户信息响应模型
class QueryUserInfoResponse(BaseModel):
    unionid: str  # 用户统一标识。针对一个微信开放平台账号下的应用，同一用户的unionid是唯一的
    openid: str  # 普通用户的标识，对当前开发者账号唯一
    nickname: Optional[str] = None  # 普通用户昵称
    sex: Optional[int] = None  # 普通用户性别，1为男性，2为女性
    province: Optional[str] = None  # 普通用户个人资料填写的省份
    city: Optional[str] = None  # 普通用户个人资料填写的城市
    country: Optional[str] = None  # 国家，如中国为CN
    headimgurl: Optional[str] = None  # 用户头像，最后一个数值代表正方形头像大小
    privilege: Optional[List[str]] = None  # 用户特权信息，json数组，如微信沃卡用户为（chinaunicom）


#删除单一会话的请求模型
class DeleteSessionRequest(BaseModel):
    system_token:str #系统token
    session_id: str  # 会话 ID  

#查询会话历史请求模型
class SessionsRequest(BaseModel):
    # user_id: str     # 微信用户 unionid
    system_token: str

#清空所有会话请求模型
class DelAllSessionsRequest(BaseModel):
    system_token:str #系统token



#查询单一会话请求模型
class QuerySingleSessionRequest(BaseModel):
    system_token:str #系统token
    session_id: str  # 会话 ID    

#单条会话信息
class SessionItem(BaseModel):
    session_id: str  # 会话 ID
    session_title: str  # 会话标题
    updata_time: str   # 更新时间
    create_time: str  # 创建时间 
    chat_type : str #会话类型
    

    
#查询会话历史响应模型
class QuerySessionsResponse(BaseModel):
    ok: int          # 0 表示成功，非 0 表示失败
    failed: str      # 失败原因（如果成功则为空字符串）
    sessions: List[SessionItem]  # 会话列表

#单条聊天记录
class ChatItem(BaseModel):
    query: Optional[str] = None  # 用户输入
    response: Optional[str] = None  # AI 回复

class ToolItem(BaseModel):
    tool_name: str
    tool_args: str  
    tool_result: str  
    create_time: str

class ChatItemWithTools(BaseModel):
    id: str
    query: str
    response: Optional[str] = None
    create_time: str
    tools: Optional[List[ToolItem]] = None

class FileItem(BaseModel):
    file_name: str
    file_path: str
    file_desc: str

class QuerySessionResponse(BaseModel):
    ok: int
    failed: str
    session_id: str
    # session_title: Optional[str] = None
    session_title: str
    chats: Optional[List[ChatItemWithTools]] = None  # 可以是 None 或 List[ChatItemWithTools]
    files: Optional[List[FileItem]] = None  # 可以是 None 或 List[FileItem]

# 单一会话的响应模型   
# class QuerySessionResponse(BaseModel):
#     session_id: str  # 会话 ID
#     ok: int          # 0 表示成功，非 0 表示失败
#     failed: str      # 空表示成功，否则是出错信息
#     chats: List[ChatItem]  # 聊天记录列表   

#插入单一会话（用户输入）请求模型
class InsertUserInputSessionRequest(BaseModel):
    id: str  # 会话ID
    query: str  # 用户输入
    response: Optional[str] = None  # 模型回答（可选）
    meta_data: Optional[Dict[str, Any]] = None  # 元数据（可选）
    feedback_score: Optional[int] = None  # 用户评分（可选）
    feedback_reason: Optional[str] = None  # 用户评分理由（可选）

#插入单一会话（用户输入）请求模型
class InsertAIInputSessionRequest(BaseModel):
    id: str     # 消息ID
    response: str       # 模型输入    
          
#新建会话请求模型
class AddSessionRequest(BaseModel):
    system_token:str
    session_title: Optional[str] = "新会话"    # 会话标题  
    chat_type: str = "normal"

#聊天消息请求模型
class ChatRequest(BaseModel):
    prompt: str

#新建会话记录响应模型
class SessionResponse(BaseResponse):
    conversation_id: str

#更改会话名称请求模型    
class UpdateSessionRequest(BaseModel):
    system_token:str
    session_id: str  # 会话 ID 
    session_title: Optional[str] = "新会话"    # 会话标题     

class FileInfo(BaseModel):
    file_name: str = Field(description="文件名")
    file_content: str = Field(description="文件内容")
    file_path: str = Field(description="文件路径")
    file_desc: str = Field(description="文件概述")

class FileGroup(BaseModel):
    conversation_id: Optional[str] = Field(description="会话 ID，UUID 格式，长度 36", max_length=36, min_length=36)
    files: List[FileInfo] = Field(description="文件列表")

class UserInput(BaseModel):
    """User input processed by the FastAPI server and sent to the target server."""
    prompt: str = Field(description="用户输入")
    system_token: str = Field(description="系统token")
    conversation_id: str = Field(description="会话id")
    file_list: List[FileGroup] = Field(description="传入文件列表", default=[])

#文件下载请求
class DownloadFileRequest(BaseModel):
    file_path: str
    system_token: str

#文件描述请求
class DescRequest(BaseModel):
    file_name: str
    file_content: str

class DescResponse(BaseModel):
    file_description: str


#新建会话记录响应模型
class DisplayResponse(BaseResponse):
    content_target: str

class WebLogoRequest(BaseModel):
    peptide_sequences: list 
    logo_type: str = "svg"  
    color_scheme: str = "auto"  
    logo_title: str = "Sequence Motif Analysis"
    system_token: str 