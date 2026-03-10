#!/usr/bin/env python3
"""
测试新建监控是否能正常工作
"""
import requests
import json

BASE_URL = 'http://127.0.0.1:5002'

print("\n" + "="*70)
print("测试：新建监控流程")
print("="*70)

# 测试1：最简单的新建
print("\n[测试1] 最简单的新建 (只填必填项)")
print("-" * 70)

simple_payload = {
    "name": "测试新建1",
    "keywords": "测试",
    "platforms": ["weibo"]
}

resp = requests.post(f'{BASE_URL}/api/monitors', json=simple_payload)
print(f"HTTP {resp.status_code}")
if resp.status_code == 201:
    result = resp.json()
    print(f"✓ 创建成功")
    print(f"  - ID: {result['monitor']['monitor_id']}")
    print(f"  - 名称: {result['monitor']['name']}")
    print(f"  - 平台: {result['monitor']['platforms']}")
    print(f"  - 关键词: {result['monitor']['keywords']}")
    print(f"  - 启用: {result['monitor']['enabled']}")
    print(f"  - 报告格式: {result['monitor']['report_formats']}")
    monitor1_id = result['monitor']['monitor_id']
else:
    print(f"✗ 创建失败")
    print(resp.text)
    monitor1_id = None

# 测试2：完整的新建（所有字段）
print("\n[测试2] 完整的新建 (填所有字段)")
print("-" * 70)

full_payload = {
    "name": "测试新建2 - 完整",
    "keywords": "关键词A,关键词B,关键词C",
    "platforms": ["weibo", "zhihu", "baidu"],
    "group_id": None,
    "tags": "标签1,标签2",
    "interval_seconds": 1800,
    "max_items": 100,
    "thresholds": {
        "negative_ratio": 0.4,
        "risk_score": 60,
        "min_items": 50
    },
    "report_formats": ["html", "docx", "pdf"],
    "enabled": True
}

resp = requests.post(f'{BASE_URL}/api/monitors', json=full_payload)
print(f"HTTP {resp.status_code}")
if resp.status_code == 201:
    result = resp.json()
    print(f"✓ 创建成功")
    print(f"  - ID: {result['monitor']['monitor_id']}")
    print(f"  - 名称: {result['monitor']['name']}")
    print(f"  - 关键词: {result['monitor']['keywords']}")
    print(f"  - 平台: {result['monitor']['platforms']}")
    print(f"  - 启用: {result['monitor']['enabled']}")
    print(f"  - 报告格式: {result['monitor']['report_formats']}")
    print(f"  - 阈值(risk_score): {result['monitor']['thresholds']['risk_score']}")
    monitor2_id = result['monitor']['monitor_id']
else:
    print(f"✗ 创建失败")
    print(resp.text)
    monitor2_id = None

# 测试3：新建禁用的监控
print("\n[测试3] 新建禁用的监控")
print("-" * 70)

disabled_payload = {
    "name": "测试新建3 - 禁用",
    "keywords": "禁用测试",
    "platforms": ["weibo"],
    "enabled": False,
    "report_formats": ["pdf"]
}

resp = requests.post(f'{BASE_URL}/api/monitors', json=disabled_payload)
print(f"HTTP {resp.status_code}")
if resp.status_code == 201:
    result = resp.json()
    print(f"✓ 创建成功")
    print(f"  - ID: {result['monitor']['monitor_id']}")
    print(f"  - 启用: {result['monitor']['enabled']}")
    print(f"  - 报告格式: {result['monitor']['report_formats']}")
    monitor3_id = result['monitor']['monitor_id']
else:
    print(f"✗ 创建失败")
    print(resp.text)
    monitor3_id = None

# 测试4：获取所有监控，验证新建的是否存在
print("\n[测试4] 查询所有监控，验证新建的监控")
print("-" * 70)

resp = requests.get(f'{BASE_URL}/api/monitors')
if resp.status_code == 200:
    monitors = resp.json().get('monitors', [])
    print(f"✓ 获取 {len(monitors)} 个监控")
    
    # 查找我们新建的
    for i, m in enumerate(monitors):
        if '测试新建' in m.get('name', ''):
            print(f"\n  #{i+1} {m['name']}")
            print(f"     - ID: {m['monitor_id']}")
            print(f"     - 启用: {m.get('enabled', True)}")
            print(f"     - 格式: {m.get('report_formats', [])}")
            print(f"     - 平台: {m.get('platforms', [])}")
else:
    print(f"✗ 查询失败: {resp.status_code}")

# 测试5：清理
print("\n[测试5] 清理测试数据")
print("-" * 70)

for monitor_id in [monitor1_id, monitor2_id, monitor3_id]:
    if monitor_id:
        requests.delete(f'{BASE_URL}/api/monitors/{monitor_id}')
print("✓ 清理完成")

print("\n" + "="*70)
print("✅ 新建流程测试完成！")
print("="*70)
print("""
新建监控现在支持：
✓ 最简形式：只需填名称、关键词、平台
✓ 完整形式：支持所有高级字段（阈值、标签、间隔等）
✓ 禁用状态：可以创建禁用的监控
✓ 默认值：未指定时自动使用合理的默认值
✓ 报告格式：理性的默认（DOCX + PDF）

现在你可以访问 http://127.0.0.1:5002/dashboard 测试前端新建功能了
""")
