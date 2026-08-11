from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Body, Request

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import StreamingResponse, JSONResponse

from sqlalchemy.orm import Session

from datetime import datetime

import uvicorn



from sqlalchemy import or_

import models

import schemas

import crud

import auth

from database import engine, get_db


from import_export import generate_template, import_from_excel, export_to_excel

from fastapi.staticfiles import StaticFiles

import os, os.path as _osp

from contextlib import asynccontextmanager



# 创建数据库表

models.Base.metadata.create_all(bind=engine)





@asynccontextmanager

async def lifespan(app: FastAPI):

    """初始化默认数据"""

    db = next(get_db())

    try:

        from sqlalchemy import text

        inspector = __import__("sqlalchemy").inspect(engine)

        cols = [c["name"] for c in inspector.get_columns("users")]

        if "employee_id" not in cols:

            db.execute(text("ALTER TABLE users ADD COLUMN employee_id VARCHAR(50)"))

            db.commit()

            print("提示: 已添加 employee_id 列")

        cols2 = [c2["name"] for c2 in inspector.get_columns("projects")]

        if "is_on_leave" not in cols:
            db.execute(text("ALTER TABLE users ADD COLUMN is_on_leave BOOLEAN DEFAULT 0"))
            db.commit()
            print("提示: 已添加 is_on_leave 列")

        if "project_leader_id" not in cols2:

            db.execute(text("ALTER TABLE projects ADD COLUMN project_leader_id INTEGER"))

            db.commit()

            print("提示: 已添加 project_leader_id 列")

        if "current_stage" not in cols2:

            db.execute(text("ALTER TABLE projects ADD COLUMN current_stage VARCHAR(50) DEFAULT '设计'"))

            db.commit()

            print("提示: 已添加 current_stage 列")
        if "drawing_list" not in cols2:
            db.execute(text("ALTER TABLE projects ADD COLUMN drawing_list TEXT DEFAULT '[]'"))
            db.commit()
            print("提示: 已添加 drawing_list 列")
        if "is_official" not in cols2:
            db.execute(text("ALTER TABLE projects ADD COLUMN is_official BOOLEAN DEFAULT 1"))
            db.commit()
            print("提示: 已添加 is_official 列")
        cols3 = [c3["name"] for c3 in inspector.get_columns("project_requests")]
        if "project_id" not in cols3:
            db.execute(text("ALTER TABLE project_requests ADD COLUMN project_id INTEGER"))
            db.commit()
            print("提示: 已添加 project_requests.project_id 列")


    except Exception as e:

        print(f"迁移错误: {e}")



    try:

        admin = db.query(models.User).filter(models.User.username == "admin").first()

        if not admin:

            from auth import get_password_hash

            admin = models.User(

                username="admin",

                password_hash=get_password_hash("admin123"),

                name="管理员",

                role="director",

                department="建筑一所",

                is_active=True

            )

            db.add(admin)

            db.commit()

            print("管理员账号已创建")

    except Exception as e:

        print(f"管理员账号创建失败: {e}")





    try:
        sync_result = crud.sync_all_projects_to_workload(db)
        print(f"项目库同步完成: {sync_result}")
    except Exception as e:
        print(f"项目库同步失败: {e}")

    yield

    db.close()

app = FastAPI(

    title="建筑一所·生产调度助手",

    description="建筑一所生产调度管理系统，支持人员技能矩阵管理、工作量统计、项目调度等核心功能",

    version="1.0.0",

    lifespan=lifespan

)









# CORS配置

app.add_middleware(

    CORSMiddleware,

    allow_origins=["http://localhost:5173", "http://localhost:3000"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)



# ============ 认证相关 ============



@app.post("/api/login", response_model=schemas.TokenResponse)

def login(user_login: schemas.UserLogin, db: Session = Depends(get_db)):

    user = crud.get_user_by_username(db, user_login.username)

    if not user or not auth.verify_password(user_login.password, user.password_hash):

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail="用户名或密码错误"

        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号已停用"
        )

    

    access_token = auth.create_access_token(

        data={"sub": str(user.id), "role": user.role if isinstance(user.role, str) else user.role.value}

    )

    

    return {

        "access_token": access_token,

        "user": schemas.UserResponse.model_validate(user)

    }



@app.post("/api/register", response_model=schemas.UserResponse)

def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):

    import sqlite3

    # 检查员工信息库

    emp_conn = sqlite3.connect(__import__("database").EMPLOYEES_DB_PATH)

    emp_cursor = emp_conn.cursor()

    emp = emp_cursor.execute(

        "SELECT id, name, department FROM employees WHERE employee_id = ? AND name = ?",

        (user_data.employee_id, user_data.name)

    ).fetchone()

    emp_conn.close()

    if not emp:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail="员工信息不匹配，请确认工号和姓名与单位员工信息库一致"

        )

    # 检查用户名是否已存在

    existing = crud.get_user_by_username(db, user_data.username)

    if existing:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail="用户名已存在"

        )

    user = crud.create_user(db, user_data.model_dump())

    # 将员工库中的姓名和部门同步到用户

    if emp:

        user.name = emp[1]

        if not user_data.department:

            user.department = emp[2]

        db.commit()

        db.refresh(user)

    return user



@app.get("/api/user/me")

def get_current_user_info(current_user: models.User = Depends(auth.get_current_user)):

    import sqlite3

    conn = sqlite3.connect(r"E:\gs\pt\2\backend\building_institute.db")

    conn.row_factory = sqlite3.Row

    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE id=?", (current_user.id,))

    row = c.fetchone()

    conn.close()

    if not row:

        return {}

    result = dict(row)

    result.pop("password_hash", None)

    resp = JSONResponse(result)

    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    return resp

@app.put("/api/user/update-account")
def update_my_account(
    data: schemas.UpdateAccountRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if not auth.verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码错误")
    new_username = (data.new_username or "").strip()
    if new_username and new_username != current_user.username:
        exists = db.query(models.User).filter(models.User.username == new_username).first()
        if exists:
            raise HTTPException(status_code=400, detail="用户名已存在")
        current_user.username = new_username
    if data.new_password:
        current_user.password_hash = auth.get_password_hash(data.new_password)
    db.commit()
    db.refresh(current_user)
    return {"message": "修改成功", "username": current_user.username}



@app.get("/api/users", response_model=list[schemas.UserResponse])

def get_users(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    return crud.get_users(db)



# ============ 技能矩阵 ============



@app.get("/api/skill-matrices")

def get_skill_matrices(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    skills = crud.get_skill_matrices(db)

    result = []

    for s in skills:

        user = db.query(models.User).filter(models.User.id == s.user_id).first()

        result.append({

            **schemas.SkillMatrixResponse.model_validate(s).model_dump(),

            "user_name": user.name if user else ""

        })

    return result



@app.post("/api/skill-matrices")

def create_skill_matrix(

    data: schemas.SkillMatrixCreate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    return crud.create_skill_matrix(db, data)



@app.put("/api/skill-matrices/{user_id}")

def update_skill_matrix(

    user_id: int,

    data: schemas.SkillMatrixBase,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    return crud.update_skill_matrix(db, user_id, data)



# ============ 项目相关 ============



@app.get("/api/projects")

def get_projects(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    role = auth.get_user_role(current_user)

    if role in ["director", "deputy_director"]:

        return crud.get_projects(db)

    name = current_user.name

    proj_ids = set()

    for m in db.query(models.ProjectMember).filter(models.ProjectMember.employee_name == name).all():

        proj_ids.add(m.project_id)

    for s in db.query(models.ProjectStageProgress).filter(models.ProjectStageProgress.assigned_to_name == name).all():

        proj_ids.add(s.project_id)

    wl_names = set()

    for r in db.query(models.WorkloadRecord).filter(or_(

        models.WorkloadRecord.overall_lead.contains(name),

        models.WorkloadRecord.architecture_lead.contains(name),

        models.WorkloadRecord.participants.contains(name)

    )).all():

        if r.project_name:

            wl_names.add(r.project_name)

    if wl_names:

        for p in db.query(models.Project).filter(models.Project.project_name.in_(wl_names)).all():

            proj_ids.add(p.id)

    for p in db.query(models.Project).filter(
        models.Project.created_by == current_user.id,
        models.Project.is_official == False
    ).all():
        proj_ids.add(p.id)

    if not proj_ids:

        return []

    projects = db.query(models.Project).filter(

        models.Project.id.in_(list(proj_ids))

    ).order_by(models.Project.created_at.desc()).all()

    return projects





@app.post("/api/projects/sync-library")
def sync_projects_to_library(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role(["director"]))
):
    return crud.sync_all_projects_to_workload(db)



@app.get("/api/employee-project-map")

def get_employee_project_map(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    members = db.query(models.ProjectMember).all()

    projects = crud.get_projects(db)

    proj_map = {p["id"]: p["project_name"] for p in projects}

    result = {}

    for m in members:

        name = m.employee_name

        if name not in result:

            result[name] = []

        pname = proj_map.get(m.project_id, "")

        if pname:

            result[name].append({"project_name": pname, "role": m.role})

    return result



@app.post("/api/projects")

def create_project(

    data: schemas.ProjectCreate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    proj = crud.create_project(db, data, current_user.id)

    import sqlite3, os

    _db = sqlite3.connect(os.path.join(os.path.dirname(__file__), "building_institute.db"))

    _db.row_factory = sqlite3.Row

    row = _db.execute("SELECT * FROM projects WHERE id=?", (proj.id,)).fetchone()

    _db.close()

    if row:

        return dict(row)

    return proj













# ========== 项目建立申请 API ==========



@app.post("/api/project-requests")

def submit_project_request(data: schemas.ProjectRequestCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):

    return crud.create_project_request(db, data.model_dump(), current_user.id)



@app.get("/api/project-requests")

def list_project_requests(status: str = None, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):

    if auth.get_user_role(current_user) in ["director", "deputy_director"]:

        return crud.get_project_requests(db, status=status)

    return crud.get_project_requests(db, user_id=current_user.id)



@app.put("/api/project-requests/{request_id}/approve")

def approve_project_request(request_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["director"]))):

    import traceback

    try:

        req, proj = crud.approve_project_request(db, request_id, current_user.id)

        if not req:

            raise HTTPException(404, detail="申请不存在")

        if not proj:

            raise HTTPException(400, detail="该申请已被处理，当前状态：" + req.status)

        return {"message": "项目已建立", "project_id": proj.id}

    except Exception as e:

        traceback.print_exc()

        raise HTTPException(500, detail=f"批准失败: {str(e)}")



@app.put("/api/project-requests/{request_id}/reject")

def reject_project_request(request_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["director"]))):

    req = crud.reject_project_request(db, request_id, current_user.id)

    if not req:

        raise HTTPException(404, detail="申请不存在")

    return {"message": "已拒绝"}

@app.delete("/api/projects/{project_id}")

def delete_project(

    project_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    """删除项目"""

    ok = crud.delete_project(db, project_id)

    if not ok:

        raise HTTPException(status_code=404, detail="项目不存在")

    return {"message": "项目已删除"}



# ============ 项目参与人员 ============



@app.get("/api/projects/{project_id}/members", response_model=list[schemas.ProjectMemberResponse])

def get_project_members(

    project_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    return crud.get_project_members(db, project_id)



@app.post("/api/projects/{project_id}/members", response_model=schemas.ProjectMemberResponse)

def add_project_member(

    project_id: int,

    data: schemas.ProjectMemberCreate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    role = auth.get_user_role(current_user)

    if role not in ["director", "deputy_director"]:

        proj = db.query(models.Project).filter(models.Project.id == project_id).first()

        if not proj or proj.project_leader_id != current_user.id:

            raise HTTPException(403, detail="无权限")

    return crud.add_project_member(db, project_id, data.model_dump())



@app.get("/api/projects/{project_id}/member-scores")
def get_project_member_scores(project_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    from models import ProjectMemberScore
    scores = db.query(ProjectMemberScore).filter(ProjectMemberScore.project_id == project_id).all()
    return [
        {
            "id": s.id, "project_id": s.project_id, "project_name": s.project_name,
            "stage": s.stage, "role": s.role, "target_user_id": s.target_user_id, "target_employee_id": s.target_employee_id, "target_user_name": s.target_user_name,
            "evaluator_id": s.evaluator_id,
            "score": s.score,
            "tech_ability": s.tech_ability, "work_quality": s.work_quality,
            "cooperation": s.cooperation, "comment": s.comment,
            "created_at": s.created_at, "updated_at": s.updated_at
        }
        for s in scores
    ]

@app.post("/api/projects/{project_id}/member-scores")
def submit_project_member_score(project_id: int, data: schemas.ProjectMemberScoreCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    from models import ProjectMemberScore
    proj = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")
    role = auth.get_user_role(current_user)
    if role != "director" and proj.project_leader_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅项目负责人或所长可以评分")
    lookup_emp = data.target_employee_id or (str(data.target_user_id) if data.target_user_id else "")
    role_val = data.role or ""
    existing = db.query(ProjectMemberScore).filter(
        ProjectMemberScore.project_id == project_id,
        ProjectMemberScore.evaluator_id == current_user.id
    ).filter(
        ProjectMemberScore.target_employee_id == lookup_emp,
        ProjectMemberScore.role == role_val
    ).first()
    if existing:
        existing.stage = data.stage or proj.current_stage
        existing.role = role_val
        existing.score = data.score
        existing.tech_ability = data.tech_ability
        existing.work_quality = data.work_quality
        existing.cooperation = data.cooperation
        existing.comment = data.comment
        existing.updated_at = datetime.utcnow()
    else:
        target = db.query(models.User).filter(models.User.id == data.target_user_id).first()
        existing = ProjectMemberScore(
            project_id=project_id,
            project_name=proj.project_name,
            role=role_val,
            stage=data.stage or proj.current_stage,
            target_user_id=data.target_user_id,
            target_employee_id=data.target_employee_id or (str(data.target_user_id) if data.target_user_id else ""),
            target_user_name=target.name if target else "",
            evaluator_id=current_user.id,
            score=data.score,
            tech_ability=data.tech_ability,
            work_quality=data.work_quality,
            cooperation=data.cooperation,
            comment=data.comment
        )
        db.add(existing)
    db.commit()
    return {"message": "评分已保存"}


@app.get("/api/projects/{project_id}/stages", response_model=list[schemas.StageProgressResponse])

def get_project_stages(

    project_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    return crud.get_project_stages(db, project_id)



@app.post("/api/projects/{project_id}/stages", response_model=schemas.StageProgressResponse)

def upsert_project_stage(

    project_id: int,

    data: schemas.StageProgressCreate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)):

    role = auth.get_user_role(current_user)

    if role not in ["director", "deputy_director"]:

        proj = db.query(models.Project).filter(models.Project.id == project_id).first()

        if not proj or proj.project_leader_id != current_user.id:

            raise HTTPException(403, detail="无权限管理此项目进度")

    result = crud.upsert_project_stage(db, project_id, data.model_dump())

    if result.assigned_to:

        crud.update_employee_workload(db, result.assigned_to)

    return result



@app.delete("/api/projects/{project_id}/stages/{stage_id}")

def delete_project_stage(

    project_id: int, stage_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    ok = crud.delete_project_stage(db, stage_id)

    if not ok:

        raise HTTPException(status_code=404, detail="阶段不存在")

    return {"message": "已删除"}



@app.post("/api/workload/update-all")

def update_all_workload(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    crud.update_employee_workload(db)

    return {"message": "负荷已更新"}





@app.put("/api/projects/{project_id}/members/{member_id}")

def update_project_member(

    project_id: int,

    member_id: int,

    data: dict,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    role = auth.get_user_role(current_user)

    if role not in ["director", "deputy_director"]:

        proj = db.query(models.Project).filter(models.Project.id == project_id).first()

        if not proj or proj.project_leader_id != current_user.id:

            raise HTTPException(403, detail="无权限")

    member = crud.update_project_member(db, project_id, member_id, data)

    if not member:

        raise HTTPException(status_code=404, detail="\u6210\u5458\u4e0d\u5b58\u5728")

    return member









@app.put("/api/projects/{project_id}/end-date")
def update_project_end_date(project_id: int, data: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    proj = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not proj:
        raise HTTPException(404, detail="项目不存在")
    role = auth.get_user_role(current_user)
    if role != "director" and proj.project_leader_id != current_user.id:
        raise HTTPException(403, detail="仅所长或项目负责人可操作")
    from datetime import datetime as _dt
    end_date = data.get("planned_end_date")
    if end_date:
        try:
            proj.planned_end_date = _dt.strptime(str(end_date)[:10], "%Y-%m-%d").date()
        except Exception:
            proj.planned_end_date = None
    db.commit()
    crud.sync_project_to_workload(db, proj)
    db.commit()
    return {"message": "预计完成时间已更新", "planned_end_date": proj.planned_end_date}



@app.put("/api/projects/{project_id}/drawing-list")
def save_project_drawing_list(
    project_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    proj = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")
    role = auth.get_user_role(current_user)
    if role not in ["director", "deputy_director"] and proj.project_leader_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅所长或项目负责人可操作")
    proj.drawing_list = data.get("drawing_list") or []
    db.commit()
    crud.sync_project_to_workload(db, proj)
    db.commit()
    return {"message": "人员安排已保存", "drawing_list": proj.drawing_list}



@app.post("/api/projects/{project_id}/start")
def start_project(project_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    proj = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not proj:
        raise HTTPException(404, detail="项目不存在")
    role = auth.get_user_role(current_user)
    if role != "director" and proj.project_leader_id != current_user.id:
        raise HTTPException(403, detail="仅所长或项目负责人可操作")
    proj.status = "in_progress"
    db.commit()
    crud.sync_project_to_workload(db, proj)
    db.commit()
    return {"message": "项目已开始", "status": proj.status}


@app.post("/api/projects/{project_id}/stop")
def stop_project(project_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    proj = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not proj:
        raise HTTPException(404, detail="项目不存在")
    role = auth.get_user_role(current_user)
    if role != "director" and proj.project_leader_id != current_user.id:
        raise HTTPException(403, detail="仅所长或项目负责人可操作")
    proj.status = "stopped"
    db.commit()
    crud.sync_project_to_workload(db, proj)
    db.commit()
    return {"message": "项目已暂停", "status": proj.status}

@app.post("/api/projects/{project_id}/complete")
def complete_project(project_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    proj = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not proj:
        raise HTTPException(404, detail="项目不存在")
    role = auth.get_user_role(current_user)
    if role != "director" and proj.project_leader_id != current_user.id:
        raise HTTPException(403, detail="仅所长或项目负责人可完成项目")
    proj.status = "closed"
    from datetime import date
    proj.actual_end_date = date.today()
    db.commit()
    crud.sync_project_to_workload(db, proj)
    db.commit()
    return {"message": "项目已完成", "status": proj.status}

@app.put("/api/projects/{project_id}/status")

def update_project_status(

    project_id: int,

    data: dict,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    proj = db.query(models.Project).filter(models.Project.id == project_id).first()

    if not proj:

        raise HTTPException(404, detail="项目不存在")

    if not auth.is_director(current_user):

        raise HTTPException(403, detail="仅所长可修改项目状态")

    new_status = data.get("status", "").lower()

    valid = ["planning", "design", "construction", "completed", "closed"]

    if new_status not in valid:

        raise HTTPException(400, detail="无效状态")

    proj.status = new_status

    db.commit()
    crud.sync_project_to_workload(db, proj)
    db.commit()

    return {"message": "项目状态已更新"}





@app.delete("/api/projects/{project_id}/members/{member_id}")

def remove_project_member(

    project_id: int,

    member_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    role = auth.get_user_role(current_user)

    if role not in ["director", "deputy_director"]:

        proj = db.query(models.Project).filter(models.Project.id == project_id).first()

        if not proj or proj.project_leader_id != current_user.id:

            raise HTTPException(403, detail="无权限")

    ok = crud.remove_project_member(db, project_id, member_id)

    if not ok:

        raise HTTPException(status_code=404, detail="项目成员不存在")

    return {"message": "已移除"}





# ============ 员工池（读取 employees.db） ============



@app.get("/api/employee-pool", response_model=list[schemas.EmployeePoolItem])

def get_employee_pool(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    return crud.get_employee_pool_merged(db)





# ============ 同步接口 ============



@app.post("/api/sync/from-workload")

def sync_from_workload(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    """从历史工作量统计库同步项目及参与人员"""

    import sqlite3

    records = db.query(models.WorkloadRecord).all()

    emp_pool = crud.get_employee_pool_merged(db)

    projects_created = 0

    members_added = 0

    seen = {}

    for r in records:

        code = (r.project_code or "").strip()

        name = (r.project_name or "").strip()

        key = code or name

        if not key:

            continue

        if key not in seen:

            seen[key] = {"name": name, "type": r.project_type or "", "code": code, "participants": set()}

        parts = [p.strip() for p in (r.participants or "").replace("，", ",").split(",") if p.strip()]

        seen[key]["participants"].update(parts)

        if r.overall_lead and r.overall_lead.strip():

            seen[key]["participants"].add(r.overall_lead.strip())

        if r.architecture_lead and r.architecture_lead.strip():

            seen[key]["participants"].add(r.architecture_lead.strip())

    for key, info in seen.items():

        existing = db.query(models.Project).filter(models.Project.project_name == info["name"]).first()

        if not existing:

            project = models.Project(

                project_name=info["name"], project_type=info["type"] or "其它",

                area=0, created_by=current_user.id

            )

            db.add(project)

            db.flush()

            projects_created += 1

        else:

            project = existing

        for pname in info["participants"]:

            matched = [e for e in emp_pool if e["name"] == pname]

            if matched:

                emp = matched[0]

                exists = db.query(models.ProjectMember).filter(

                    models.ProjectMember.project_id == project.id,

                    models.ProjectMember.employee_id == emp["employee_id"]

                ).first()

                if not exists:

                    db.add(models.ProjectMember(

                        project_id=project.id, employee_id=emp["employee_id"],

                        employee_name=emp["name"], department=emp["department"],

                        role="一般设计人"

                    ))

                    members_added += 1

    db.commit()

    return {

        "projects_created": projects_created, "members_added": members_added,

        "total_records": len(records), "unique_projects": len(seen)

    }





@app.post("/api/sync/employee-skills")

def sync_employee_skills(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    """从员工信息库同步到人员账号和技能矩阵（自动同步，无需手动触发）"""

    return crud.sync_employees_db_to_users(db)







# ============ 能力模块 API ============



# ============ 知识库管理 ============



# ============ 员工管理 API ============

# ============ employee API ============



@app.get("/api/employees", response_model=list[schemas.EmployeeResponse])

def get_all_employees(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    """获取所有员工"""

    return crud.get_all_employees(db)



@app.post("/api/employees")

def create_employee(

    data: schemas.EmployeeCreate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    """创建员工"""

    existing = crud.get_user_by_username(db, data.username)

    if existing:

        raise HTTPException(status_code=400, detail="用户名已存在")

    return crud.create_employee(db, data)



@app.put("/api/employees/{employee_id}")

def update_employee(

    employee_id: int,

    data: schemas.EmployeeUpdate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    """更新员工"""

    employee = crud.update_employee(db, employee_id, data)

    if not employee:

        raise HTTPException(status_code=404, detail="员工不存在")

    return employee



@app.delete("/api/employees/{employee_id}")

def delete_employee(

    employee_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    """删除员工（软删除）"""

    user = db.query(models.User).filter(models.User.id == employee_id).first()

    if not user:

        raise HTTPException(status_code=404, detail="员工不存在")

    user.is_active = False

    db.commit()

    return {"message": "删除成功"}



@app.post("/api/employees/clear-all")

def clear_all_employees(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    """清空所有导入的员工"""

    deleted = db.query(models.User).filter(models.User.employee_id.isnot(None)).delete()

    db.commit()

    return {"message": "已清空 " + str(deleted) + " 条员工数据"}



@app.get("/api/config/profile-options")

def get_profile_options():

    import sqlite3

    import os

    options = {

        "profession": ["建筑", "结构", "给排水", "暖通", "电气", "规划", "景观", "室内设计", "概预算", "BIM设计"],

        "title": ["助理工程师", "工程师", "高级工程师", "教授级高级工程师"],

        "registration": ["一级注册建筑师", "一级注册结构工程师", "注册公用设备工程师(给水排水)", "注册公用设备工程师(暖通空调)", "注册电气工程师(供配电)", "注册土木工程师(岩土)", "注册规划师", "无"]

    }

    return options

@app.get("/api/config/constants")

def get_constants():

    return {

        "project_types": ["站房","枢纽","大铁","轨交","民建","改造","援外","BIM","方案","建筑","咨询","总包"],

        "professions": ["建筑","结构","给排水","暖通","电气","规划","景观","室内","概预算"],

        "load_statuses": ["空闲","轻量","适中","饱满","超负荷","休假"],

    }



# ============ Excel import/export ============



@app.get("/api/employees/template/download")

def download_template():

    output = generate_template()

    return StreamingResponse(

        output,

        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

        headers={"Content-Disposition": "attachment; filename=template.xlsx"}

    )



@app.post("/api/employees/import")

async def import_employees(

    file: UploadFile = File(...),

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    """批量导入员工"""

    if not file.filename.endswith('.xlsx'):

        raise HTTPException(400, "请上传 .xlsx 文件")

    content = await file.read()

    results = import_from_excel(content, db)

    return results



@app.get("/api/employees/export")

def export_employees(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    """导出员工到Excel"""

    output = export_to_excel(db)

    return StreamingResponse(

        output,

        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

        headers={"Content-Disposition": "attachment; filename=export.xlsx"}

    )



# ============ workload record API ============



@app.get("/api/workload-records")

def get_workload_records(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    return crud.get_workload_records(db)

@app.delete("/api/workload-records/all")

def clear_workload(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    count = db.query(models.WorkloadRecord).delete()

    db.commit()

    return {"deleted": count}









# ============ 账号管理 API ============

@app.get("/api/admin/users", response_model=list[schemas.UserAdminResponse])

def admin_get_users(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    return crud.get_all_users(db)



@app.put("/api/admin/users/{user_id}")

def admin_update_user(

    user_id: int, data: schemas.UserUpdateAdmin,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    user = crud.update_user_by_admin(db, user_id, data.model_dump(exclude_unset=True))

    if not user: raise HTTPException(404, detail="用户不存在")

    return {"message": "已更新", "role": user.role}



# ============ 审批流程 API ============

@app.post("/api/change-requests", response_model=schemas.ChangeRequestResponse)

def submit_change_request(

    data: schemas.ChangeRequestCreate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    # Get old value

    old_val = getattr(current_user, data.field_name, "")

    req_data = data.model_dump()

    req_data["old_value"] = str(old_val) if old_val else ""

    return crud.create_change_request(db, current_user.id, req_data)



@app.get("/api/change-requests", response_model=list[schemas.ChangeRequestResponse])

def list_change_requests(

    status: str = None,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    role = auth.get_user_role(current_user)

    if role in ["director", "deputy_director"]:

        return crud.get_change_requests(db, status=status)

    return crud.get_change_requests(db, user_id=current_user.id)



@app.put("/api/change-requests/{request_id}/review")

def review_request(

    request_id: int, data: schemas.ChangeRequestReview,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director", "deputy_director"]))

):

    req = crud.review_change_request(db, request_id, current_user.id, data.status, data.comment or "")

    if not req: raise HTTPException(404, detail="请求不存在")

    return {"message": "已" + ("通过" if data.status == "approved" else "拒绝")}





# ============ 量化分配新模块 API ============



@app.get("/api/performance/rewards")

def list_rewards(assessment_id: int = None, user_id: int = None, db: Session = Depends(get_db)):

    import crud

    return crud.get_rewards(db, assessment_id, user_id)



@app.post("/api/performance/rewards")

def create_reward(data: schemas.RewardRecordCreate, db: Session = Depends(get_db), current_user = Depends(auth.require_role(["director"]))):

    return crud.add_reward(db, data.model_dump())



@app.delete("/api/performance/rewards/{rid}")

def remove_reward(rid: int, db: Session = Depends(get_db), current_user = Depends(auth.require_role(["director"]))):

    ok = crud.delete_reward(db, rid)

    if not ok: raise HTTPException(404, detail="记录不存在")

    return {"message": "已删除"}



@app.get("/api/performance/bonus-points")

def list_bonus_points(assessment_id: int = None, user_id: int = None, db: Session = Depends(get_db)):

    return crud.get_bonus_points(db, assessment_id, user_id)



@app.post("/api/performance/bonus-points")

def create_bonus_point(data: schemas.BonusPointCreate, db: Session = Depends(get_db), current_user = Depends(auth.require_role(["director"]))):

    return crud.add_bonus_point(db, data.model_dump())



@app.delete("/api/performance/bonus-points/{bid}")

def remove_bonus_point(bid: int, db: Session = Depends(get_db), current_user = Depends(auth.require_role(["director"]))):

    ok = crud.delete_bonus_point(db, bid)

    if not ok: raise HTTPException(404, detail="记录不存在")

    return {"message": "已删除"}



@app.get("/api/performance/special-cases")

def list_special_cases(assessment_id: int = None, db: Session = Depends(get_db)):

    return crud.get_special_cases(db, assessment_id)



@app.post("/api/performance/special-cases")

def create_special_case(data: schemas.SpecialCaseCreate, db: Session = Depends(get_db), current_user = Depends(auth.require_role(["director"]))):

    return crud.add_special_case(db, data.model_dump())



@app.delete("/api/performance/special-cases/{sid}")

def remove_special_case(sid: int, db: Session = Depends(get_db), current_user = Depends(auth.require_role(["director"]))):

    ok = crud.delete_special_case(db, sid)

    if not ok: raise HTTPException(404, detail="记录不存在")

    return {"message": "已删除"}



@app.post("/api/performance/calculate-personal")

def calc_personal(data: dict, db: Session = Depends(get_db), current_user = Depends(auth.require_role(["director"]))):

    aid = data.get("assessment_id")

    if not aid: raise HTTPException(400, detail="assessment_id required")

    result = crud.calc_personal_performance(db, aid)

    return result



# ============ 初始化数据 ============



# 启动服务





# Static files handled in __main__





@app.delete("/api/workload-records/{record_id}")

def delete_workload_record(

    record_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    ok = crud.delete_workload_record(db, record_id)

    if not ok:

        raise HTTPException(status_code=404, detail="记录不存在")

    return {"message": "删除成功"}



@app.post("/api/workload-records/import")

async def import_workload(

    file: UploadFile = File(...),

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    if not file.filename.endswith('.xlsx'):

        raise HTTPException(400, "请上传 .xlsx 文件")

    content = await file.read()

    from import_export import import_workload_from_excel

    results = import_workload_from_excel(content, db)

    return results



@app.get("/api/workload-records/template/download")
def download_workload_template(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role(["director"]))
):
    from import_export import generate_workload_template
    output = generate_workload_template()
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=workload_template.xlsx"}
    )



@app.get("/api/workload-records/export")

def export_workload(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    records = crud.get_workload_records(db)
    projects = db.query(models.Project).all()
    project_by_code = {}
    project_by_name = {}
    for p in projects:
        if p.project_code and p.project_code.strip():
            project_by_code[p.project_code.strip()] = p
        if p.project_name and p.project_name.strip():
            project_by_name[p.project_name.strip()] = p
    member_rows = db.query(models.ProjectMember).all()
    members_by_project = {}
    for m in member_rows:
        members_by_project.setdefault(m.project_id, []).append(m)

    def member_names(project, roles):
        names = []
        seen = set()
        for m in members_by_project.get(project.id, []):
            if m.role in roles and m.employee_name and m.employee_name not in seen:
                seen.add(m.employee_name)
                names.append(m.employee_name)
        return "、".join(names)

    def find_project(r):
        if r.project_code and r.project_code.strip() in project_by_code:
            return project_by_code[r.project_code.strip()]
        if r.project_name and r.project_name.strip() in project_by_name:
            return project_by_name[r.project_name.strip()]
        return None

    columns = ["项目编号", "项目类型", "规模", "阶段", "开始日期", "预计结束", "计划工天", "项目负责人", "设计", "复核", "专业负责人", "院审", "总体审核", "集团审核"]

    import pandas as pd

    from io import BytesIO

    data = []

    for r in records:
        p = find_project(r)
        scale = r.scale or ""
        if not scale and p and p.area:
            scale = ("%g" % p.area) + "㎡"
        data.append({
            "项目编号": r.project_code or "",
            "项目类型": p.project_type if p and p.project_type else (r.project_type or ""),
            "规模": scale,
            "阶段": p.current_stage if p and p.current_stage else (r.stage or ""),
            "开始日期": p.start_date.strftime("%Y-%m-%d") if p and p.start_date else "",
            "预计结束": p.planned_end_date.strftime("%Y-%m-%d") if p and p.planned_end_date else "",
            "计划工天": p.planned_man_days if p and p.planned_man_days else (r.calculated_work_days or ""),
            "项目负责人": member_names(p, {"项目负责人"}) if p else (r.overall_lead or ""),
            "设计": member_names(p, {"设计", "设计阶段"}) if p else "",
            "复核": member_names(p, {"复核", "复核阶段"}) if p else "",
            "专业负责人": member_names(p, {"专业负责人", "专业审核"}) if p else "",
            "院审": member_names(p, {"院审"}) if p else "",
            "总体审核": member_names(p, {"总体审核"}) if p else "",
            "集团审核": member_names(p, {"集团审核"}) if p else "",
        })

    df = pd.DataFrame(data, columns=columns)

    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:

        df.to_excel(writer, sheet_name='workload', index=False)

    output.seek(0)

    return StreamingResponse(

        output,

        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

        headers={"Content-Disposition": "attachment; filename=workload.xlsx"}

    )

@app.get("/api/knowledge-base/quality-standards")

def get_quality_standards(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    return crud.get_quality_standards(db)



@app.post("/api/knowledge-base/quality-standards")

def create_quality_standard(

    data: schemas.QualityStandardCreate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    return crud.create_quality_standard(db, data)



@app.get("/api/performance/my-projects")

def get_my_projects(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    name = current_user.name



    result_map = {}



    # 1. 从 WorkloadRecord 查找

    wl_records = db.query(models.WorkloadRecord).filter(

        or_(

            models.WorkloadRecord.overall_lead.contains(name),

            models.WorkloadRecord.architecture_lead.contains(name),

            models.WorkloadRecord.participants.contains(name)

        )

    ).all()

    for r in wl_records:

        pname = r.project_name or ""

        role_parts = []

        if r.overall_lead and name in r.overall_lead: role_parts.append("总体/专册")

        if r.architecture_lead and name in r.architecture_lead: role_parts.append("建筑专册")

        if r.participants and name in r.participants: role_parts.append("参与人员")

        result_map[pname] = {

            "project_name": pname,

            "project_code": r.project_code or "",

            "project_type": r.project_type or "",

            "stage": r.stage or "",

            "year": r.year or "",

            "role": "、".join(role_parts) if role_parts else "参与人员",

            "calculated_work_days": r.calculated_work_days or 0,

            "actual_work_days_architecture": r.actual_work_days_architecture or 0,

            "actual_work_days_structure": r.actual_work_days_structure or 0

        }



    # 2. 从 ProjectMember 查找

    memberships = db.query(models.ProjectMember).filter(

        models.ProjectMember.employee_name == name

    ).all()

    for m in memberships:

        p = db.query(models.Project).filter(models.Project.id == m.project_id).first()

        if p and p.project_name and p.is_official:

            key = p.project_name

            if key not in result_map:

                result_map[key] = {

                    "project_name": key,

                    "project_code": "",

                    "project_type": p.project_type or "",

                    "stage": p.current_stage or "",

                    "year": "",

                    "role": m.role + "(项目管理模块)",

                    "project_leader_id": p.project_leader_id,

                    "calculated_work_days": 0,

                    "actual_work_days_architecture": 0,

                    "actual_work_days_structure": 0

                }



    # 3. 从 ProjectStageProgress 查找

    stages = db.query(models.ProjectStageProgress).filter(

        models.ProjectStageProgress.assigned_to_name == name

    ).all()

    for s in stages:

        p = db.query(models.Project).filter(models.Project.id == s.project_id).first()

        if p and p.project_name and p.is_official:

            key = p.project_name

            if key not in result_map:

                result_map[key] = {

                    "project_name": key,

                    "project_code": "",

                    "project_type": p.project_type or "",

                    "stage": s.stage_name,

                    "year": "",

                    "role": s.stage_name + "(阶段负责)",

                    "calculated_work_days": 0,

                    "actual_work_days_architecture": 0,

                    "actual_work_days_structure": 0

                }



    # 如果所长/副所长，加载所有项目

    _role = auth.get_user_role(current_user)

    if _role in ["director", "deputy_director"]:

        for _proj in db.query(models.Project).all():

            _pn = _proj.project_name

            if _pn and _pn not in result_map:

                result_map[_pn] = {

                    "project_name": _pn,

                    "project_code": "",

                    "project_type": _proj.project_type or "",

                    "stage": _proj.current_stage or "",

                    "year": "",

                    "role": "所长查看",

                    "calculated_work_days": 0,

                    "actual_work_days_architecture": 0,

                    "actual_work_days_structure": 0

                }



    # 判断编辑权限

    _can_edit_all = _role in ["director", "deputy_director"]

    _leader_ids = set()

    _name_to_id = {}

    if not _can_edit_all:

        for _p in db.query(models.Project).all():

            _name_to_id[_p.project_name] = _p.id

            if _p.project_leader_id == current_user.id:

                _leader_ids.add(_p.id)



    _result = []

    for _key, _val in result_map.items():

        _can_edit = _can_edit_all

        if not _can_edit:

            _pid = _name_to_id.get(_key)

            if _pid and _pid in _leader_ids:

                _can_edit = True

        _val["can_edit"] = _can_edit

        _val["is_participant"] = _val.get("role") != "所长查看"

        _result.append(_val)

    return _result





# ============ 绩效考核 API ============



@app.get("/api/performance/employees")

def get_performance_employees(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    employees = db.query(models.User).filter(models.User.is_active == True, models.User.employee_id.isnot(None)).all()

    return [{

        "id": e.id, "name": e.name, "employee_id": e.employee_id,

        "profession": e.profession

    } for e in employees]





@app.post("/api/performance/assessments", response_model=schemas.PerformanceAssessmentResponse)

def create_performance_assessment(

    data: schemas.PerformanceAssessmentCreate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    return crud.create_assessment(db, data.model_dump())





@app.get("/api/performance/assessments", response_model=list[schemas.PerformanceAssessmentResponse])

def list_performance_assessments(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    return crud.get_assessments(db)





@app.delete("/api/performance/assessments/{assessment_id}")

def delete_performance_assessment(

    assessment_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    ok = crud.delete_assessment(db, assessment_id)

    if not ok:

        raise HTTPException(status_code=404, detail="考核不存在")

    return {"message": "删除成功"}





@app.post("/api/performance/workdays")

def create_workday(

    data: schemas.WorkdayRecordCreate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director", "project_leader"]))

):

    record = crud.create_workday_record(db, data.model_dump(), current_user.id)

    return {"id": record.id, "G": record.G, "message": "工天记录已创建"}







@app.delete('/api/performance/workdays/{record_id}')

def delete_workday(record_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    ok = crud.delete_workday_record(db, record_id)
    if not ok:
        raise HTTPException(status_code=404, detail='记录不存在')
    return {'message': '已删除'}

@app.post("/api/performance/alloc-save-final")

def save_alloc_final(body: dict, db: Session = Depends(get_db)):

    import json

    from models import ProjectWorkdayAlloc

    pid = body.get("project_id", 0)

    if not pid:

        return {"error": "missing project_id"}

    data = body.get("data", {}); dd = data if isinstance(data, dict) else {}; dd["locked"] = True; data_str = json.dumps(data, ensure_ascii=False)

    alloc = db.query(ProjectWorkdayAlloc).filter(ProjectWorkdayAlloc.project_id == pid).first()

    if alloc:

        alloc.data = data_str

        alloc.updated_at = datetime.utcnow()

    else:

        proj = db.query(models.Project).filter(models.Project.id == pid).first()

        name = proj.project_name if proj else ""

        alloc = ProjectWorkdayAlloc(project_id=pid, project_name=name, data=data_str)

        db.add(alloc)

    db.commit()

    return {"message": "ok"}







@app.post("/api/performance/workday-list")

def get_workday_list(data: dict, db = Depends(get_db), current_user = Depends(auth.get_current_user)):

    assessment_id = data.get("assessment_id", 0)

    return crud.get_workday_records(db, assessment_id)



@app.get("/api/performance/workday-alloc/{project_id}")

def load_workday_alloc(project_id: int, db = Depends(get_db)):

    import json

    from models import ProjectWorkdayAlloc

    alloc = db.query(ProjectWorkdayAlloc).filter(ProjectWorkdayAlloc.project_id == project_id).first()

    if not alloc:

        return {"project_id": project_id, "data": {}}

    return {"project_id": project_id, "data": json.loads(alloc.data)}





@app.post("/api/performance/scores")

def submit_score(

    data: schemas.PerformanceScoreCreate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    score = crud.create_performance_score(db, data.model_dump(), current_user.id)

    return {"id": score.id, "message": "评分已提交"}





@app.get("/api/performance/scores")

def list_scores(

    assessment_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    return crud.get_scores_for_assessment(db, assessment_id)





@app.post("/api/performance/assessments/{assessment_id}/calculate")

def calculate_results(

    assessment_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    results = crud.calculate_assessment_results(db, assessment_id)

    if results is None:

        raise HTTPException(status_code=404, detail="考核不存在")

    return results





@app.get("/api/performance/assessments/{assessment_id}/results")

def get_results(

    assessment_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director", "deputy_director"]))

):

    return crud.calculate_assessment_results(db, assessment_id)


@app.get("/api/performance/leader-scores")
def get_leader_scores(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    import json
    from models import ProjectMemberScore, ProjectWorkdayAlloc, ProjectMember

    employees = db.query(models.User).filter(models.User.is_active == True, models.User.employee_id.isnot(None)).all()
    member_scores = db.query(ProjectMemberScore).all()
    allocs = db.query(ProjectWorkdayAlloc).all()
    project_members = db.query(ProjectMember).all()

    alloc_members_by_project = {}
    for alloc in allocs:
        try:
            data = json.loads(alloc.data)
            alloc_members_by_project[alloc.project_id] = data.get("members", [])
        except Exception:
            alloc_members_by_project[alloc.project_id] = []

    pm_map = {}
    for pm in project_members:
        pm_map[(pm.project_id, pm.employee_id, pm.role)] = pm.id

    result = []
    for emp in employees:
        emp_scores = [s for s in member_scores if s.target_employee_id == emp.employee_id]
        l_weighted_num = 0
        l_weighted_den = 0
        if emp_scores:
            emp_scores_by_project = {}
            for ms in emp_scores:
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

        leader_score = round(l_weighted_num / l_weighted_den, 2) if l_weighted_den > 0 else 0
        result.append({"user_id": emp.id, "employee_id": emp.employee_id, "name": emp.name, "leader_score": leader_score})

    return result











@app.put("/api/workload-records/{record_id}", response_model=schemas.WorkloadRecordResponse)

def update_workload(

    record_id: int,

    data: schemas.WorkloadRecordUpdate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    record = crud.update_workload_record(db, record_id, data.model_dump(exclude_unset=True))

    if not record:

        raise HTTPException(status_code=404, detail="记录不存在")

    return record









@app.post("/api/workload-records/dedup")

def dedup_workload(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.require_role(["director"]))

):

    deleted = crud.dedup_workload_records(db)

    return {"deleted": deleted}









@app.get("/api/performance/workday-requests")

def list_workday_reqs(db=Depends(get_db), current_user=Depends(auth.get_current_user)):

    role = auth.get_user_role(current_user)

    if role in ["director", "deputy_director"]:

        from sqlalchemy import func as _sf

        subq = db.query(

            models.WorkdayChangeRequest.user_id,

            models.WorkdayChangeRequest.project_name,

            _sf.max(models.WorkdayChangeRequest.id).label('max_id')

        ).group_by(

            models.WorkdayChangeRequest.user_id,

            models.WorkdayChangeRequest.project_name

        ).subquery()

        q = db.query(models.WorkdayChangeRequest).join(subq, 

            models.WorkdayChangeRequest.id == subq.c.max_id)

    else:

        q = db.query(models.WorkdayChangeRequest).filter(

            models.WorkdayChangeRequest.user_id == current_user.id)

    reqs = q.order_by(models.WorkdayChangeRequest.created_at.desc()).all()

    result = []

    for r in reqs:

        u = db.query(models.User).filter(models.User.id == r.user_id).first()

        result.append({"id": r.id, "user_name": u.name if u else "", "project_name": r.project_name,

            "A": r.A, "B": r.B, "C": r.C, "D": r.D, "E": r.E, "F": r.F,

            "status": r.status, "comment": r.comment or "", "created_at": r.created_at})

    return result



@app.post("/api/create-request")

def submit_workday_req(data: dict, db=Depends(get_db), current_user=Depends(auth.get_current_user)):

    existing = db.query(models.WorkdayChangeRequest).filter(

        models.WorkdayChangeRequest.user_id == current_user.id,

        models.WorkdayChangeRequest.project_name == data.get("project_name"),

        models.WorkdayChangeRequest.status == "pending"

    ).first()

    if existing:

        existing.A = data.get("A",0); existing.B = data.get("B",1); existing.C = data.get("C",1)

        existing.D = data.get("D",1); existing.E = data.get("E",1); existing.F = data.get("F",1)

        existing.created_at = datetime.utcnow()

        db.commit()

        return {"id": existing.id, "updated": True}

    req = models.WorkdayChangeRequest(

        user_id=current_user.id,

        assessment_id=data.get("assessment_id"),

        project_name=data.get("project_name"),

        A=data.get("A",0), B=data.get("B",1), C=data.get("C",1),

        D=data.get("D",1), E=data.get("E",1), F=data.get("F",1),

        status="pending")

    db.add(req); db.commit()

    return {"id": req.id}







async def list_workday_reqs(

    request: Request,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(auth.get_current_user)

):

    if request.method == "POST":

        import json as _j

        data = await request.json()

        req = models.WorkdayChangeRequest(

            user_id=current_user.id,

            assessment_id=data.get("assessment_id"),

            project_name=data.get("project_name"),

            A=data.get("A",0), B=data.get("B",1), C=data.get("C",1),

            D=data.get("D",1), E=data.get("E",1), F=data.get("F",1),

            status="pending")

        db.add(req); db.commit()

        return {"id": req.id}

    role = auth.get_user_role(current_user)

    q = db.query(models.WorkdayChangeRequest)

    if role not in ["director", "deputy_director"]:

        q = q.filter(models.WorkdayChangeRequest.user_id == current_user.id)

    reqs = q.order_by(models.WorkdayChangeRequest.created_at.desc()).all()

    result = []

    for r in reqs:

        u = db.query(models.User).filter(models.User.id == r.user_id).first()

        result.append({"id": r.id, "user_name": u.name if u else "", "project_name": r.project_name,

            "A": r.A, "B": r.B, "C": r.C, "D": r.D, "E": r.E, "F": r.F,

            "status": r.status, "comment": r.comment or "", "created_at": r.created_at})

    return result

@app.put("/api/performance/workday-requests/{req_id}/approve")

def approve_workday_req(req_id: int, data: dict, db=Depends(get_db),

    current_user=Depends(auth.require_role(["director","deputy_director"]))):

    req = db.query(models.WorkdayChangeRequest).filter(models.WorkdayChangeRequest.id == req_id).first()

    if not req: raise HTTPException(404, detail="not found")

    req.status = "approved"

    req.reviewer_id = current_user.id

    req.reviewed_at = datetime.utcnow()

    # Find WorkdayRecord by user_id + project_name + assessment_id

    rec = db.query(models.WorkdayRecord).filter(

        models.WorkdayRecord.user_id == req.user_id,

        models.WorkdayRecord.project_name == req.project_name,

        models.WorkdayRecord.assessment_id == req.assessment_id

    ).first()

    # If not found by assessment_id, try project_name + user_id only

    if not rec:

        rec = db.query(models.WorkdayRecord).filter(

            models.WorkdayRecord.user_id == req.user_id,

            models.WorkdayRecord.project_name == req.project_name

        ).first()

    if rec:

        rec.A = req.A; rec.B = req.B; rec.C = req.C

        rec.D = req.D; rec.E = req.E; rec.F = req.F

        rec.G = req.A * req.B * req.C * req.D * req.E * req.F

    else:

        rec = models.WorkdayRecord(

            assessment_id=req.assessment_id,

            user_id=req.user_id,

            project_name=req.project_name,

            project_type="",

            A=req.A, B=req.B, C=req.C, D=req.D, E=req.E, F=req.F,

            G=req.A * req.B * req.C * req.D * req.E * req.F,

            submitted_by=current_user.id

        )

        db.add(rec)

    db.commit()

    return {"message": "approved"} 





@app.put("/api/performance/workday-requests/{req_id}/reject")

def reject_workday_req(req_id: int, data: dict, db=Depends(get_db),

    current_user=Depends(auth.require_role(["director","deputy_director"]))):

    req = db.query(models.WorkdayChangeRequest).filter(models.WorkdayChangeRequest.id == req_id).first()

    if not req: raise HTTPException(404, detail="not found")

    req.status = "rejected"

    req.reviewer_id = current_user.id

    req.reviewed_at = datetime.utcnow()

    db.commit()

    return {"message": "rejected"}



_dist_path = _osp.join(_osp.dirname(_osp.abspath(__file__)), "..", "frontend", "dist")

if _osp.isdir(_dist_path):

    app.mount("/", StaticFiles(directory=_dist_path, html=True), name="frontend")

else:

    print("Frontend dist not found")



from fastapi.responses import FileResponse as _FR, JSONResponse as _JR

@app.exception_handler(404)

async def _spa_fallback(request, exc):

    _idx = _osp.join(_dist_path, "index.html")

    if _osp.exists(_idx):

        return _FR(_idx)

    return _JR({"detail": "Not Found"}, status_code=404)



# ====== 工天分配 API ======





    import json

    from models import ProjectWorkdayAlloc

    alloc = db.query(ProjectWorkdayAlloc).filter(ProjectWorkdayAlloc.project_id == project_id).first()

    if not alloc:

        return {"project_id": project_id, "data": {}}

    return {"project_id": project_id, "data": json.loads(alloc.data)}



@app.put("/api/performance/workday-alloc/{project_id}")

def handle_workday_alloc(project_id: int, body: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):

    import json

    from models import ProjectWorkdayAlloc

    data_str = json.dumps(body.get("data", {}), ensure_ascii=False)

    alloc = db.query(ProjectWorkdayAlloc).filter(ProjectWorkdayAlloc.project_id == project_id).first()

    if alloc:

        alloc.data = data_str

        alloc.updated_at = datetime.utcnow()

    else:

        proj = db.query(models.Project).filter(models.Project.id == project_id).first()

        name = proj.project_name if proj else ""

        alloc = ProjectWorkdayAlloc(project_id=project_id, project_name=name, data=data_str)

        db.add(alloc)

    db.commit()

    return {"message": "已保存"}











if __name__ == "__main__":

    uvicorn.run("main:app", host="0.0.0.0", port=8000)




