#!/bin/bash

# 课程管理系统启动脚本

echo "🚀 启动课程管理系统..."
echo ""
cd /Users/mycore/Projects/CourseMgrWeb

# 检查虚拟环境是否存在
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在，请先创建虚拟环境："
    echo "   python -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# 激活虚拟环境
echo "📦 激活虚拟环境..."
source .venv/bin/activate

# 检查Flask是否已安装
if ! python -c "import flask" 2>/dev/null; then
    echo "❌ Flask未安装，正在安装依赖..."
    pip install -r requirements.txt
fi

# 检查应用文件是否存在
if [ ! -f "app.py" ]; then
    echo "❌ app.py 文件不存在"
    exit 1
fi

echo "✅ 环境检查完成"
echo ""
echo "🌐 启动Web应用..."
echo "   访问地址: http://127.0.0.1:5001"
echo "   按 Ctrl+C 停止应用"
echo ""

# 启动应用
python app.py
