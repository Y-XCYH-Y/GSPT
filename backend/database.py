import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./building_institute.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMPLOYEES_DB_PATH = os.path.join(BASE_DIR, "employees.db")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_project_form_columns():
    """确保旧库中已存在新建项目表单新增字段对应的列。"""
    db_path = os.path.join(BASE_DIR, "building_institute.db")
    if not os.path.exists(db_path):
        return
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "projects" in tables:
            cols = {r[1] for r in cur.execute("PRAGMA table_info(projects)").fetchall()}
            if "work_rounds" not in cols:
                cur.execute("ALTER TABLE projects ADD COLUMN work_rounds INTEGER DEFAULT 1")
            if "round_reason" not in cols:
                cur.execute("ALTER TABLE projects ADD COLUMN round_reason TEXT")
        if "project_requests" in tables:
            cols = {r[1] for r in cur.execute("PRAGMA table_info(project_requests)").fetchall()}
            if "description" not in cols:
                cur.execute("ALTER TABLE project_requests ADD COLUMN description TEXT")
            if "drawing_list" not in cols:
                cur.execute("ALTER TABLE project_requests ADD COLUMN drawing_list TEXT DEFAULT '[]'")
            if "work_rounds" not in cols:
                cur.execute("ALTER TABLE project_requests ADD COLUMN work_rounds INTEGER DEFAULT 1")
            if "round_reason" not in cols:
                cur.execute("ALTER TABLE project_requests ADD COLUMN round_reason TEXT")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"项目字段迁移失败: {e}")


_migrate_project_form_columns()
