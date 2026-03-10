#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""集成测试：验证HTML报告导出的完整流程"""

import sys
sys.path.insert(0, '.')

import json
from osint_cn.api import app

# 创建Flask测试客户端
client = app.test_client()

# 第一步：执行仪表板pipeline
print("→ 第一步：执行仪表板采集分析流水线...")
response = client.post(
    '/api/dashboard/pipeline',
    json={
        'keyword': '测试服务',
        'platforms': ['weibo', 'baidu'],
        'limit': 50
    },
    headers={'Content-Type': 'application/json'}
)

if response.status_code not in (200, 201):
    print(f"✗ Pipeline执行失败: {response.status_code}")
    print(f"  Response: {response.json}")
    sys.exit(1)

pipeline_result = response.json
pipeline_id = pipeline_result.get('pipeline_id')
if not pipeline_id:
    print(f"✗ 未获取到pipeline_id")
    print(f"  Response: {pipeline_result}")
    sys.exit(1)

print(f"✓ Pipeline执行成功")
print(f"  Pipeline ID: {pipeline_id}")
print(f"  报告标题: {pipeline_result.get('report', {}).get('title')}")

# 第二步：测试HTML导出
print("\n→ 第二步：测试HTML格式导出...")
response = client.get(
    f'/api/reports/{pipeline_id}/export?format=html',
    headers={'Accept': 'text/html'}
)

if response.status_code != 200:
    print(f"✗ HTML导出失败: {response.status_code}")
    print(f"  Response: {response.data[:500]}")
    sys.exit(1)

html_content = response.data.decode('utf-8')
if not html_content.startswith('<!DOCTYPE'):
    print(f"✗ HTML内容格式错误，不是有效的HTML")
    sys.exit(1)

if len(html_content) < 5000:
    print(f"✗ HTML内容过小: {len(html_content)} bytes")
    sys.exit(1)

print(f"✓ HTML导出成功")
print(f"  HTML文件大小: {len(html_content):,} bytes")
print(f"  Content-Type: {response.content_type}")

# 第三步：测试DOCX导出
print("\n→ 第三步：测试DOCX格式导出...")
response = client.get(
    f'/api/reports/{pipeline_id}/export?format=docx',
    headers={'Accept': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
)

if response.status_code != 200:
    print(f"✗ DOCX导出失败: {response.status_code}")
    sys.exit(1)

print(f"✓ DOCX导出成功")
print(f"  DOCX文件大小: {len(response.data):,} bytes")

# 第四步：测试PDF导出
print("\n→ 第四步：测试PDF格式导出...")
response = client.get(
    f'/api/reports/{pipeline_id}/export?format=pdf',
    headers={'Accept': 'application/pdf'}
)

if response.status_code != 200:
    print(f"✗ PDF导出失败: {response.status_code}")
    sys.exit(1)

print(f"✓ PDF导出成功")
print(f"  PDF文件大小: {len(response.data):,} bytes")

# 验证HTML内容
print("\n→ 第五步：验证HTML内容结构...")
validation_checks = [
    ('DOCTYPE声明', '<!DOCTYPE html>' in html_content),
    ('报告标题', '测试服务' in html_content),
    ('CSS变量', '--primary-color' in html_content),
    ('深色主题', '[data-theme="dark"]' in html_content),
    ('图表容器', 'chart-container' in html_content),
    ('Chart.js集成', 'chart.js' in html_content),
    ('目录导航', 'table-of-contents' in html_content),
    ('主题切换按钮', 'theme-toggle' in html_content),
    ('打印导出按钮', 'print-btn' in html_content),
    ('KPI卡片', 'kpi-card' in html_content),
]

all_passed = True
for check_name, result in validation_checks:
    status = "✓" if result else "✗"
    print(f"  {status} {check_name}")
    if not result:
        all_passed = False

if all_passed:
    print("\n✓✓✓ 所有集成测试通过！")
    print("\n系统现在支持以下导出格式：")
    print("  • HTML: 专业的网页格式报告，支持深色主题和交互式图表")
    print("  • DOCX: Word文档格式，便于编辑和分享")
    print("  • PDF: 便携式文档格式，便于打印和归档")
else:
    print("\n! 部分验证失败")
    sys.exit(1)
