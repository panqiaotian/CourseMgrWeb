#!/usr/bin/env python3
"""
初始化管理员安全设置脚本
用于设置默认管理员账户并要求首次登录时修改密码
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, User
from app import generate_password_hash, load_config

def init_admin_security():
    """初始化管理员安全设置"""
    
    # 获取数据库路径
    db_path = load_config()
    
    # 创建数据库连接
    engine = create_engine(f'sqlite:///{db_path}')
    
    # 确保所有表都存在
    Base.metadata.create_all(engine)
    
    # 创建会话
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 检查是否需要添加新字段（向后兼容）
        try:
            # 尝试查询新字段，如果失败说明需要添加
            session.execute(text("SELECT must_change_password FROM users LIMIT 1"))
            print("✓ 数据库字段已存在")
        except Exception:
            print("正在添加新的安全字段...")
            # 添加新字段
            session.execute(text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0"))
            session.execute(text("ALTER TABLE users ADD COLUMN password_changed_at DATE"))
            session.execute(text("ALTER TABLE users ADD COLUMN created_at DATE"))
            session.commit()
            print("✓ 安全字段添加成功")
        
        # 检查是否存在管理员账户
        admin_user = session.query(User).filter_by(username='admin').first()
        
        if not admin_user:
            # 创建默认管理员账户
            print("正在创建默认管理员账户...")
            admin_password = 'admin123'  # 默认密码
            admin_user = User(
                username='admin',
                password_hash=generate_password_hash(admin_password),
                role='admin',
                name='系统管理员',
                must_change_password=True,  # 要求首次登录修改密码
                created_at=datetime.now().date()
            )
            session.add(admin_user)
            session.commit()
            
            print("✓ 默认管理员账户创建成功")
            print(f"  用户名: admin")
            print(f"  默认密码: {admin_password}")
            print("  ⚠️  首次登录时将要求修改密码")
        else:
            # 检查现有管理员是否需要设置强制修改密码
            if not hasattr(admin_user, 'must_change_password') or admin_user.must_change_password is None:
                print("正在更新现有管理员账户安全设置...")
                admin_user.must_change_password = True
                admin_user.created_at = admin_user.created_at or datetime.now().date()
                session.commit()
                print("✓ 管理员账户安全设置更新成功")
            else:
                print("✓ 管理员账户已存在且安全设置正常")
        
        # 检查其他用户的安全设置
        users_without_security = session.query(User).filter(
            (User.must_change_password.is_(None)) | 
            (User.created_at.is_(None))
        ).all()
        
        if users_without_security:
            print(f"正在更新 {len(users_without_security)} 个用户的安全设置...")
            for user in users_without_security:
                if user.must_change_password is None:
                    user.must_change_password = False  # 现有用户不强制修改
                if user.created_at is None:
                    user.created_at = datetime.now().date()
            session.commit()
            print("✓ 用户安全设置更新完成")
        
        print("\n🔒 安全初始化完成！")
        print("=" * 50)
        print("安全功能说明：")
        print("1. 管理员首次登录时将被要求修改默认密码")
        print("2. 密码必须至少6位，包含字母和数字")
        print("3. 登录失败5次后IP将被锁定")
        print("4. 密码使用bcrypt加密存储")
        print("=" * 50)
        
    except Exception as e:
        session.rollback()
        print(f"❌ 初始化失败: {str(e)}")
        return False
    finally:
        session.close()
    
    return True

if __name__ == '__main__':
    print("课程管理系统 - 安全初始化")
    print("=" * 50)
    
    if init_admin_security():
        print("✅ 初始化成功！现在可以启动应用程序。")
        sys.exit(0)
    else:
        print("❌ 初始化失败！请检查错误信息。")
        sys.exit(1)