"""
迁移脚本：为 students 表添加 student_type 和 enrollment_status 字段
- 新增列，默认值分别为 '应届' 和 '在学'
- 已有数据自动填充默认值，不会被修改
"""
import sqlite3
import json
import os

def migrate():
    # 读取数据库路径
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    db_path = os.path.join(os.path.dirname(__file__), config.get('database_path', './data/course.db'))

    print(f"连接数据库: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 检查是否已有该列
    cursor.execute("PRAGMA table_info(students)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"当前列: {columns}")

    changes = []

    if 'student_type' not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN student_type TEXT DEFAULT '应届'")
        changes.append("添加 student_type 列 (默认: 应届)")
        print("✓ 添加 student_type 列")
    else:
        print("- student_type 列已存在，跳过")

    if 'enrollment_status' not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN enrollment_status TEXT DEFAULT '在学'")
        changes.append("添加 enrollment_status 列 (默认: 在学)")
        print("✓ 添加 enrollment_status 列")
    else:
        print("- enrollment_status 列已存在，跳过")

    conn.commit()

    # 验证
    cursor.execute("SELECT COUNT(*) FROM students")
    total = cursor.fetchone()[0]

    if 'student_type' in columns and 'enrollment_status' in columns:
        cursor.execute("SELECT student_type, enrollment_status, COUNT(*) FROM students GROUP BY student_type, enrollment_status")
        stats = cursor.fetchall()
        print(f"\n当前学生统计 (共 {total} 人):")
        for row in stats:
            print(f"  {row[0]} / {row[1]}: {row[2]} 人")

    conn.close()

    if changes:
        print(f"\n迁移完成: {', '.join(changes)}")
    else:
        print("\n无需迁移，所有列已存在")

    print(f"✓ 所有 {total} 名学生保持原有数据不变")

if __name__ == '__main__':
    migrate()
