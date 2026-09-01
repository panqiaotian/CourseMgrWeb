#!/usr/bin/env python3
"""
添加测试课程报名数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import Session
from models import CourseEnrollment, Student
from datetime import date

def add_test_data():
    """添加测试课程报名数据"""
    db_session = Session()
    try:
        # 获取第一个学生
        student = db_session.query(Student).first()
        if not student:
            print("❌ 没有找到学生数据，请先添加学生")
            return
        
        print(f"找到学生: {student.name}")
        
        # 创建测试课程报名记录
        enrollment = CourseEnrollment(
            student_id=student.id,
            subject="数学",
            course_type="一对一",
            start_date=date.today(),
            end_date=date(2024, 12, 31),
            fee_per_lesson=100.0,
            total_lessons=20,
            total_fee=2000.0,
            remaining_fee=1500.0
        )
        
        db_session.add(enrollment)
        db_session.commit()
        
        print("✅ 测试课程报名记录添加成功")
        print(f"   学生: {student.name}")
        print(f"   科目: {enrollment.subject}")
        print(f"   课程类型: {enrollment.course_type}")
        print(f"   总费用: {enrollment.total_fee}")
        
        # 验证数据
        total = db_session.query(CourseEnrollment).count()
        print(f"✅ 当前课程报名记录总数: {total}")
        
    except Exception as e:
        db_session.rollback()
        print(f"❌ 添加测试数据失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    add_test_data()