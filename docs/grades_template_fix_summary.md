# 成绩管理页面路由修复总结

## 问题描述
访问成绩管理页面时出现路由错误：
```
werkzeug.routing.exceptions.BuildError: Could not build url for endpoint 'add_grade'. Did you mean 'grades' instead?
```

## 根本原因
成绩管理系统的路由命名与其他管理页面不同：
- 其他页面：`add_student`, `add_teacher`, `add_payment` 等
- 成绩管理：`add_exam` (添加考试记录)

## 修复内容

### 1. 路由引用修复
- `add_grade` → `add_exam`
- `edit_grade` → `edit_exam` 
- `delete_grade` → `delete_exam`

### 2. 数据模型理解
成绩管理系统分为两个层次：
- **ExamRecord**: 考试记录（考试基本信息）
- **StudentScore**: 学生成绩（每个学生在特定考试中的分数）

当前模板显示的是考试记录列表，不是学生成绩列表。

### 3. 模板字段修复
更新表格字段以匹配ExamRecord模型：

| 原字段 | 新字段 | 说明 |
|--------|--------|------|
| 学生姓名 | 考试名称 | grade.name |
| 考试类型 | 年级 | grade.grade |
| 分数 | 教师 | grade.teacher |
| - | 满分 | grade.total_score |

### 4. 界面文本更新
- "成绩列表" → "考试记录列表"
- "添加成绩" → "添加考试记录"
- 搜索提示更新为"搜索考试名称, 科目, 年级..."

## 系统架构说明

### 成绩管理工作流程
1. **创建考试记录** (`/grades/add_exam`) - 设置考试基本信息
2. **管理学生成绩** (`/grades/manage/<exam_id>`) - 为特定考试录入学生分数
3. **查看考试列表** (`/grades`) - 显示所有考试记录

### 路由结构
```
/grades                    - 考试记录列表页面
/grades/add_exam          - 添加考试记录
/grades/edit_exam/<id>    - 编辑考试记录  
/grades/delete_exam/<id>  - 删除考试记录
/grades/manage/<id>       - 管理考试成绩
```

## 测试验证
修复后应该能够：
1. ✅ 正常访问成绩管理页面
2. ✅ 点击"添加考试记录"按钮
3. ✅ 编辑和删除考试记录
4. ✅ 搜索和分页功能正常

## 注意事项
- 成绩管理页面现在显示的是考试记录，不是学生成绩
- 要查看和编辑具体学生成绩，需要点击考试记录进入管理页面
- 这种设计符合教育管理系统的常见模式：先创建考试，再录入成绩