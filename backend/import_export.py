import pandas as pd
from io import BytesIO
from sqlalchemy.orm import Session
from datetime import datetime
import models
from auth import get_password_hash

# Excel 模板字段
TEMPLATE_COLUMNS = [
    "人员编号",
    "姓名", "性别", "专业方向", "注册情况", "职称情况",
    "出生年月", "参加工作时间", "擅长项目类型", "历史项目经验",
    "是否驻外", "备注", "备注", "备注"
]

PROJECT_TYPES = ["站房", "枢纽", "大铁", "轨交", "民建", "改造", "援外", "BIM", "方案", "建模", "咨询", "总包"]
POSITION_LEVELS = ["一级总体", "二级总体", "一级设计人", "二级设计人", "三级设计人"]
PROFESSIONS = ["建筑", "结构", "给排水", "暖通", "电气", "规划", "景观", "室内", "概预算"]
LOAD_STATUSES = ["空闲","轻量","适中","饱满","超负荷","休假"]


def generate_template():
    """生成 Excel 模板"""
    output = BytesIO()
    
    # 创建模板 DataFrame
    df_template = pd.DataFrame(columns=TEMPLATE_COLUMNS)
    
    # 添加示例数据
    df_template.loc[0] = [
        "001",
        "张三", "男", "建筑", "一级注册建筑师", "高级工程师",
        "1985-03", "2010-07", "站房、枢纽", "参与过XX高铁站房设计，担任专业负责人",
        "否", "70%", "一级总体", "0.7", ""
    ]
    
    # 创建 Excel 文件
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 数据模板 sheet
        df_template.to_excel(writer, sheet_name='人员信息', index=False)
        
        # 下拉选项 sheet
        options_data = {
            "专业方向": PROFESSIONS,
            "擅长项目类型": PROJECT_TYPES,
            "备注": LOAD_STATUSES,
            "性别": ["男", "女"],
            "是否驻外": ["是", "否"]
        }
        
        # 填充选项
        max_len = max(len(v) for v in options_data.values())
        options_df = pd.DataFrame({k: v + [''] * (max_len - len(v)) for k, v in options_data.items()})
        options_df.to_excel(writer, sheet_name='下拉选项参考', index=False)
        
        # 获取工作表，设置列宽
        ws = writer.sheets['人员信息']
        for i, col in enumerate(TEMPLATE_COLUMNS, 1):
            ws.column_dimensions[chr(64 + i)].width = 18
    
    output.seek(0)
    return output


def import_from_excel(file_content: bytes, db: Session):
    """从 Excel 导入员工数据"""
    # 清空旧数据，重新导入以保证数据一致性
    # 保留管理员账号不删除
    # 排除管理员账号不删除
    db.query(models.User).filter(models.User.username != "admin").delete(synchronize_session=False)
    db.commit()
    # 确保导入后管理员账号仍存在
    admin_exists = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin_exists:
        import auth as _auth
        _admin = models.User(
            username="admin",
            password_hash=_auth.get_password_hash("admin123"),
            name="管理员",
            role="director",
            department="建筑一所",
            is_active=True
        )
        db.add(_admin)
        db.commit()
    # 读取第一个 sheet（兼容不同命名）
    df = pd.read_excel(BytesIO(file_content), sheet_name=0)
    
    results = {"created": 0, "updated": 0, "failed": 0, "errors": []}
    used_usernames = set()
    
    for index, row in df.iterrows():
        try:
            name = str(row.get("姓名", "")).strip()
            if not name or name == "nan":
                continue
            
            # 生成用户名
            username = generate_username(name, db, used_usernames)
            
            # 安全获取字段值
            def safe_str(value, default=""):
                if value is None or (isinstance(value, float) and pd.isna(value)):
                    return default
                return str(value).strip()
            
            employee_id = safe_str(row.get("人员编号", ""))
            user = models.User(
                username=username,
                password_hash=get_password_hash("123456"),
                name=name,
                employee_id=employee_id,
                gender=safe_str(row.get("性别", "")),
                profession=safe_str(row.get("专业方向", "")),
                registration=safe_str(row.get("注册情况", "")),
                title=safe_str(row.get("职称情况", "")),
                birth_date=safe_str(row.get("出生年月", "")),
                work_start_date=safe_str(row.get("参加工作时间", "")),
                project_types=parse_project_types(safe_str(row.get("擅长项目类型", ""))),
                experience=safe_str(row.get("历史项目经验", "")),
                is_field=safe_str(row.get("是否驻外", "否")),
                remark=safe_str(row.get("备注", "")),
                role="member",
                department="建筑一所"
            )
            db.add(user)
            results["created"] += 1
            
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"第{index+2}行: {str(e)}")
    
    print('=== BEFORE COMMIT ===')
    db.commit()
    print('=== AFTER COMMIT ===')
    return results


def export_to_excel(db: Session):
    """导出所有员工数据为 Excel"""
    users = db.query(models.User).filter(models.User.is_active == True).all()
    
    data = []
    for user in users:
        data.append({
            "人员编号": user.employee_id or "",
            "姓名": user.name or "",
            "性别": user.gender or "",
            "专业方向": user.profession or "",
            "注册情况": user.registration or "",
            "职称情况": user.title or "",
            "出生年月": user.birth_date or "",
            "参加工作时间": user.work_start_date or "",
            "擅长项目类型": "、".join(user.project_types) if user.project_types else "",
            "历史项目经验": user.experience or "",
            "是否驻外": user.is_field or "否",
            "备注": user.remark or ""
        })
    
    df = pd.DataFrame(data, columns=TEMPLATE_COLUMNS)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='人员信息', index=False)
        ws = writer.sheets['人员信息']
        for i, col in enumerate(TEMPLATE_COLUMNS, 1):
            ws.column_dimensions[chr(64 + i)].width = 18
    
    output.seek(0)
    return output


def generate_username(name: str, db: Session, used: set = None) -> str:
    """生成不重复的用户名"""
    base = name.lower().replace(' ', '_').replace('　', '_')
    if not base:
        base = "user"
    
    import re
    base = re.sub(r'[^a-z0-9_]', '', base)
    if not base:
        base = "user"
    
    username = base
    count = 1
    while db.query(models.User).filter(models.User.username == username).first() or (used is not None and username in used):
        username = f"{base}{count}"
        count += 1
    
    if used is not None:
        used.add(username)
    return username


def parse_project_types(text: str) -> list:
    """解析擅长项目类型"""
    if not text or text == "nan":
        return []
    text = text.replace("、", ",").replace("；", ",").replace("，", ",").replace(" ", ",")
    types = [t.strip() for t in text.split(",") if t.strip()]
    valid_types = [t for t in types if t not in ["nan", "None", ""]]
    return valid_types


def parse_float(value) -> float:
    """safe convert to float"""
    try:
        if value is None:
            return 0.0
        if isinstance(value, str):
            value = value.strip().replace('%', '')
            if not value or value == "nan":
                return 0.0
            return float(value)
        import math
        if math.isnan(value):
            return 0.0
        return float(value)
    except:
        return 0.0

# data cleaning for import
def clean_field_value(field, value):
    v = str(value).strip()
    if field == 'is_field':
        if v.startswith('是'):
            return '是'
        if v.startswith('否'):
            return '否'
        return '否'
    
def import_workload_from_excel(file_content, db):
    import pandas as pd
    import models
    from io import BytesIO
    from datetime import datetime as dt
    df = pd.read_excel(BytesIO(file_content), sheet_name=0)
    results = {"created": 0, "updated": 0, "failed": 0, "errors": []}

    # Helper: fill a field from file data only when the file has a meaningful value
    def _val(data, key, raw, default=""):
        if raw is None or (isinstance(raw, float) and str(raw) == "nan"):
            return default
        v = str(raw).strip()
        if v == "":
            return default
        data[key] = v

    headers = [str(h).strip() for h in df.columns]

    def _find_col(name):
        for i, h in enumerate(headers):
            if h == name:
                return i
        return -1

    new_mode = _find_col("项目编号") >= 0

    if new_mode:
        def _cell(row, name, default=""):
            i = _find_col(name)
            if i < 0 or i >= len(row):
                return default
            v = row[i]
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return default
            s = str(v).strip()
            return s if s and s.lower() != "nan" else default

        def _parse_float(s):
            try:
                return float(s)
            except Exception:
                return 0

        def _parse_date(s):
            if not s:
                return None
            try:
                from datetime import datetime as _dt
                return _dt.strptime(str(s)[:10], "%Y-%m-%d").date()
            except Exception:
                return None

        def _parse_area(s):
            import re
            m = re.search(r"[\d.]+", s or "")
            return float(m.group()) if m else 0

        def _split_names(s):
            if not s:
                return []
            return [x.strip() for x in s.replace("、", ",").replace("，", ",").replace("；", ",").replace(";", ",").split(",") if x.strip()]

        role_cols = ["设计", "复核", "专业负责人", "院审", "总体审核", "集团审核"]
        for idx, row in df.iterrows():
            try:
                code = _cell(row, "项目编号")
                if not code:
                    continue
                project_type = _cell(row, "项目类型")
                scale = _cell(row, "规模")
                stage = _cell(row, "阶段")
                start_date = _parse_date(_cell(row, "开始日期"))
                end_date = _parse_date(_cell(row, "预计结束"))
                planned_days = _parse_float(_cell(row, "计划工天", "0"))
                lead = _cell(row, "项目负责人")
                participants = "、".join([x for x in [_cell(row, c) for c in role_cols] if x])

                existing = db.query(models.WorkloadRecord).filter(models.WorkloadRecord.project_code == code).first()
                if existing:
                    existing.project_code = code
                    if not existing.project_name:
                        existing.project_name = code
                    if project_type:
                        existing.project_type = project_type
                    if scale:
                        existing.scale = scale
                    if stage:
                        existing.stage = stage
                    if lead:
                        existing.overall_lead = lead
                    if participants:
                        existing.participants = participants
                    if planned_days:
                        existing.calculated_work_days = planned_days
                    results["updated"] += 1
                else:
                    rec = models.WorkloadRecord(
                        project_code=code,
                        project_name=code,
                        project_type=project_type,
                        scale=scale,
                        stage=stage,
                        overall_lead=lead,
                        participants=participants,
                        calculated_work_days=planned_days,
                        year=str(dt.utcnow().year)
                    )
                    db.add(rec)
                    results["created"] += 1

                project = db.query(models.Project).filter(models.Project.project_code == code).first()
                if not project:
                    project = models.Project(
                        project_code=code,
                        project_name=code,
                        project_type=project_type or "其它",
                        area=_parse_area(scale),
                        start_date=start_date,
                        planned_end_date=end_date,
                        planned_man_days=planned_days,
                        current_stage=stage,
                        created_by=1
                    )
                    db.add(project)
                    db.flush()
                else:
                    if project_type:
                        project.project_type = project_type
                    if start_date:
                        project.start_date = start_date
                    if end_date:
                        project.planned_end_date = end_date
                    if planned_days:
                        project.planned_man_days = planned_days
                    if stage:
                        project.current_stage = stage

                for role_col in role_cols:
                    names = _split_names(_cell(row, role_col))
                    for name in names:
                        exists = db.query(models.ProjectMember).filter(
                            models.ProjectMember.project_id == project.id,
                            models.ProjectMember.employee_id == name,
                            models.ProjectMember.role == role_col
                        ).first()
                        if not exists:
                            db.add(models.ProjectMember(
                                project_id=project.id,
                                employee_id=name,
                                employee_name=name,
                                department="",
                                role=role_col
                            ))
            except Exception as e:
                results["failed"] += 1
                results["errors"].append("Row " + str(idx + 2) + ": " + str(e))
        from crud import sync_all_projects_to_workload
        sync_all_projects_to_workload(db)
        return results

    for idx, row in df.iterrows():
        try:
            code_val = row.iloc[1] if len(row) > 1 else None
            if code_val is None or (isinstance(code_val, float) and str(code_val) == "nan"):
                continue
            code = str(code_val).strip()

            project_name = ""
            if not pd.isna(row.iloc[2]):
                project_name = str(row.iloc[2]).strip()

            # Check if the project already exists: match by project_code first,
            # since the same project_code means the same project
            existing = None
            if code:
                existing = db.query(models.WorkloadRecord).filter(models.WorkloadRecord.project_code == code).first()
            if existing is None and project_name:
                existing = db.query(models.WorkloadRecord).filter(models.WorkloadRecord.project_name == project_name).first()

            if existing:
                # Update existing record with non-empty file values
                if not pd.isna(row.iloc[0]):
                    existing.sequence = int(row.iloc[0])
                if code:
                    existing.project_code = code
                if project_name:
                    existing.project_name = project_name
                _val(existing, "project_type", row.iloc[3] if len(row) > 3 else None)
                _val(existing, "scale", row.iloc[4] if len(row) > 4 else None)
                _val(existing, "overall_lead", row.iloc[5] if len(row) > 5 else None)
                _val(existing, "architecture_lead", row.iloc[6] if len(row) > 6 else None)
                if len(row) > 7 and not pd.isna(row.iloc[7]):
                    existing.calculated_work_days = float(row.iloc[7])
                _val(existing, "stage", row.iloc[8] if len(row) > 8 else None)
                if len(row) > 12 and not pd.isna(row.iloc[12]):
                    existing.participants = str(row.iloc[12]).strip()
                if len(row) > 13 and not pd.isna(row.iloc[13]):
                    existing.specific_work = str(row.iloc[13]).strip()
                if len(row) > 14 and not pd.isna(row.iloc[14]):
                    existing.actual_work_days_architecture = float(row.iloc[14])
                if len(row) > 15 and not pd.isna(row.iloc[15]):
                    existing.actual_work_days_structure = float(row.iloc[15])
                if len(row) > 16 and not pd.isna(row.iloc[16]):
                    existing.actual_work_days_other = float(row.iloc[16])
                if len(row) > 17 and not pd.isna(row.iloc[17]):
                    existing.actual_duration_days = float(row.iloc[17])
                _val(existing, "quality_grade", row.iloc[18] if len(row) > 18 else None)
                _val(existing, "year", row.iloc[19] if len(row) > 19 else None)
                _val(existing, "remark", row.iloc[20] if len(row) > 20 else None)
                results["updated"] += 1
            else:
                # Create a new record
                data = {}
                data["sequence"] = int(row.iloc[0]) if not pd.isna(row.iloc[0]) else None
                data["project_code"] = code
                data["project_name"] = project_name
                data["project_type"] = str(row.iloc[3]).strip() if len(row) > 3 and not pd.isna(row.iloc[3]) else ""
                data["scale"] = str(row.iloc[4]).strip() if len(row) > 4 and not pd.isna(row.iloc[4]) else ""
                data["overall_lead"] = str(row.iloc[5]).strip() if len(row) > 5 and not pd.isna(row.iloc[5]) else ""
                data["architecture_lead"] = str(row.iloc[6]).strip() if len(row) > 6 and not pd.isna(row.iloc[6]) else ""
                data["calculated_work_days"] = float(row.iloc[7]) if len(row) > 7 and not pd.isna(row.iloc[7]) else 0
                data["stage"] = str(row.iloc[8]).strip() if len(row) > 8 and not pd.isna(row.iloc[8]) else ""
                data["participants"] = str(row.iloc[12]).strip() if len(row) > 12 and not pd.isna(row.iloc[12]) else ""
                data["specific_work"] = str(row.iloc[13]).strip() if len(row) > 13 and not pd.isna(row.iloc[13]) else ""
                data["actual_work_days_architecture"] = float(row.iloc[14]) if len(row) > 14 and not pd.isna(row.iloc[14]) else 0
                data["actual_work_days_structure"] = float(row.iloc[15]) if len(row) > 15 and not pd.isna(row.iloc[15]) else 0
                data["actual_work_days_other"] = float(row.iloc[16]) if len(row) > 16 and not pd.isna(row.iloc[16]) else 0
                data["actual_duration_days"] = float(row.iloc[17]) if len(row) > 17 and not pd.isna(row.iloc[17]) else 0
                data["quality_grade"] = str(row.iloc[18]).strip() if len(row) > 18 and not pd.isna(row.iloc[18]) else ""
                data["year"] = str(row.iloc[19]).strip() if len(row) > 19 and not pd.isna(row.iloc[19]) else ""
                data["remark"] = str(row.iloc[20]).strip() if len(row) > 20 and not pd.isna(row.iloc[20]) else ""

                rec = models.WorkloadRecord(**data)
                db.add(rec)
                results["created"] += 1

        except Exception as e:
            results["failed"] += 1
            results["errors"].append("Row " + str(idx + 2) + ": " + str(e))

    db.commit()
    return results


def generate_workload_template():
    """生成项目库 Excel 导入模板"""
    import pandas as pd
    from io import BytesIO
    output = BytesIO()
    columns = [
        "项目编号", "项目类型", "规模", "阶段", "开始日期", "预计结束", "计划工天", "项目负责人",
        "设计", "复核", "专业负责人", "院审", "总体审核", "集团审核"
    ]
    df = pd.DataFrame(columns=columns)
    df.loc[0] = [
        "DT2026-001-01", "大铁", "50000㎡", "初步设计", "2026-01-01", "2026-12-31", "120", "张三",
        "李四、王五", "赵六", "孙七", "", "", ""
    ]
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='项目库', index=False)
    output.seek(0)
    return output
