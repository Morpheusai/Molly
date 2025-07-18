from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any,Literal, Union
from pydantic import validator



#基础响应模型
class  BaseResponse(BaseModel):
    ok: int = 0              # 0 表示成功，非 0 表示失败
    failed: str = ""         # 出错信息，默认为空


#创建用户请求模型
class AddUserRequest(BaseModel):
    unionid: str  # 用户统一标识（主键，必填）
    openid: str  # 普通用户标识（必填）
    role: Literal['chief', 'assistant'] = 'assistant'  # 用户角色，默认助手
    nickname: Optional[str] = None  # 用户昵称
    phone: Optional[str] = None  # 手机号
    email: Optional[str] = None  # 邮箱
    city: Optional[str] = None  # 城市
    province: Optional[str] = None  # 省份
    country: Optional[str] = None  # 国家
    headimgurl: Optional[str] = None  # 头像URL
    created_by: Optional[str] = None  # 邀请人unionid
    is_active: bool = True  # 是否激活，默认True

# #查询用户信息请求模型    
# class QueryUserInfoRequest(BaseModel):
#     openid : str  # 普通用户的标识，对当前开发者账号唯一
#     unionid: str     # 用户统一标识。针对一个微信开放平台账号下的应用，同一用户的unionid是唯一的    

# #查询用户信息响应模型
# class QueryUserInfoResponse(BaseModel):
#     unionid: str  # 用户统一标识。针对一个微信开放平台账号下的应用，同一用户的unionid是唯一的
#     openid: str  # 普通用户的标识，对当前开发者账号唯一
#     nickname: Optional[str] = None  # 普通用户昵称
#     sex: Optional[int] = None  # 普通用户性别，1为男性，2为女性
#     province: Optional[str] = None  # 普通用户个人资料填写的省份
#     city: Optional[str] = None  # 普通用户个人资料填写的城市
#     country: Optional[str] = None  # 国家，如中国为CN
#     headimgurl: Optional[str] = None  # 用户头像，最后一个数值代表正方形头像大小
#     privilege: Optional[List[str]] = None  # 用户特权信息，json数组，如微信沃卡用户为（chinaunicom）


# #删除单一会话的请求模型
# class DeleteSessionRequest(BaseModel):
#     conversation_id: str  # 会话 ID  

# # #查询会话历史请求模型
# # class SessionsRequest(BaseModel):
# #     # user_id: str     # 微信用户 unionid
# #     system_token: str



# #查询单一会话请求模型
# class QuerySingleSessionRequest(BaseModel):
#     conversation_id: str  # 会话 ID    

# #单条会话信息
# class SessionItem(BaseModel):
#     conversation_id: str  # 会话 ID
#     session_title: str  # 会话标题
#     updata_time: str   # 更新时间
#     create_time: str  # 创建时间 
#     chat_type : str #会话类型
    

    
# #查询会话历史响应模型
# class QuerySessionsResponse(BaseModel):
#     ok: int          # 0 表示成功，非 0 表示失败
#     failed: str      # 失败原因（如果成功则为空字符串）
#     sessions: List[SessionItem]  # 会话列表

# #单条聊天记录
# class ChatItem(BaseModel):
#     query: Optional[str] = None  # 用户输入
#     response: Optional[str] = None  # AI 回复

# class ToolItem(BaseModel):
#     tool_name: str
#     tool_args: str  
#     tool_result: str  
#     create_time: str
#     tool_result_analysis :str
#     tool_middle_result :str

# class ChatItemWithTools(BaseModel):
#     id: str
#     query: str
#     response: Optional[str] = None
#     create_time: str
#     tools: Optional[List[ToolItem]] = None

# class FileItem(BaseModel):
#     file_name: str
#     file_path: str
#     file_desc: str

# class QuerySessionResponse(BaseModel):
#     ok: int
#     failed: str
#     conversation_id: str
#     session_title: str
#     chat_type:str
#     chats: Optional[List[ChatItemWithTools]] = None  # 可以是 None 或 List[ChatItemWithTools]
#     files: Optional[List[FileItem]] = None  # 可以是 None 或 List[FileItem]
#     neo_files: Optional[List[FileItem]] = None

# # 单一会话的响应模型   
# # class QuerySessionResponse(BaseModel):
# #     conversation_id: str  # 会话 ID
# #     ok: int          # 0 表示成功，非 0 表示失败
# #     failed: str      # 空表示成功，否则是出错信息
# #     chats: List[ChatItem]  # 聊天记录列表   

          
# #新建会话请求模型
# class AddSessionRequest(BaseModel):
#     session_title: Optional[str] = "新会话"    # 会话标题  
#     chat_type: str = "normal"

# #聊天消息请求模型
# class ChatRequest(BaseModel):
#     prompt: str

# #新建会话记录响应模型
# class SessionResponse(BaseResponse):
#     conversation_id: str

# #更改会话名称请求模型    
# class UpdateSessionRequest(BaseModel):
#     conversation_id: str  # 会话 ID 
#     session_title: Optional[str] = "新会话"    # 会话标题     

class FileInfoWithContent(BaseModel):
    file_name: str = Field(description="文件名")
    file_content: str = Field(description="文件内容")
    file_path: str = Field(description="文件路径")
    file_desc: str = Field(description="文件概述")
    file_origin: int = Field(description="文件上传类型，0表示用户上传，1表示系统上传")

class FileGroup(BaseModel):
    conversation_id: Optional[str] = Field(description="会话 ID，UUID 格式，长度 36", max_length=36, min_length=36)
    files: List[FileInfoWithContent] = Field(description="文件列表")

class UserInput(BaseModel):
    """User input processed by the FastAPI server and sent to the target server."""
    prompt: str = Field(description="用户输入")
    conversation_id: str = Field(description="会话id")
    file_list: List[FileGroup] = Field(description="传入文件列表", default=[])
    conversation_chat_type: str = Field(description="会话聊天类型", default="normal")


class CustomPredictUserInputRequest(BaseModel):
    """用户自定义参数的请求类，包含必填字段验证"""
    patient_id: int = Field(description="病人id")
    parameters: dict[str, Any] = Field(
        description="预测参数，必须包含netchop且其中必须包含input_filename",
        examples=[{
            "netchop": {
                "input_filename": "minio://molly/4aa36c4a-dba3-4640-b2f7-dc2b6fd2662b.fasta"
            }
        }]
    )

    # @validator('parameters')
    # def validate_parameters(cls, v):
    #     """验证parameters中必须包含netchop且其中必须包含input_filename"""
    #     if not isinstance(v, dict):
    #         raise ValueError('parameters必须是字典类型')
        
    #     if 'netchop' not in v:
    #         raise ValueError('parameters中必须包含netchop字段')
            
    #     netchop = v.get('netchop')
    #     if not isinstance(netchop, dict):
    #         raise ValueError('netchop必须是字典类型')
            
    #     if 'input_filename' not in netchop:
    #         raise ValueError('netchop中必须包含input_filename字段')
            
    #     return v

class PredictUserInputRequest(BaseModel):
    """Basic user input for the agent."""
    patient_id: int = Field(description="病人id")
    conversation_id: int = Field(description="会话id")
    file_path: str = Field(
        description="测序文件minio路径",
        examples=["minio://molly/6e461c0b-876c-4a98-9e7e-a743ec71c7b0_bigmhc_el.fasta"],
    )
    conversation_chat_type: str = Field(description="会话聊天类型", default="normal")
    parameters: dict[str, Any] = Field(
        description="预测参数",
        default={},
        examples=[
            {
                "netchop": {
                    "cleavage_site_threshold": 0.5,
                    "model": 0,
                    "format": 0,
                    "strict": 0
                },
                "netctlpan": {
                    "peptide_length": -1 ,
                    "weight_of_tap": 0.025,
                    "weight_of_clevage": 0.225,
                    "epi_threshold": 1.0,
                    "output_threshold": -99.9,
                    "sort_by": -1
                },
                "netmhcpan": { 
                    "peptide_length": -1 ,
                    "high_threshold_of_bp": 0.5,
                    "low_threshold_of_bp": 2.0,
                    "rank_cutoff": -99.9,
                },
                "bigmhc_im": {
                }
            }
        ]
    )

class PredictUserInputAgentRequest(BaseModel):
    prompt: str = Field(
        description="User input to the agent.",
        examples=["_______________________________DQATSLRILNNGHAFNVEFDDSQDKAVLK"or"What is the weather in Tokyo?"],
    )

    patient_id: int = Field(description="病人id")

    predict_id: int = Field(description="预测表id")

    conversation_id: int = Field(
        description="会话id",
    )

    file_path: str = Field(
        description="测序文件minio路径",
        examples=["minio://molly/6e461c0b-876c-4a98-9e7e-a743ec71c7b0_bigmhc_el.fasta"],
    )
    mhc_allele: str = Field(
        description="HLA分型",
        examples=["HLA-A*0201,HLA-B*0702"],
    )
    cdr3: Optional[List[str]] = Field(
        description="cdr3序列",
        examples=[["CASSIRSSYEQYF", "CASSLGQGAEAFF"]],
        default=None,
    )
    conversation_chat_type: str = Field(description="会话聊天类型", default="predict_neo_antigen")

    parameters: dict[str, Any] = Field(
    description="预测参数",
    default={},
    examples=[
        {
            "netchop": {
                "peptide_length": [9],
                "cleavage_site_threshold": 0.5,
                "model": 0,
                "format": 0,
                "strict": 0
            },
            "netctlpan": {
                "peptide_length": [9],
                "weight_of_tap": 0.025,
                "weight_of_clevage": 0.225,
                "epi_threshold": 1.0,
                "output_threshold": -99.9,
                "sort_by": -1
            },
            "netmhcpan": { 
                "peptide_length": [9],
                "high_threshold_of_bp": 0.5,
                "low_threshold_of_bp": 2.0,
                "rank_cutoff": -99.9,
            },
            "bigmhc_im": {
            }
        }
    ]
)


#文件下载请求
class DownloadFileRequest(BaseModel):
    file_path: str

#文件描述请求
class DescRequest(BaseModel):
    file_name: str
    file_content: str

class DescResponse(BaseModel):
    file_description: str


# #新建会话记录响应模型
class DisplayResponse(BaseResponse):
    content_target: str

# class WebLogoRequest(BaseModel):
#     peptide_sequences: list 
#     logo_type: str = "svg"  
#     color_scheme: str = "auto"  
#     logo_title: str = "Sequence Motif Analysis"

# #neo文件迁移到普通文件请求
# class MigrateFileRequest(BaseModel):
#     file_paths: List[str]
#     conversation_id: str
    
# class ResetConversationRequest(BaseModel):
#     conversation_id: str

# 创建病历请求模型
class CreateMedicalRecordRequest(BaseModel):
    patient_id: Optional[Union[int, str]] = ""  # 新增或修改病人时用
    project_id: int = Field(..., description="所属项目ID")
    medical_record_number: Optional[str] = Field(default="", description="病历号")
    name: Optional[str] = Field(default="", description="患者姓名")
    gender: Optional[Literal['male', 'female', 'other']] = Field(default="other", description="性别")
    birth_date: Optional[str] = Field(default="", description="出生日期，格式：YYYY-MM-DD")
    phone: Optional[str] = Field(default="", description="联系电话")
    email: Optional[str] = Field(default="", description="电子邮箱")
    hospital: Optional[str] = Field(default="", description="所在医院")
    blood_type: Optional[Literal['A', 'B', 'AB', 'O', 'unknown']] = Field(default="unknown", description="血型")
    tumor_type: Optional[str] = Field(default="", description="癌种类型")
    HLA_type: Optional[str] = Field(default="", description="HLA分型")
    CDR_type: Optional[str] = Field(default="", description="CDR数据")
    treatment_state: Optional[str] = Field(default="", description="治疗阶段")
    additional_info: Optional[str] = Field(default="", description="附加信息")
    source_id: Optional[int] = Field(default=None, description="病历来源文件ID，可不传")
    clinical_medication: Optional[str] = Field(default="", description="临床用药")
    clinical_diagnosis: Optional[str] = Field(default="", description="临床诊断")

# 创建病历响应模型
class CreateMedicalRecordResponse(BaseResponse):
    patient_id: Optional[int] = Field(None, description="创建的患者ID")

# 文件简要信息的数据结构，用于描述单个文件的核心属性
class FileBriefInfo(BaseModel):
    file_name: str  # 文件名
    file_type: str  # 文件类型（如病历、测序等）
    file_desc: str  # 文件描述
    file_path: str  # 文件存储路径
    created_at: str  # 文件创建时间（字符串格式）

# 病人及其所有文件信息的数据结构
class PatientWithFilesInfo(BaseModel):
    patient_id: int  # 病人主键ID
    medical_record_number: str  # 病历号
    name: str  # 患者姓名
    gender: str  # 性别
    birth_date: Optional[str]  # 出生日期
    phone: str  # 联系电话
    email: str  # 电子邮箱
    hospital: str  # 所在医院
    blood_type: str  # 血型
    tumor_type: str  # 癌种类型
    HLA_type: str  # HLA分型
    CDR_type: str  # CDR数据
    treatment_state: str  # 治疗阶段
    additional_info: str  # 附加信息
    status: str  # 病历状态
    source_id: str  # 病历来源文件ID
    created_at: str  # 病人创建时间
    files: List[FileBriefInfo]  # 该病人下所有文件的简要信息列表

# 用户所有病人及其文件信息的接口响应结构
class UserPatientsFilesResponse(BaseResponse):
    patients: List[PatientWithFilesInfo] = []  # 病人及其文件信息的列表

# 获取项目下所有病人简要信息请求模型
class GetProjectPatientsRequest(BaseModel):
    project_id: int = Field(..., description="所属项目ID")

# 病人简要信息
class PatientBriefInfo(BaseModel):
    patient_id: int  # 病人主键ID
    name: str        # 病人姓名
    medical_record_number:str #病人编号

# 获取项目下所有病人简要信息响应模型
class PatientBriefListResponse(BaseResponse):
    data: Optional[List[PatientBriefInfo]] = None

# 病人详细信息的数据结构（不含id/source_id/created_at等字段）
class PatientDetailInfo(BaseModel):
    medical_record_number: str  # 病历号
    name: str                  # 患者姓名
    gender: str                # 性别
    birth_date: str | None = None  # 出生日期
    phone: str                 # 联系电话
    email: str                 # 电子邮箱
    hospital: str              # 所在医院
    blood_type: str            # 血型
    tumor_type: str            # 癌种类型
    HLA_type: str              # HLA分型
    CDR_type: str              # CDR数据
    treatment_state: str       # 治疗阶段
    additional_info: str       # 附加信息
    clinical_medication: str | None = None  # 临床用药
    clinical_diagnosis: str | None = None   # 临床诊断
    status: str                # 病历状态
    updated_at: str | None = None  # 更新时间

# 获取病人详细信息的接口响应结构
class PatientDetailResponse(BaseResponse):
    data: PatientDetailInfo | None = None  # 病人详细信息

# 获取病人详细信息的请求模型
class PatientDetailRequest(BaseModel):
    patient_id: int  # 需要查询的病人主键ID
    file_type: Optional[str] = Field(None, description="要筛选的文件类型，不传则返回所有类型")

# 创建项目请求模型
class CreateProjectRequest(BaseModel):
    project_id: Optional[int] = Field(default=None, description="项目ID，如果不传则创建新项目，如果传入则更新现有项目")
    name: Optional[str] = Field(default=None, description="项目名称")
    project_code: Optional[str] = Field(default=None, description="项目编号")
    short_name: Optional[str] = Field(default=None, description="项目简称")
    description: Optional[str] = Field(default=None, description="项目简介")
    project_type: Optional[Literal['IIT', '注册试验', '探索性研究']] = Field(default=None, description="项目类型")
    indication: Optional[str] = Field(default=None, description="适应症")
    study_phase: Optional[Literal['I期', 'II期', 'III期', '未指定', 'IIT']] = Field(default=None, description="研究分期")
    is_multicenter: Optional[Literal['是', '否']] = Field(default=None, description="是否多中心")
    registration_number: Optional[str] = Field(default=None, description="注册号")
    registration_platform_url: Optional[str] = Field(default=None, description="注册平台链接")
    principal_investigator: Optional[str] = Field(default=None, description="项目负责人")
    pi_email: Optional[str] = Field(default=None, description="项目负责人邮箱")
    hospital: Optional[str] = Field(default=None, description="所属医院")
    phone: Optional[str] = Field(default=None, description="手机号")
    patient_enrollment_count: Optional[int] = Field(default=None, description="患者入组人数")
    status: Optional[int] = Field(default=0, description="项目状态：0-保存草稿，1-创建立项")
    enrollment_criteria: Optional[str] = Field(default=None, description="入组要求")

# 创建项目响应模型
class CreateProjectResponse(BaseResponse):
    project_id: int | None = Field(None, description="创建的项目ID")

# 查询项目列表响应模型
class ProjectInfo(BaseModel):
    project_id: int
    name: str
    status: int = Field(description="项目状态：0-保存草稿，1-创建立项")

class ProjectListResponse(BaseResponse):
    projects: list[ProjectInfo] = []

class PatientInfoRequest(BaseModel):
    """病人信息提取请求模型"""
    patient_info: str = Field(description="病人的原始信息文本")

class PatientInfoResponse(BaseResponse):
    """病人信息提取响应模型"""
    content: Optional[str] = Field(None, description="文件完整内容")
    structured_info: dict = Field(description="结构化后的病人信息")

class FileInfo(BaseModel):
    """
    单个文件信息，包含文件名、路径、类型和描述
    """
    file_name: str  # 文件名
    file_path: str  # 文件路径
    file_type: str  # 文件类型
    file_desc: str  # 文件描述

class PatientFilesResponse(BaseResponse):
    """
    查询病人所有文件时的响应结构
    files: 文件列表
    total: 文件总数
    """
    files: list[FileInfo] = []  # 文件列表
    total: int = 0  # 文件总数

class CreateConversationRequest(BaseModel):
    """创建新会话的请求模型"""
    patient_id: int = Field(description="病人id")
    conversation_type: Optional[str] = Field(default="normal", description="会话类型")
    title: Optional[str] = Field(default="新会话", description="会话标题")

class CreateConversationResponse(BaseResponse):
    """创建新会话的响应模型"""
    conversation_id: Optional[int] = Field(None, description="新建的会话ID")

class GetConversationMessagesRequest(BaseModel):
    """获取会话消息列表的请求模型"""
    patient_id: int = Field(..., description="病人ID")
    conversation_type: str = Field(..., description="会话类型")

class MessageInfo(BaseModel):
    """单个消息的信息模型"""
    id: int
    type: str
    content: str
    create_time: str

class ConversationMessagesResponse(BaseResponse):
    """会话消息列表的响应模型"""
    conversation_id: Optional[int] = Field(default=None)
    messages: List[MessageInfo] = []

class GetWorkflowStatusRequest(BaseModel):
    """获取工作流状态请求模型"""
    patient_id: int = Field(..., description="病人ID")

class WorkflowStatusInfo(BaseModel):
    """工作流状态信息模型"""
    stage: str
    status: str
    rank: int

class GetWorkflowStatusResponse(BaseResponse):
    """获取工作流状态响应模型"""
    data: Optional[List[WorkflowStatusInfo]] = None

class PredictionDetailItem(BaseModel):
    rank: int
    tool_name: str
    tool_parameters: dict[str, Any]
    status: str
    start_time: str | None = None
    end_time: str | None = None
    elapsed_time: int | None = None
    error_message: str | None = None
    tool_output: dict | None = None
    flag: int = 0

class PredictionGroup(BaseModel):
    prediction_id: int
    create_time: str
    prediction_details: list[PredictionDetailItem]

class PredictionDetailListResponse(BaseResponse):
    details: list[PredictionGroup] = []
    flag: int = 0


"""验证工具的输入、输出类，存入预测细节表中"""

class NetchopParameters(BaseModel):
    input_filename: str = Field(
        description = "指定输入的fasta文件名",
        examples = ["testA.fsa"],
    )
    cleavage_site_threshold: float = Field(
        description="设定切割位点的阈值(0~1 之间的浮点数), 值越高，预测越严格，返回的切割位点越少。",
        default=0.5,
        examples=[0.5],
    )
    model: int = Field(
        description="选择预测模型版本: 0-Cterm3.0(预测C端切割位点); 1-20S-3.0(预测蛋白酶体 20S 的切割位点)",
        default = 0,
        examples=[0],
    )
    format: int = Field(
        description = "控制输出格式: 0-长格式(默认，包含详细预测信息); 1-短格式(仅输出切割位点)",
        default = 0,
        examples=[0],
    )
    strict: int = Field(
        description="关闭严格模式: 严格模式（默认）会过滤低置信度预测，关闭后可能增加假阳性。",
        default = 0,
        examples=[0],
    )

class NetctlpanParameters(BaseModel):
    input_filename: str = Field(
        description = "指定输入的fasta文件名",
        examples=["testA.fsa"],
    )
    mhc_allele: str = Field(
        description="指定HLA等位基因（MHC 分子类型）",
        default = "HLA-A02:01",
        examples=["HLA-A02:01"],
    )
    peptide_length: int = Field(
        description = "是否指定肽段长度, -1: 不指定，默认输出8-11长度的结果",
        default = -1,
        examples = [8],
    )
    weight_of_tap: float = Field(
        description = "TAP 转运效率的权重(综合得分计算)，权重值越低，TAP 对综合得分的影响越小。调整此参数可优化预测模型。 ",
        default = 0.025,
        examples=[0],
    )
    weight_of_clevage: float = Field(
        description = "蛋白酶体切割效率的权重（综合得分计算）。比TAP权重大，表明切割效率对综合得分影响更显著。",
        default = 0.225,
        examples=[0],
    )
    epi_threshold: float = Field(
        description = "定义表位（epitope）的阈值，高于此值的肽段可能被标记为潜在表位。用于快速筛选高亲和力候选肽段，具体阈值需根据实验数据调整。  ",
        default = 1.0,
        examples=[0],
    )
    output_threshold: float = Field(
        description = "输出结果的得分阈值，仅显示高于此值的预测结果。默认值极低，通常会输出所有结果。若需筛选高亲和力肽段，可设为正值（如 1.0）。",
        default = -99.9,
        examples=[0],
    )
    sort_by: int = Field(
        description = \
f"""
控制输出结果的排序方式: 
  0: 按综合得分（Combined）排序
  1: 按MHC结合得分（MHC）排序
  2: 按蛋白酶体切割效率（Cleavage）排序
  3: 按TAP转运效率（TAP）排序  
  <0: 保持原始顺序（不排序）  
""",
        default = -1,
        examples=[0],
    )

class NetmhcpanParameters(BaseModel):
    input_filename: str = Field(
        description = "指定输入的fasta文件名",
        examples=["testA.fsa"],
    )
    mhc_allele: str = Field(
        description="指定HLA等位基因（MHC 分子类型）",
        default = "HLA-A02:01",
        examples=["HLA-A02:01"],
    )
    peptide_length: int = Field(
        description = "是否指定肽段长度, -1: 不指定，默认输出8-11长度的结果",
        default = -1,
        examples = [8],
    )
    high_threshold_of_bp: float = Field(
        description = "设置高亲和力肽段的阈值。阈值越低，筛选出来的高亲和力肽段亲和力越好。",
        default = 0.5,
        examples=[0.1],
    )
    low_threshold_of_bp: float = Field(
        description = "设定低结合力肽段的阈值。阈值越高，筛选出来的低结合力肽段亲和力越差。 ",
        default = 2.0,
        examples=[2.1],
    )
    rank_cutoff: float = Field(
        description = \
f"""
控制输出结果的%Rank截断值。  
说明：
 - 若设置为正数（如5.0），则仅输出%Rank ≤ 5.0的肽段。
 - 若设置为负数（如默认值-99.9），则输出所有肽段（无论%Rank高低）。
 - 该参数用于灵活控制结果文件的体积和筛选范围。
""",
        default = -99.9,
        examples=[5.0],
    )

class BigmhcIMParameters(BaseModel):
    """Parameters for BigMHC-IM."""
    input_filename: str = Field(
        description = "指定输入的fasta文件名",
        examples=["testA.fsa"],
    )
    mhc_allele: str = Field(
        description="指定HLA等位基因（MHC 分子类型）",
        default = "HLA-A02:01",
        examples=["HLA-A02:01"],
    )

class ToolOutput(BaseModel):
    """
    工具输出模型
    - output: 工具输出内容（字典）
    """
    tool_output: dict = Field(description="工具输出内容")

# 新增：工具输入输出请求模型
class ToolInputOutputRequest(BaseModel):
    """工具输入输出请求模型"""
    patient_id: int = Field(..., description="病人ID")
    prediction_id: int = Field(..., description="预测ID")
    mode: int = Field(..., description="模式：0-工具输入参数，1-工具输出结果")
    tool_name: str = Field(..., description="工具名称：BigMHC_IM、NetChop、NetCTLpan、NetMHCPan")
    parameters: dict = Field(..., description="工具参数或输出结果")
    flag: int = Field(default=0, description="流程结束标志：0-未结束，1-已结束")

# 新增：工具输入输出响应模型
class ToolInputOutputResponse(BaseResponse):
    """工具输入输出响应模型"""
    predict_detail_id: Optional[int] = Field(None, description="预测详情ID")

class HandleAIMessageRequest(BaseModel):
    """
    处理AI消息的请求模型。
    用于指定会话ID和要追加或新建的AI消息内容。
    字段：
        conversation_id: int，会话ID。
        ai_message: str，要追加或新建的AI消息内容。
    """
    conversation_id: int = Field(..., description="会话ID")
    ai_message: str = Field(..., description="AI消息内容")

class HandleAIMessageResponse(BaseResponse):
    """
    处理AI消息的响应模型。
    返回操作后的消息ID和最新的消息内容。
    字段：
        message_id: int | None，操作后的消息ID。
        content: str | None，最新的消息内容。
    """
    message_id: int | None = Field(None, description="操作后的消息ID")
    content: str | None = Field(None, description="最新的消息内容")

class GetProjectDetailRequest(BaseModel):
    """
    获取项目详情的请求模型
    参数：
        project_id: 项目ID
    """
    project_id: int = Field(..., description="项目ID")

class ProjectDetailInfo(BaseModel):
    """
    项目详情信息模型（包含所有字段）
    """
    name: str = Field(description="项目名称")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")
    project_code: str | None = Field(None, description="项目编号")
    short_name: str | None = Field(None, description="项目简称")
    description: str | None = Field(None, description="项目简介")
    project_type: str = Field(description="项目类型")
    indication: str | None = Field(None, description="适应症")
    study_phase: str = Field(description="研究分期")
    is_multicenter: str = Field(description="是否多中心")
    registration_number: str | None = Field(None, description="注册号")
    registration_platform_url: str | None = Field(None, description="注册平台链接")
    principal_investigator: str | None = Field(None, description="项目负责人")
    pi_email: str | None = Field(None, description="项目负责人邮箱")
    doctor_enrollment_count: int = Field(description="医生入组人数")
    patient_enrollment_count: int | None = Field(None, description="患者入组人数")
    hospital: str | None = Field(None, description="所属医院")
    phone: str | None = Field(None, description="手机号")
    status: int = Field(description="项目状态：0-保存草稿，1-创建立项")
    enrollment_criteria: str | None = Field(None, description="入组要求")

class GetProjectDetailResponse(BaseResponse):
    """
    获取项目详情的响应模型
    字段：
        data: 项目详情信息（ProjectDetailInfo）
    """
    data: ProjectDetailInfo | None = None

class GetProjectStageStatsRequest(BaseModel):
    """
    获取项目阶段统计的请求模型
    参数：
        project_id: 项目ID
    """
    project_id: int = Field(..., description="项目ID")


class GetProjectStageStatsResponse(BaseResponse):
    """
    获取项目阶段统计的响应模型
    字段：
        data: 统计信息字典，包含病人资料和测序数据的覆盖率与阶段进展
    """
    data: dict | None = None  # 见接口说明

# 项目完整信息模型，包含项目表所有字段，供项目列表/详情接口使用
class ProjectFullInfo(BaseModel):
    project_id: int  # 项目ID
    name: str  # 项目名称
    project_code: str | None = None  # 项目编号
    short_name: str | None = None  # 项目简称
    description: str | None = None  # 项目简介
    project_type: str | None = None  # 项目类型
    indication: str | None = None  # 适应症
    study_phase: str | None = None  # 研究分期
    is_multicenter: str | None = None  # 是否多中心
    registration_number: str | None = None  # 注册号
    registration_platform_url: str | None = None  # 注册平台链接
    principal_investigator: str | None = None  # 项目负责人
    pi_email: str | None = None  # 项目负责人邮箱
    hospital: str | None = None  # 所属医院
    phone: str | None = None  # 联系电话
    patient_enrollment_count: int | None = None  # 患者入组人数
    doctor_enrollment_count: int | None = None  # 医生入组人数
    status: int  # 项目状态
    created_at: str | None = None  # 创建时间
    updated_at: str | None = None  # 更新时间
    created_by: str | None = None  # 创建者unionid
    enrollment_criteria: str | None = None  # 入组要求

# 项目完整信息列表响应模型，projects为ProjectFullInfo列表
class ProjectFullListResponse(BaseResponse):
    projects: list[ProjectFullInfo] = []  # 项目完整信息列表

# 病人完整信息模型，包含病人表所有字段，供项目下病人列表/详情接口使用
class PatientFullInfo(BaseModel):
    patient_id: int  # 病人ID
    project_id: int  # 所属项目ID
    source_id: int | None = None  # 源文件ID
    medical_record_number: str | None = None  # 病历号
    name: str  # 患者姓名
    gender: str | None = None  # 性别
    birth_date: str | None = None  # 出生日期
    phone: str | None = None  # 联系电话
    email: str | None = None  # 电子邮箱
    hospital: str | None = None  # 就诊医院
    blood_type: str | None = None  # 血型
    tumor_type: str | None = None  # 肿瘤类型
    HLA_type: str | None = None  # HLA分型
    CDR_type: str | None = None  # CDR数据
    treatment_state: str | None = None  # 治疗阶段
    additional_info: str | None = None  # 附加信息
    clinical_medication: str | None = None  # 临床用药
    clinical_diagnosis: str | None = None  # 临床诊断
    status: str  # 病历状态
    created_by: str  # 创建者unionid
    created_at: str | None = None  # 创建时间
    updated_at: str | None = None  # 更新时间

# 病人完整信息列表响应模型，data为PatientFullInfo列表
class PatientFullListResponse(BaseResponse):
    data: list[PatientFullInfo] = []  # 病人完整信息列表

class TaskQueueStatusRequest(BaseModel):
    """任务队列状态查询请求模型"""
    conversation_id: int = Field(..., description="会话ID")

class TaskQueueStatusItem(BaseModel):
    """单个任务队列状态信息模型"""
    task_id: int = Field(..., description="任务ID（自增主键）")
    celery_task_id: Optional[str] = Field(default=None, description="Celery任务ID")
    status: str = Field(..., description="任务状态（queued/running/completed/failed）")
    queue_position: int = Field(..., description="任务在队列中的位置（从1开始）")
    wait_time: int = Field(..., description="预计还需等待时间（单位：秒）")

class TaskQueueStatusResponse(BaseResponse):
    """任务队列状态查询响应模型"""
    tasks: list[TaskQueueStatusItem] = Field(default=[], description="该病人下所有任务的状态列表")


class DeleteFileRequest(BaseModel):
    """
    删除测序文件的请求模型。
    输入参数：
    - patient_id: 病人ID，指定要删除文件所属的病人。
    - file_path: 要删除的文件路径（唯一定位文件）。
    """
    patient_id: int = Field(..., description="病人ID")
    file_path: str = Field(..., description="要删除的文件路径")

class DeleteFileResponse(BaseResponse):
    """
    删除测序文件的响应模型。
    继承BaseResponse，ok=0表示成功，ok=1表示失败，failed为错误信息。
    新增字段：can_delete，0表示可以删除，1表示不能删除
    """
    can_delete: int = 0

