from sqlalchemy.orm import Session
from sqlalchemy import func
import models
import schemas
from typing import List, Optional
from datetime import datetime, date
import sqlite3
import json

def _round_workdays(v):
    try:
        f = float(v or 0)
    except Exception:
        return 0
    return int(f + 0.5) if f >= 0 else int(f - 0.5)

PROJECT_TYPE_CODE_MAP = {
    "站房": "ZF", "枢纽": "SN", "大铁": "DT", "轨交": "GJ", "民建": "MJ",
    "改造": "GZ", "援外": "YW", "BIM": "BI", "方案": "FA", "建模": "JM",
    "咨询": "ZX", "总包": "ZB"
}

def auto_project_code(db: Session, project_type: str):
    prefix = PROJECT_TYPE_CODE_MAP.get(project_type or "", (project_type or "")[:2].upper())
    now = date.today()
    base = "%s-%04d-%02d-%02d" % (prefix, now.year, now.month, now.day)
    count = db.query(models.Project).filter(models.Project.project_code.like(base + "%")).count()
    if not count:
        return base
    return "%s-%02d" % (base, count + 1)

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
    rows = conn.execute("SELECT id, project_code, group_code, project_name, project_type, area, status, start_date, planned_end_date, actual_end_date, planned_man_days, actual_man_days, alert_level, description, work_rounds, round_reason, created_by, project_leader_id, current_stage, drawing_list, is_official FROM projects").fetchall()
    conn.close()
    result = []
    for r in rows:
        row = dict(r)
        if isinstance(row.get("drawing_list"), str):
            try:
                row["drawing_list"] = json.loads(row["drawing_list"] or "[]")
            except Exception:
                row["drawing_list"] = []
        row["is_official"] = bool(row.get("is_official"))
        result.append(row)

    latest_assessment = db.query(models.PerformanceAssessment).order_by(
        models.PerformanceAssessment.created_at.desc(),
        models.PerformanceAssessment.id.desc()
    ).first()
    wd_by_name = {}
    if latest_assessment:
        for rec in db.query(models.WorkdayRecord).filter(
            models.WorkdayRecord.assessment_id == latest_assessment.id
        ).all():
            key = rec.project_name or ""
            wd_by_name.setdefault(key, []).append(rec)

    def _pick_record(recs, leader_id):
        if not recs:
            return None
        return max(recs, key=lambda r: r.id)

    for row in result:
        recs = wd_by_name.get(row.get("project_name") or "", [])
        if not recs:
            recs = wd_by_name.get(row.get("project_code") or "", [])
        rec = _pick_record(recs, row.get("project_leader_id"))
        row["basic_work_days"] = _round_workdays(rec.A) if rec and rec.A is not None else None
        row["final_work_days"] = _round_workdays(rec.G) if rec and rec.G is not None else None
    return result

def _sync_project_to_workload(db: Session, pdata: dict, user_id: int):
    pcode = (pdata.get("project_code") or "").strip()
    pname = (pdata.get("project_name") or "").strip()
    existing = None
    if pcode:
        existing = db.query(models.WorkloadRecord).filter(models.WorkloadRecord.project_code == pcode).first()
    if not existing and pname:
        existing = db.query(models.WorkloadRecord).filter(models.WorkloadRecord.project_name == pname).first()

    stage = pdata.get("current_stage") or pdata.get("stage") or ""
    participants = (pdata.get("participants") or "").strip()
    leader_name = (pdata.get("project_leader_name") or "").strip()
    scale_val = pdata.get("scale") or ""
    if not scale_val and pdata.get("area") is not None:
        try:
            area_float = float(pdata["area"])
            scale_val = ("%g" % area_float) + "㎡"
        except Exception:
            scale_val = ""

    if not existing:
        wr = models.WorkloadRecord(
            project_code=pcode,
            project_name=pname,
            project_type=pdata.get("project_type") or "",
            stage=stage,
            scale=scale_val,
            overall_lead=leader_name,
            participants=participants,
            calculated_work_days=float(pdata.get("planned_man_days") or 0),
            year=str(datetime.utcnow().year)
        )
        db.add(wr)
        return wr

    if pcode:
        existing.project_code = pcode
    if pname:
        existing.project_name = pname
    if pdata.get("project_type"):
        existing.project_type = pdata["project_type"]
    if stage:
        existing.stage = stage
    if scale_val and (not existing.scale or existing.scale in ("nan", "None", "")):
        existing.scale = scale_val
    if leader_name:
        existing.overall_lead = leader_name
    if participants:
        existing.participants = participants
    if not existing.calculated_work_days and pdata.get("planned_man_days"):
        existing.calculated_work_days = float(pdata["planned_man_days"])
    existing.updated_at = datetime.utcnow()
    return existing


def _project_to_workload_payload(db: Session, project: models.Project) -> dict:
    pdata = {
        "id": project.id,
        "project_code": project.project_code or "",
        "project_name": project.project_name or "",
        "project_type": project.project_type or "",
        "current_stage": project.current_stage or "",
        "area": project.area if project.area is not None else 0,
        "planned_man_days": project.planned_man_days or 0,
        "start_date": project.start_date,
        "planned_end_date": project.planned_end_date,
    }
    if project.project_leader_id:
        leader = db.query(models.User).filter(models.User.id == project.project_leader_id).first()
        if leader and leader.name:
            pdata["project_leader_name"] = leader.name
    members = db.query(models.ProjectMember).filter(models.ProjectMember.project_id == project.id).all()
    names = []
    seen_names = set()
    for m in members:
        name = (m.employee_name or "").strip()
        if name and name not in seen_names:
            seen_names.add(name)
            names.append(name)
    pdata["participants"] = "、".join(names)
    return pdata


def sync_project_to_workload(db: Session, project: models.Project):
    if not bool(getattr(project, "is_official", True)):
        return
    _sync_project_to_workload(db, _project_to_workload_payload(db, project), project.created_by or 0)


def sync_all_projects_to_workload(db: Session):
    projects = db.query(models.Project).filter(models.Project.is_official == True).all()
    for project in projects:
        _sync_project_to_workload(db, _project_to_workload_payload(db, project), project.created_by or 0)
    db.commit()
    return {
        "synced": len(projects),
        "records": db.query(models.WorkloadRecord).count()
    }


def create_project(db: Session, data: schemas.ProjectCreate, user_id: int):
    payload = data.model_dump()
    if not (payload.get("project_code") or "").strip():
        payload["project_code"] = auto_project_code(db, payload.get("project_type") or "")
    project = models.Project(**payload, created_by=user_id, project_leader_id=user_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    sync_project_to_workload(db, project)
    db.commit()
    return project


def _remove_project_from_workload(db: Session, project: models.Project):
    pcode = (project.project_code or "").strip()
    pname = (project.project_name or "").strip()
    record = None
    if pcode:
        record = db.query(models.WorkloadRecord).filter(models.WorkloadRecord.project_code == pcode).first()
    if not record and pname:
        record = db.query(models.WorkloadRecord).filter(models.WorkloadRecord.project_name == pname).first()
    if record:
        db.delete(record)

def _remove_project_workday_records(db: Session, project: models.Project):
    pname = (project.project_name or "").strip()
    if pname:
        db.query(models.WorkdayRecord).filter(models.WorkdayRecord.project_name == pname).delete(synchronize_session=False)

def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()

# 任务操作
def delete_project(db: Session, project_id: int) -> bool:
    """删除项目"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        return False
    # Delete related members first
    db.query(models.ProjectMember).filter(models.ProjectMember.project_id == project_id).delete(synchronize_session=False)
    db.query(models.Task).filter(models.Task.project_id == project_id).delete(synchronize_session=False)
    db.query(models.ProjectMemberScore).filter(models.ProjectMemberScore.project_id == project_id).delete(synchronize_session=False)
    db.query(models.ProjectWorkdayAlloc).filter(models.ProjectWorkdayAlloc.project_id == project_id).delete(synchronize_session=False)
    _remove_project_from_workload(db, project)
    _remove_project_workday_records(db, project)
    db.delete(project)
    db.commit()
    return True

def clear_project_library(db: Session):
    """清空整个项目库：项目、工作量记录及项目相关的工天数据。"""
    projects = db.query(models.Project).all()
    project_names = set()
    for p in projects:
        if p.project_name and p.project_name.strip():
            project_names.add(p.project_name.strip())
        if p.project_code and p.project_code.strip():
            project_names.add(p.project_code.strip())

    db.query(models.ProjectMember).delete(synchronize_session=False)
    db.query(models.ProjectStageProgress).delete(synchronize_session=False)
    db.query(models.Task).delete(synchronize_session=False)
    db.query(models.WorkloadHistory).delete(synchronize_session=False)
    db.query(models.QualityAssessment).delete(synchronize_session=False)
    db.query(models.ProjectMemberScore).delete(synchronize_session=False)
    db.query(models.ProjectWorkdayAlloc).delete(synchronize_session=False)
    db.query(models.WorkloadRecord).delete(synchronize_session=False)
    if project_names:
        db.query(models.WorkdayRecord).filter(
            models.WorkdayRecord.project_name.in_(list(project_names))
        ).delete(synchronize_session=False)
    db.query(models.Project).delete(synchronize_session=False)
    db.commit()
    return {"projects": len(projects)}

def repair_legacy_data(db: Session):
    """修复历史遗留数据：工天重复、成员编号为姓名、项目空阶段/暂估工天。"""
    result = {"workday_duplicates": 0, "members_repaired": 0, "projects_filled": 0}

    groups = db.query(
        models.WorkdayRecord.assessment_id,
        models.WorkdayRecord.project_name,
        func.max(models.WorkdayRecord.id).label("keep_id")
    ).group_by(
        models.WorkdayRecord.assessment_id,
        models.WorkdayRecord.project_name
    ).all()
    keep_ids = [g.keep_id for g in groups]
    if keep_ids:
        dup = db.query(models.WorkdayRecord).filter(
            ~models.WorkdayRecord.id.in_(keep_ids)
        ).delete(synchronize_session=False)
        result["workday_duplicates"] = dup

    users = db.query(models.User).filter(
        models.User.is_active == True,
        models.User.employee_id.isnot(None),
        models.User.employee_id != ""
    ).all()
    user_by_name = {}
    for u in users:
        if u.name:
            user_by_name.setdefault(u.name.strip(), u)

    for m in db.query(models.ProjectMember).all():
        eid = (m.employee_id or "").strip()
        ename = (m.employee_name or "").strip()
        if eid and (eid == ename or eid.startswith("EXT_")):
            u = user_by_name.get(ename)
            if u:
                m.employee_id = u.employee_id
                m.department = u.department or m.department
            else:
                m.employee_id = ""
                if not (m.note or "").strip():
                    m.note = "院外人员"
            result["members_repaired"] += 1

    for p in db.query(models.Project).all():
        wl = None
        if p.project_code:
            wl = db.query(models.WorkloadRecord).filter(models.WorkloadRecord.project_code == p.project_code).first()
        if not wl:
            wl = db.query(models.WorkloadRecord).filter(models.WorkloadRecord.project_name == p.project_name).first()
        changed = False
        if not p.current_stage and wl and wl.stage:
            p.current_stage = wl.stage
            changed = True
        if not p.planned_man_days and wl and wl.calculated_work_days:
            p.planned_man_days = wl.calculated_work_days
            changed = True
        if changed:
            result["projects_filled"] += 1

    for p in db.query(models.Project).all():
        _sync_project_leader(db, p.id)

    db.commit()
    return result

def get_personal_workday_summary(db: Session, assessment_id: int):
    """返回考核期内每个员工的总工天（与考核结果同口径）。"""
    employees = db.query(models.User).filter(
        models.User.is_active == True,
        models.User.employee_id.isnot(None),
        models.User.employee_id != ""
    ).all()
    workdays_all = db.query(models.WorkdayRecord).filter(
        models.WorkdayRecord.assessment_id == assessment_id
    ).all()

    def _round_int(v):
        try:
            f = float(v or 0)
        except Exception:
            f = 0
        return int(f + 0.5) if f >= 0 else int(f - 0.5)

    def _allocate_days(pool, pcts):
        out = []
        if pool <= 0 or not pcts:
            return [0] * len(pcts or [])
        total_pct = sum(max(0, p or 0) for p in pcts)
        if total_pct <= 0:
            return [0] * len(pcts)
        exact = [pool * max(0, p or 0) / total_pct for p in pcts]
        floors = [int(x) for x in exact]
        remaining = pool - sum(floors)
        order = sorted(range(len(exact)), key=lambda i: (exact[i] - floors[i], -i), reverse=True)
        for i in range(min(remaining, len(order))):
            floors[order[i]] += 1
        return floors

    projects = db.query(models.Project).all()
    project_by_id = {p.id: p for p in projects}
    project_id_by_name = {p.project_name: p.id for p in projects if p.project_name}
    project_members = db.query(models.ProjectMember).all()
    pm_by_id = {m.id: m for m in project_members}
    employee_by_id = {u.employee_id: u.id for u in employees}

    allocs = db.query(models.ProjectWorkdayAlloc).all()
    parsed_allocs = []
    allocated_project_ids = set()
    for a in allocs:
        try:
            obj = json.loads(a.data or "{}")
        except Exception:
            continue
        members = obj.get("members") or []
        leader_pct = obj.get("leaderPct", 0.05) or 0
        if leader_pct <= 1:
            leader_pct = leader_pct * 100
        parsed_allocs.append({
            "id": a.id,
            "project_id": a.project_id,
            "leader_pct": float(leader_pct),
            "members": members,
            "obj": obj
        })
        allocated_project_ids.add(a.project_id)

    alloc_personal = {}
    for item in parsed_allocs:
        project = project_by_id.get(item["project_id"])
        if not project:
            continue
        candidates = [r for r in workdays_all if r.project_name == project.project_name]
        chosen = max(candidates, key=lambda r: r.id) if candidates else None
        total_g = _round_int(chosen.G) if chosen else 0

        if total_g > 0 and project.project_leader_id:
            leader_share = _round_int(total_g * item["leader_pct"] / 100.0)
            leader_share = min(leader_share, total_g)
            remaining = total_g - leader_share
            alloc_personal[project.project_leader_id] = alloc_personal.get(project.project_leader_id, 0) + leader_share
        else:
            remaining = total_g

        members = [m for m in item["members"] if m.get("id")]
        pcts = [float(m.get("pct") or 0) for m in members]
        days = _allocate_days(remaining, pcts)
        for m, day in zip(members, days):
            pm = pm_by_id.get(m.get("id"))
            if not pm or not pm.employee_id:
                continue
            uid = employee_by_id.get(pm.employee_id)
            if uid is None:
                continue
            if day > 0:
                alloc_personal[uid] = alloc_personal.get(uid, 0) + day

        item["obj"]["members"] = item["members"]
        alloc_row = db.query(models.ProjectWorkdayAlloc).filter(
            models.ProjectWorkdayAlloc.id == item["id"]
        ).first()
        if alloc_row:
            alloc_row.data = json.dumps(item["obj"], ensure_ascii=False)

    totals = {uid: _round_int(days) for uid, days in alloc_personal.items()}
    for r in workdays_all:
        if not r.user_id:
            continue
        pid = project_id_by_name.get(r.project_name or "")
        if pid in allocated_project_ids:
            continue
        totals[r.user_id] = totals.get(r.user_id, 0) + _round_int(r.G or 0)

    db.commit()
    result = []
    for u in employees:
        result.append({
            "user_id": u.id,
            "name": u.name,
            "employee_id": u.employee_id,
            "profession": u.profession or "",
            "department": u.department or "",
            "total_workdays": totals.get(u.id, 0)
        })
    result.sort(key=lambda x: (-x["total_workdays"], x["name"] or ""))
    return result

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
    G = _round_workdays(data["A"] * data["B"] * data["C"] * data["D"] * data["E"] * data["F"])
    existing = db.query(models.WorkdayRecord).filter(
        models.WorkdayRecord.assessment_id == data["assessment_id"],
        models.WorkdayRecord.project_name == data.get("project_name")
    ).first()
    if existing:
        existing.user_id = data["user_id"]
        existing.project_type = data.get("project_type")
        existing.A = data["A"]
        existing.B = data["B"]
        existing.C = data["C"]
        existing.D = data["D"]
        existing.E = data["E"]
        existing.F = data["F"]
        existing.G = G
        existing.submitted_by = submitted_by
        db.commit()
        db.refresh(existing)
        return existing
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

    def _round_int(v):
        try:
            f = float(v or 0)
        except Exception:
            f = 0
        return int(f + 0.5) if f >= 0 else int(f - 0.5)

    def _allocate_days(pool, pcts):
        out = []
        if pool <= 0 or not pcts:
            return [0] * len(pcts or [])
        total_pct = sum(max(0, p or 0) for p in pcts)
        if total_pct <= 0:
            return [0] * len(pcts)
        exact = [pool * max(0, p or 0) / total_pct for p in pcts]
        floors = [int(x) for x in exact]
        remaining = pool - sum(floors)
        order = sorted(range(len(exact)), key=lambda i: (exact[i] - floors[i], -i), reverse=True)
        for i in range(min(remaining, len(order))):
            floors[order[i]] += 1
        return floors

    projects = db.query(models.Project).all()
    project_by_id = {p.id: p for p in projects}
    project_id_by_name = {p.project_name: p.id for p in projects if p.project_name}
    project_members = db.query(models.ProjectMember).all()
    pm_by_id = {m.id: m for m in project_members}
    employee_by_id = {u.employee_id: u.id for u in employees}

    allocs = db.query(models.ProjectWorkdayAlloc).all()
    parsed_allocs = []
    allocated_project_ids = set()
    for a in allocs:
        try:
            obj = json.loads(a.data or "{}")
        except Exception:
            continue
        members = obj.get("members") or []
        leader_pct = obj.get("leaderPct", 0.05) or 0
        if leader_pct <= 1:
            leader_pct = leader_pct * 100
        parsed_allocs.append({
            "id": a.id,
            "project_id": a.project_id,
            "leader_pct": float(leader_pct),
            "members": members,
            "obj": obj
        })
        allocated_project_ids.add(a.project_id)

    alloc_personal = {}
    for item in parsed_allocs:
        project = project_by_id.get(item["project_id"])
        if not project:
            continue
        candidates = [r for r in workdays_all if r.project_name == project.project_name]
        chosen = max(candidates, key=lambda r: r.id) if candidates else None
        total_g = _round_int(chosen.G) if chosen else 0

        if total_g > 0 and project.project_leader_id:
            leader_share = _round_int(total_g * item["leader_pct"] / 100.0)
            leader_share = min(leader_share, total_g)
            remaining = total_g - leader_share
            alloc_personal[project.project_leader_id] = alloc_personal.get(project.project_leader_id, 0) + leader_share
        else:
            remaining = total_g

        members = [m for m in item["members"] if m.get("id")]
        pcts = [float(m.get("pct") or 0) for m in members]
        days = _allocate_days(remaining, pcts)
        for m, day in zip(members, days):
            pm = pm_by_id.get(m.get("id"))
            if not pm or not pm.employee_id:
                continue
            uid = employee_by_id.get(pm.employee_id)
            if uid is None:
                continue
            if day > 0:
                alloc_personal[uid] = alloc_personal.get(uid, 0) + day

        item["obj"]["members"] = item["members"]
        alloc_row = db.query(models.ProjectWorkdayAlloc).filter(
            models.ProjectWorkdayAlloc.id == item["id"]
        ).first()
        if alloc_row:
            alloc_row.data = json.dumps(item["obj"], ensure_ascii=False)

    alloc_by_uid = {}
    for uid, days in alloc_personal.items():
        alloc_by_uid[uid] = _round_int(days)

    fallback_by_uid = {}
    for r in workdays_all:
        if not r.user_id:
            continue
        pid = project_id_by_name.get(r.project_name or "")
        if pid in allocated_project_ids:
            continue
        fallback_by_uid[r.user_id] = fallback_by_uid.get(r.user_id, 0) + _round_int(r.G or 0)

    # Clear old results
    db.query(models.AssessmentResult).filter(models.AssessmentResult.assessment_id == assessment_id).delete()

    total_all_workdays = sum(alloc_by_uid.values()) + sum(fallback_by_uid.values())

    results = []
    for emp in employees:
        emp_scores = [s for s in scores_all if s.target_user_id == emp.id]
        emp_workdays = alloc_by_uid.get(emp.id, 0)
        emp_workdays += fallback_by_uid.get(emp.id, 0)

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
        all_emp_workdays = [alloc_by_uid.get(u.id, 0) + fallback_by_uid.get(u.id, 0) for u in employees]
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
    return db.query(models.User).filter(models.User.is_active == True).order_by(models.User.id).all()

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

def _sync_project_leader(db: Session, project_id: int):
    """让项目负责人字段与项目成员中的“项目负责人”保持一致。"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        return
    leader_member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.role == "项目负责人"
    ).order_by(models.ProjectMember.id).first()
    if leader_member and leader_member.employee_id:
        leader_user = db.query(models.User).filter(models.User.employee_id == leader_member.employee_id).first()
        project.project_leader_id = leader_user.id if leader_user else None
    else:
        project.project_leader_id = None

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
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if project:
        _sync_project_leader(db, project_id)
        sync_project_to_workload(db, project)
        db.commit()
    return {
        "id": member.id,
        "project_id": member.project_id,
        "employee_id": member.employee_id,
        "employee_name": member.employee_name,
        "department": member.department,
        "role": member.role,
        "stage_status": member.stage_status or "pending",
        "note": member.note or "",
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
    if "note" in data:
        member.note = data["note"]
    if "stage_status" in data:
        member.stage_status = data["stage_status"]
    db.commit()
    db.refresh(member)
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if project:
        _sync_project_leader(db, project_id)
        sync_project_to_workload(db, project)
        db.commit()
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
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if project:
        _sync_project_leader(db, project_id)
        sync_project_to_workload(db, project)
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
    if not (data.get("project_code") or "").strip():
        data["project_code"] = auto_project_code(db, data.get("project_type") or "")
    req = models.ProjectRequest(**data, requested_by=user_id, status="pending")
    db.add(req)
    db.commit()
    db.refresh(req)
    from datetime import datetime
    _start = datetime.strptime(req.start_date, "%Y-%m-%d").date() if req.start_date else None
    _end = datetime.strptime(req.planned_end_date, "%Y-%m-%d").date() if req.planned_end_date else None
    proj = models.Project(
        project_name=req.project_name,
        project_code=req.project_code or "",
        group_code=req.group_code or "",
        project_type=req.project_type,
        area=req.area,
        status="planning",
        start_date=_start,
        planned_end_date=_end,
        planned_man_days=req.planned_man_days,
        description=req.description,
        drawing_list=req.drawing_list or [],
        work_rounds=req.work_rounds or 1,
        round_reason=req.round_reason,
        created_by=user_id,
        project_leader_id=user_id,
        current_stage=req.stage,
        is_official=False
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    req.project_id = proj.id
    maker = db.query(models.User).filter(models.User.id == user_id).first()
    if maker:
        db.add(models.ProjectMember(
            project_id=proj.id,
            employee_id=maker.employee_id or maker.username,
            employee_name=maker.name,
            department=maker.department or "",
            role="项目负责人"
        ))
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
            "id": r.id, "project_id": r.project_id, "project_name": r.project_name, "project_type": r.project_type,
            "area": r.area, "stage": r.stage, "start_date": r.start_date, "project_code": r.project_code or "",
            "group_code": r.group_code or "",
            "description": r.description, "drawing_list": r.drawing_list or [],
            "work_rounds": r.work_rounds or 1, "round_reason": r.round_reason,
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
    proj = None
    if req.project_id:
        proj = db.query(models.Project).filter(models.Project.id == req.project_id).first()
    if not proj and req.project_code:
        proj = db.query(models.Project).filter(models.Project.project_code == req.project_code).first()
    if not proj:
        proj = db.query(models.Project).filter(models.Project.project_name == req.project_name).first()
    if not proj:
        proj = models.Project(
            project_name=req.project_name, project_code=req.project_code or "", project_type=req.project_type,
            group_code=req.group_code or "",
            area=req.area, status="planning", start_date=_start,
            planned_end_date=_end,
            planned_man_days=req.planned_man_days,
            description=req.description,
            drawing_list=req.drawing_list or [],
            work_rounds=req.work_rounds or 1,
            round_reason=req.round_reason,
            created_by=req.requested_by, project_leader_id=req.requested_by,
            current_stage=req.stage
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)
    proj.is_official = True
    proj.project_name = req.project_name
    proj.project_code = req.project_code or proj.project_code
    proj.group_code = req.group_code or proj.group_code
    proj.project_type = req.project_type
    proj.area = req.area
    proj.description = req.description
    proj.drawing_list = req.drawing_list or []
    proj.work_rounds = req.work_rounds or 1
    proj.round_reason = req.round_reason
    proj.current_stage = req.stage
    proj.start_date = _start
    proj.planned_end_date = _end
    proj.planned_man_days = req.planned_man_days
    req.project_id = proj.id
    db.commit()
    sync_project_to_workload(db, proj)
    maker = db.query(models.User).filter(models.User.id == req.requested_by).first()
    if maker:
        exists_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == proj.id,
            models.ProjectMember.employee_name == maker.name,
            models.ProjectMember.role == "项目负责人"
        ).first()
        if not exists_member:
            db.add(models.ProjectMember(
                project_id=proj.id,
                employee_id=maker.employee_id or maker.username,
                employee_name=maker.name,
                department=maker.department or "",
                role="项目负责人"
            ))
        db.commit()
        sync_project_to_workload(db, proj)
        db.commit()
    return req, proj

def reject_project_request(db: Session, request_id: int, reviewer_id: int):
    req = db.query(models.ProjectRequest).filter(models.ProjectRequest.id == request_id).first()
    if not req:
        return None
    if req.status != "pending":
        return req
    if req.project_id:
        proj = db.query(models.Project).filter(models.Project.id == req.project_id).first()
        if proj and not proj.is_official:
            db.query(models.ProjectMember).filter(models.ProjectMember.project_id == proj.id).delete(synchronize_session=False)
            db.query(models.ProjectStageProgress).filter(models.ProjectStageProgress.project_id == proj.id).delete(synchronize_session=False)
            db.query(models.Task).filter(models.Task.project_id == proj.id).delete(synchronize_session=False)
            db.query(models.ProjectMemberScore).filter(models.ProjectMemberScore.project_id == proj.id).delete(synchronize_session=False)
            db.query(models.ProjectWorkdayAlloc).filter(models.ProjectWorkdayAlloc.project_id == proj.id).delete(synchronize_session=False)
            _remove_project_workday_records(db, proj)
            db.delete(proj)
    req.status = "rejected"
    req.reviewer_id = reviewer_id
    req.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(req)
    return req
