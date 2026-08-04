from sqlalchemy.orm import Session
from sqlalchemy import func
import models
import schemas
from typing import List, Optional
from datetime import datetime, date
import sqlite3
import json

# 用户操作
def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_users(db: Session) -> List[models.User]:
    return db.query(models.User).filter(models.User.is_active == True).all()

def create_user(db: Session, user_data: dict):
    import auth
    user = models.User(
        username=user_data["username"],
        password_hash=auth.get_password_hash(user_data["password"]),
        name=user_data["name"],
        department=user_data.get("department", ""),
        role="member",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# 技能矩阵操作
def get_skill_matrices(db: Session) -> List[models.SkillMatrix]:
    return db.query(models.SkillMatrix).all()

def get_skill_matrix_by_user(db: Session, user_id: int):
    return db.query(models.SkillMatrix).filter(models.SkillMatrix.user_id == user_id).first()

def create_skill_matrix(db: Session, data: schemas.SkillMatrixCreate):
    skill = models.SkillMatrix(**data.model_dump())
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill

def update_skill_matrix(db: Session, user_id: int, data: schemas.SkillMatrixBase):
    skill = db.query(models.SkillMatrix).filter(models.SkillMatrix.user_id == user_id).first()
    if skill:
        for key, value in data.model_dump().items():
            setattr(skill, key, value)
        db.commit()
        db.refresh(skill)
    return skill

# 项目操作
def get_projects(db: Session) -> List[models.Project]:
    import sqlite3, os
    db_path = os.path.join(os.path.dirname(__file__), "building_institute.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, project_name, project_type, area, status, start_date, planned_end_date, actual_end_date, planned_man_days, actual_man_days, alert_level, description, created_by, project_leader_id, current_stage FROM projects").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def _sync_project_to_workload(db: Session, pdata: dict, user_id: int):
    from datetime import datetime
    existing = None
    pcode = pdata.get("project_code", "")
    pname = pdata.get("project_name", "")
    if pcode:
        existing = db.query(models.WorkloadRecord).filter(models.WorkloadRecord.project_code == pcode).first()
    if not existing and pname:
        existing = db.query(models.WorkloadRecord).filter(models.WorkloadRecord.project_name == pname).first()
    if not existing:
        wr = models.WorkloadRecord(
            project_code=pdata.get("project_code", ""),
            project_name=pdata.get("project_name", ""),
            project_type=pdata.get("project_type", ""),
            stage=pdata.get("current_stage", ""),
            year=str(datetime.utcnow().year)
        )
        db.add(wr)
        print(f"?????(???): {pdata.get('project_name', '')}")


def create_project(db: Session, data: schemas.ProjectCreate, user_id: int):
    project = models.Project(**data.model_dump(), created_by=user_id, project_leader_id=user_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    # ?????????
    _sync_project_to_workload(db, data.model_dump(), user_id)
    db.commit()
    return project

def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()

# 任务操作
def delete_project(db: Session, project_id: int) -> bool:
    """删除项目"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        return False
    # Delete related members first
    db.query(models.ProjectMember).filter(models.ProjectMember.project_id == project_id).delete()
    db.query(models.Task).filter(models.Task.project_id == project_id).delete()
    db.delete(project)
    db.commit()
    return True

def get_tasks_by_project(db: Session, project_id: int) -> List[models.Task]:
    return db.query(models.Task).filter(models.Task.project_id == project_id).all()

def create_task(db: Session, project_id: int, data: schemas.TaskCreate):
    task = models.Task(project_id=project_id, **data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

# 质量评定操作
def get_quality_standards(db: Session) -> List[models.QualityStandard]:
    return db.query(models.QualityStandard).all()

def create_quality_standard(db: Session, data: schemas.QualityStandardCreate):
    standard = models.QualityStandard(**data.model_dump())
    db.add(standard)
    db.commit()
    db.refresh(standard)
    return standard
# 获取所有员工（含详细信息）
def get_all_employees(db: Session) -> List[models.User]:
    sync_employees_db_to_users(db)
    update_employee_workload(db)
    return db.query(models.User).filter(models.User.is_active == True).order_by(models.User.id).all()

# 创建员工
def create_employee(db: Session, data: schemas.EmployeeCreate):
    from auth import get_password_hash
    user = models.User(
        username=data.username,
        password_hash=get_password_hash(data.password),
        name=data.name,
        employee_id=data.employee_id,
        gender=data.gender,
        profession=data.profession,
        registration=data.registration,
        title=data.title,
        birth_date=data.birth_date,
        work_start_date=data.work_start_date,
        project_types=data.project_types,
        experience=data.experience,
        is_field=data.is_field,
        current_load=data.current_load,
        occupancy_rate=data.occupancy_rate,
        remark=data.remark,
        role=data.role,
        department=data.department
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# 更新员工
def update_employee(db: Session, employee_id: int, data: schemas.EmployeeUpdate):
    user = db.query(models.User).filter(models.User.id == employee_id).first()
    if not user:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user

# 获取项目类型列表
PROJECT_TYPES = ["站房", "枢纽", "大铁", "轨交", "民建", "改造", "援外", "BIM", "方案", "建模", "咨询", "总包"]


# 获取专业方向列表
PROFESSIONS = ["建筑", "结构", "给排水", "暖通", "电气", "规划", "景观", "室内", "概预算"]

# 获取负荷状态列表
LOAD_STATUSES = ["空闲","轻量","适中","饱满","超负荷","休假"]
# ====== 项目进度阶段 ======

def get_project_stages(db: Session, project_id: int):
    # 获取项目阶段列表
    return db.query(models.ProjectStageProgress).filter(
        models.ProjectStageProgress.project_id == project_id
    ).order_by(models.ProjectStageProgress.id).all()


def upsert_project_stage(db: Session, project_id: int, data: dict):
    # 创建或更新项目阶段
    existing = db.query(models.ProjectStageProgress).filter(
        models.ProjectStageProgress.project_id == project_id,
        models.ProjectStageProgress.stage_name == data["stage_name"]
    ).first()
    if existing:
        existing.status = data.get("status", existing.status)
        existing.assigned_to = data.get("assigned_to", existing.assigned_to)
        existing.assigned_to_name = data.get("assigned_to_name", existing.assigned_to_name)
        if data.get("status") == "in_progress" and not existing.started_at:
            existing.started_at = datetime.utcnow()
        if data.get("status") == "completed" and not existing.completed_at:
            existing.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        _sync_assignee_to_member(db, project_id, data)
        # 阶段完成时检查是否所有6个阶段都已完成
        if data.get("status") == "completed":
            _auto_complete_project(db, project_id)
        return existing
    stage = models.ProjectStageProgress(
        project_id=project_id, stage_name=data["stage_name"],
        status=data.get("status", "pending"),
        assigned_to=data.get("assigned_to"),
        assigned_to_name=data.get("assigned_to_name", "")
    )
    if stage.status == "in_progress":
        stage.started_at = datetime.utcnow()
    db.add(stage)
    db.commit()
    db.refresh(stage)
    _sync_assignee_to_member(db, project_id, data)
    # 如果是直接创建已完成阶段，也检查
    if stage.status == "completed":
        _auto_complete_project(db, project_id)
    return stage



def _sync_assignee_to_member(db: Session, project_id: int, data: dict):
    """将阶段责任人同步到项目参与人员"""
    assigned_to = data.get("assigned_to")
    assigned_to_name = data.get("assigned_to_name", "")
    stage_name = data.get("stage_name", "")
    stage_label = stage_name + "阶段"

    name = ""
    emp_id = ""
    if assigned_to is not None:
        user = db.query(models.User).filter(models.User.id == assigned_to).first()
        if user:
            name = user.name
            emp_id = user.employee_id or ""
            if not assigned_to_name:
                assigned_to_name = name
    if not name and assigned_to_name:
        name = assigned_to_name
        u = db.query(models.User).filter(models.User.name == name).first()
        if u:
            emp_id = u.employee_id or ""

    if not name:
        return

    existing = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.employee_name == name
    ).first()
    if not existing:
        mem = models.ProjectMember(
            project_id=project_id,
            employee_id=emp_id,
            employee_name=name,
            role=stage_label
        )
        db.add(mem)
        db.commit()
    elif stage_label not in existing.role:
        existing.role = existing.role + "、" + stage_label


def _backfill_stage_members(db: Session, project_id: int):
    """将已存在的阶段分配人员补录到项目成员"""
    stages = db.query(models.ProjectStageProgress).filter(
        models.ProjectStageProgress.project_id == project_id
    ).all()
    added = 0
    for s in stages:
        name = s.assigned_to_name or ""
        if not name:
            continue
        exists = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.employee_name == name
        ).first()
        if exists:
            continue
        emp_id = ""
        u = db.query(models.User).filter(models.User.name == name).first()
        if u:
            emp_id = u.employee_id or ""
        stage_label = s.stage_name + "阶段"
        mem = models.ProjectMember(
            project_id=project_id, employee_id=emp_id,
            employee_name=name, role=stage_label
        )
        db.add(mem)
        added += 1
    if added:
        db.commit()


STAGE_NAMES_LIST = ["设计", "复核", "专业审核", "院审", "总体审核", "集团审核"]


def _auto_complete_project(db: Session, project_id: int):
    """检查项目是否所有阶段已完成，是则自动将项目标记为 completed"""
    all_stages = db.query(models.ProjectStageProgress).filter(
        models.ProjectStageProgress.project_id == project_id
    ).all()
    existing_names = {s.stage_name for s in all_stages}
    if existing_names == set(STAGE_NAMES_LIST) and all(s.status == "completed" for s in all_stages):
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if project and project.status != models.ProjectStatus.COMPLETED:
            project.status = models.ProjectStatus.COMPLETED
            project.actual_end_date = datetime.utcnow().date()
            msg = "项目自动完成: " + project.project_name + " (ID=" + str(project_id) + ")"
            print(msg)
            db.commit()


def delete_project_stage(db: Session, stage_id: int):
    # 删除项目阶段
    stage = db.query(models.ProjectStageProgress).filter(models.ProjectStageProgress.id == stage_id).first()
    if stage:
        db.delete(stage)
        db.commit()
        return True
    return False


# ====== 工作量计算 ======

def update_employee_workload(db: Session, user_id: int = None):
    # 根据员工参与的项目数和在办阶段数更新负荷状态
    if user_id:
        users = [db.query(models.User).filter(models.User.id == user_id).first()]
    else:
        users = db.query(models.User).filter(models.User.is_active == True).all()
    for user in users:
        if not user:
            continue
        if getattr(user, "is_on_leave", False):
            user.current_load = "休假"
            user.occupancy_rate = 0.0
            continue
        # 计算参与项目数
        proj_count = db.query(models.ProjectMember).filter(
            models.ProjectMember.employee_name == user.name
        ).count()
        # 计算在办阶段数
        stage_count = db.query(models.ProjectStageProgress).filter(
            models.ProjectStageProgress.assigned_to == user.id,
            models.ProjectStageProgress.status == "in_progress"
        ).count()
        total = proj_count + stage_count
        if total == 0:
            user.current_load = "空闲"
            user.occupancy_rate = 0.0
        elif total <= 1:
            user.current_load = "轻量"
            user.occupancy_rate = 0.3
        elif total <= 2:
            user.current_load = "适中"
            user.occupancy_rate = 0.5
        elif total <= 3:
            user.current_load = "饱满"
            user.occupancy_rate = 0.8
        else:
            user.current_load = "超负荷"
            user.occupancy_rate = 1.0
    db.commit()
    return True


# 工作量记录操作
def get_workload_records(db: Session):
    return db.query(models.WorkloadRecord).order_by(models.WorkloadRecord.id).all()

def create_workload_record(db: Session, data):
    record = models.WorkloadRecord(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def delete_workload_record(db: Session, record_id: int):
    record = db.query(models.WorkloadRecord).filter(models.WorkloadRecord.id == record_id).first()
    if record:
        db.delete(record)
        db.commit()
        return True
    return False

def bulk_create_workload_records(db: Session, records_data: list):
    records = [models.WorkloadRecord(**r) for r in records_data]
    for r in records:
        db.add(r)
    db.commit()
    return records


# ============ 绩效考核 CRUD ============

def get_assessments(db: Session):
    return db.query(models.PerformanceAssessment).order_by(models.PerformanceAssessment.created_at.desc()).all()

def get_assessment(db: Session, assessment_id: int):
    return db.query(models.PerformanceAssessment).filter(models.PerformanceAssessment.id == assessment_id).first()

def create_assessment(db: Session, data):
    assessment = models.PerformanceAssessment(**data)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment

def delete_assessment(db: Session, assessment_id: int):
    a = db.query(models.PerformanceAssessment).filter(models.PerformanceAssessment.id == assessment_id).first()
    if a:
        db.delete(a)
        db.commit()
        return True
    return False

# 工天记录 CRUD
def get_workday_records(db: Session, assessment_id: int):
    records = db.query(models.WorkdayRecord).filter(models.WorkdayRecord.assessment_id == assessment_id).all()
    result = []
    for r in records:
        user = db.query(models.User).filter(models.User.id == r.user_id).first()
        result.append({
            "id": r.id, "assessment_id": r.assessment_id, "user_id": r.user_id,
            "user_name": user.name if user else "",
            "project_name": r.project_name, "project_type": r.project_type,
            "A": r.A, "B": r.B, "C": r.C, "D": r.D, "E": r.E, "F": r.F, "G": r.G,
            "submitted_by": r.submitted_by, "created_at": r.created_at
        })
    return result

def create_workday_record(db: Session, data: dict, submitted_by: int):
    G = data["A"] * data["B"] * data["C"] * data["D"] * data["E"] * data["F"]
    record = models.WorkdayRecord(
        assessment_id=data["assessment_id"], user_id=data["user_id"],
        project_name=data.get("project_name"), project_type=data.get("project_type"),
        A=data["A"], B=data["B"], C=data["C"], D=data["D"], E=data["E"], F=data["F"],
        G=G, submitted_by=submitted_by
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def delete_workday_record(db: Session, record_id: int):
    r = db.query(models.WorkdayRecord).filter(models.WorkdayRecord.id == record_id).first()
    if r:
        db.delete(r)
        db.commit()
        return True
    return False

# 考核评分 CRUD
def get_scores_for_assessment(db: Session, assessment_id: int):
    scores = db.query(models.PerformanceScore).filter(models.PerformanceScore.assessment_id == assessment_id).all()
    result = []
    for s in scores:
        target = db.query(models.User).filter(models.User.id == s.target_user_id).first()
        evaluator = db.query(models.User).filter(models.User.id == s.evaluator_id).first()
        result.append({
            "id": s.id, "assessment_id": s.assessment_id,
            "target_user_id": s.target_user_id, "target_user_name": target.name if target else "",
            "evaluator_id": s.evaluator_id, "evaluator_name": evaluator.name if evaluator else "",
            "evaluator_role": s.evaluator_role, "score": s.score,
            "weight": s.weight, "project_name": s.project_name,
            "comment": s.comment, "created_at": s.created_at,
            "tech_quality": s.tech_quality, "work_attitude": s.work_attitude,
            "emergency_task": s.emergency_task, "extra_contribution": s.extra_contribution
        })
    return result

def create_performance_score(db: Session, data: dict, evaluator_id: int):
    weight_map = {"director": 0.3, "deputy_director": 0.2, "project_leader": 0.3, "peer": 0.2}
    weight = weight_map.get(data["evaluator_role"], 0.0)
    existing = db.query(models.PerformanceScore).filter(
        models.PerformanceScore.assessment_id == data["assessment_id"],
        models.PerformanceScore.target_user_id == data["target_user_id"],
        models.PerformanceScore.evaluator_id == evaluator_id,
        models.PerformanceScore.evaluator_role == data["evaluator_role"]
    ).first()
    if existing:
        existing.score = data["score"]
        existing.weight = weight
        existing.comment = data.get("comment")
        if data.get("project_name"):
            existing.project_name = data["project_name"]
        existing.tech_quality = data.get("tech_quality", existing.tech_quality)
        existing.work_attitude = data.get("work_attitude", existing.work_attitude)
        existing.emergency_task = data.get("emergency_task", existing.emergency_task)
        existing.extra_contribution = data.get("extra_contribution", existing.extra_contribution)
        db.commit()
        db.refresh(existing)
        return existing
    score = models.PerformanceScore(
        assessment_id=data["assessment_id"], target_user_id=data["target_user_id"],
        evaluator_id=evaluator_id, evaluator_role=data["evaluator_role"],
        score=data["score"], weight=weight, comment=data.get("comment"),
        project_name=data.get("project_name"),
        tech_quality=data.get("tech_quality"),
        work_attitude=data.get("work_attitude"),
        emergency_task=data.get("emergency_task"),
        extra_contribution=data.get("extra_contribution")
    )
    db.add(score)
    db.commit()
    db.refresh(score)
    return score

# 计算考核结果
def calculate_assessment_results(db: Session, assessment_id: int):
    assessment = db.query(models.PerformanceAssessment).filter(models.PerformanceAssessment.id == assessment_id).first()
    if not assessment:
        return None

    employees = db.query(models.User).filter(models.User.is_active == True, models.User.employee_id.isnot(None)).all()
    scores_all = db.query(models.PerformanceScore).filter(models.PerformanceScore.assessment_id == assessment_id).all()
    workdays_all = db.query(models.WorkdayRecord).filter(models.WorkdayRecord.assessment_id == assessment_id).all()

    # Clear old results
    db.query(models.AssessmentResult).filter(models.AssessmentResult.assessment_id == assessment_id).delete()

    total_all_workdays = sum(r.G or 0 for r in workdays_all)

    results = []
    for emp in employees:
        emp_scores = [s for s in scores_all if s.target_user_id == emp.id]
        emp_workdays = sum(r.G or 0 for r in workdays_all if r.user_id == emp.id)

        director_s = [s for s in emp_scores if s.evaluator_role == "director"]
        deputy_s = [s for s in emp_scores if s.evaluator_role == "deputy_director"]
        leader_s = [s for s in emp_scores if s.evaluator_role == "project_leader"]
        peer_s = [s for s in emp_scores if s.evaluator_role == "peer"]

        # Helper to average category scores from a list of scores
        def _avg_category(cat, scores_list):
            vals = [getattr(s, cat) for s in scores_list if getattr(s, cat) is not None]
            return sum(vals) / len(vals) if vals else 0

        # Compute per-dimension averages across all evaluator roles
        all_scores_for_cat = director_s + deputy_s + leader_s + peer_s
        avg_tq = _avg_category("tech_quality", all_scores_for_cat)
        avg_wa = _avg_category("work_attitude", all_scores_for_cat)
        avg_et = _avg_category("emergency_task", all_scores_for_cat)
        avg_ec = _avg_category("extra_contribution", all_scores_for_cat)
        # Workday output = personal workdays / max workdays (normalized to 0-100)
        all_emp_workdays = [sum(r.G or 0 for r in workdays_all if r.user_id == u.id) for u in employees]
        max_wd = max(all_emp_workdays) if all_emp_workdays else 1
        avg_wdo = (emp_workdays / max_wd * 100) if max_wd > 0 else 0

        d_score = sum(s.score for s in director_s) / len(director_s) if director_s else 0
        dp_score = sum(s.score for s in deputy_s) / len(deputy_s) if deputy_s else 0

        # Project leader weighted scoring: per-role scores from ProjectMemberScore
        # weighted by each role's allocated workdays in ProjectWorkdayAlloc
        member_scores = db.query(models.ProjectMemberScore).filter(
            models.ProjectMemberScore.target_employee_id == emp.employee_id
        ).all()

        allocs = db.query(models.ProjectWorkdayAlloc).all()
        alloc_members_by_project = {}
        for alloc in allocs:
            try:
                data = json.loads(alloc.data)
                alloc_members_by_project[alloc.project_id] = data.get("members", [])
            except Exception:
                alloc_members_by_project[alloc.project_id] = []

        all_project_members = db.query(models.ProjectMember).all()
        pm_map = {}
        for pm in all_project_members:
            pm_map[(pm.project_id, pm.employee_id, pm.role)] = pm.id

        l_weighted_num = 0
        l_weighted_den = 0
        if member_scores:
            emp_scores_by_project = {}
            for ms in member_scores:
                emp_scores_by_project.setdefault(ms.project_id, []).append(ms)

            for pid, ms_list in emp_scores_by_project.items():
                alloc_members = alloc_members_by_project.get(pid, [])
                days_by_mid = {}
                total_project_days = 0
                for am in alloc_members:
                    mid = am.get("id")
                    days = am.get("days", 0) or 0
                    days_by_mid[mid] = days
                    total_project_days += days

                if total_project_days <= 0:
                    continue

                role_num = 0
                role_den = 0
                personal_days = 0
                for ms in ms_list:
                    mid = pm_map.get((pid, emp.employee_id, ms.role))
                    if mid is None:
                        continue
                    days = days_by_mid.get(mid, 0)
                    if days <= 0 or ms.score is None:
                        continue
                    ratio = days / total_project_days
                    role_num += ms.score * ratio
                    role_den += ratio
                    personal_days += days

                if role_den > 0:
                    project_score = role_num / role_den
                    personal_ratio = personal_days / total_project_days
                    l_weighted_num += project_score * personal_ratio
                    l_weighted_den += personal_ratio

        if l_weighted_den > 0:
            l_score = l_weighted_num / l_weighted_den
        else:
            # Fallback: simple average if no workday data
            l_scores = [s.score for s in leader_s if s.score]
            l_score = sum(l_scores) / len(l_scores) if l_scores else 0

        p_scores = [s.score for s in peer_s if s.score]
        p_score = sum(p_scores) / len(p_scores) if p_scores else 0

        # If employee has no project workdays, leader weight goes to director
        if emp_workdays == 0 and l_score == 0:
            final_score = d_score * 0.6 + dp_score * 0.2 + p_score * 0.2
        else:
            final_score = d_score * 0.3 + dp_score * 0.2 + l_score * 0.3 + p_score * 0.2
        final_coefficient = round(final_score / 100, 2)

        # 绩效金额 = bonus_total * gamma * (personal_workdays / total_workdays) * coeff
        if total_all_workdays > 0:
            perf_amount = assessment.bonus_total * assessment.gamma * (emp_workdays / total_all_workdays) * final_coefficient
        else:
            perf_amount = 0

        result = models.AssessmentResult(
            assessment_id=assessment_id, user_id=emp.id,
            total_workdays=emp_workdays,
            director_score=d_score, deputy_score=dp_score,
            leader_score=l_score, peer_score=p_score,
            avg_tech_quality=avg_tq, avg_work_attitude=avg_wa,
            avg_emergency_task=avg_et, avg_extra_contribution=avg_ec,
            avg_workday_output=avg_wdo,
            final_score=final_score, final_coefficient=final_coefficient,
            performance_amount=perf_amount
        )
        db.add(result)
        results.append(result)

    assessment.status = "已完成"
    db.commit()
    for r in results:
        db.refresh(r)

    # Return formatted results
    output = []
    for r in results:
        user = db.query(models.User).filter(models.User.id == r.user_id).first()
        output.append({
            "id": r.id, "assessment_id": r.assessment_id, "user_id": r.user_id,
            "user_name": user.name if user else "",
            "profession": user.profession if user else "",
            "total_workdays": r.total_workdays,
            "director_score": r.director_score, "deputy_score": r.deputy_score,
            "leader_score": r.leader_score, "peer_score": r.peer_score,
            "final_score": r.final_score, "final_coefficient": r.final_coefficient,
            "performance_amount": r.performance_amount
        })
    return output

def get_assessment_results(db: Session, assessment_id: int):
    results = db.query(models.AssessmentResult).filter(models.AssessmentResult.assessment_id == assessment_id).all()
    output = []
    for r in results:
        user = db.query(models.User).filter(models.User.id == r.user_id).first()
        output.append({
            "id": r.id, "assessment_id": r.assessment_id, "user_id": r.user_id,
            "user_name": user.name if user else "",
            "profession": user.profession if user else "",
            "total_workdays": r.total_workdays,
            "director_score": r.director_score, "deputy_score": r.deputy_score,
            "leader_score": r.leader_score, "peer_score": r.peer_score,
            "final_score": r.final_score, "final_coefficient": r.final_coefficient,
            "performance_amount": r.performance_amount
        })
    return output


def update_workload_record(db: Session, record_id: int, data: dict):
    record = db.query(models.WorkloadRecord).filter(models.WorkloadRecord.id == record_id).first()
    if not record:
        return None
    for key, value in data.items():
        if value is not None:
            setattr(record, key, value)
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record

def dedup_workload_records(db: Session):
    records = db.query(models.WorkloadRecord).order_by(models.WorkloadRecord.id).all()
    seen = set()
    deleted = 0
    to_delete = []
    for r in records:
        code = r.project_code.strip() if r.project_code else ""
        if code and code in seen:
            to_delete.append(r.id)
            deleted += 1
        elif code:
            seen.add(code)
    if to_delete:
        db.query(models.WorkloadRecord).filter(models.WorkloadRecord.id.in_(to_delete)).delete(synchronize_session=False)
        db.commit()
    return deleted


# ====== 账号管理 CRTUD ======
def get_all_users(db: Session):
    return db.query(models.User).order_by(models.User.id).all()

def update_user_by_admin(db: Session, user_id: int, data: dict):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: return None
    for key, value in data.items():
        if value is not None:
            setattr(user, key, value)
    # 休假状态与负荷状态绑定
    if "is_on_leave" in data and data.get("is_on_leave") is not None:
        update_employee_workload(db, user_id)

    db.commit()
    db.refresh(user)
    return user

# ====== 审批流程 CRUD ======
def create_change_request(db: Session, user_id: int, data: dict):
    req = models.ChangeRequest(
        user_id=user_id,
        field_name=data["field_name"],
        new_value=data["new_value"],
        status="pending"
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req

def get_change_requests(db: Session, status: str = None, user_id: int = None):
    q = db.query(models.ChangeRequest)
    if status:
        q = q.filter(models.ChangeRequest.status == status)
    if user_id:
        q = q.filter(models.ChangeRequest.user_id == user_id)
    results = q.order_by(models.ChangeRequest.created_at.desc()).all()
    output = []
    for r in results:
        u = db.query(models.User).filter(models.User.id == r.user_id).first()
        rv = db.query(models.User).filter(models.User.id == r.reviewer_id).first() if r.reviewer_id else None
        output.append({
            "id": r.id, "user_id": r.user_id, "user_name": u.name if u else "",
            "field_name": r.field_name, "old_value": r.old_value, "new_value": r.new_value,
            "status": r.status, "reviewer_id": r.reviewer_id,
            "reviewer_name": rv.name if rv else "",
            "review_comment": r.review_comment, "created_at": r.created_at,
            "reviewed_at": r.reviewed_at
        })
    return output

def review_change_request(db: Session, request_id: int, reviewer_id: int, status: str, comment: str = ""):
    req = db.query(models.ChangeRequest).filter(models.ChangeRequest.id == request_id).first()
    if not req: return None
    req.status = status
    req.reviewer_id = reviewer_id
    req.review_comment = comment
    req.reviewed_at = datetime.utcnow()
    # 审批通过后，将变更应用到用户实际数据
    if status == "approved":
        user = db.query(models.User).filter(models.User.id == req.user_id).first()
        if user and hasattr(user, req.field_name):
            setattr(user, req.field_name, req.new_value)
    db.commit()
    db.refresh(req)
    return req


# ====== 员工库 → User + SkillMatrix 同步 ======

def sync_employees_db_to_users(db: Session) -> dict:
    """从 employees.db 自动同步到 User 表和 SkillMatrix 表"""
    import auth, sqlite3
    from database import EMPLOYEES_DB_PATH
    conn = sqlite3.connect(EMPLOYEES_DB_PATH)
    employees = conn.execute(
        "SELECT employee_id, name, department, position FROM employees WHERE status='在职'"
    ).fetchall()
    conn.close()
    users_created = 0
    skills_created = 0
    for emp_id, name, dept, position in employees:
        user = db.query(models.User).filter(models.User.employee_id == emp_id).first()
        if not user:
            user = models.User(
                username=emp_id.lower(),
                password_hash=auth.get_password_hash("123456"),
                name=name, employee_id=emp_id, department=dept,
                role="member", is_active=True
            )
            db.add(user)
            db.flush()
            users_created += 1
        skill = db.query(models.SkillMatrix).filter(models.SkillMatrix.user_id == user.id).first()
        if not skill:
            skill = models.SkillMatrix(
                user_id=user.id, skills=[], specialties=[],
                experience_years=0, max_workload=1.0, rating=3
            )
            db.add(skill)
            db.flush()
            skills_created += 1
        if not user.department and dept:
            user.department = dept
    db.commit()
    return {"users_created": users_created, "skills_created": skills_created, "total_employees": len(employees)}


# ====== 项目参与人员 ======

def get_project_members(db: Session, project_id: int) -> List[dict]:
    # 自动同步阶段责任人到项目成员（补录历史数据）
    # _backfill_stage_members removed
    members = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id
    ).order_by(models.ProjectMember.id).all()
    return [{
        "id": m.id,
        "project_id": m.project_id,
        "employee_id": m.employee_id,
        "employee_name": m.employee_name,
        "department": m.department,
        "role": m.role,
        "stage_status": m.stage_status or "pending",
        "note": m.note or "",
        "created_at": m.created_at
    } for m in members]

def add_project_member(db: Session, project_id: int, data: dict):
    member = models.ProjectMember(
        project_id=project_id,
        employee_id=data["employee_id"],
        employee_name=data["employee_name"],
        department=data.get("department", ""),
        role=data["role"]
    )
    member.stage_status = data.get("stage_status", "pending")
    member.note = data.get("note", "")
    db.add(member)
    db.commit()
    db.refresh(member)
    return {
        "id": member.id,
        "project_id": member.project_id,
        "employee_id": member.employee_id,
        "employee_name": member.employee_name,
        "department": member.department,
        "role": member.role,
        "stage_status": member.stage_status or "pending",
        "created_at": member.created_at
    }

def update_project_member(db: Session, project_id: int, member_id: int, data: dict):
    member = db.query(models.ProjectMember).filter(
        models.ProjectMember.id == member_id,
        models.ProjectMember.project_id == project_id
    ).first()
    if not member:
        return None
    if "role" in data:
        member.role = data["role"]
        if data["role"] == "项目负责人":
            _u = db.query(models.User).filter(models.User.employee_id == member.employee_id).first()
            if _u:
                _p = db.query(models.Project).filter(models.Project.id == project_id).first()
                if _p:
                    _p.project_leader_id = _u.id
    if "note" in data:
        member.note = data["note"]
    if "stage_status" in data:
        member.stage_status = data["stage_status"]
    db.commit()
    db.refresh(member)
    return {
        "id": member.id, "project_id": member.project_id,
        "employee_id": member.employee_id, "employee_name": member.employee_name,
        "department": member.department, "role": member.role,
        "note": member.note,
        "created_at": member.created_at
    }


def remove_project_member(db: Session, project_id: int, member_id: int) -> bool:
    member = db.query(models.ProjectMember).filter(
        models.ProjectMember.id == member_id,
        models.ProjectMember.project_id == project_id
    ).first()
    if not member:
        return False
    # 清除相关阶段进度
    db.query(models.ProjectStageProgress).filter(
        models.ProjectStageProgress.project_id == project_id,
        models.ProjectStageProgress.assigned_to_name == member.employee_name
    ).delete(synchronize_session=False)
    # 更新负荷
    u = db.query(models.User).filter(models.User.name == member.employee_name).first()
    if u:
        update_employee_workload(db, u.id)
    db.delete(member)
    db.commit()
    return True


# ====== 员工池（读取 employees.db） ======

def get_employee_pool() -> List[dict]:
    from database import EMPLOYEES_DB_PATH
    conn = sqlite3.connect(EMPLOYEES_DB_PATH)
    c = conn.cursor()
    rows = c.execute(
        "SELECT employee_id, name, department, position FROM employees WHERE status='在职'"
    ).fetchall()
    conn.close()
    return [{
        "employee_id": r[0],
        "name": r[1],
        "department": r[2],
        "position": r[3]
    } for r in rows]


def get_employee_pool_merged(db=None) -> list:
    """合并员工库和系统用户表的员工列表（含 user_id）"""
    pool = get_employee_pool()
    # Add default user_id
    for e in pool:
        e["user_id"] = None
    existing_ids = {e["employee_id"] for e in pool}
    if db:
        import models
        users = db.query(models.User).filter(
            models.User.employee_id.isnot(None),
            models.User.employee_id != "",
            models.User.is_active == True
        ).all()
        # Build employee_id -> user_id map
        emp_to_uid = {u.employee_id: u.id for u in users if u.employee_id}
        # Update user_id for existing pool items
        for e in pool:
            if e["employee_id"] in emp_to_uid:
                e["user_id"] = emp_to_uid[e["employee_id"]]
        # Add users not in employees.db
        for u in users:
            if u.employee_id and u.employee_id not in existing_ids:
                pool.append({
                    "employee_id": u.employee_id,
                    "name": u.name,
                    "department": u.department or "",
                    "position": "",
                    "user_id": u.id
                })
                existing_ids.add(u.employee_id)
    return pool


# ========== 量化分配 CRUD ==========

def get_rewards(db: Session, assessment_id: int = None, user_id: int = None):
    q = db.query(models.RewardRecord)
    if assessment_id: q = q.filter(models.RewardRecord.assessment_id == assessment_id)
    if user_id: q = q.filter(models.RewardRecord.user_id == user_id)
    results = q.order_by(models.RewardRecord.created_at.desc()).all()
    out = []
    for r in results:
        u = db.query(models.User).filter(models.User.id == r.user_id).first()
        out.append({"id": r.id, "assessment_id": r.assessment_id, "user_id": r.user_id,
            "user_name": u.name if u else "", "category": r.category, "amount": r.amount,
            "description": r.description, "date": r.date, "created_at": r.created_at})
    return out

def add_reward(db: Session, data: dict):
    r = models.RewardRecord(**data)
    db.add(r); db.commit(); db.refresh(r)
    return r

def delete_reward(db: Session, rid: int):
    r = db.query(models.RewardRecord).filter(models.RewardRecord.id == rid).first()
    if not r: return False
    db.delete(r); db.commit(); return True

def get_bonus_points(db: Session, assessment_id: int = None, user_id: int = None):
    q = db.query(models.BonusPoint)
    if assessment_id: q = q.filter(models.BonusPoint.assessment_id == assessment_id)
    if user_id: q = q.filter(models.BonusPoint.user_id == user_id)
    results = q.order_by(models.BonusPoint.created_at.desc()).all()
    out = []
    for r in results:
        u = db.query(models.User).filter(models.User.id == r.user_id).first()
        out.append({"id": r.id, "assessment_id": r.assessment_id, "user_id": r.user_id,
            "user_name": u.name if u else "", "type": r.type, "points": r.points,
            "reason": r.reason, "date": r.date, "created_at": r.created_at})
    return out

def add_bonus_point(db: Session, data: dict):
    r = models.BonusPoint(**data)
    db.add(r); db.commit(); db.refresh(r)
    return r

def delete_bonus_point(db: Session, bid: int):
    r = db.query(models.BonusPoint).filter(models.BonusPoint.id == bid).first()
    if not r: return False
    db.delete(r); db.commit(); return True

def get_special_cases(db: Session, assessment_id: int = None):
    q = db.query(models.SpecialCase)
    if assessment_id: q = q.filter(models.SpecialCase.assessment_id == assessment_id)
    results = q.order_by(models.SpecialCase.created_at.desc()).all()
    out = []
    for r in results:
        u = db.query(models.User).filter(models.User.id == r.user_id).first()
        out.append({"id": r.id, "assessment_id": r.assessment_id, "user_id": r.user_id,
            "user_name": u.name if u else "", "case_type": r.case_type,
            "start_date": r.start_date, "end_date": r.end_date, "notes": r.notes,
            "coefficient": r.coefficient, "created_at": r.created_at})
    return out

def add_special_case(db: Session, data: dict):
    r = models.SpecialCase(**data)
    db.add(r); db.commit(); db.refresh(r)
    return r

def delete_special_case(db: Session, sid: int):
    r = db.query(models.SpecialCase).filter(models.SpecialCase.id == sid).first()
    if not r: return False
    db.delete(r); db.commit(); return True

def calc_personal_performance(db: Session, assessment_id: int):
    assessment = db.query(models.PerformanceAssessment).filter(models.PerformanceAssessment.id == assessment_id).first()
    if not assessment: return None
    total_perf = assessment.bonus_total
    gamma = assessment.gamma or 1.0
    employees = db.query(models.User).filter(models.User.is_active == True).all()
    workdays = db.query(models.WorkdayRecord).filter(models.WorkdayRecord.assessment_id == assessment_id).all()
    results_db = db.query(models.AssessmentResult).filter(models.AssessmentResult.assessment_id == assessment_id).all()
    rewards = db.query(models.RewardRecord).filter(models.RewardRecord.assessment_id == assessment_id).all()
    bonuses = db.query(models.BonusPoint).filter(models.BonusPoint.assessment_id == assessment_id).all()
    cases = db.query(models.SpecialCase).filter(models.SpecialCase.assessment_id == assessment_id).all()

    total_wd = sum(w.G or 0 for w in workdays)
    if total_wd == 0: return []

    out = []
    for emp in employees:
        emp_wd = sum(w.G or 0 for w in workdays if w.user_id == emp.id)
        emp_result = next((r for r in results_db if r.user_id == emp.id), None)
        coeff = emp_result.final_coefficient if emp_result else 1.0
        # Personal workday performance
        wd_perf = total_perf * gamma * (emp_wd / total_wd) * coeff
        # Rewards total
        reward_total = sum(r.amount for r in rewards if r.user_id == emp.id)
        # Bonus/demerit total
        bonus_total = sum(b.points for b in bonuses if b.user_id == emp.id and b.type == "bonus")
        demerit_total = sum(b.points for b in bonuses if b.user_id == emp.id and b.type == "demerit")
        # Special coefficient
        sc = next((c for c in cases if c.user_id == emp.id), None)
        sp_coeff = sc.coefficient if sc else 1.0
        total = wd_perf + reward_total + bonus_total - demerit_total
        # Cap at 2x average
        avg_perf = total_perf / max(len(employees), 1)
        total = min(total, avg_perf * 2)
        out.append({
            "user_id": emp.id, "user_name": emp.name, "workday_perf": round(wd_perf, 2),
            "coefficient": coeff, "reward_total": round(reward_total, 2),
            "bonus_total": round(bonus_total, 2), "demerit_total": round(demerit_total, 2),
            "special_coeff": sp_coeff, "total_performance": round(total, 2)
        })
    return out


# ========== 项目建立申请 CRUD ==========

def create_project_request(db: Session, data: dict, user_id: int):
    req = models.ProjectRequest(**data, requested_by=user_id, status="pending")
    db.add(req)
    db.commit()
    db.refresh(req)
    return req

def get_project_requests(db: Session, status: str = None, user_id: int = None):
    q = db.query(models.ProjectRequest)
    if status:
        q = q.filter(models.ProjectRequest.status == status)
    if user_id:
        q = q.filter(models.ProjectRequest.requested_by == user_id)
    results = q.order_by(models.ProjectRequest.created_at.desc()).all()
    out = []
    for r in results:
        req_user = db.query(models.User).filter(models.User.id == r.requested_by).first() if r.requested_by else None
        rev_user = db.query(models.User).filter(models.User.id == r.reviewer_id).first() if r.reviewer_id else None
        out.append({
            "id": r.id, "project_name": r.project_name, "project_type": r.project_type,
            "area": r.area, "stage": r.stage, "start_date": r.start_date,
            "planned_end_date": r.planned_end_date, "planned_man_days": r.planned_man_days,
            "status": r.status, "requested_by": r.requested_by,
            "requester_name": req_user.name if req_user else "",
            "reviewer_name": rev_user.name if rev_user else "",
            "created_at": r.created_at, "reviewed_at": r.reviewed_at
        })
    return out

def approve_project_request(db: Session, request_id: int, reviewer_id: int):
    req = db.query(models.ProjectRequest).filter(models.ProjectRequest.id == request_id).first()
    if not req:
        return None, None
    if req.status != "pending":
        return req, None
    req.status = "approved"
    req.reviewer_id = reviewer_id
    from datetime import datetime
    req.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(req)
    _start = datetime.strptime(req.start_date, "%Y-%m-%d").date() if req.start_date else None
    _end = datetime.strptime(req.planned_end_date, "%Y-%m-%d").date() if req.planned_end_date else None
    proj = models.Project(
        project_name=req.project_name, project_code=req.project_code or "", project_type=req.project_type,
        area=req.area, status="planning", start_date=_start,
        planned_end_date=_end,
        planned_man_days=req.planned_man_days,
        created_by=req.requested_by, project_leader_id=req.requested_by,
        current_stage=req.stage
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    _sync_project_to_workload(db, {"project_code": req.project_code or "", "project_name": req.project_name, "project_type": req.project_type, "current_stage": req.stage}, req.requested_by)
    maker = db.query(models.User).filter(models.User.id == req.requested_by).first()
    if maker:
        member = models.ProjectMember(
            project_id=proj.id,
            employee_id=maker.employee_id or maker.username,
            employee_name=maker.name,
            department=maker.department or "",
            role="项目负责人"
        )
        db.add(member)
        db.commit()
    return req, proj

def reject_project_request(db: Session, request_id: int, reviewer_id: int):
    req = db.query(models.ProjectRequest).filter(models.ProjectRequest.id == request_id).first()
    if not req:
        return None
    if req.status != "pending":
        return req
    req.status = "rejected"
    req.reviewer_id = reviewer_id
    req.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(req)
    return req
