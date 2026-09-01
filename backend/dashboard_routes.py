from datetime import datetime
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
from auth import require_role
from database import get_db


router = APIRouter(prefix="/api/dashboard", tags=["数据看板"])

STATUS_LABELS = {
    "planning": "方案阶段",
    "in_progress": "进行中",
    "design": "设计阶段",
    "construction": "施工阶段",
    "completed": "已完工",
    "closed": "已结项",
    "stopped": "暂停",
}


def _workload_records(db: Session, year: int):
    return (
        db.query(models.WorkloadRecord)
        .filter(models.WorkloadRecord.year == str(year))
        .all()
    )


def _assessment_workdays(db: Session, year: int):
    return (
        db.query(models.WorkdayRecord)
        .join(models.PerformanceAssessment, models.WorkdayRecord.assessment_id == models.PerformanceAssessment.id)
        .filter(models.PerformanceAssessment.year == str(year))
        .all()
    )


@router.get("/overview")
def dashboard_overview(db: Session = Depends(get_db), _: models.User = Depends(require_role(["director", "deputy_director"]))):
    year = datetime.now().year
    projects = db.query(models.Project).all()
    staff_count = db.query(models.User).filter(models.User.is_active == True).count()
    year_workdays = round(sum(r.calculated_work_days or 0 for r in _workload_records(db, year)), 2)

    status_map = {}
    for p in projects:
        st = p.status or "planning"
        status_map[st] = status_map.get(st, 0) + 1

    return {
        "project_count": len(projects),
        "active_project_count": sum(
            1 for p in projects if (p.status or "planning") not in ("completed", "closed")
        ),
        "staff_count": int(staff_count or 0),
        "year_workdays": year_workdays,
        "status_distribution": [
            {"name": STATUS_LABELS.get(st, st), "value": v}
            for st, v in status_map.items()
        ],
    }


@router.get("/workdays")
def dashboard_workdays(
    year: int = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(["director", "deputy_director"])),
):
    year = year or datetime.now().year
    records = _workload_records(db, year)

    month_map = {}
    project_map = {}
    for r in records:
        workdays = r.calculated_work_days or 0
        if r.created_at:
            key = r.created_at.strftime("%Y-%m")
            month_map[key] = month_map.get(key, 0) + workdays
        pname = (r.project_name or "").strip()
        if pname:
            project_map[pname] = project_map.get(pname, 0) + workdays

    month_trend = []
    for month in range(1, 13):
        key = "%04d-%02d" % (year, month)
        month_trend.append({"month": key, "workdays": round(month_map.get(key, 0), 2)})

    project_distribution = sorted(
        ({"name": name, "value": round(value, 2)} for name, value in project_map.items() if value > 0),
        key=lambda x: -x["value"],
    )

    user_map = {}
    for r in _assessment_workdays(db, year):
        if r.user_id:
            user_map[r.user_id] = user_map.get(r.user_id, 0) + (r.G or 0)
    user_names = {u.id: u.name for u in db.query(models.User).all()}
    person_ranking = sorted(
        (
            {"name": user_names.get(uid, str(uid)), "workdays": round(value, 2)}
            for uid, value in user_map.items()
        ),
        key=lambda x: -x["workdays"],
    )[:10]

    if not person_ranking:
        alloc_person = {}
        for a in db.query(models.ProjectWorkdayAlloc).all():
            try:
                obj = json.loads(a.data or "{}")
            except Exception:
                continue
            for m in obj.get("members") or []:
                name = m.get("name")
                days = m.get("days") or 0
                if name:
                    alloc_person[name] = alloc_person.get(name, 0) + days
        person_ranking = sorted(
            (
                {"name": name, "workdays": round(value, 2)}
                for name, value in alloc_person.items()
            ),
            key=lambda x: -x["workdays"],
        )[:10]

    return {
        "month_trend": month_trend,
        "project_distribution": project_distribution,
        "person_ranking": person_ranking,
    }
