"""
能力模块实现 - 7项 SKILL
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
import models
from datetime import datetime, date
from typing import List, Dict, Any

class SkillEngine:
    
    def __init__(self, db: Session):
        self.db = db
    
    # 1. 工作量评估
    def estimate_workload(self, project_type: str, area: float, stage: str) -> Dict[str, Any]:
        """按项目类型/规模/阶段估算所需人天"""
        # 工作量估算系数（可配置）
        coefficients = {
            "站房配套房屋": {"planning": 0.015, "design": 0.03, "construction": 0.02},
            "住宅": {"planning": 0.01, "design": 0.025, "construction": 0.015},
            "商业综合体": {"planning": 0.02, "design": 0.04, "construction": 0.03},
            "工业厂房": {"planning": 0.012, "design": 0.028, "construction": 0.018},
        }
        
        coeff = coefficients.get(project_type, {}).get(stage, 0.02)
        estimated_days = area * coeff
        
        # 建议团队规模
        if estimated_days < 30:
            team_size = "1-2人"
            duration = f"{estimated_days:.0f}天"
        elif estimated_days < 60:
            team_size = "2-3人"
            duration = f"{estimated_days/2:.0f}天"
        else:
            team_size = "3-5人"
            duration = f"{estimated_days/3:.0f}天"
        
        return {
            "estimated_man_days": round(estimated_days, 1),
            "suggested_team_size": team_size,
            "estimated_duration": duration,
            "coefficient_used": coeff,
            "stage": stage,
            "project_type": project_type,
            "area": area
        }
    
    # 2. 人员任务分配
    def assign_personnel(self, project_id: int) -> Dict[str, Any]:
        """基于人员技能矩阵智能匹配并分配任务"""
        project = self.db.query(models.Project).filter(models.Project.id == project_id).first()
        if not project:
            return {"error": "项目不存在"}
        
        # 获取所有可用人员及其技能矩阵
        available_users = self.db.query(models.User).filter(
            models.User.is_active == True
        ).all()
        
        assignments = []
        for user in available_users:
            skill = self.db.query(models.SkillMatrix).filter(
                models.SkillMatrix.user_id == user.id
            ).first()
            
            if skill and skill.current_workload < skill.max_workload:
                utilization = (skill.current_workload / skill.max_workload * 100) if skill.max_workload > 0 else 0
                assignments.append({
                    "user_id": user.id,
                    "name": user.name,
                    "rating": skill.rating,
                    "utilization": round(utilization, 1),
                    "available_capacity": round(skill.max_workload - skill.current_workload, 2),
                    "skills": skill.skills,
                    "specialties": skill.specialties
                })
        
        # 按能力评级和可用容量排序
        assignments.sort(key=lambda x: (x["rating"], x["available_capacity"]), reverse=True)
        
        return {
            "project_id": project_id,
            "project_name": project.project_name,
            "suggested_assignments": assignments[:5],  # 推荐前5名
            "total_candidates": len(assignments)
        }
    
    # 3. 进度跟踪预警
    def check_progress_alerts(self) -> Dict[str, Any]:
        """比对计划与实际，红/黄/绿三级延期预警"""
        projects = self.db.query(models.Project).filter(
            models.Project.status.in_(["planning", "design", "construction"])
        ).all()
        
        alerts = {"red": [], "yellow": [], "green": []}
        
        for project in projects:
            tasks = self.db.query(models.Task).filter(
                models.Task.project_id == project.id,
                models.Task.status != "completed"
            ).all()
            
            delayed_tasks = []
            for task in tasks:
                if task.end_date and task.end_date < date.today() and task.progress < 100:
                    days_delayed = (date.today() - task.end_date).days
                    delayed_tasks.append({
                        "task_id": task.id,
                        "task_name": task.task_name,
                        "days_delayed": days_delayed,
                        "progress": task.progress
                    })
            
            total_tasks = len(tasks)
            delayed_count = len(delayed_tasks)
            
            if total_tasks > 0:
                delay_ratio = delayed_count / total_tasks
                if delay_ratio > 0.3:
                    alert_level = "red"
                elif delay_ratio > 0.1 or delayed_count > 0:
                    alert_level = "yellow"
                else:
                    alert_level = "green"
            else:
                alert_level = "green"
            
            alert_info = {
                "project_id": project.id,
                "project_name": project.project_name,
                "status": project.status,
                "total_tasks": total_tasks,
                "delayed_tasks": delayed_count,
                "delay_ratio": round(delayed_count/total_tasks*100, 1) if total_tasks > 0 else 0,
                "delayed_details": delayed_tasks
            }
            
            alerts[alert_level].append(alert_info)
            
            # 更新项目预警级别
            if alert_level == "red":
                project.alert_level = models.AlertLevel.RED
            elif alert_level == "yellow":
                project.alert_level = models.AlertLevel.YELLOW
            else:
                project.alert_level = models.AlertLevel.GREEN
        
        self.db.commit()
        
        return {
            "summary": {
                "red_count": len(alerts["red"]),
                "yellow_count": len(alerts["yellow"]),
                "green_count": len(alerts["green"])
            },
            "alerts": alerts
        }
    
    # 4. 资源调配建议
    def resource_allocation_suggestion(self) -> Dict[str, Any]:
        """多项目冲突时给出最优人员调配方案"""
        # 获取所有进行中的项目
        active_projects = self.db.query(models.Project).filter(
            models.Project.status.in_(["planning", "design", "construction"])
        ).all()
        
        # 获取人员负荷
        users = self.db.query(models.User).filter(models.User.is_active == True).all()
        workload_data = []
        
        for user in users:
            skill = self.db.query(models.SkillMatrix).filter(
                models.SkillMatrix.user_id == user.id
            ).first()
            
            assigned_tasks = self.db.query(models.Task).filter(
                models.Task.assigned_to == user.id,
                models.Task.status != "completed"
            ).count()
            
            workload_data.append({
                "user_id": user.id,
                "name": user.name,
                "current_workload": skill.current_workload if skill else 0,
                "max_workload": skill.max_workload if skill else 1,
                "active_tasks": assigned_tasks,
                "utilization": round(skill.current_workload/skill.max_workload*100, 1) if skill and skill.max_workload > 0 else 0
            })
        
        # 找出过载和空闲人员
        overloaded = [w for w in workload_data if w["utilization"] > 80]
        available = [w for w in workload_data if w["utilization"] < 50]
        
        suggestions = []
        if overloaded and available:
            for over in overloaded[:3]:
                best_match = min(available, key=lambda x: abs(50 - x["utilization"]))
                suggestions.append({
                    "from_user": over["name"],
                    "from_utilization": over["utilization"],
                    "to_user": best_match["name"],
                    "to_utilization": best_match["utilization"],
                    "suggestion": f"建议将 {over['name']} 的部分任务调配给 {best_match['name']}"
                })
        
        return {
            "total_active_projects": len(active_projects),
            "workload_overview": workload_data,
            "overloaded_personnel": overloaded,
            "available_personnel": available,
            "reallocation_suggestions": suggestions
        }
    
    # 5. 工作量统计
    def workload_statistics(self, period_start: date = None, period_end: date = None) -> Dict[str, Any]:
        """汇总实际投入人天，偏差分析与负荷分布"""
        if not period_start:
            period_start = date.today().replace(day=1)
        if not period_end:
            period_end = date.today()
        
        # 项目维度统计
        projects = self.db.query(models.Project).all()
        project_stats = []
        total_planned = 0
        total_actual = 0
        
        for project in projects:
            planned = project.planned_man_days or 0
            actual = project.actual_man_days or 0
            deviation = actual - planned
            deviation_pct = (deviation / planned * 100) if planned > 0 else 0
            
            project_stats.append({
                "project_name": project.project_name,
                "planned_days": planned,
                "actual_days": actual,
                "deviation": round(deviation, 1),
                "deviation_pct": round(deviation_pct, 1),
                "status": project.status
            })
            total_planned += planned
            total_actual += actual
        
        # 人员维度统计
        users = self.db.query(models.User).filter(models.User.is_active == True).all()
        user_stats = []
        
        for user in users:
            skill = self.db.query(models.SkillMatrix).filter(
                models.SkillMatrix.user_id == user.id
            ).first()
            
            active_tasks = self.db.query(models.Task).filter(
                models.Task.assigned_to == user.id,
                models.Task.status == "in_progress"
            ).count()
            
            user_stats.append({
                "name": user.name,
                "current_load": skill.current_workload if skill else 0,
                "max_load": skill.max_workload if skill else 1,
                "active_tasks": active_tasks,
                "rating": skill.rating if skill else 0
            })
        
        return {
            "period": f"{period_start} ~ {period_end}",
            "total_planned_man_days": round(total_planned, 1),
            "total_actual_man_days": round(total_actual, 1),
            "overall_deviation": round(total_actual - total_planned, 1),
            "project_stats": project_stats,
            "user_workload_distribution": user_stats
        }
    
    # 6. 项目复盘
    def project_review(self, project_id: int) -> Dict[str, Any]:
        """收尾对比计划与实际，沉淀经验回灌知识库"""
        project = self.db.query(models.Project).filter(models.Project.id == project_id).first()
        if not project:
            return {"error": "项目不存在"}
        
        tasks = self.db.query(models.Task).filter(models.Task.project_id == project_id).all()
        
        # 任务完成分析
        total_tasks = len(tasks)
        completed_tasks = [t for t in tasks if t.status == "completed"]
        delayed_tasks = [t for t in tasks if t.end_date and t.end_date < date.today() and t.progress < 100]
        
        # 时间偏差分析
        planned_days = project.planned_man_days or 0
        actual_days = project.actual_man_days or 0
        
        # 经验总结
        lessons = []
        if actual_days > planned_days * 1.2:
            lessons.append("工作量预估偏保守，建议后续类似项目上调15-20%估算")
        if len(delayed_tasks) > total_tasks * 0.2:
            lessons.append("延期任务较多，建议加强过程管控和里程碑检查")
        if completed_tasks:
            avg_actual = sum(t.actual_days for t in completed_tasks) / len(completed_tasks)
            avg_estimated = sum(t.estimated_days for t in completed_tasks) / len(completed_tasks)
            if avg_actual > avg_estimated:
                lessons.append(f"任务平均超时{(avg_actual-avg_estimated):.1f}天，建议优化任务拆分粒度")
        
        return {
            "project_name": project.project_name,
            "status": project.status,
            "planned_man_days": planned_days,
            "actual_man_days": actual_days,
            "deviation": round(actual_days - planned_days, 1),
            "deviation_pct": round((actual_days-planned_days)/planned_days*100, 1) if planned_days > 0 else 0,
            "task_completion_rate": round(len(completed_tasks)/total_tasks*100, 1) if total_tasks > 0 else 0,
            "delayed_task_count": len(delayed_tasks),
            "lessons_learned": lessons,
            "knowledge_base_suggestions": lessons  # 可回灌知识库
        }
    
    # 7. 项目质量评定
    def quality_assessment(self, project_id: int) -> Dict[str, Any]:
        """按标准做质量等级评定与红线识别"""
        project = self.db.query(models.Project).filter(models.Project.id == project_id).first()
        if not project:
            return {"error": "项目不存在"}
        
        # 获取质量标准
        standards = self.db.query(models.QualityStandard).all()
        
        if not standards:
            # 默认标准
            default_standards = [
                {"category": "设计规范", "weight": 30, "pass_score": 60},
                {"category": "进度控制", "weight": 25, "pass_score": 60},
                {"category": "成本控制", "weight": 20, "pass_score": 60},
                {"category": "安全管理", "weight": 15, "pass_score": 70},
                {"category": "文档完整性", "weight": 10, "pass_score": 60},
            ]
        else:
            default_standards = [
                {"category": s.category, "weight": s.weight, "pass_score": s.pass_score}
                for s in standards
            ]
        
        # 模拟评定（实际应接入评定系统）
        assessment_details = []
        red_lines = []
        total_score = 0
        
        for std in default_standards:
            # 基于项目数据模拟评分
            if std["category"] == "进度控制":
                delay_pct = ((project.actual_man_days - project.planned_man_days) / project.planned_man_days * 100) if project.planned_man_days > 0 else 0
                score = max(30, 100 - delay_pct)
            elif std["category"] == "设计规范":
                score = 85  # 模拟值
            elif std["category"] == "成本控制":
                score = 78
            elif std["category"] == "安全管理":
                score = 90
            else:
                score = 75
            
            weighted_score = score * std["weight"] / 100
            total_score += weighted_score
            
            assessment_details.append({
                "category": std["category"],
                "score": round(score, 1),
                "weight": std["weight"],
                "weighted_score": round(weighted_score, 1),
                "pass": score >= std["pass_score"]
            })
            
            if score < std["pass_score"]:
                red_lines.append(f"{std['category']}不达标(得分{score:.0f}, 及格线{std['pass_score']})")
        
        # 等级评定
        if total_score >= 90:
            grade = "A"
        elif total_score >= 75:
            grade = "B"
        elif total_score >= 60:
            grade = "C"
        else:
            grade = "D"
        
        return {
            "project_name": project.project_name,
            "overall_score": round(total_score, 1),
            "grade": grade,
            "assessment_details": assessment_details,
            "red_line_violations": red_lines,
            "pass": grade != "D",
            "recommendation": "建议通过验收" if grade in ["A", "B"] else "需要整改后重新评定" if grade == "C" else "严重不达标，需全面整改"
        }