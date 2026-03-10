"""
全国主流平台舆情检测中心大屏

参考行业大屏布局，保留左侧导航。
适配后续超大屏展示场景。
"""

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>全国主流平台舆情检测中心</title>
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
            grid-template-rows: 88px 1fr;
            gap: 10px;
            padding: 10px;
        }

        .topbar {
            grid-column: 1 / -1;
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            background: linear-gradient(90deg, #0a1730 0%, #102a52 50%, #0a1730 100%);
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: 0 0 18px rgba(43, 215, 255, 0.12);
            padding: 10px 18px;
            gap: 16px;
        }

        .top-title {
            font-size: 28px;
            font-weight: 700;
            color: #f2f7ff;
            letter-spacing: 2px;
        }

        .top-meta {
            display: flex;
            gap: 12px 18px;
            align-items: center;
            justify-content: flex-end;
            flex-wrap: wrap;
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

        .query-controls {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            justify-content: flex-end;
        }

        .query-presets {
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
            justify-content: flex-end;
            width: 100%;
        }

        .preset-btn {
            height: 30px;
            padding: 0 10px;
            border-radius: 999px;
            border: 1px solid rgba(111, 203, 255, 0.25);
            background: rgba(15, 39, 75, 0.82);
            color: #bfe3ff;
            font-size: 12px;
            cursor: pointer;
            transition: 0.2s ease;
        }

        .preset-btn:hover,
        .preset-btn.active {
            background: linear-gradient(180deg, rgba(46, 140, 255, 0.42), rgba(16, 75, 150, 0.72));
            color: #ffffff;
            border-color: rgba(111, 203, 255, 0.45);
        }

        .query-input,
        .query-select {
            height: 34px;
            border: 1px solid var(--line);
            border-radius: 6px;
            background: #0f274b;
            color: #dce9ff;
            padding: 0 10px;
            font-size: 13px;
            outline: none;
        }

        .query-input {
            width: 220px;
        }

        .query-platforms {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            color: #9fc3ee;
            font-size: 12px;
            max-width: 600px;
        }

        .query-platforms label {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            cursor: pointer;
            padding: 3px 8px;
            border-radius: 999px;
            border: 1px solid rgba(111, 203, 255, 0.2);
            background: rgba(15, 39, 75, 0.75);
            white-space: nowrap;
        }

        .query-platforms input {
            accent-color: var(--cyan);
        }

        .btn-primary {
            background: linear-gradient(180deg, #0fb57f, #0b8b62);
            border-color: rgba(56, 209, 153, 0.5);
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
            font-size: 18px;
            font-weight: 700;
            color: var(--yellow);
            font-family: ui-monospace, Menlo, Monaco, Consolas, monospace;
        }

        .sentiment-ring {
            width: 124px;
            height: 124px;
            border-radius: 50%;
            margin: 0 auto;
            border: 8px solid #15345f;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            background: conic-gradient(var(--green) 0 46%, var(--yellow) 46% 78%, var(--red) 78% 100%);
        }

        .sentiment-ring::after {
            content: "";
            width: 78px;
            height: 78px;
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
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .sentiment-overview {
            display: grid;
            grid-template-columns: 124px 1fr;
            gap: 12px;
            align-items: center;
            min-height: 0;
        }

        .sentiment-metrics {
            display: grid;
            gap: 8px;
        }

        .subpanel-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: var(--cyan);
            font-size: 14px;
            font-weight: 600;
            padding-top: 2px;
        }

        .hot-words-cloud {
            display: flex;
            flex-wrap: wrap;
            align-content: flex-start;
            gap: 10px 8px;
            padding: 12px;
            min-height: 144px;
            border: 1px solid var(--line-soft);
            border-radius: 10px;
            background: radial-gradient(circle at top left, rgba(43, 215, 255, 0.12), rgba(13, 26, 50, 0.92) 62%);
            overflow: auto;
        }

        .hot-word-item {
            --accent: #49cbff;
            --size: 18px;
            display: inline-flex;
            align-items: center;
            max-width: 100%;
            min-height: 34px;
            padding: 6px 12px;
            border-radius: 999px;
            border: 1px solid color-mix(in srgb, var(--accent) 45%, transparent);
            background: color-mix(in srgb, var(--accent) 12%, rgba(8, 20, 39, 0.88));
            box-shadow: inset 0 0 18px color-mix(in srgb, var(--accent) 10%, transparent);
            color: var(--accent);
            font-size: var(--size);
            font-weight: 700;
            line-height: 1.15;
            letter-spacing: 0.5px;
            white-space: normal;
            word-break: break-all;
        }

        .hot-word-item[data-rank="1"] {
            min-height: 42px;
            padding: 8px 16px;
        }

        .hot-word-item[data-rank="2"],
        .hot-word-item[data-rank="3"] {
            padding: 7px 14px;
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

        .drawer-input,
        .drawer-textarea {
            width: 100%;
            background: #102a50;
            color: #dce9ff;
            border: 1px solid var(--line);
            border-radius: 6px;
            padding: 8px 10px;
            font-size: 12px;
        }

        .drawer-textarea {
            min-height: 70px;
            resize: vertical;
        }

        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }

        .form-grid-full {
            grid-column: 1 / -1;
        }

        .form-label {
            color: #8fb0df;
            font-size: 12px;
            margin-bottom: 6px;
            display: block;
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
                grid-template-rows: 100px 1fr;
            }

            .main {
                grid-template-columns: 240px 1fr 280px;
            }

            .top-title {
                font-size: 24px;
            }

            .query-platforms {
                max-width: 520px;
            }

            .sentiment-overview {
                grid-template-columns: 1fr;
            }

            .sentiment-ring {
                width: 116px;
                height: 116px;
            }

            .sentiment-ring::after {
                width: 74px;
                height: 74px;
            }

            .hot-words-cloud {
                min-height: 128px;
                padding: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="screen">
        <header class="topbar">
            <div class="top-title" id="top-title">全国主流平台舆情检测中心</div>
            <div class="top-meta">
                <div class="query-controls">
                    <input id="pipeline-keyword" class="query-input" type="text" placeholder="输入公司/产品/事件关键词" value="舆情热点" />
                    <select id="pipeline-max-items" class="query-select">
                        <option value="30">30条/平台</option>
                        <option value="60">60条/平台</option>
                        <option value="100" selected>100条/平台</option>
                        <option value="150">150条/平台</option>
                        <option value="200">200条/平台</option>
                        <option value="300">300条/平台</option>
                        <option value="500">500条/平台</option>
                    </select>
                    <div class="query-platforms" id="pipeline-platforms">
                        <label><input type="checkbox" value="weibo" checked />微博</label>
                        <label><input type="checkbox" value="douyin" checked />抖音</label>
                        <label><input type="checkbox" value="kuaishou" />快手</label>
                        <label><input type="checkbox" value="zhihu" checked />知乎</label>
                        <label><input type="checkbox" value="baidu" checked />百度</label>
                        <label><input type="checkbox" value="wechat" />公众号</label>
                        <label><input type="checkbox" value="xiaohongshu" />小红书</label>
                        <label><input type="checkbox" value="bilibili" />B站</label>
                        <label><input type="checkbox" value="tieba" checked />贴吧</label>
                        <label><input type="checkbox" value="toutiao" />头条</label>
                    </div>
                    <button id="pipeline-run-btn" class="btn btn-primary" onclick="runDashboardPipeline()">一键采集分析</button>
                    <div class="query-presets" id="pipeline-presets">
                        <button class="preset-btn active" type="button" data-preset="brand" onclick="applyPipelinePreset('brand', this)">品牌舆情</button>
                        <button class="preset-btn" type="button" data-preset="complaint" onclick="applyPipelinePreset('complaint', this)">客诉投诉</button>
                        <button class="preset-btn" type="button" data-preset="competitor" onclick="applyPipelinePreset('competitor', this)">竞品对比</button>
                        <button class="preset-btn" type="button" data-preset="deep-report" onclick="applyPipelinePreset('deep-report', this)">深度报告</button>
                    </div>
                </div>
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
                <div class="side-item" data-view="group-overview">🧩 分组总览</div>
                <div class="side-item" data-view="competitor-overview">⚔ 竞品对比</div>
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
                    <div class="news-item">政策动态：新规发布，关注交互质量提升</div>
                    <div class="news-item">用户热议课后服务价格标准，多地出台透明化公示方案</div>
                    <div class="news-item">全国重点区域春季业务启动，咨询量环比增长 18%</div>
                    <div class="news-item">“双减”执行后培训服务升级，满意度持续上升</div>
                    <div class="news-item">平台食品安全话题升温，集团专项督导已上线</div>
                    <div class="news-item">AI 教学辅助工具试点扩容，师生互动效率提升</div>
                </div>
            </section>

            <section class="panel" style="grid-column: 2; grid-row: 1;">
                <div class="panel-header">
                    <span id="panel-map-title">全国舆情热力分布</span>
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
                    <div class="sentiment-overview">
                        <div class="sentiment-ring">
                            <div class="sentiment-face">🙂</div>
                        </div>
                        <div class="sentiment-metrics">
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
                        </div>
                    </div>

                    <div class="subpanel-title"><span>热词分析</span><small>实时</small></div>
                    <div class="hot-words-cloud" id="hot-words">
                        <span class="hot-word-item" data-rank="1" style="--size: 28px; --accent: #49cbff;">舆情热点</span>
                        <span class="hot-word-item" data-rank="2" style="--size: 22px; --accent: #2e8cff;">用户态度</span>
                        <span class="hot-word-item" data-rank="3" style="--size: 24px; --accent: #87ddff;">服务评价</span>
                        <span class="hot-word-item" data-rank="4" style="--size: 18px; --accent: #6fcbff;">业务动态</span>
                        <span class="hot-word-item" data-rank="5" style="--size: 20px; --accent: #4fbaff;">风险预警</span>
                        <span class="hot-word-item" data-rank="6" style="--size: 16px; --accent: #9cd9ff;">正面传播</span>
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
                    本次舆情主要集中在用户体验与服务透明度两个维度，讨论来源以主流社交平台与用户社群为主。
                    其中“关键业务”“消费透明度”相关话题热度上升明显。建议持续跟踪高频关键词，结合工单系统联动处置，
                    对重点投诉在 2 小时内完成首次响应并发布统一解释口径。
                </div>
            </section>

            <section class="risk-box">
                <div class="risk-title">最新动态 / 风险提示</div>
                <div class="risk-list" id="risk-list">
                    <div class="risk-item">【高优】核心业务“退费处理慢”讨论量 1 小时增长 67%，建议客服中心加派坐席。</div>
                    <div class="risk-item">【中优】“服务体验反馈”在用户社群扩散，建议业务部门发布说明与学习路径建议。</div>
                    <div class="risk-item">【建议】“服务设施优化”获得较多正向反馈，可作为官方正面传播素材。</div>
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
        let latestPipelineResult = null;
        let pipelineRunning = false;
        const monitorState = {
            monitors: [],
            groups: [],
            selectedId: null,
            selectedGroupId: ''
        };
        const competitorState = {
            baseGroupId: ''
        };
        const PIPELINE_PRESETS = {
            brand: {
                maxItems: 100,
                platforms: ['weibo', 'douyin', 'zhihu', 'baidu', 'tieba']
            },
            complaint: {
                maxItems: 150,
                platforms: ['weibo', 'douyin', 'kuaishou', 'xiaohongshu', 'toutiao']
            },
            competitor: {
                maxItems: 200,
                platforms: ['weibo', 'douyin', 'zhihu', 'bilibili', 'tieba', 'toutiao']
            },
            'deep-report': {
                maxItems: 500,
                platforms: ['weibo', 'douyin', 'kuaishou', 'zhihu', 'baidu', 'wechat', 'xiaohongshu', 'bilibili', 'tieba', 'toutiao']
            }
        };
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
            overview: { top: '全国主流平台舆情检测中心', news: '热门新闻', map: '全国主流平台舆情热力分布', sentiment: '社会情绪指数', trend: '发展趋势' },
            realtime: { top: '全国主流平台实时舆情监测中心', news: '实时舆情流', map: '实时区域分布', sentiment: '情绪变化', trend: '小时趋势' },
            sentiment: { top: '全国主流平台情感分析中心', news: '情感样本', map: '情感地域分布', sentiment: '情感统计', trend: '情感趋势' },
            complaints: { top: '全国主流平台客诉追踪中心', news: '最新客诉', map: '客诉区域分布', sentiment: '客诉情绪', trend: '客诉趋势' },
            keywords: { top: '全国主流平台关键词监控中心', news: '关键词相关动态', map: '关键词区域分布', sentiment: '关键词情感', trend: '关键词热度趋势' },
            'group-overview': { top: '全国主流平台监控分组总览', news: '分组动态摘要', map: '分组覆盖区域', sentiment: '分组风险分布', trend: '分组热度对比' },
            'competitor-overview': { top: '全国主流平台竞品对比中心', news: '竞品动态摘要', map: '竞品关注焦点', sentiment: '竞争态势判断', trend: '竞品热度对比' },
            trend: { top: '全国主流平台趋势分析中心', news: '趋势相关新闻', map: '趋势区域分布', sentiment: '趋势情绪', trend: '综合趋势' },
            report: { top: '全国主流平台舆情报告中心', news: '报告摘要', map: '报告区域摘要', sentiment: '报告情绪摘要', trend: '报告趋势摘要' },
            alert: { top: '全国主流平台危机预警中心', news: '预警相关动态', map: '预警区域分布', sentiment: '风险情绪', trend: '预警趋势' },
            setting: { top: '全国主流平台系统配置中心', news: '系统公告', map: '系统覆盖区域', sentiment: '服务状态', trend: '系统运行趋势' }
        };

        async function apiRequest(url) {
            const response = await fetch(API_BASE + url);
            return response.json();
        }

        async function apiPost(url, payload) {
            const response = await fetch(API_BASE + url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload || {})
            });
            return response.json();
        }

        async function apiPut(url, payload) {
            const response = await fetch(API_BASE + url, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload || {})
            });
            return response.json();
        }

        async function apiDelete(url) {
            const response = await fetch(API_BASE + url, { method: 'DELETE' });
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
                const size = [28, 24, 22, 20, 18, 17, 16, 16][index] || 16;
                const color = ['#49cbff', '#4fbaff', '#6fcbff', '#2e8cff', '#87ddff'][index % 5];
                return `<span class="hot-word-item" data-rank="${index + 1}" style="--size:${size}px;--accent:${color};">${escapeHtml(word)}</span>`;
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
                content.textContent = `${name} 当前舆情热度为 ${value}，主要讨论集中在服务质量、业务评价和用户反馈。` +
                    `建议该地区加强高频投诉处理，并在 2 小时内完成首次公开响应。`;
            }

            if (riskList) {
                riskList.innerHTML = `
                    <div class="risk-item">【高优】${name} 地区“价格标准”相关讨论持续增长，建议发布费用构成说明。</div>
                    <div class="risk-item">【中优】${name} 用户社群出现课程体验反馈分化，建议同步教研优化计划。</div>
                    <div class="risk-item">【建议】${name} 正向内容可围绕“师资建设”和“交互成果”加强传播。</div>
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

        function updateTrendFromSeries(series) {
            if (!Array.isArray(series) || !series.length) return;
            const trend = {};
            series.slice(-10).forEach((point) => {
                const key = point.time || '-';
                trend[key] = point.count || 0;
            });
            updateTrend(trend);
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

        function getSelectedPlatforms() {
            const checked = Array.from(document.querySelectorAll('#pipeline-platforms input[type="checkbox"]:checked'));
            const values = checked.map(item => item.value).filter(Boolean);
            return values.length ? values : ['weibo', 'douyin', 'zhihu', 'baidu', 'tieba'];
        }

        function applyPipelinePreset(name, trigger) {
            const preset = PIPELINE_PRESETS[name];
            if (!preset) return;

            const maxItemsEl = document.getElementById('pipeline-max-items');
            if (maxItemsEl) {
                maxItemsEl.value = String(preset.maxItems);
            }

            const platformInputs = document.querySelectorAll('#pipeline-platforms input[type="checkbox"]');
            platformInputs.forEach((input) => {
                input.checked = preset.platforms.includes(input.value);
            });

            document.querySelectorAll('#pipeline-presets .preset-btn').forEach((button) => {
                button.classList.toggle('active', button === trigger || button.getAttribute('data-preset') === name);
            });
        }

        function updateByPipelineResult(result) {
            if (!result || !result.success) return;
            latestPipelineResult = result;

            document.getElementById('heat-total').textContent = (result.total_items || 0).toLocaleString('zh-CN');

            const sentimentStat = result.analysis?.sentiment?.data?.statistics || {};
            updateSentiment({
                positive: sentimentStat.positive_count || 0,
                neutral: sentimentStat.neutral_count || 0,
                negative: sentimentStat.negative_count || 0
            });

            const trendSeries = result.analysis?.trend?.data?.time_series || [];
            updateTrendFromSeries(trendSeries);

            const riskFactors = result.analysis?.risk?.data?.risk_factors || [];
            updateAlerts(riskFactors.map(item => ({ message: item })));

            const hotWords = (result.wordcloud || []).slice(0, 8).map(item => item.name).filter(Boolean);
            if (hotWords.length) updateHotWords(hotWords);

            const reportFindings = result.report?.findings || [];
            if (reportFindings.length) updateNews(reportFindings);
        }

        function renderGroupOverviewDrawer(data) {
            const groups = data?.groups || [];
            const rows = groups.map((item) => `
                <tr>
                    <td>${escapeHtml(item.name)}</td>
                    <td>${item.monitor_count || 0}</td>
                    <td>${item.heat || 0}</td>
                    <td>${item.risk_score || 0}</td>
                    <td>${Math.round((item.negative_ratio || 0) * 100)}%</td>
                    <td>${escapeHtml((item.top_keywords || []).join('、') || '-')}</td>
                </tr>
            `).join('');

            const html = `
                <div class="drawer-card">
                    <div class="drawer-card-title">分组风险对比</div>
                    ${rows ? `
                        <table class="drawer-table">
                            <thead><tr><th>分组</th><th>对象数</th><th>热度</th><th>风险分</th><th>负面占比</th><th>关注词</th></tr></thead>
                            <tbody>${rows}</tbody>
                        </table>
                    ` : '<div class="drawer-empty">暂无分组监控数据，请先创建并执行监控对象</div>'}
                </div>
            `;
            showDetailDrawer('监控分组总览', html);
        }

        function renderCompetitorOverviewDrawer(data) {
            const groups = data?.groups || [];
            const comparisons = data?.comparisons || [];
            const baseGroup = data?.base_group || {};
            const options = groups.map((item) => `
                <option value="${escapeHtml(item.group_id || '')}" ${item.group_id === baseGroup.group_id ? 'selected' : ''}>${escapeHtml(item.name || '未命名分组')}</option>
            `).join('');
            const rows = comparisons.map((item) => `
                <tr>
                    <td>${escapeHtml(item.rival_name || '-')}</td>
                    <td>${escapeHtml(item.status || '-')}</td>
                    <td>${item.heat_gap > 0 ? '+' : ''}${item.heat_gap || 0}</td>
                    <td>${item.risk_gap > 0 ? '+' : ''}${item.risk_gap || 0}</td>
                    <td>${Math.round((item.negative_gap || 0) * 100)}%</td>
                    <td>${escapeHtml((item.keyword_overlap || []).join('、') || '-')}</td>
                </tr>
            `).join('');
            const strongestRival = data?.overview?.strongest_rival || '暂无';

            const html = `
                <div class="drawer-card">
                    <div class="drawer-card-title">竞品对比设置</div>
                    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
                        <select id="competitor-base-group" style="min-width:220px;padding:8px 10px;background:rgba(10,25,47,0.9);border:1px solid rgba(111,203,255,0.35);color:#dff5ff;border-radius:8px;" onchange="changeCompetitorBaseGroup(this.value)">
                            ${options}
                        </select>
                        <span style="color:#8bbce6;">当前基准：${escapeHtml(baseGroup.name || '暂无')}</span>
                        <span style="color:#8bbce6;">重点竞品：${escapeHtml(strongestRival)}</span>
                    </div>
                </div>
                <div class="drawer-card">
                    <div class="drawer-card-title">竞争态势摘要</div>
                    <div style="color:#cfe8ff;line-height:1.8;">
                        ${(comparisons[0]?.summary) ? escapeHtml(comparisons[0].summary) : '暂无竞品对比数据，请至少准备两个已执行的监控分组。'}
                    </div>
                </div>
                <div class="drawer-card">
                    <div class="drawer-card-title">竞品横向对比</div>
                    ${rows ? `
                        <table class="drawer-table">
                            <thead><tr><th>竞品分组</th><th>态势</th><th>热度差</th><th>风险分差</th><th>负面差</th><th>共同关注</th></tr></thead>
                            <tbody>${rows}</tbody>
                        </table>
                    ` : '<div class="drawer-empty">暂无竞品对比数据，请先创建至少两个分组并执行监控对象</div>'}
                </div>
            `;
            showDetailDrawer('竞品对比', html);
        }

        function changeCompetitorBaseGroup(groupId) {
            competitorState.baseGroupId = groupId || '';
            loadCompetitorOverviewData(competitorState.baseGroupId);
        }

        async function runDashboardPipeline() {
            if (pipelineRunning) {
                return;
            }

            const runBtn = document.getElementById('pipeline-run-btn');
            const keywordInput = document.getElementById('pipeline-keyword');
            const maxItemsEl = document.getElementById('pipeline-max-items');
            const keyword = (keywordInput?.value || '').trim();

            if (!keyword) {
                alert('请先输入关键词，例如公司名或产品名。');
                return;
            }

            const payload = {
                keyword,
                max_items: Number(maxItemsEl?.value || 60),
                platforms: getSelectedPlatforms()
            };

            try {
                pipelineRunning = true;
                if (runBtn) {
                    runBtn.disabled = true;
                    runBtn.textContent = '采集中...';
                }

                const result = await safeApiPost('/api/dashboard/pipeline', payload);
                if (!result || !result.success) {
                    const message = result?.message || '采集分析失败，请检查平台可用性后重试';
                    alert(message);
                    return;
                }

                updateByPipelineResult(result);
                renderReportDrawer({ report: result.report, pipeline: result });
            } finally {
                pipelineRunning = false;
                if (runBtn) {
                    runBtn.disabled = false;
                    runBtn.textContent = '一键采集分析';
                }
            }
        }

        async function safeApiPost(url, payload) {
            try {
                return await apiPost(url, payload);
            } catch (error) {
                console.error(`请求失败: ${url}`, error);
                return null;
            }
        }

        async function safeApiPut(url, payload) {
            try {
                return await apiPut(url, payload);
            } catch (error) {
                console.error(`请求失败: ${url}`, error);
                return null;
            }
        }

        async function safeApiDelete(url) {
            try {
                return await apiDelete(url);
            } catch (error) {
                console.error(`请求失败: ${url}`, error);
                return null;
            }
        }

        function exportCurrentReport(format) {
            const pipelineId = latestPipelineResult?.pipeline_id;
            if (!pipelineId) {
                alert('当前没有可导出的报告，请先执行一次采集分析。');
                return;
            }
            window.open(`${API_BASE}/api/reports/${encodeURIComponent(pipelineId)}/export?format=${encodeURIComponent(format)}`, '_blank');
        }

        function getSelectedMonitor() {
            return (monitorState.monitors || []).find(item => item.monitor_id === monitorState.selectedId) || null;
        }

        function populateMonitorForm(monitor) {
            const setValue = (id, value) => {
                const el = document.getElementById(id);
                if (el) el.value = value || '';
            };
            setValue('monitor-id', monitor?.monitor_id || '');
            setValue('monitor-name', monitor?.name || '');
            setValue('monitor-group-id', monitor?.group_id || '');
            setValue('monitor-tags', (monitor?.tags || []).join('，'));
            setValue('monitor-keywords', (monitor?.keywords || []).join('，'));
            setValue('monitor-platforms', (monitor?.platforms || []).join(','));
            setValue('monitor-interval', monitor?.interval_seconds || 1800);
            setValue('monitor-max-items', monitor?.max_items || 60);
            setValue('monitor-negative-threshold', monitor?.thresholds?.negative_ratio ?? 0.3);
            setValue('monitor-risk-threshold', monitor?.thresholds?.risk_score ?? 50);
            setValue('monitor-min-items', monitor?.thresholds?.min_items ?? 30);
        }

        function bindMonitorDrawerEvents() {
            document.querySelectorAll('.drawer-row[data-monitor-id]').forEach((row) => {
                row.onclick = () => {
                    monitorState.selectedId = row.getAttribute('data-monitor-id');
                    renderMonitorDrawer();
                };
            });
            const resetBtn = document.getElementById('monitor-reset-btn');
            if (resetBtn) {
                resetBtn.onclick = () => {
                    monitorState.selectedId = null;
                    renderMonitorDrawer();
                };
            }
            const saveBtn = document.getElementById('monitor-save-btn');
            if (saveBtn) saveBtn.onclick = saveMonitorFromForm;
            const deleteBtn = document.getElementById('monitor-delete-btn');
            if (deleteBtn) deleteBtn.onclick = deleteSelectedMonitor;
            const runBtn = document.getElementById('monitor-run-btn');
            if (runBtn) runBtn.onclick = runSelectedMonitor;
            const groupSaveBtn = document.getElementById('monitor-group-save-btn');
            if (groupSaveBtn) groupSaveBtn.onclick = saveMonitorGroupFromForm;
            const groupDeleteBtn = document.getElementById('monitor-group-delete-btn');
            if (groupDeleteBtn) groupDeleteBtn.onclick = deleteSelectedGroup;
            const groupFilter = document.getElementById('monitor-group-filter');
            if (groupFilter) {
                groupFilter.onchange = () => {
                    monitorState.selectedGroupId = groupFilter.value || '';
                    renderMonitorDrawer();
                };
            }
            document.querySelectorAll('.drawer-row[data-group-id]').forEach((row) => {
                row.onclick = () => {
                    monitorState.selectedGroupId = row.getAttribute('data-group-id') || '';
                    renderMonitorDrawer();
                };
            });
        }

        async function saveMonitorGroupFromForm() {
            const selectedGroupId = monitorState.selectedGroupId;
            const payload = {
                name: document.getElementById('monitor-group-name')?.value || '',
                description: document.getElementById('monitor-group-description')?.value || '',
                color: document.getElementById('monitor-group-color')?.value || '#2e8cff'
            };
            const result = selectedGroupId
                ? await safeApiPut(`/api/monitor-groups/${encodeURIComponent(selectedGroupId)}`, payload)
                : await safeApiPost('/api/monitor-groups', payload);
            if (!result || !result.success) {
                alert(result?.message || '保存分组失败');
                return;
            }
            monitorState.selectedGroupId = result.group?.group_id || '';
            await loadSettingsViewData();
        }

        async function deleteSelectedGroup() {
            if (!monitorState.selectedGroupId) {
                alert('请先选择一个分组。');
                return;
            }
            const result = await safeApiDelete(`/api/monitor-groups/${encodeURIComponent(monitorState.selectedGroupId)}`);
            if (!result || !result.success) {
                alert(result?.message || '删除分组失败');
                return;
            }
            monitorState.selectedGroupId = '';
            await loadSettingsViewData();
        }

        async function saveMonitorFromForm() {
            const monitorId = document.getElementById('monitor-id')?.value || '';
            const payload = {
                name: document.getElementById('monitor-name')?.value || '',
                group_id: document.getElementById('monitor-group-id')?.value || null,
                tags: document.getElementById('monitor-tags')?.value || '',
                keywords: document.getElementById('monitor-keywords')?.value || '',
                platforms: (document.getElementById('monitor-platforms')?.value || '').split(',').map(item => item.trim()).filter(Boolean),
                interval_seconds: Number(document.getElementById('monitor-interval')?.value || 1800),
                max_items: Number(document.getElementById('monitor-max-items')?.value || 60),
                thresholds: {
                    negative_ratio: Number(document.getElementById('monitor-negative-threshold')?.value || 0.3),
                    risk_score: Number(document.getElementById('monitor-risk-threshold')?.value || 50),
                    min_items: Number(document.getElementById('monitor-min-items')?.value || 30)
                },
                report_formats: ['docx', 'pdf'],
                enabled: true
            };
            const result = monitorId
                ? await safeApiPut(`/api/monitors/${encodeURIComponent(monitorId)}`, payload)
                : await safeApiPost('/api/monitors', payload);
            if (!result || !result.success) {
                alert(result?.message || '保存监控对象失败');
                return;
            }
            monitorState.selectedId = result.monitor?.monitor_id || null;
            await loadSettingsViewData();
        }

        async function deleteSelectedMonitor() {
            const selected = getSelectedMonitor();
            if (!selected) {
                alert('请先选择一个监控对象。');
                return;
            }
            const result = await safeApiDelete(`/api/monitors/${encodeURIComponent(selected.monitor_id)}`);
            if (!result || !result.success) {
                alert(result?.message || '删除监控对象失败');
                return;
            }
            monitorState.selectedId = null;
            await loadSettingsViewData();
        }

        async function runSelectedMonitor() {
            const selected = getSelectedMonitor();
            if (!selected) {
                alert('请先选择一个监控对象。');
                return;
            }
            const result = await safeApiPost(`/api/monitors/${encodeURIComponent(selected.monitor_id)}/run`, {});
            if (!result || !result.success) {
                alert(result?.message || '执行监控对象失败');
                return;
            }
            const latestPipelineId = (result.pipeline_ids || []).slice(-1)[0];
            if (latestPipelineId && latestPipelineResult?.pipeline_id !== latestPipelineId) {
                const dashboardData = await safeApiRequest('/api/dashboard/education');
                if (dashboardData?.success) {
                    const latest = dashboardData.dashboard?.latest_report;
                    if (latest) latestPipelineResult = { report: latest, pipeline_id: latestPipelineId };
                }
            }
            await loadSettingsViewData();
            alert(`监控执行完成，生成 ${result.pipeline_ids?.length || 0} 份报告。`);
        }

        function renderMonitorDrawer() {
            const selected = getSelectedMonitor();
            const activeGroup = (monitorState.groups || []).find(item => item.group_id === monitorState.selectedGroupId) || null;
            const groupOptions = ['<option value="">未分组</option>'].concat(
                (monitorState.groups || []).map(group => {
                    const selectedAttr = group.group_id === selected?.group_id ? 'selected' : '';
                    return `<option value="${escapeHtml(group.group_id)}" ${selectedAttr}>${escapeHtml(group.name)}</option>`;
                })
            ).join('');
            const groupRows = (monitorState.groups || []).map(group => {
                const selectedClass = group.group_id === monitorState.selectedGroupId ? 'active' : '';
                return `
                    <tr class="drawer-row ${selectedClass}" data-group-id="${escapeHtml(group.group_id)}">
                        <td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${escapeHtml(group.color)};"></span></td>
                        <td>${escapeHtml(group.name)}</td>
                        <td>${escapeHtml(group.description || '-')}</td>
                    </tr>
                `;
            }).join('');
            const filteredMonitors = (monitorState.monitors || []).filter(item => {
                if (!monitorState.selectedGroupId) return true;
                return item.group_id === monitorState.selectedGroupId;
            });
            const rows = filteredMonitors.map(item => {
                const selectedClass = item.monitor_id === monitorState.selectedId ? 'active' : '';
                return `
                    <tr class="drawer-row ${selectedClass}" data-monitor-id="${escapeHtml(item.monitor_id)}">
                        <td>${escapeHtml(item.name)}</td>
                        <td>${escapeHtml((item.keywords || []).join(' / '))}</td>
                        <td>${escapeHtml((item.platforms || []).join(', '))}</td>
                        <td>${escapeHtml(item.last_status || 'idle')}</td>
                    </tr>
                `;
            }).join('');

            const html = `
                <div class="drawer-card">
                    <div class="drawer-card-title">监控分组</div>
                    ${groupRows ? `
                        <table class="drawer-table">
                            <thead><tr><th></th><th>名称</th><th>说明</th></tr></thead>
                            <tbody>${groupRows}</tbody>
                        </table>
                    ` : '<div class="drawer-empty">暂无分组</div>'}
                    <div class="form-grid" style="margin-top:10px;">
                        <div>
                            <label class="form-label">分组名称</label>
                            <input class="drawer-input" id="monitor-group-name" value="${escapeHtml(activeGroup?.name || '')}" placeholder="如：品牌组" />
                        </div>
                        <div>
                            <label class="form-label">分组颜色</label>
                            <input class="drawer-input" id="monitor-group-color" value="${escapeHtml(activeGroup?.color || '#2e8cff')}" placeholder="#2e8cff" />
                        </div>
                        <div class="form-grid-full">
                            <label class="form-label">分组说明</label>
                            <input class="drawer-input" id="monitor-group-description" value="${escapeHtml(activeGroup?.description || '')}" placeholder="如：品牌声量与客诉监控" />
                        </div>
                    </div>
                    <div class="drawer-toolbar" style="margin-top:10px;">
                        <button class="drawer-btn" id="monitor-group-save-btn">保存分组</button>
                        <button class="drawer-btn" id="monitor-group-delete-btn">删除分组</button>
                    </div>
                </div>
                <div class="drawer-card">
                    <div class="drawer-toolbar">
                        <div class="drawer-card-title" style="margin:0;">监控对象管理</div>
                        <select class="drawer-select" id="monitor-group-filter">
                            <option value="">全部分组</option>
                            ${(monitorState.groups || []).map(group => `<option value="${escapeHtml(group.group_id)}" ${group.group_id === monitorState.selectedGroupId ? 'selected' : ''}>${escapeHtml(group.name)}</option>`).join('')}
                        </select>
                        <button class="drawer-btn" id="monitor-reset-btn">新建</button>
                    </div>
                    ${rows ? `
                        <table class="drawer-table">
                            <thead><tr><th>名称</th><th>关键词</th><th>平台</th><th>状态</th></tr></thead>
                            <tbody>${rows}</tbody>
                        </table>
                    ` : '<div class="drawer-empty">暂无监控对象，请先创建</div>'}
                </div>
                <div class="drawer-card">
                    <div class="drawer-card-title">监控对象配置</div>
                    <input type="hidden" id="monitor-id" value="${escapeHtml(selected?.monitor_id || '')}" />
                    <div class="form-grid">
                        <div>
                            <label class="form-label">名称</label>
                            <input class="drawer-input" id="monitor-name" value="${escapeHtml(selected?.name || '')}" placeholder="如：品牌A客诉监控" />
                        </div>
                        <div>
                            <label class="form-label">所属分组</label>
                            <select class="drawer-select" id="monitor-group-id">${groupOptions}</select>
                        </div>
                        <div class="form-grid-full">
                            <label class="form-label">标签</label>
                            <input class="drawer-input" id="monitor-tags" value="${escapeHtml((selected?.tags || []).join('，'))}" placeholder="如：品牌，投诉，退款" />
                        </div>
                        <div>
                            <label class="form-label">平台</label>
                            <input class="drawer-input" id="monitor-platforms" value="${escapeHtml((selected?.platforms || ['weibo','zhihu','baidu']).join(','))}" placeholder="weibo,zhihu,baidu" />
                        </div>
                        <div class="form-grid-full">
                            <label class="form-label">关键词</label>
                            <textarea class="drawer-textarea" id="monitor-keywords" placeholder="多个关键词用逗号分隔">${escapeHtml((selected?.keywords || []).join('，'))}</textarea>
                        </div>
                        <div>
                            <label class="form-label">监控间隔（秒）</label>
                            <input class="drawer-input" id="monitor-interval" type="number" value="${escapeHtml(selected?.interval_seconds || 1800)}" />
                        </div>
                        <div>
                            <label class="form-label">每平台采集量</label>
                            <input class="drawer-input" id="monitor-max-items" type="number" value="${escapeHtml(selected?.max_items || 60)}" />
                        </div>
                        <div>
                            <label class="form-label">负面占比阈值</label>
                            <input class="drawer-input" id="monitor-negative-threshold" type="number" step="0.01" value="${escapeHtml(selected?.thresholds?.negative_ratio ?? 0.3)}" />
                        </div>
                        <div>
                            <label class="form-label">风险分阈值</label>
                            <input class="drawer-input" id="monitor-risk-threshold" type="number" step="1" value="${escapeHtml(selected?.thresholds?.risk_score ?? 50)}" />
                        </div>
                        <div>
                            <label class="form-label">采集量阈值</label>
                            <input class="drawer-input" id="monitor-min-items" type="number" step="1" value="${escapeHtml(selected?.thresholds?.min_items ?? 30)}" />
                        </div>
                    </div>
                    <div class="drawer-toolbar" style="margin-top:10px;">
                        <button class="drawer-btn" id="monitor-save-btn">保存</button>
                        <button class="drawer-btn" id="monitor-run-btn">立即执行</button>
                        <button class="drawer-btn" id="monitor-delete-btn">删除</button>
                    </div>
                </div>
            `;
            showDetailDrawer('系统设置 / 监控对象', html);
            populateMonitorForm(selected);
            bindMonitorDrawerEvents();
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
            const pipeline = reportData?.pipeline || latestPipelineResult;
            const pipelineReport = pipeline?.report;

            if (pipelineReport) {
                const findings = (pipelineReport.findings || []).map(item => `<li>${escapeHtml(item)}</li>`).join('');
                const recommendations = (pipelineReport.recommendations || []).map(item => `<li>${escapeHtml(item)}</li>`).join('');
                const aiInsight = pipelineReport.ai_insight || {};
                const aiActions = (aiInsight.action_recommendations || []).map(item => `<li>${escapeHtml(item)}</li>`).join('');
                const aiTalkingPoints = (aiInsight.pr_talking_points || []).map(item => `<li>${escapeHtml(item)}</li>`).join('');

                const html = `
                    <div class="drawer-card">
                        <div class="drawer-card-title">舆情/客诉分析报告</div>
                        <div class="drawer-toolbar" style="margin-bottom:8px;">
                            <button class="drawer-btn" onclick="exportCurrentReport('html')">导出 HTML</button>
                            <button class="drawer-btn" onclick="exportCurrentReport('docx')">导出 Word</button>
                            <button class="drawer-btn" onclick="exportCurrentReport('pdf')">导出 PDF</button>
                        </div>
                        <table class="drawer-table">
                            <tbody>
                                <tr><th>报告标题</th><td>${escapeHtml(pipelineReport.title || '-')}</td></tr>
                                <tr><th>生成时间</th><td>${escapeHtml(pipelineReport.generated_at || '-')}</td></tr>
                                <tr><th>关键词</th><td>${escapeHtml(pipeline?.keyword || '-')}</td></tr>
                                <tr><th>平台</th><td>${escapeHtml((pipeline?.platforms || []).join(', ') || '-')}</td></tr>
                                <tr><th>采集条数</th><td>${pipeline?.total_items || 0}</td></tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="drawer-card">
                        <div class="drawer-card-title">结论摘要</div>
                        <div>${escapeHtml(pipelineReport.summary || '-')}</div>
                    </div>
                    <div class="drawer-card">
                        <div class="drawer-card-title">关键发现</div>
                        <ol style="padding-left: 18px; line-height: 1.7;">${findings || '<li>暂无</li>'}</ol>
                    </div>
                    <div class="drawer-card">
                        <div class="drawer-card-title">参考建议</div>
                        <ol style="padding-left: 18px; line-height: 1.7;">${recommendations || '<li>暂无</li>'}</ol>
                    </div>
                    <div class="drawer-card">
                        <div class="drawer-card-title">AI 研判</div>
                        <div><strong>摘要：</strong>${escapeHtml(aiInsight.executive_summary || '暂无 AI 摘要')}</div>
                        <div style="margin-top:6px;"><strong>风险判断：</strong>${escapeHtml(aiInsight.risk_judgment || '暂无 AI 风险判断')}</div>
                        <div style="margin-top:6px;"><strong>来源：</strong>${escapeHtml(aiInsight.source || 'unknown')}</div>
                    </div>
                    <div class="drawer-card">
                        <div class="drawer-card-title">AI 处置建议</div>
                        <ol style="padding-left: 18px; line-height: 1.7;">${aiActions || '<li>暂无</li>'}</ol>
                    </div>
                    <div class="drawer-card">
                        <div class="drawer-card-title">AI 公关口径</div>
                        <ol style="padding-left: 18px; line-height: 1.7;">${aiTalkingPoints || '<li>暂无</li>'}</ol>
                    </div>
                `;
                showDetailDrawer('舆情报告明细', html);
                return;
            }

            const report = reportData?.report || {};
            const stat = report.statistics || {};
            const feature = report.features || {};
            const fallbackHtml = `
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
            showDetailDrawer('舆情报告明细', fallbackHtml);
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
                const cloud = dashboard.wordcloud || [];
                if (cloud.length) {
                    updateHotWords(cloud.slice(0, 8).map(item => item.name).filter(Boolean));
                }
                if (dashboard.latest_report && !latestPipelineResult) {
                    latestPipelineResult = { success: true, report: dashboard.latest_report, keyword: '最近监测', platforms: [] };
                }

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
            renderReportDrawer({ ...(reportData || {}), pipeline: latestPipelineResult });
        }

        async function loadGroupOverviewData() {
            const data = await safeApiRequest('/api/dashboard/groups-overview');
            if (!data || !data.success) {
                updateNews(['暂无分组总览数据，请先在系统设置中创建并执行监控对象。']);
                updateAlerts([{ message: '暂无分组风险数据' }]);
                renderGroupOverviewDrawer({ groups: [] });
                return;
            }

            document.getElementById('heat-total').textContent = `${data.overview?.group_count || 0}组 / ${data.overview?.monitor_count || 0}对象`;
            updateNews(data.news || []);
            updateTrend(data.trend || {});
            updateAlerts(data.alerts || []);
            updateHotWords(data.hot_words || []);

            const top = data.detail || {};
            const region = document.getElementById('ticker-region');
            const heat = document.getElementById('ticker-heat');
            const source = document.getElementById('ticker-source');
            const content = document.getElementById('ticker-content');
            if (region) region.textContent = `分组：${top.name || '暂无'}`;
            if (heat) heat.textContent = `风险分：${top.risk_score || 0} / 负面占比：${Math.round((top.negative_ratio || 0) * 100)}%`;
            if (source) source.textContent = `对象数：${top.monitor_count || 0} / 报告数：${top.pipeline_count || 0}`;
            if (content) content.textContent = top.latest_summary || '暂无分组摘要，请先执行监控对象。';

            renderGroupOverviewDrawer(data);
        }

        async function loadCompetitorOverviewData(baseGroupId) {
            const targetGroupId = baseGroupId || competitorState.baseGroupId;
            const query = targetGroupId ? `?base_group_id=${encodeURIComponent(targetGroupId)}` : '';
            const data = await safeApiRequest(`/api/dashboard/competitor-overview${query}`);
            if (!data || !data.success) {
                updateNews(['暂无竞品对比数据，请先创建并执行至少两个监控分组。']);
                updateAlerts([{ message: '暂无竞品风险对比数据' }]);
                renderCompetitorOverviewDrawer({ groups: [], comparisons: [] });
                return;
            }

            competitorState.baseGroupId = data.base_group?.group_id || '';
            document.getElementById('heat-total').textContent = `${data.overview?.base_group || '暂无'} / ${data.overview?.rival_count || 0}个竞品`;
            updateNews(data.news || []);
            updateTrend(data.trend || {});
            updateAlerts(data.alerts || []);
            updateHotWords(data.hot_words || []);

            const region = document.getElementById('ticker-region');
            const heat = document.getElementById('ticker-heat');
            const source = document.getElementById('ticker-source');
            const content = document.getElementById('ticker-content');
            if (region) region.textContent = `基准分组：${data.base_group?.name || '暂无'}`;
            if (heat) heat.textContent = `重点竞品：${data.overview?.strongest_rival || '暂无'}`;
            if (source) source.textContent = `竞品数量：${data.overview?.rival_count || 0}`;
            if (content) content.textContent = data.comparisons?.[0]?.summary || '暂无竞品对比结论，请先执行更多分组监控。';

            renderCompetitorOverviewDrawer(data);
        }

        async function loadSettingsViewData() {
            const [groupsData, monitorsData] = await Promise.all([
                safeApiRequest('/api/monitor-groups'),
                safeApiRequest('/api/monitors')
            ]);
            monitorState.groups = groupsData?.success ? (groupsData.groups || []) : [];
            monitorState.monitors = monitorsData?.success ? (monitorsData.monitors || []) : [];
            if (monitorState.selectedId && !monitorState.monitors.find(item => item.monitor_id === monitorState.selectedId)) {
                monitorState.selectedId = null;
            }
            if (monitorState.selectedGroupId && !monitorState.groups.find(item => item.group_id === monitorState.selectedGroupId)) {
                monitorState.selectedGroupId = '';
            }
            renderMonitorDrawer();
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

            if (view === 'group-overview') {
                await loadGroupOverviewData();
                return;
            }

            if (view === 'competitor-overview') {
                await loadCompetitorOverviewData();
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
                await loadSettingsViewData();
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
