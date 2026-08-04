from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

# 用户相关
class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    name: str
    department: str = ""
    profession: str = ""
    title: str = ""
    phone: str = ""
    employee_id: str = ""

class UserResponse(BaseModel):
    id: int
    username: str
    name: str
    role: str
    department: str
    is_active: bool

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# 技能矩阵
class SkillMatrixBase(BaseModel):
    skills: List[str] = []
    specialties: List[str] = []
    experience_years: int = 0
    max_workload: float = 1.0
    current_workload: float = 0.0
    rating: int = 3

class SkillMatrixCreate(SkillMatrixBase):
    user_id: int

class SkillMatrixResponse(SkillMatrixBase):
    id: int
    user_id: int
    user_name: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True

# 项目相关
class ProjectCreate(BaseModel):
    project_code: str = ""
    project_name: str
    project_type: str
    area: float
    status: str = "planning"
    start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    planned_man_days: float = 0
    current_stage: Optional[str] = "方案设计"
    description: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    project_code: str = ""
    project_name: str
    project_type: str
    area: float
    status: str
    start_date: Optional[date]
    planned_end_date: Optional[date]
    actual_end_date: Optional[date]
    planned_man_days: float
    actual_man_days: float
    alert_level: str
    current_stage: Optional[str] = None
    project_leader_id: Optional[int] = None
    description: Optional[str]
    current_stage: Optional[str] = None
    project_leader_id: Optional[int] = None
    created_at: datetime
    tasks: Optional[List['TaskResponse']] = []

    class Config:
        from_attributes = True

# 任务相关
class TaskCreate(BaseModel):
    task_name: str
    assigned_to: Optional[int] = None
    estimated_days: float = 0
    priority: int = 1
    current_stage: Optional[str] = None
    project_leader_id: Optional[int] = None
    description: Optional[str] = None

class TaskResponse(BaseModel):
    id: int
    project_id: int
    task_name: str
    assigned_to: Optional[int]
    assignee_name: Optional[str] = None
    estimated_days: float
    actual_days: float
    status: str
    priority: int
    progress: int
    start_date: Optional[date]
    end_date: Optional[date]

    class Config:
        from_attributes = True

# 统计数据
class WorkloadStats(BaseModel):
    user_name: str
    department: str
    current_workload: float
    max_workload: float
    utilization_rate: float
    active_projects: int

class ProjectStats(BaseModel):
    total_projects: int
    active_projects: int
    delayed_projects: int
    completed_projects: int
    total_man_days: float
    user_workloads: List[WorkloadStats]

class SkillResponse(BaseModel):
    id: int
    name: str
    description: str
    icon: str
    color: str

class QuickCommand(BaseModel):
    id: int
    text: str
    skill_id: Optional[int] = None

# 对话相关
class ChatRequest(BaseModel):
    query: str
    skill: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    skill_used: Optional[str] = None
    data: Optional[dict] = None

# 质量评定
class QualityStandardCreate(BaseModel):
    category: str
    standard_name: str
    current_stage: Optional[str] = None
    project_leader_id: Optional[int] = None
    description: Optional[str] = None
    weight: float = 1.0
    pass_score: float = 60.0

class QualityAssessmentCreate(BaseModel):
    project_id: int
    overall_score: float
    grade: str
    details: dict = {}
    red_line_violations: List[str] = []
    comments: Optional[str] = None
    # 员工信息创建
class EmployeeCreate(BaseModel):
    username: str
    password: str
    name: str
    employee_id: Optional[str] = None
    gender: Optional[str] = None
    profession: Optional[str] = None
    registration: Optional[str] = None
    title: Optional[str] = None
    birth_date: Optional[str] = None
    work_start_date: Optional[str] = None
    project_types: List[str] = []
    experience: Optional[str] = None
    is_field: str = '否'
    current_load: str = '空闲'
    occupancy_rate: Optional[float] = 0.0
    remark: Optional[str] = None
    role: str = 'member'
    department: str = '建筑一所'

# 员工信息更新
class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    employee_id: Optional[str] = None
    gender: Optional[str] = None
    profession: Optional[str] = None
    registration: Optional[str] = None
    title: Optional[str] = None
    birth_date: Optional[str] = None
    work_start_date: Optional[str] = None
    project_types: Optional[List[str]] = None
    experience: Optional[str] = None
    is_field: Optional[str] = None
    current_load: Optional[str] = None
    occupancy_rate: Optional[float] = None
    remark: Optional[str] = None
    role: Optional[str] = None

# 员工完整信息响应
class EmployeeResponse(BaseModel):
    id: int
    username: str
    name: str
    employee_id: Optional[str] = None
    gender: Optional[str]
    profession: Optional[str]
    registration: Optional[str]
    title: Optional[str]
    birth_date: Optional[str]
    work_start_date: Optional[str]
    project_types: List[str]
    experience: Optional[str]
    is_field: str
    current_load: str
    occupancy_rate: Optional[float] = 0.0
    remark: Optional[str]
    role: str
    department: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
# 导入常量配置
class WorkloadRecordCreate(BaseModel):
    project_code: str = ""
    project_name: str = ""
    project_type: Optional[str] = None
    scale: Optional[str] = None
    overall_lead: Optional[str] = None
    architecture_lead: Optional[str] = None
    calculated_work_days: float = 0
    stage: Optional[str] = None
    calculated_work_days_2: float = 0
    participants: Optional[str] = None
    specific_work: Optional[str] = None
    actual_work_days_architecture: float = 0
    actual_work_days_structure: float = 0
    actual_work_days_other: float = 0
    actual_duration_days: float = 0
    quality_grade: Optional[str] = None
    year: Optional[str] = None
    remark: Optional[str] = None

class WorkloadRecordResponse(WorkloadRecordCreate):
    id: int
    sequence: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 绩效考核
class PerformanceAssessmentCreate(BaseModel):
    year: str
    name: Optional[str] = None
    bonus_total: float = 0.0
    gamma: float = 1.0

class PerformanceAssessmentResponse(BaseModel):
    id: int
    year: str
    name: Optional[str]
    status: str
    bonus_total: float
    gamma: float
    created_at: datetime

    class Config:
        from_attributes = True

class WorkdayRecordCreate(BaseModel):
    assessment_id: int
    user_id: int
    project_name: Optional[str] = None
    project_type: Optional[str] = None
    A: float = 0.0
    B: float = 1.0
    C: float = 1.0
    D: float = 1.0
    E: float = 1.0
    F: float = 1.0

class WorkdayRecordResponse(WorkdayRecordCreate):
    id: int
    G: float
    submitted_by: Optional[int] = None
    user_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PerformanceScoreCreate(BaseModel):
    assessment_id: int
    target_user_id: int
    score: float
    evaluator_role: str
    project_name: Optional[str] = None
    comment: Optional[str] = None
    tech_quality: Optional[float] = None
    work_attitude: Optional[float] = None
    emergency_task: Optional[float] = None
    extra_contribution: Optional[float] = None

class PerformanceScoreResponse(BaseModel):
    id: int
    assessment_id: int
    target_user_id: int
    evaluator_id: int
    evaluator_role: str
    score: float
    weight: float
    project_name: Optional[str] = None
    comment: Optional[str] = None
    tech_quality: Optional[float] = None
    work_attitude: Optional[float] = None
    emergency_task: Optional[float] = None
    extra_contribution: Optional[float] = None
    target_user_name: Optional[str] = None
    evaluator_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AssessmentResultResponse(BaseModel):
    id: int
    assessment_id: int
    user_id: int
    user_name: Optional[str] = None
    profession: Optional[str] = None
    total_workdays: float
    director_score: float
    deputy_score: float
    leader_score: float
    peer_score: float
    avg_tech_quality: float = 0.0
    avg_work_attitude: float = 0.0
    avg_emergency_task: float = 0.0
    avg_extra_contribution: float = 0.0
    avg_workday_output: float = 0.0
    final_score: float
    final_coefficient: float
    performance_amount: float

    class Config:
        from_attributes = True


class WorkloadRecordUpdate(BaseModel):
    project_code: Optional[str] = None
    project_name: Optional[str] = None
    project_type: Optional[str] = None
    scale: Optional[str] = None
    overall_lead: Optional[str] = None
    architecture_lead: Optional[str] = None
    calculated_work_days: Optional[float] = None
    stage: Optional[str] = None
    participants: Optional[str] = None
    specific_work: Optional[str] = None
    actual_work_days_architecture: Optional[float] = None
    actual_work_days_structure: Optional[float] = None
    actual_work_days_other: Optional[float] = None
    actual_duration_days: Optional[float] = None
    quality_grade: Optional[str] = None
    year: Optional[str] = None
    remark: Optional[str] = None

# ====== 账号管理 & 审批 ======
class UserUpdateAdmin(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_on_leave: Optional[bool] = None

class UserAdminResponse(BaseModel):
    id: int
    username: str
    name: str
    role: str
    department: str = ""
    employee_id: Optional[str] = None
    profession: Optional[str] = None
    is_active: bool = True
    is_on_leave: bool = False
    current_load: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class ChangeRequestCreate(BaseModel):
    field_name: str
    new_value: str

class ChangeRequestReview(BaseModel):
    status: str
    comment: Optional[str] = None

class ChangeRequestResponse(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    field_name: str
    old_value: Optional[str] = None
    new_value: str
    status: str
    reviewer_id: Optional[int] = None
    reviewer_name: Optional[str] = None
    review_comment: Optional[str] = None
    created_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# ====== 项目参与人员 ======
class ProjectMemberCreate(BaseModel):
    employee_id: str
    employee_name: str
    department: str = ""
    role: str

class ProjectMemberResponse(BaseModel):
    id: int
    project_id: int
    employee_id: str
    employee_name: str
    department: str
    role: str
    created_at: Optional[datetime] = None
    stage_status: str = "pending"
    note: str = ""

    class Config:
        from_attributes = True


# 员工池（来自 employees.db）
class EmployeePoolItem(BaseModel):
    employee_id: str
    name: str
    department: str
    position: str = ""
    user_id: Optional[int] = None

class StageProgressCreate(BaseModel):
    stage_name: str
    status: str = "pending"
    assigned_to: Optional[int] = None
    assigned_to_name: str = ""

class StageProgressResponse(BaseModel):
    id: int
    project_id: int
    stage_name: str
    status: str
    assigned_to: Optional[int] = None
    assigned_to_name: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

STAGE_NAMES = ["设计", "复核", "专业审核", "院审", "总体审核", "集团审核"]

PROJECT_ROLES = [
    "项目负责人", "建筑专业负责人", "结构专业负责人",
    "给排水设计", "暖通设计", "电气设计",
    "规划", "景观", "室内设计",
    "造价/概预算", "驻场代表", "BIM负责人", "一般设计人"
]


class ProjectRequestCreate(BaseModel):
    project_code: str = ""
    project_name: str
    project_type: str = "民建"
    area: float = 0
    stage: str = "方案设计"
    start_date: Optional[str] = None
    planned_end_date: Optional[str] = None
    planned_man_days: float = 0

class ProjectRequestResponse(BaseModel):
    id: int
    project_name: str
    project_type: str
    area: float
    stage: str
    start_date: Optional[str] = None
    planned_end_date: Optional[str] = None
    planned_man_days: float
    status: str
    requested_by: Optional[int] = None
    requester_name: Optional[str] = None
    reviewer_name: Optional[str] = None
    created_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    class Config: from_attributes = True

# ====== 量化分配新模块 ======

class RewardRecordCreate(BaseModel):
    assessment_id: int
    user_id: int
    category: str
    amount: float = 0
    current_stage: Optional[str] = None
    project_leader_id: Optional[int] = None
    description: Optional[str] = None
    date: Optional[str] = None

class RewardRecordResponse(BaseModel):
    id: int
    assessment_id: int
    user_id: int
    user_name: Optional[str] = None
    category: str
    amount: float
    current_stage: Optional[str] = None
    project_leader_id: Optional[int] = None
    description: Optional[str] = None
    date: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config: from_attributes = True

class BonusPointCreate(BaseModel):
    assessment_id: int
    user_id: int
    type: str
    points: float = 0
    reason: Optional[str] = None
    date: Optional[str] = None

class BonusPointResponse(BaseModel):
    id: int
    assessment_id: int
    user_id: int
    user_name: Optional[str] = None
    type: str
    points: float
    reason: Optional[str] = None
    date: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config: from_attributes = True

class SpecialCaseCreate(BaseModel):
    assessment_id: int
    user_id: int
    case_type: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    notes: Optional[str] = None
    coefficient: float = 1.0

class SpecialCaseResponse(BaseModel):
    id: int
    assessment_id: int
    user_id: int
    user_name: Optional[str] = None
    case_type: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    notes: Optional[str] = None
    coefficient: float
    created_at: Optional[datetime] = None
    class Config: from_attributes = True


class ProjectMemberScoreCreate(BaseModel):
    target_user_id: Optional[int] = None
    target_employee_id: Optional[str] = None
    role: Optional[str] = None
    stage: Optional[str] = None
    score: Optional[float] = None
    tech_ability: Optional[float] = None
    work_quality: Optional[float] = None
    cooperation: Optional[float] = None
    comment: Optional[str] = None

class ProjectMemberScoreResponse(BaseModel):
    id: int
    project_id: int
    project_name: Optional[str] = None
    role: Optional[str] = None
    stage: Optional[str] = None
    target_user_id: Optional[int] = None
    target_employee_id: Optional[str] = None
    target_user_name: Optional[str] = None
    evaluator_id: int
    score: Optional[float] = None
    tech_ability: Optional[float] = None
    work_quality: Optional[float] = None
    cooperation: Optional[float] = None
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
