"""
教育集团舆情监控大屏

参考行业大屏布局，保留左侧导航。
适配后续超大屏展示场景。
"""

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>教育集团舆情综合态势</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        :root {
            --bg-page: #060d1b;
            --bg-panel: #0d1a32;
            --bg-panel-2: #0a1630;
            --line: #173b6f;
            --line-soft: rgba(54, 135, 255, 0.2);
            --text-main: #dce9ff;
            --text-soft: #8fb0df;
            --blue: #2e8cff;
            --cyan: #2bd7ff;
            --green: #1ee58b;
            --yellow: #ffcf4d;
            --orange: #ff8b3d;
            --red: #ff4d6d;
        }

        html, body {
            width: 100%;
            height: 100%;
            overflow: hidden;
        }

        body {
            background: radial-gradient(ellipse at top, #0f2244 0%, var(--bg-page) 45%, #040a16 100%);
            color: var(--text-main);
            font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
        }

        .screen {
            height: 100vh;
            display: grid;
            grid-template-columns: 320px 1fr;
            grid-template-rows: 68px 1fr;
            gap: 10px;
            padding: 10px;
        }

        .topbar {
            grid-column: 1 / -1;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: linear-gradient(90deg, #0a1730 0%, #102a52 50%, #0a1730 100%);
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: 0 0 18px rgba(43, 215, 255, 0.12);
            padding: 0 18px;
        }

        .top-title {
            font-size: 28px;
            font-weight: 700;
            color: #f2f7ff;
            letter-spacing: 2px;
        }

        .top-meta {
            display: flex;
            gap: 18px;
            align-items: center;
            font-size: 14px;
            color: var(--text-soft);
        }

        .top-meta strong {
            color: var(--yellow);
            font-family: ui-monospace, Menlo, Monaco, Consolas, monospace;
        }

        .btn {
            border: 1px solid var(--line);
            background: linear-gradient(180deg, #1b4f97, #12417f);
            color: #fff;
            border-radius: 6px;
            height: 34px;
            padding: 0 12px;
            cursor: pointer;
        }

        .sidebar {
            background: linear-gradient(180deg, #0f5fbd 0%, #0a4d9c 100%);
            border: 1px solid rgba(140, 200, 255, 0.3);
            border-radius: 8px;
            overflow-y: auto;
            padding: 16px 0;
        }

        .side-group {
            margin: 0 0 18px;
        }

        .side-title {
            font-size: 16px;
            color: rgba(219, 238, 255, 0.9);
            margin: 6px 18px 10px;
            letter-spacing: 1px;
        }

        .side-item {
            height: 52px;
            margin: 8px 12px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            padding: 0 16px;
            font-size: 20px;
            color: rgba(232, 243, 255, 0.95);
            cursor: pointer;
            transition: 0.25s;
        }

        .side-item:hover {
            background: rgba(255, 255, 255, 0.12);
        }

        .side-item.active {
            background: linear-gradient(90deg, rgba(160, 204, 255, 0.46), rgba(160, 204, 255, 0.22));
            box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.18);
        }

        .main {
            display: grid;
            grid-template-columns: 280px 1fr 320px;
            grid-template-rows: 1fr 180px;
            gap: 10px;
            min-height: 0;
        }

        .panel {
            background: linear-gradient(180deg, var(--bg-panel) 0%, #0b1730 100%);
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: inset 0 0 40px rgba(32, 120, 255, 0.08);
            min-height: 0;
            position: relative;
        }

        .panel-header {
            height: 38px;
            border-bottom: 1px solid var(--line-soft);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 12px;
            font-size: 14px;
            color: var(--cyan);
            font-weight: 600;
        }

        .panel-body {
            height: calc(100% - 38px);
            padding: 10px;
            overflow: hidden;
        }

        .news-list {
            height: 100%;
            overflow: auto;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .news-item {
            color: #b8cff1;
            font-size: 13px;
            padding-left: 14px;
            position: relative;
            white-space: nowrap;
            text-overflow: ellipsis;
            overflow: hidden;
        }

        .news-item::before {
            content: "";
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--orange);
            position: absolute;
            left: 0;
            top: 7px;
        }

        .chart-wrap {
            width: 100%;
            height: 100%;
            min-height: 0;
        }

        .map-stage {
            position: relative;
            width: 100%;
            height: 100%;
            border: 1px solid var(--line-soft);
            border-radius: 8px;
            background: radial-gradient(circle at center, rgba(50, 120, 255, 0.18), rgba(50, 120, 255, 0.04) 45%, transparent 80%);
            overflow: hidden;
        }

        .map-echarts {
            width: 100%;
            height: 100%;
        }

        .map-svg {
            width: 100%;
            height: 100%;
            opacity: 0.9;
        }

        .hot-tag {
            position: absolute;
            background: #e63f4f;
            color: #fff;
            font-size: 12px;
            padding: 3px 8px;
            border-radius: 4px;
            box-shadow: 0 0 10px rgba(230, 63, 79, 0.45);
        }

        .metric {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
            padding: 8px 10px;
            border: 1px solid var(--line-soft);
            border-radius: 6px;
            background: rgba(31, 87, 167, 0.15);
        }

        .metric .name {
            color: #b8cff1;
            font-size: 13px;
        }

        .metric .val {
            font-size: 22px;
            font-weight: 700;
            color: var(--yellow);
            font-family: ui-monospace, Menlo, Monaco, Consolas, monospace;
        }

        .sentiment-ring {
            width: 140px;
            height: 140px;
            border-radius: 50%;
            margin: 6px auto 14px;
            border: 8px solid #15345f;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            background: conic-gradient(var(--green) 0 46%, var(--yellow) 46% 78%, var(--red) 78% 100%);
        }

        .sentiment-ring::after {
            content: "";
            width: 90px;
            height: 90px;
            border-radius: 50%;
            background: #0b1a34;
            position: absolute;
        }

        .sentiment-face {
            z-index: 1;
            font-size: 28px;
        }

        .rank-row {
            display: grid;
            grid-template-columns: 40px 1fr 52px;
            align-items: center;
            gap: 8px;
            margin: 8px 0;
            color: #b8cff1;
            font-size: 12px;
        }

        .rank-bar {
            height: 7px;
            border-radius: 4px;
            background: #173866;
            overflow: hidden;
        }

        .rank-bar i {
            display: block;
            height: 100%;
            background: linear-gradient(90deg, #1d74ff, #29d6ff);
        }

        .right-scroll {
            overflow-y: auto;
            height: 100%;
        }

        .bottom-info {
            grid-column: 1 / 3;
            background: linear-gradient(180deg, #0f1f3d, #0d1832);
            border: 1px solid var(--line);
            border-radius: 8px;
            display: grid;
            grid-template-columns: 200px 1fr;
            gap: 10px;
            padding: 10px;
        }

        .ticker-time {
            border-right: 1px solid var(--line-soft);
            padding-right: 10px;
            color: #84abdb;
            font-size: 13px;
        }

        .ticker-content {
            color: #c3d8f8;
            line-height: 1.7;
            font-size: 13px;
            overflow: hidden;
        }

        .risk-box {
            grid-column: 3;
            background: linear-gradient(180deg, #0f1f3d, #0d1832);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 10px;
            display: grid;
            grid-template-rows: 40px 1fr;
            min-height: 0;
        }

        .risk-title {
            color: #ff7f95;
            font-size: 14px;
            font-weight: 700;
            display: flex;
            align-items: center;
        }

        .risk-list {
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .risk-item {
            padding: 8px;
            border-left: 3px solid var(--red);
            background: rgba(255, 77, 109, 0.08);
            color: #ff9caf;
            border-radius: 4px;
            font-size: 12px;
            line-height: 1.5;
        }

        .detail-drawer {
            position: fixed;
            top: 84px;
            right: -520px;
            width: 500px;
            height: calc(100vh - 94px);
            background: linear-gradient(180deg, #102243 0%, #0a1832 100%);
            border: 1px solid var(--line);
            border-right: none;
            border-radius: 10px 0 0 10px;
            box-shadow: -8px 0 24px rgba(0, 0, 0, 0.35);
            transition: right 0.25s ease;
            z-index: 30;
            display: grid;
            grid-template-rows: 46px 1fr;
        }

        .detail-drawer.open {
            right: 0;
        }

        .drawer-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 12px;
            border-bottom: 1px solid var(--line-soft);
            color: var(--cyan);
            font-weight: 600;
        }

        .drawer-close {
            width: 26px;
            height: 26px;
            border: 1px solid var(--line);
            background: #12305b;
            color: #dce9ff;
            border-radius: 6px;
            cursor: pointer;
        }

        .drawer-body {
            padding: 10px;
            overflow-y: auto;
        }

        .drawer-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            color: #c7dcfb;
        }

        .drawer-table th,
        .drawer-table td {
            border-bottom: 1px solid var(--line-soft);
            padding: 8px 6px;
            text-align: left;
            vertical-align: top;
        }

        .drawer-table th {
            color: #8fb0df;
            font-weight: 600;
            background: rgba(35, 96, 178, 0.12);
        }

        .drawer-card {
            border: 1px solid var(--line-soft);
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
            background: rgba(31, 87, 167, 0.12);
        }

        .drawer-card-title {
            color: #9fd1ff;
            font-weight: 700;
            margin-bottom: 6px;
        }

        .drawer-toolbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            margin-bottom: 10px;
            flex-wrap: wrap;
        }

        .drawer-select {
            min-width: 140px;
            background: #102a50;
            color: #dce9ff;
            border: 1px solid var(--line);
            border-radius: 6px;
            padding: 6px 8px;
            font-size: 12px;
        }

        .drawer-pagination {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #8fb0df;
            font-size: 12px;
        }

        .drawer-btn {
            border: 1px solid var(--line);
            background: #12305b;
            color: #dce9ff;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 12px;
            cursor: pointer;
        }

        .drawer-btn:disabled {
            opacity: 0.45;
            cursor: not-allowed;
        }

        .drawer-row {
            cursor: pointer;
        }

        .drawer-row.active {
            background: rgba(73, 203, 255, 0.1);
        }

        .drawer-detail {
            margin-top: 10px;
            border: 1px solid var(--line-soft);
            border-radius: 8px;
            padding: 10px;
            background: rgba(16, 42, 80, 0.55);
        }

        .drawer-detail-title {
            color: #9fd1ff;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .drawer-empty {
            color: #8fb0df;
            font-size: 13px;
            text-align: center;
            padding: 30px 0;
        }

        body.fullscreen .screen {
            padding: 0;
            gap: 0;
            grid-template-rows: 74px 1fr;
        }

        body.fullscreen .topbar,
        body.fullscreen .sidebar,
        body.fullscreen .panel,
        body.fullscreen .bottom-info,
        body.fullscreen .risk-box {
            border-radius: 0;
        }

        @media (max-width: 1600px) {
            .screen {
                grid-template-columns: 280px 1fr;
            }

            .main {
                grid-template-columns: 240px 1fr 280px;
            }
        }
    </style>
</head>
<body>
    <div class="screen">
        <header class="topbar">
            <div class="top-title" id="top-title">全国教育集团舆情综合态势</div>
            <div class="top-meta">
                <span>热度总计：<strong id="heat-total">56,479</strong></span>
                <span>时间：<strong id="current-time">--:--:--</strong></span>
                <span>日期：<strong id="current-date">----</strong></span>
                <button class="btn" onclick="toggleFullscreen()">全屏</button>
            </div>
        </header>

        <aside class="sidebar">
            <div class="side-group">
                <div class="side-title">监测</div>
                <div class="side-item active" data-view="overview">🏎 舆情概览</div>
                <div class="side-item" data-view="realtime">📡 实时监测</div>
                <div class="side-item" data-view="sentiment">😊 情感分析</div>
            </div>

            <div class="side-group">
                <div class="side-title">管理</div>
                <div class="side-item" data-view="complaints">❗ 客诉追踪</div>
                <div class="side-item" data-view="keywords">🏷 关键词监控</div>
            </div>

            <div class="side-group">
                <div class="side-title">分析</div>
                <div class="side-item" data-view="trend">📈 趋势分析</div>
                <div class="side-item" data-view="report">📄 舆情报告</div>
            </div>

            <div class="side-group">
                <div class="side-title">其他</div>
                <div class="side-item" data-view="alert">⚠ 危机预警</div>
                <div class="side-item" data-view="setting">⚙ 系统设置</div>
            </div>
        </aside>

        <main class="main">
            <section class="panel" style="grid-column: 1; grid-row: 1;">
                <div class="panel-header">
                    <span id="panel-news-title">热门新闻</span>
                    <small>实时滚动</small>
                </div>
                <div class="panel-body news-list" id="news-list">
                    <div class="news-item">教育部发布中小学数字化转型指导意见，关注课堂质量提升</div>
                    <div class="news-item">家长热议课后服务收费标准，多地出台透明化公示方案</div>
                    <div class="news-item">全国重点校区春季招生启动，咨询量环比增长 18%</div>
                    <div class="news-item">“双减”执行后培训服务升级，满意度持续上升</div>
                    <div class="news-item">校园食品安全话题升温，集团专项督导已上线</div>
                    <div class="news-item">AI 教学辅助工具试点扩容，师生互动效率提升</div>
                </div>
            </section>

            <section class="panel" style="grid-column: 2; grid-row: 1;">
                <div class="panel-header">
                    <span id="panel-map-title">全国校区舆情热力分布</span>
                    <small>单位：热度指数</small>
                </div>
                <div class="panel-body">
                    <div class="map-stage">
                        <div id="chinaMap" class="map-echarts"></div>
                        <div class="hot-tag" id="map-hot-tag" style="right: 84px; top: 185px;">最新告警：上海市</div>
                    </div>
                </div>
            </section>

            <section class="panel" style="grid-column: 3; grid-row: 1;">
                <div class="panel-header">
                    <span id="panel-sentiment-title">社会情绪指数</span>
                    <small>今日</small>
                </div>
                <div class="panel-body right-scroll">
                    <div class="sentiment-ring">
                        <div class="sentiment-face">🙂</div>
                    </div>

                    <div class="metric">
                        <span class="name">正面</span>
                        <span class="val" style="color: var(--green);" id="sentiment-positive">13.5万</span>
                    </div>
                    <div class="metric">
                        <span class="name">中立</span>
                        <span class="val" style="color: var(--yellow);" id="sentiment-neutral">11万</span>
                    </div>
                    <div class="metric">
                        <span class="name">负面</span>
                        <span class="val" style="color: var(--red);" id="sentiment-negative">3.7万</span>
                    </div>

                    <div class="panel-header" style="margin-top: 8px;"><span>热词分析</span><small>实时</small></div>
                    <div style="padding: 10px 0; color: #67b8ff; font-size: 18px; line-height: 1.8;" id="hot-words">
                        <span style="font-size: 34px; color: #49cbff;">师资</span>
                        <span style="font-size: 24px; color: #2e8cff;">教学质量</span>
                        <span style="font-size: 28px; color: #87ddff;">收费</span>
                        <span style="font-size: 20px; color: #6fcbff;">双减</span>
                        <span style="font-size: 26px; color: #4fbaff;">校园安全</span>
                        <span style="font-size: 18px; color: #9cd9ff;">托管</span>
                    </div>
                </div>
            </section>

            <section class="panel" style="grid-column: 1; grid-row: 2;">
                <div class="panel-header">
                    <span id="panel-trend-title">发展趋势</span>
                    <small>近 7 日</small>
                </div>
                <div class="panel-body chart-wrap">
                    <canvas id="trendChart"></canvas>
                </div>
            </section>

            <section class="bottom-info">
                <div class="ticker-time">
                    <div style="font-size: 18px; color: var(--cyan); font-weight: 700;" id="ticker-time">今天 14:34</div>
                    <div style="margin-top: 6px;" id="ticker-region">地区：上海</div>
                    <div style="margin-top: 6px; color: var(--yellow);" id="ticker-heat">热度：高（3120）</div>
                    <div style="margin-top: 6px;" id="ticker-source">来源：今日头条</div>
                </div>
                <div class="ticker-content" id="ticker-content">
                    本次舆情主要集中在教育服务体验与学费透明度两个维度，讨论来源以微博、短视频平台与家长社群为主。
                    其中“师资稳定性”“收费标准公开”相关话题热度上升明显。建议持续跟踪高频关键词，结合校区工单系统联动处置，
                    对重点投诉在 2 小时内完成首次响应并发布统一解释口径。
                </div>
            </section>

            <section class="risk-box">
                <div class="risk-title">最新动态 / 风险提示</div>
                <div class="risk-list" id="risk-list">
                    <div class="risk-item">【高优】某校区“退费处理慢”讨论量 1 小时增长 67%，建议客服中心加派坐席。</div>
                    <div class="risk-item">【中优】“课程难度偏高”在家长群扩散，建议教研组发布说明与学习路径建议。</div>
                    <div class="risk-item">【提示】“校园设施升级”获得较多正向反馈，可作为官方正面传播素材。</div>
                </div>
            </section>
        </main>
    </div>

    <aside class="detail-drawer" id="detail-drawer">
        <div class="drawer-head">
            <span id="drawer-title">明细面板</span>
            <button class="drawer-close" onclick="hideDetailDrawer()">×</button>
        </div>
        <div class="drawer-body" id="drawer-body">
            <div class="drawer-empty">请选择客诉追踪或舆情报告查看明细</div>
        </div>
    </aside>

    <script>
        const API_BASE = '';
        let mapChart = null;
        let trendChart = null;
        let currentView = 'overview';
        const complaintState = {
            collections: [],
            alerts: [],
            filteredCollections: [],
            platform: 'all',
            page: 1,
            pageSize: 8,
            selectedCollectionId: null,
            selectedCollectionDetail: null,
            detailCache: {}
        };

        const viewMeta = {
            overview: { top: '全国教育集团舆情综合态势', news: '热门新闻', map: '全国校区舆情热力分布', sentiment: '社会情绪指数', trend: '发展趋势' },
            realtime: { top: '教育集团实时舆情监测中心', news: '实时舆情流', map: '实时区域分布', sentiment: '情绪变化', trend: '小时趋势' },
            sentiment: { top: '教育集团情感分析中心', news: '情感样本', map: '情感地域分布', sentiment: '情感统计', trend: '情感趋势' },
            complaints: { top: '教育集团客诉追踪中心', news: '最新客诉', map: '客诉区域分布', sentiment: '客诉情绪', trend: '客诉趋势' },
            keywords: { top: '教育集团关键词监控中心', news: '关键词相关动态', map: '关键词区域分布', sentiment: '关键词情感', trend: '关键词热度趋势' },
            trend: { top: '教育集团趋势分析中心', news: '趋势相关新闻', map: '趋势区域分布', sentiment: '趋势情绪', trend: '综合趋势' },
            report: { top: '教育集团舆情报告中心', news: '报告摘要', map: '报告区域摘要', sentiment: '报告情绪摘要', trend: '报告趋势摘要' },
            alert: { top: '教育集团危机预警中心', news: '预警相关动态', map: '预警区域分布', sentiment: '风险情绪', trend: '预警趋势' },
            setting: { top: '教育集团系统配置中心', news: '系统公告', map: '系统覆盖区域', sentiment: '服务状态', trend: '系统运行趋势' }
        };

        async function apiRequest(url) {
            const response = await fetch(API_BASE + url);
            return response.json();
        }

        async function safeApiRequest(url) {
            try {
                return await apiRequest(url);
            } catch (error) {
                console.error(`请求失败: ${url}`, error);
                return null;
            }
        }

        function updateClock() {
            const now = new Date();
            document.getElementById('current-time').textContent = now.toLocaleTimeString('zh-CN', { hour12: false });
            document.getElementById('current-date').textContent = now.toLocaleDateString('zh-CN');
            document.getElementById('ticker-time').textContent = `今天 ${now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })}`;
        }

        function bindSidebar() {
            document.querySelectorAll('.side-item').forEach((item) => {
                item.addEventListener('click', () => {
                    document.querySelectorAll('.side-item').forEach((el) => el.classList.remove('active'));
                    item.classList.add('active');
                    const view = item.getAttribute('data-view') || 'overview';
                    switchView(view);
                });
            });
        }

        function showDetailDrawer(title, html) {
            const drawer = document.getElementById('detail-drawer');
            const drawerTitle = document.getElementById('drawer-title');
            const drawerBody = document.getElementById('drawer-body');
            if (!drawer || !drawerTitle || !drawerBody) return;
            drawerTitle.textContent = title;
            drawerBody.innerHTML = html;
            drawer.classList.add('open');
        }

        function hideDetailDrawer() {
            const drawer = document.getElementById('detail-drawer');
            if (drawer) drawer.classList.remove('open');
        }

        function updateViewTitle(view) {
            const meta = viewMeta[view] || viewMeta.overview;
            const setText = (id, text) => {
                const el = document.getElementById(id);
                if (el) el.textContent = text;
            };
            setText('top-title', meta.top);
            setText('panel-news-title', meta.news);
            setText('panel-map-title', meta.map);
            setText('panel-sentiment-title', meta.sentiment);
            setText('panel-trend-title', meta.trend);
        }

        function updateHotWords(words) {
            const hotWords = document.getElementById('hot-words');
            if (!hotWords || !Array.isArray(words) || !words.length) return;
            hotWords.innerHTML = words.slice(0, 8).map((word, index) => {
                const size = [34, 30, 28, 24, 22, 20, 18, 18][index] || 18;
                const color = ['#49cbff', '#4fbaff', '#6fcbff', '#2e8cff', '#87ddff'][index % 5];
                return `<span style="font-size:${size}px;color:${color};margin-right:10px;">${word}</span>`;
            }).join('');
        }

        function toggleFullscreen() {
            document.body.classList.toggle('fullscreen');
        }

        let provinceHeatData = [
            { name: '北京', value: 2860 },
            { name: '天津', value: 1320 },
            { name: '上海', value: 3120 },
            { name: '重庆', value: 1420 },
            { name: '河北', value: 1650 },
            { name: '河南', value: 1980 },
            { name: '云南', value: 860 },
            { name: '辽宁', value: 1210 },
            { name: '黑龙江', value: 920 },
            { name: '湖南', value: 1740 },
            { name: '安徽', value: 1360 },
            { name: '山东', value: 2380 },
            { name: '新疆', value: 580 },
            { name: '江苏', value: 2480 },
            { name: '浙江', value: 2290 },
            { name: '江西', value: 1180 },
            { name: '湖北', value: 1720 },
            { name: '广西', value: 980 },
            { name: '甘肃', value: 620 },
            { name: '山西', value: 930 },
            { name: '内蒙古', value: 680 },
            { name: '陕西', value: 1480 },
            { name: '吉林', value: 760 },
            { name: '福建', value: 1570 },
            { name: '贵州', value: 910 },
            { name: '广东', value: 2760 },
            { name: '青海', value: 350 },
            { name: '西藏', value: 180 },
            { name: '四川', value: 2060 },
            { name: '宁夏', value: 420 },
            { name: '海南', value: 510 },
            { name: '台湾', value: 730 },
            { name: '香港', value: 460 },
            { name: '澳门', value: 260 }
        ];

        const provinceSourceMap = {
            '北京': '微博', '上海': '今日头条', '广东': '抖音', '江苏': '知乎',
            '浙江': '小红书', '山东': '百度', '四川': '微博', '湖北': '知乎'
        };

        async function loadChinaGeoJSON() {
            const urls = [
                'https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json',
                'https://fastly.jsdelivr.net/npm/echarts@5/map/json/china.json'
            ];

            for (const url of urls) {
                try {
                    const response = await fetch(url);
                    if (!response.ok) continue;
                    return await response.json();
                } catch (error) {
                    continue;
                }
            }
            return null;
        }

        function heatLevel(value) {
            if (value >= 2500) return '高';
            if (value >= 1200) return '中';
            return '低';
        }

        function updateMapSelection(name, value) {
            const tag = document.getElementById('map-hot-tag');
            const region = document.getElementById('ticker-region');
            const heat = document.getElementById('ticker-heat');
            const source = document.getElementById('ticker-source');
            const content = document.getElementById('ticker-content');
            const riskList = document.getElementById('risk-list');
            const level = heatLevel(value);
            const sourceName = provinceSourceMap[name] || '全网聚合';

            if (tag) tag.textContent = `最新告警：${name}`;
            if (region) region.textContent = `地区：${name}`;
            if (heat) heat.textContent = `热度：${level}（${value}）`;
            if (source) source.textContent = `来源：${sourceName}`;
            if (content) {
                content.textContent = `${name} 当前舆情热度为 ${value}，主要讨论集中在教学质量、收费标准和服务反馈。` +
                    `建议该地区校区优先处理高频投诉，并在 2 小时内完成首次公开响应。`;
            }

            if (riskList) {
                riskList.innerHTML = `
                    <div class="risk-item">【高优】${name} 地区“收费标准”相关讨论持续增长，建议发布费用构成说明。</div>
                    <div class="risk-item">【中优】${name} 家长群出现课程体验反馈分化，建议同步教研优化计划。</div>
                    <div class="risk-item">【提示】${name} 正向内容可围绕“师资建设”和“课堂成果”加强传播。</div>
                `;
            }
        }

        async function initChinaMap() {
            if (typeof echarts === 'undefined') return;

            const mapEl = document.getElementById('chinaMap');
            if (!mapEl) return;

            const geoJSON = await loadChinaGeoJSON();
            if (!geoJSON) {
                mapEl.innerHTML = '<div style="color:#8fb0df;padding:14px;">地图数据加载失败，请检查网络。</div>';
                return;
            }

            echarts.registerMap('china-edu', geoJSON);
            mapChart = echarts.init(mapEl);

            mapChart.setOption({
                backgroundColor: 'transparent',
                tooltip: {
                    trigger: 'item',
                    formatter: (params) => `${params.name}<br/>热度：${params.value || 0}`
                },
                visualMap: {
                    min: 0,
                    max: 3200,
                    orient: 'horizontal',
                    left: 'center',
                    bottom: 8,
                    text: ['高', '低'],
                    textStyle: { color: '#8fb0df' },
                    inRange: {
                        color: ['#1d3f6f', '#2472d2', '#49b1ff', '#ffc857', '#ff6b6b']
                    },
                    calculable: true,
                    itemWidth: 12,
                    itemHeight: 90
                },
                series: [
                    {
                        name: '舆情热度',
                        type: 'map',
                        map: 'china-edu',
                        roam: true,
                        zoom: 1.12,
                        nameMap: {
                            '内蒙古自治区': '内蒙古', '广西壮族自治区': '广西', '西藏自治区': '西藏', '宁夏回族自治区': '宁夏', '新疆维吾尔自治区': '新疆'
                        },
                        label: {
                            show: true,
                            color: '#bcd4f4',
                            fontSize: 9
                        },
                        itemStyle: {
                            borderColor: '#6bb7ff',
                            borderWidth: 1,
                            areaColor: '#173864'
                        },
                        emphasis: {
                            label: { color: '#ffffff' },
                            itemStyle: { areaColor: '#2e8cff' }
                        },
                        data: provinceHeatData
                    }
                ]
            });

            mapChart.on('click', (params) => {
                const clickedValue = typeof params.value === 'number' ? params.value : 0;
                updateMapSelection(params.name, clickedValue);
            });

            window.addEventListener('resize', () => mapChart && mapChart.resize());
        }

        function initTrendChart() {
            const canvas = document.getElementById('trendChart');
            if (!canvas) return;
            trendChart = new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: ['17:00', '18:00', '19:00', '20:00', '21:00', '22:00', '23:00'],
                    datasets: [{
                        data: [620, 780, 690, 920, 840, 760, 710],
                        borderRadius: 4,
                        backgroundColor: '#2e8cff'
                    }]
                },
                options: {
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: {
                            grid: { color: 'rgba(84, 153, 255, 0.15)' },
                            ticks: { color: '#8fb0df' }
                        },
                        y: {
                            grid: { color: 'rgba(84, 153, 255, 0.15)' },
                            ticks: { color: '#8fb0df' }
                        }
                    }
                }
            });
        }

        function updateNews(news) {
            const container = document.getElementById('news-list');
            if (!container || !Array.isArray(news)) return;
            container.innerHTML = news.slice(0, 10).map(item => `<div class="news-item">${item}</div>`).join('');
        }

        function updateSentiment(sentiment) {
            if (!sentiment) return;
            document.getElementById('sentiment-positive').textContent = (sentiment.positive || 0).toLocaleString('zh-CN');
            document.getElementById('sentiment-neutral').textContent = (sentiment.neutral || 0).toLocaleString('zh-CN');
            document.getElementById('sentiment-negative').textContent = (sentiment.negative || 0).toLocaleString('zh-CN');
        }

        function updateTrend(trend) {
            if (!trendChart || !trend) return;
            const labels = Object.keys(trend);
            const values = labels.map(key => trend[key]);
            if (!labels.length) return;
            trendChart.data.labels = labels;
            trendChart.data.datasets[0].data = values;
            trendChart.update();
        }

        function convertRealtimeToTrend(items) {
            const bucket = {};
            const now = new Date();
            for (let i = 0; i < 7; i++) {
                const d = new Date(now.getTime() - i * 3600 * 1000);
                const key = `${String(d.getHours()).padStart(2, '0')}:00`;
                bucket[key] = 0;
            }

            (items || []).forEach((item) => {
                const ts = item.publish_time || item.collected_at;
                if (!ts) return;
                try {
                    const d = new Date(ts);
                    const key = `${String(d.getHours()).padStart(2, '0')}:00`;
                    if (bucket[key] !== undefined) bucket[key] += 1;
                } catch (e) {
                    return;
                }
            });
            return bucket;
        }

        function updateMapData(data) {
            if (!Array.isArray(data) || !data.length) return;
            provinceHeatData = data;
            if (mapChart) {
                mapChart.setOption({
                    series: [{ data: provinceHeatData }]
                });
            }
        }

        function updateAlerts(alerts) {
            const riskList = document.getElementById('risk-list');
            if (!riskList) return;
            if (!Array.isArray(alerts) || !alerts.length) {
                riskList.innerHTML = '<div class="risk-item">当前无活跃预警</div>';
                return;
            }
            riskList.innerHTML = alerts.slice(0, 5).map(alert => {
                const message = alert.message || alert.title || JSON.stringify(alert).slice(0, 80);
                return `<div class="risk-item">${message}</div>`;
            }).join('');
        }

        function escapeHtml(value) {
            return String(value || '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function getCollectionDetailPanelHtml() {
            if (!complaintState.selectedCollectionId) {
                return '<div class="drawer-empty">请先选择一条客诉采集记录</div>';
            }

            const base = complaintState.collections.find(item => item.id === complaintState.selectedCollectionId);
            if (!base) {
                return '<div class="drawer-empty">所选记录不存在或已失效</div>';
            }

            const detail = complaintState.selectedCollectionDetail;
            if (!detail) {
                return '<div class="drawer-empty">正在加载记录详情...</div>';
            }

            const dataRows = Array.isArray(detail.data) ? detail.data.slice(0, 8).map(item => {
                const content = escapeHtml(item.content || '-').slice(0, 80);
                const author = escapeHtml(item.author || '-');
                const time = item.publish_time ? new Date(item.publish_time).toLocaleString('zh-CN') : '-';
                return `<tr><td>${author}</td><td>${content}</td><td>${time}</td></tr>`;
            }).join('') : '';

            const collectedAt = base.collected_at ? new Date(base.collected_at).toLocaleString('zh-CN') : '-';

            return `
                <div class="drawer-detail-title">采集记录详情</div>
                <table class="drawer-table">
                    <tbody>
                        <tr><th>记录ID</th><td>${escapeHtml(base.id || '-')}</td></tr>
                        <tr><th>平台</th><td>${escapeHtml(base.platform || '-')}</td></tr>
                        <tr><th>关键词</th><td>${escapeHtml(base.keyword || '-')}</td></tr>
                        <tr><th>采集时间</th><td>${collectedAt}</td></tr>
                        <tr><th>总条数</th><td>${detail.total || 0}</td></tr>
                    </tbody>
                </table>
                <div class="drawer-detail-title" style="margin-top:10px;">样本数据（前8条）</div>
                ${dataRows ? `
                    <table class="drawer-table">
                        <thead>
                            <tr><th>作者</th><th>内容</th><th>发布时间</th></tr>
                        </thead>
                        <tbody>${dataRows}</tbody>
                    </table>
                ` : '<div class="drawer-empty">该记录暂无样本数据</div>'}
            `;
        }

        function bindComplaintDrawerEvents() {
            const platformSelect = document.getElementById('complaint-platform-filter');
            const prevBtn = document.getElementById('complaint-page-prev');
            const nextBtn = document.getElementById('complaint-page-next');

            if (platformSelect) {
                platformSelect.onchange = async (event) => {
                    complaintState.platform = event.target.value || 'all';
                    complaintState.page = 1;
                    complaintState.selectedCollectionId = null;
                    complaintState.selectedCollectionDetail = null;
                    renderComplaintDrawer();
                    const first = complaintState.filteredCollections[0];
                    if (first && first.id) {
                        await loadCollectionDetail(first.id);
                    }
                };
            }

            if (prevBtn) {
                prevBtn.onclick = async () => {
                    if (complaintState.page <= 1) return;
                    complaintState.page -= 1;
                    complaintState.selectedCollectionId = null;
                    complaintState.selectedCollectionDetail = null;
                    renderComplaintDrawer();
                    const first = complaintState.filteredCollections[(complaintState.page - 1) * complaintState.pageSize];
                    if (first && first.id) {
                        await loadCollectionDetail(first.id);
                    }
                };
            }

            if (nextBtn) {
                nextBtn.onclick = async () => {
                    const totalPages = Math.max(1, Math.ceil(complaintState.filteredCollections.length / complaintState.pageSize));
                    if (complaintState.page >= totalPages) return;
                    complaintState.page += 1;
                    complaintState.selectedCollectionId = null;
                    complaintState.selectedCollectionDetail = null;
                    renderComplaintDrawer();
                    const first = complaintState.filteredCollections[(complaintState.page - 1) * complaintState.pageSize];
                    if (first && first.id) {
                        await loadCollectionDetail(first.id);
                    }
                };
            }

            document.querySelectorAll('.drawer-row[data-collection-id]').forEach((row) => {
                row.onclick = async () => {
                    const collectionId = row.getAttribute('data-collection-id');
                    if (!collectionId) return;
                    await loadCollectionDetail(collectionId);
                };
            });
        }

        async function loadCollectionDetail(collectionId) {
            if (!collectionId) return;

            complaintState.selectedCollectionId = collectionId;
            if (complaintState.detailCache[collectionId]) {
                complaintState.selectedCollectionDetail = complaintState.detailCache[collectionId];
                renderComplaintDrawer();
                return;
            }

            complaintState.selectedCollectionDetail = null;
            renderComplaintDrawer();

            const detail = await safeApiRequest(`/api/collections/${encodeURIComponent(collectionId)}?page=1&page_size=20`);
            if (detail && detail.success) {
                complaintState.detailCache[collectionId] = detail;
                complaintState.selectedCollectionDetail = detail;
            } else {
                complaintState.selectedCollectionDetail = { data: [], total: 0 };
            }
            renderComplaintDrawer();
        }

        function renderComplaintDrawer() {
            const platformSet = new Set((complaintState.collections || []).map(item => item.platform).filter(Boolean));
            const platforms = ['all', ...Array.from(platformSet)];

            const filtered = (complaintState.collections || []).filter(item => {
                if (complaintState.platform === 'all') return true;
                return item.platform === complaintState.platform;
            });
            complaintState.filteredCollections = filtered;

            const totalPages = Math.max(1, Math.ceil(filtered.length / complaintState.pageSize));
            if (complaintState.page > totalPages) complaintState.page = totalPages;
            if (complaintState.page < 1) complaintState.page = 1;

            const start = (complaintState.page - 1) * complaintState.pageSize;
            const pageRows = filtered.slice(start, start + complaintState.pageSize);
            const pageIdSet = new Set(pageRows.map(item => item.id));
            if (complaintState.selectedCollectionId && !pageIdSet.has(complaintState.selectedCollectionId)) {
                complaintState.selectedCollectionId = null;
                complaintState.selectedCollectionDetail = null;
            }

            const rows = pageRows.map(item => {
                const time = item.collected_at ? new Date(item.collected_at).toLocaleString('zh-CN') : '-';
                const selected = complaintState.selectedCollectionId === item.id ? 'active' : '';
                return `
                    <tr class="drawer-row ${selected}" data-collection-id="${escapeHtml(item.id || '')}">
                        <td>${item.platform || '-'}</td>
                        <td>${item.keyword || '-'}</td>
                        <td>${item.items_count || 0}</td>
                        <td>${time}</td>
                    </tr>
                `;
            }).join('');

            const alertsHtml = (complaintState.alerts || []).slice(0, 5).map(item => {
                const message = item.message || item.title || '客诉预警';
                return `<div class="drawer-card"><div class="drawer-card-title">预警</div><div>${message}</div></div>`;
            }).join('');

            const options = platforms.map(platform => {
                const selected = complaintState.platform === platform ? 'selected' : '';
                const label = platform === 'all' ? '全部平台' : platform;
                return `<option value="${escapeHtml(platform)}" ${selected}>${escapeHtml(label)}</option>`;
            }).join('');

            const html = `
                <div class="drawer-card">
                    <div class="drawer-toolbar">
                        <div class="drawer-card-title" style="margin:0;">客诉采集记录</div>
                        <select class="drawer-select" id="complaint-platform-filter">${options}</select>
                    </div>
                    ${rows ? `
                        <table class="drawer-table">
                            <thead>
                                <tr><th>平台</th><th>关键词</th><th>数量</th><th>时间</th></tr>
                            </thead>
                            <tbody>${rows}</tbody>
                        </table>
                        <div class="drawer-pagination">
                            <button class="drawer-btn" id="complaint-page-prev" ${complaintState.page <= 1 ? 'disabled' : ''}>上一页</button>
                            <span>第 ${complaintState.page} / ${totalPages} 页（共 ${filtered.length} 条）</span>
                            <button class="drawer-btn" id="complaint-page-next" ${complaintState.page >= totalPages ? 'disabled' : ''}>下一页</button>
                        </div>
                    ` : '<div class="drawer-empty">暂无客诉采集记录</div>'}
                    <div class="drawer-detail">${getCollectionDetailPanelHtml()}</div>
                </div>
                <div class="drawer-card-title" style="margin: 8px 0;">关联预警</div>
                ${alertsHtml || '<div class="drawer-empty">暂无客诉相关预警</div>'}
            `;
            showDetailDrawer('客诉追踪明细', html);
            bindComplaintDrawerEvents();
        }

        function renderReportDrawer(reportData) {
            const report = reportData?.report || {};
            const stat = report.statistics || {};
            const feature = report.features || {};

            const html = `
                <div class="drawer-card">
                    <div class="drawer-card-title">系统报告摘要</div>
                    <table class="drawer-table">
                        <tbody>
                            <tr><th>生成时间</th><td>${report.report_time || '-'}</td></tr>
                            <tr><th>系统状态</th><td>${report.system_status || '-'}</td></tr>
                            <tr><th>采集记录数</th><td>${stat.collections_count ?? 0}</td></tr>
                            <tr><th>分析记录数</th><td>${stat.analysis_count ?? 0}</td></tr>
                            <tr><th>任务数</th><td>${stat.tasks_count ?? 0}</td></tr>
                            <tr><th>运行时长(秒)</th><td>${Math.floor(stat.uptime_seconds || 0)}</td></tr>
                        </tbody>
                    </table>
                </div>
                <div class="drawer-card">
                    <div class="drawer-card-title">能力覆盖</div>
                    <div><strong>采集：</strong>${(feature.collection || []).join('、') || '-'}</div>
                    <div style="margin-top:6px;"><strong>处理：</strong>${(feature.processing || []).join('、') || '-'}</div>
                    <div style="margin-top:6px;"><strong>分析：</strong>${(feature.analysis || []).join('、') || '-'}</div>
                </div>
            `;

            showDetailDrawer('舆情报告明细', html);
        }

        async function loadDashboardData() {
            try {
                const response = await apiRequest('/api/dashboard/education');
                if (!response.success) return;

                const dashboard = response.dashboard || {};
                const overview = dashboard.overview || {};

                document.getElementById('heat-total').textContent = (overview.total_heat || 0).toLocaleString('zh-CN');
                updateNews(dashboard.news || []);
                updateSentiment(dashboard.sentiment || {});
                updateTrend(dashboard.trend || {});
                updateMapData(dashboard.province_heat || []);
                updateAlerts(dashboard.alerts || []);

                const topRegion = (dashboard.province_heat || [])[0];
                if (topRegion) {
                    updateMapSelection(topRegion.name, topRegion.value);
                }
            } catch (error) {
                console.error('加载大屏数据失败:', error);
            }
        }

        async function loadRealtimeViewData() {
            const [realtimeData, dashboardData] = await Promise.all([
                safeApiRequest('/api/realtime/data?limit=120'),
                safeApiRequest('/api/dashboard/education')
            ]);

            if (dashboardData && dashboardData.success) {
                updateNews(dashboardData.dashboard?.news || []);
                updateMapData(dashboardData.dashboard?.province_heat || []);
                updateSentiment(dashboardData.dashboard?.sentiment || {});
                const topRegion = (dashboardData.dashboard?.province_heat || [])[0];
                if (topRegion) updateMapSelection(topRegion.name, topRegion.value);
            }

            if (realtimeData && realtimeData.success) {
                const items = realtimeData.data || [];
                document.getElementById('heat-total').textContent = items.length.toLocaleString('zh-CN');
                updateTrend(convertRealtimeToTrend(items));
            }
        }

        async function loadAlertViewData() {
            const [alertStats, activeAlerts, dashboardData] = await Promise.all([
                safeApiRequest('/api/alert/stats'),
                safeApiRequest('/api/alert/active'),
                safeApiRequest('/api/dashboard/education')
            ]);

            if (alertStats && alertStats.success) {
                const total = alertStats.stats?.total_alerts || 0;
                const active = alertStats.stats?.active_alerts || 0;
                document.getElementById('heat-total').textContent = `${total} / ${active}`;
            }

            if (activeAlerts && activeAlerts.success) {
                updateAlerts(activeAlerts.alerts || []);
                updateNews((activeAlerts.alerts || []).map(a => a.message || a.title || '预警事件').slice(0, 10));
            }

            if (dashboardData && dashboardData.success) {
                updateMapData(dashboardData.dashboard?.province_heat || []);
                updateTrend(dashboardData.dashboard?.trend || {});
            }
        }

        async function loadComplaintViewData() {
            const [collectionsData, activeAlerts] = await Promise.all([
                safeApiRequest('/api/collections'),
                safeApiRequest('/api/alert/active')
            ]);

            const collections = collectionsData?.success ? (collectionsData.collections || []) : [];
            const alerts = activeAlerts?.success ? (activeAlerts.alerts || []) : [];
            complaintState.collections = collections;
            complaintState.alerts = alerts;
            complaintState.page = 1;
            complaintState.selectedCollectionId = null;
            complaintState.selectedCollectionDetail = null;
            complaintState.detailCache = {};
            renderComplaintDrawer();

            const first = complaintState.filteredCollections[0];
            if (first && first.id) {
                await loadCollectionDetail(first.id);
            }
        }

        async function loadReportViewData() {
            const reportData = await safeApiRequest('/api/report');
            renderReportDrawer(reportData || {});
        }

        async function loadIntelViewData() {
            const [intelStats, dashboardData] = await Promise.all([
                safeApiRequest('/api/intel/stats'),
                safeApiRequest('/api/dashboard/education')
            ]);

            if (intelStats && intelStats.success) {
                const stats = intelStats.stats || {};
                const totalIntel = stats.total_intel || 0;
                document.getElementById('heat-total').textContent = totalIntel.toLocaleString('zh-CN');

                const topKeywords = (stats.top_keywords || []).map(k => typeof k === 'string' ? k : (k.keyword || k.name)).filter(Boolean);
                if (topKeywords.length) updateHotWords(topKeywords);
            }

            if (dashboardData && dashboardData.success) {
                const d = dashboardData.dashboard || {};
                updateNews(d.news || []);
                updateSentiment(d.sentiment || {});
                updateTrend(d.trend || {});
                updateMapData(d.province_heat || []);
            }
        }

        async function switchView(view) {
            currentView = view;
            updateViewTitle(view);

            if (view === 'overview') {
                await loadDashboardData();
                return;
            }

            if (view === 'realtime') {
                await loadRealtimeViewData();
                return;
            }

            if (view === 'alert' || view === 'complaints') {
                await loadAlertViewData();
                if (view === 'complaints') {
                    await loadComplaintViewData();
                } else {
                    hideDetailDrawer();
                }
                return;
            }

            if (view === 'report') {
                await loadIntelViewData();
                await loadReportViewData();
                return;
            }

            if (view === 'setting') {
                hideDetailDrawer();
                return;
            }

            hideDetailDrawer();
            await loadIntelViewData();
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'f' || e.key === 'F') toggleFullscreen();
            if (e.key === 'Escape') document.body.classList.remove('fullscreen');
        });

        document.addEventListener('DOMContentLoaded', () => {
            updateClock();
            setInterval(updateClock, 1000);
            bindSidebar();
            initTrendChart();
            initChinaMap();
            switchView('overview');
            setInterval(() => switchView(currentView), 30000);
        });
    </script>
</body>
</html>
'''
