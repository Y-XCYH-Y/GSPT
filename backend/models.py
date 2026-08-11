from sqlalchemy import Column, JSON, Integer, String, Float, DateTime, Date, Boolean, JSON, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base

class UserRole(str, enum.Enum):
    DIRECTOR = "director"      # 所长
    DEPUTY_DIRECTOR = "deputy_director"  # 副所长
    PROJECT_LEADER = "project_leader"    # 项目负责人
    TEAM_MEMBER = "member"     # 团队成员

class ProjectStatus(str, enum.Enum):
    PLANNING = "planning"           # 方案阶段
    DESIGN = "design"               # 设计阶段
    CONSTRUCTION = "construction"   # 施工阶段
    COMPLETED = "completed"         # 已完工
    CLOSED = "closed"               # 已结项

class TaskStatus(str, enum.Enum):
    PENDING = "pending"         # 待分配
    IN_PROGRESS = "in_progress" # 进行中
    DELAYED = "delayed"         # 延期
    COMPLETED = "completed"     # 已完成

class AlertLevel(str, enum.Enum):
    GREEN = "green"     # 正常
    YELLOW = "yellow"   # 预警
    RED = "red"         # 严重延期

# 用户表
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    name = Column(String(100), nullable=False)
    employee_id = Column(String(50))  # 人员编号
    gender = Column(String(10))  # 男/女
    profession = Column(String(50))  # 专业方向：建筑、结构、给排水等
    registration = Column(String(100))  # 注册情况
    title = Column(String(50))  # 职称情况
    birth_date = Column(String(10))  # 出生年月
    work_start_date = Column(String(10))  # 参加工作时间
    project_types = Column(JSON, default=list)  # 擅长项目类型（多选）
    experience = Column(Text)  # 历史项目经验
    is_field = Column(String(5), default='否')  # 是否驻外
    current_load = Column(String(20), default='空闲')  # 当前负荷状态
    occupancy_rate = Column(Float, default=0.0)  # 占用比例
    remark = Column(Text)  # 备注
    role = Column(String(20), default='member')  # director/member
    department = Column(String(100), default="建筑一所")
    is_active = Column(Boolean, default=True)
    is_on_leave = Column(Boolean, default=False)  # 休假状态
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 人员技能矩阵
class SkillMatrix(Base):
    __tablename__ = "skill_matrices"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    skills = Column(JSON, default=list)
    specialties = Column(JSON, default=list)
    experience_years = Column(Integer, default=0)
    max_workload = Column(Float, default=1.0)
    current_workload = Column(Float, default=0.0)
    rating = Column(Integer, default=3)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", backref="skill_matrix")

# 项目表
class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    project_code = Column(String(200), default="", comment="????")
    project_name = Column(String(200), nullable=False)
    project_type = Column(String(100), nullable=False)  # 项目类型
    area = Column(Float, nullable=False)  # 建筑面积(㎡)
    status = Column(String(12), default="planning")
    project_leader_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="项目负责人")
    current_stage = Column(String(50), default="设计", comment="当前进度阶段")
    start_date = Column(Date)
    planned_end_date = Column(Date)
    actual_end_date = Column(Date)
    planned_man_days = Column(Float, default=0)  # 基本工天（用于计算计划工天）
    drawing_list = Column(JSON, default=list)  # 图名清单 [{name, area, personnel, remark}]
    actual_man_days = Column(Float, default=0)   # 实际人天
    is_official = Column(Boolean, default=True)
    alert_level = Column(Enum(AlertLevel), default=AlertLevel.GREEN)
    description = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])
    project_leader = relationship("User", foreign_keys=[project_leader_id])


class ProjectStageProgress(Base):
    __tablename__ = "project_stage_progress"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    stage_name = Column(String(50), nullable=False, comment="阶段：设计/复核/专业审核/院审/总体审核/集团审核")
    status = Column(String(20), default="pending", comment="pending/in_progress/completed")
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True, comment="责任人")
    assigned_to_name = Column(String(100), default="")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    project = relationship("Project", foreign_keys=[project_id])
    assignee = relationship("User", foreign_keys=[assigned_to])

# 任务表
class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    task_name = Column(String(200), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"))
    estimated_days = Column(Float, default=0)
    actual_days = Column(Float, default=0)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    priority = Column(Integer, default=1)  # 1-5
    start_date = Column(Date)
    end_date = Column(Date)
    progress = Column(Integer, default=0)  # 0-100
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assigned_to])

# 质量评定标准
class QualityStandard(Base):
    __tablename__ = "quality_standards"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False)  # 评定类别
    standard_name = Column(String(200), nullable=False)
    description = Column(Text)
    weight = Column(Float, default=1.0)  # 权重
    pass_score = Column(Float, default=60.0)  # 及格分
    created_at = Column(DateTime, default=datetime.utcnow)

# 项目质量评定记录
class QualityAssessment(Base):
    __tablename__ = "quality_assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    assessor_id = Column(Integer, ForeignKey("users.id"))
    overall_score = Column(Float)  # 总分
    grade = Column(String(20))     # A/B/C/D
    details = Column(JSON)         # 各标准得分
    red_line_violations = Column(JSON, default=list)  # 红线违规
    comments = Column(Text)
    assessed_at = Column(DateTime, default=datetime.utcnow)

class WorkloadHistory(Base):
    __tablename__ = "workload_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    man_days = Column(Float, default=0)
    period_start = Column(Date)
    period_end = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
# 用户表
class WorkloadRecord(Base):
    __tablename__ = "workload_records"

    id = Column(Integer, primary_key=True, index=True)
    sequence = Column(Integer)
    project_code = Column(String(100))
    project_name = Column(String(200))
    project_type = Column(String(100))
    scale = Column(String(100))
    overall_lead = Column(String(100))
    architecture_lead = Column(String(100))
    calculated_work_days = Column(Float, default=0)
    stage = Column(String(100))
    calculated_work_days_2 = Column(Float, default=0)
    participants = Column(String(500))
    specific_work = Column(Text)
    actual_work_days_architecture = Column(Float, default=0)
    actual_work_days_structure = Column(Float, default=0)
    actual_work_days_other = Column(Float, default=0)
    actual_duration_days = Column(Float, default=0)
    quality_grade = Column(String(50))
    year = Column(String(10))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# 绩效考核
class PerformanceAssessment(Base):
    __tablename__ = "performance_assessments"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(String(10), nullable=False)
    name = Column(String(200))
    status = Column(String(20), default="进行中")
    bonus_total = Column(Float, default=0.0)
    gamma = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workdays = relationship("WorkdayRecord", back_populates="assessment", cascade="all, delete-orphan")
    scores = relationship("PerformanceScore", back_populates="assessment", cascade="all, delete-orphan")
    results = relationship("AssessmentResult", back_populates="assessment", cascade="all, delete-orphan")


class WorkdayRecord(Base):
    __tablename__ = "workday_records"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("performance_assessments.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_name = Column(String(200))
    project_type = Column(String(100))
    A = Column(Float, default=0.0)
    B = Column(Float, default=1.0)
    C = Column(Float, default=1.0)
    D = Column(Float, default=1.0)
    E = Column(Float, default=1.0)
    F = Column(Float, default=1.0)
    G = Column(Float, default=0.0)
    submitted_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    assessment = relationship("PerformanceAssessment", back_populates="workdays")
    user = relationship("User", foreign_keys=[user_id])


class PerformanceScore(Base):
    __tablename__ = "performance_scores"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("performance_assessments.id"), nullable=False)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    evaluator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    evaluator_role = Column(String(30), nullable=False)
    project_name = Column(String(200), nullable=True, comment="项目名称（项目负责人评分时填写）")
    score = Column(Float, nullable=False)
    tech_quality = Column(Float, default=None, comment="技术质量（0-100）")
    work_attitude = Column(Float, default=None, comment="工作态度与配合（0-100）")
    emergency_task = Column(Float, default=None, comment="紧急任务承担（0-100）")
    extra_contribution = Column(Float, default=None, comment="额外贡献（0-100）")
    weight = Column(Float, default=0.0)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    assessment = relationship("PerformanceAssessment", back_populates="scores")
    target_user = relationship("User", foreign_keys=[target_user_id])
    evaluator = relationship("User", foreign_keys=[evaluator_id])


class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("performance_assessments.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_workdays = Column(Float, default=0.0)
    director_score = Column(Float, default=0.0)
    deputy_score = Column(Float, default=0.0)
    leader_score = Column(Float, default=0.0)
    peer_score = Column(Float, default=0.0)
    avg_tech_quality = Column(Float, default=0.0)
    avg_work_attitude = Column(Float, default=0.0)
    avg_emergency_task = Column(Float, default=0.0)
    avg_extra_contribution = Column(Float, default=0.0)
    avg_workday_output = Column(Float, default=0.0)
    final_score = Column(Float, default=0.0)
    final_coefficient = Column(Float, default=1.0)
    performance_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    assessment = relationship("PerformanceAssessment", back_populates="results")
    user = relationship("User")




# ====== 用户审批流程 ======
class ChangeRequest(Base):
    __tablename__ = "change_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    field_name = Column(String(100))
    old_value = Column(Text)
    new_value = Column(Text)
    status = Column(String(20), default="pending")
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])


# ====== 项目参与人员 ======
class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    employee_id = Column(String(50), nullable=False, comment="员工工号，关联 employees.db")
    employee_name = Column(String(100), nullable=False)
    department = Column(String(100), default="")
    role = Column(String(50), nullable=False, comment="在项目中的角色")
    note = Column(Text, default="", comment="备注")
    stage_status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", foreign_keys=[project_id])


class WorkdayChangeRequest(Base):
    __tablename__ = "workday_change_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assessment_id = Column(Integer)
    project_name = Column(String(200))
    A = Column(Float, default=0)
    B = Column(Float, default=1.0)
    C = Column(Float, default=1.0)
    D = Column(Float, default=1.0)
    E = Column(Float, default=1.0)
    F = Column(Float, default=1.0)
    status = Column(String(20), default="pending")
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])




class ProjectRequest(Base):
    __tablename__ = "project_requests"
    id = Column(Integer, primary_key=True, index=True)
    project_code = Column(String(200), default="", comment="????")
    project_name = Column(String(200), nullable=False)
    project_type = Column(String(100), default="民建")
    area = Column(Float, default=0)
    stage = Column(String(50), default="方案设计")
    start_date = Column(String(20))
    planned_end_date = Column(String(20))
    planned_man_days = Column(Float, default=0)
    status = Column(String(20), default="pending")
    requested_by = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)


class ProjectWorkdayAlloc(Base):
    __tablename__ = "project_workday_alloc"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False)
    project_name = Column(String(200))
    data = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

# ====== 量化分配新模块 ======

class RewardRecord(Base):
    __tablename__ = "rewards_records"
    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("performance_assessments.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(50), nullable=False)
    amount = Column(Float, default=0)
    description = Column(Text)
    date = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

class BonusPoint(Base):
    __tablename__ = "bonus_points"
    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("performance_assessments.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(10), nullable=False)
    points = Column(Float, default=0)
    reason = Column(Text)
    date = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

class SpecialCase(Base):
    __tablename__ = "special_cases"
    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("performance_assessments.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    case_type = Column(String(50), nullable=False)
    start_date = Column(String(20))
    end_date = Column(String(20))
    notes = Column(Text)
    coefficient = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProjectMemberScore(Base):
    __tablename__ = "project_member_scores"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False)
    project_name = Column(String(200))
    role = Column(String(50), default="", comment="角色（设计/复核等）")
    stage = Column(String(50), default="")
    target_user_id = Column(Integer, nullable=True)
    target_employee_id = Column(String(100), nullable=True)
    target_user_name = Column(String(100))
    evaluator_id = Column(Integer, nullable=False)
    score = Column(Float, default=None, comment="综合评分（0-100）")
    tech_ability = Column(Float, default=None, comment="技术能力")
    work_quality = Column(Float, default=None, comment="工作质量")
    cooperation = Column(Float, default=None, comment="配合效率")
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
