#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试HTML报告生成功能"""

import sys
sys.path.insert(0, '.')

from osint_cn.api import _build_report_html
from datetime import datetime

# 模拟数据
keyword = "测试品牌"
platforms = ["weibo", "douyin", "zhihu"]
total_items = 250

# 模拟分析结果
analysis = {
    'sentiment': {
        'data': {
            'statistics': {
                'positive_count': 85,
                'negative_count': 120,
                'neutral_count': 45
            }
        }
    },
    'risk': {
        'data': {
            'risk_level': 'high',
            'risk_score': 72.5,
            'recommendations': [
                '建议在24小时内发布官方声明确认情况',
                '联系主要意见领袖进行舆论引导',
                '准备危机公关团队进行24/7监测',
                '制定详细的客诉处置和跟进方案'
            ]
        }
    },
    'trend': {
        'data': {
            'peak_time': '2025-08-27 14:30',
            'peak_count': 1250
        }
    }
}

# 词云数据
wordcloud = [
    {'name': '品牌危机', 'value': 250},
    {'name': '用户投诉', 'value': 180},
    {'name': '负面舆论', 'value': 165},
    {'name': '官方回应', 'value': 140},
    {'name': '媒体关注', 'value': 125},
    {'name': '社交传播', 'value': 110},
    {'name': '客户满意度', 'value': 95},
    {'name': '服务改进', 'value': 80},
    {'name': '品质问题', 'value': 75},
    {'name': '退款要求', 'value': 70},
]

# AI报告
ai_report = {
    'executive_summary': '本次舆情事件涉及3个主流平台，总覆盖人群超过500万，负面声量占比达48%。建议立即启动危机公关预案。',
    'risk_judgment': '当前风险等级为高，舆论热度持续上升，需要采取积极的官方回应和客诉处置措施。',
    'action_recommendations': [
        '成立危机应对小组，明确各部门责任',
        '在2小时内发布第一份官方声明',
        '建立客诉快速处理绿色通道'
    ],
    'pr_talking_points': [
        '我们已关注到相关反馈，正在全力调查并做出改进',
        '客户满意度是我们最高的优先级',
        '感谢社会各界的监督，我们会更加谨慎'
    ]
}

# 生成报告
html_content = _build_report_html(keyword, platforms, total_items, analysis, wordcloud, ai_report)

# 保存报告
output_path = '/tmp/test_report.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✓ HTML报告已生成")
print(f"✓ 保存位置: {output_path}")

# 验证内容
checks = [
    ('报告标题', keyword in html_content),
    ('KPI卡片', '85' in html_content and '120' in html_content),
    ('风险等级', 'high' in html_content),
    ('热词词云', '品牌危机' in html_content),
    ('AI智能洞察', 'AI智能' in html_content or 'highlight-box' in html_content),
    ('图表容器', 'chart-container' in html_content),
    ('深色主题支持', '[data-theme="dark"]' in html_content),
    ('目录导航', 'table-of-contents' in html_content),
    ('导出按钮', 'theme-toggle' in html_content or 'btn' in html_content),
]

print("\n≡ 验证内容结构:")
all_passed = True
for check_name, result in checks:
    status = "✓" if result else "✗"
    print(f"  {status} {check_name}")
    if not result:
        all_passed = False

if all_passed:
    print("\n✓✓✓ 所有验证全部通过！HTML报告格式正确")
    print(f"\n可以在浏览器中打开: {output_path}")
else:
    print("\n! 部分验证失败，请检查HTML生成代码")
    sys.exit(1)

# 显示文件大小
import os
file_size = os.path.getsize(output_path)
print(f"✓ 文件大小: {file_size:,} bytes")
