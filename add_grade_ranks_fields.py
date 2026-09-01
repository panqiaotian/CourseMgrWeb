#!/usr/bin/env python3
"""
添加年级排名和班级排名字段脚本
用于在student_scores表中添加grade_rank和class_rank字段
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base
from app import load_config

def add_grade_ranks_fields():
    """添加年级排名和班级排名字段"""
    
    # 获取数据库路径
    config = load_config()
    db_path = config.get("database_path", "./data/course.db")
    
    # 创建数据库连接（使用与主应用相同的配置）
    engine = create_engine(
        f'sqlite:///{db_path}',
        connect_args={'check_same_thread': False},
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )
    
    # 确保所有表都存在
    Base.metadata.create_all(engine)
    
    # 创建会话
    SessionFactory = sessionmaker(bind=engine)
    session = scoped_session(SessionFactory)()
    
    try:
        # 检查是否需要添加新字段（向后兼容）
        try:
            # 尝试查询新字段，如果失败说明需要添加
            session.execute(text("SELECT grade_rank FROM student_scores LIMIT 1"))
            print("✓ grade_rank字段已存在")
        except Exception:
            print("正在添加grade_rank字段...")
            # 添加新字段
            session.execute(text("ALTER TABLE student_scores ADD COLUMN grade_rank VARCHAR(50)"))
            session.commit()
            print("✓ grade_rank字段添加成功")
        
        try:
            # 尝试查询新字段，如果失败说明需要添加
            session.execute(text("SELECT class_rank FROM student_scores LIMIT 1"))
            print("✓ class_rank字段已存在")
        except Exception:
            print("正在添加class_rank字段...")
            # 添加新字段
            session.execute(text("ALTER TABLE student_scores ADD COLUMN class_rank VARCHAR(50)"))
            session.commit()
            print("✓ class_rank字段添加成功")
        
        print("\n✅ 年级排名和班级排名字段添加完成！")
        print("=" * 50)
        print("新增字段说明：")
        print("1. grade_rank: 年级排名（手动录入）")
        print("2. class_rank: 班级排名（手动录入）")
        print("=" * 50)
        
    except Exception as e:
        session.rollback()
        print(f"❌ 添加字段失败: {str(e)}")
        return False
    finally:
        session.close()
    
    return True

if __name__ == '__main__':
    print("课程管理系统 - 添加年级排名和班级排名字段")
    print("=" * 50)
    
    if add_grade_ranks_fields():
        print("✅ 字段添加成功！现在可以启动应用程序。")
        sys.exit(0)
    else:
        print("❌ 字段添加失败！请检查错误信息。")
        sys.exit(1)