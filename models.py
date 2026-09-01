# 包含所有Base声明和表类定义（Student/Schedule/CourseRecord等）
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Time, Date, Float, Boolean
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime  # 添加datetime导入，用于created_at默认值

Base = declarative_base()

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    gender = Column(String)
    grade = Column(String)

class Schedule(Base):
    __tablename__ = 'schedules'
    id = Column(Integer, primary_key=True)
    subject = Column(String)
    date_type = Column(String)
    teacher = Column(String)
    start_time = Column(Time)
    duration = Column(Integer)
    students = relationship('Student', secondary='schedule_students')

class ScheduleStudent(Base):
    __tablename__ = 'schedule_students'
    schedule_id = Column(Integer, ForeignKey('schedules.id'), primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'), primary_key=True)

class CourseRecord(Base):
    __tablename__ = 'course_records'
    id = Column(Integer, primary_key=True)
    subject = Column(String)  # 新增直接存储科目
    date = Column(Date)
    start_time = Column(Time)
    duration = Column(Integer)
    teacher = Column(String)  # 新增直接存储教师
    content = Column(String)
    homework = Column(String)
    notes = Column(String)
    students = relationship(
        'RecordStudent',
        back_populates='record',
        cascade="all, delete-orphan",  # <--- 关键修改
        lazy='joined'  # 添加 lazy='joined' 以即时加载关联数据
    )
    
class ExamRecord(Base):
    """考试记录表，存储考试基本信息"""
    __tablename__ = 'exam_records'
    id = Column(Integer, primary_key=True)
    name = Column(String)  # 考试名称，如"10月月考"
    subject = Column(String)  # 科目
    grade = Column(String)  # 年级
    teacher = Column(String)  # 任课老师
    total_score = Column(Integer)  # 满分分值
    exam_date = Column(Date)  # 考试日期
    student_group_id = Column(Integer, ForeignKey('student_groups.id'))  # 关联的学生班级ID
    
    # 关联学生成绩
    student_scores = relationship(
        'StudentScore',
        back_populates='exam',
        cascade="all, delete-orphan"
    )
    
    # 关联学生班级
    student_group = relationship('StudentGroup', backref='exams')


class StudentScore(Base):
    """学生成绩表，存储每个学生在特定考试中的成绩"""
    __tablename__ = 'student_scores'
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('exam_records.id', ondelete="CASCADE"))
    student_id = Column(Integer, ForeignKey('students.id'))
    score = Column(Float)  # 分数
    rank = Column(String)  # 名次
    grade_rank = Column(String)  # 年级排名
    class_rank = Column(String)  # 班级排名
    
    # 关联关系
    exam = relationship('ExamRecord', back_populates='student_scores')
    student = relationship('Student', backref='scores')

class StudentGroup(Base):
    """学生班级表，存储学生班级基本信息"""
    __tablename__ = 'student_groups'
    id = Column(Integer, primary_key=True)
    name = Column(String)  # 班级名称
    grade = Column(String)  # 年级
    subject = Column(String)  # 科目
    teacher = Column(String)  # 教师
    # 关联学生
    students = relationship(
        'GroupStudent',
        back_populates='group',
        cascade="all, delete-orphan"
    )

class GroupStudent(Base):
    """学生班级与学生的关联表"""
    __tablename__ = 'group_students'
    group_id = Column(Integer, ForeignKey('student_groups.id', ondelete="CASCADE"), primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'), primary_key=True)
    
    # 关联关系
    group = relationship('StudentGroup', back_populates='students')
    student = relationship('Student')


class RecordStudent(Base):
    __tablename__ = 'record_students'
    record_id = Column(Integer, ForeignKey('course_records.id', ondelete="CASCADE"), primary_key=True)  # <--- 添加ondelete
    student_id = Column(Integer, ForeignKey('students.id'), primary_key=True)
    attendance = Column(String, default='出席')
    homework_status = Column(String)
    study_status = Column(String)
    student = relationship('Student', backref='record_students', lazy='joined')
    record = relationship('CourseRecord', back_populates='students', lazy='joined')

class Payment(Base):
    """缴费记录表"""
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id', ondelete="SET NULL"), nullable=True)
    amount = Column(Float)  # 缴费金额
    payment_date = Column(Date)  # 缴费日期
    payment_method = Column(String)  # 支付方式
    discount = Column(Float, default=0)  # 优惠金额
    
    student = relationship('Student', backref='payments')

class CourseEnrollment(Base):
    """课程报名表"""
    __tablename__ = 'course_enrollments'
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    subject = Column(String)  # 科目
    course_type = Column(String)  # 课程类型(小班/一对一等)
    start_date = Column(Date)  # 开始日期
    end_date = Column(Date)  # 结束日期
    fee_per_lesson = Column(Float)  # 每课时费用
    total_lessons = Column(Integer)  # 总课时数
    total_fee = Column(Float)  # 总费用
    remaining_fee = Column(Float, default=0)  # 欠费金额
    
    student = relationship('Student', backref='enrollments')

class Parent(Base):
    """家长表"""
    __tablename__ = 'parents'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    students = relationship('Student', secondary='parent_students')

class ParentStudent(Base):
    """家长学生关联表"""
    __tablename__ = 'parent_students'
    parent_id = Column(Integer, ForeignKey('parents.id'), primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'), primary_key=True)

class Teacher(Base):
    """教师表，存储教师基本信息"""
    __tablename__ = 'teachers'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # 教师姓名
    gender = Column(String)  # 性别
    phone = Column(String)  # 联系电话
    email = Column(String)  # 电子邮箱
    subject = Column(String)  # 主教科目
    status = Column(String, default='在职')  # 状态：在职/离职
    entry_date = Column(Date)  # 入职日期
    notes = Column(String)  # 备注信息
    user_id = Column(Integer, ForeignKey('users.id', ondelete="SET NULL"), nullable=True)  # 关联用户账号
    
    # 关联用户
    user = relationship('User', backref='teacher_profile')

# 添加用户表用于Web登录认证
class User(Base):
    """用户表，用于Web系统登录认证"""
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default='teacher')  # 角色：admin, teacher
    name = Column(String)  # 用户真实姓名
    must_change_password = Column(Boolean, default=False)  # 是否必须修改密码
    password_changed_at = Column(Date)  # 密码最后修改时间
    created_at = Column(Date, default=datetime.now().date)  # 账户创建时间

# 添加数据库引擎和会话的定义


class SemesterTag(Base):
    """学期标签表，用于定义日期范围和标签"""
    __tablename__ = 'semester_tags'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # 标签名称
    start_date = Column(Date, nullable=False)  # 开始日期
    end_date = Column(Date, nullable=False)  # 结束日期
    tag_type = Column(String, nullable=False)  # 标签类型：上学期、下学期、寒假、暑假
    created_at = Column(Date, default=datetime.now().date)  # 创建时间
    updated_at = Column(Date)  # 更新时间

def get_session(db_path):
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)  # 创建所有表
    Session = sessionmaker(bind=engine)
    return Session