#!/usr/bin/env python3
"""
检查用户状态脚本 - 查看当前用户的密码状态
"""

import requests
from bs4 import BeautifulSoup
import re

# 登录信息
login_url = "http://localhost:5001/login"
login_data = {
    "username": "admin",
    "password": "admin123"
}

# 创建会话
session = requests.Session()

print("=== 开始检查用户状态 ===")

# 1. 登录
print("1. 尝试登录...")
response = session.post(login_url, data=login_data)
print(f"   登录响应状态码: {response.status_code}")
print(f"   登录后URL: {response.url}")

# 2. 检查是否被重定向到修改密码页面
if "change_password" in response.url:
    print("   ⚠️  检测到被重定向到修改密码页面")
    
    # 解析页面内容
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 检查是否有强制修改密码的提示
    force_change = soup.find('input', {'name': 'force'})
    if force_change and force_change.get('value') == 'True':
        print("   🔍 检测到强制修改密码标记")
    
    # 检查页面中的提示信息
    alerts = soup.find_all(class_=re.compile(r'alert'))
    for alert in alerts:
        if '强制' in alert.text or '必须' in alert.text:
            print(f"   💬 页面提示: {alert.text.strip()}")

# 3. 尝试访问其他页面
print("\n2. 尝试访问首页...")
index_url = "http://localhost:5001/"
response = session.get(index_url)
print(f"   首页响应状态码: {response.status_code}")
print(f"   首页URL: {response.url}")

# 4. 检查会话cookie
cookies = session.cookies.get_dict()
print(f"\n3. 会话Cookie: {cookies}")

# 5. 检查响应头
print(f"   响应头中的Set-Cookie: {response.headers.get('Set-Cookie', '无')}")

print("\n=== 检查完成 ===")