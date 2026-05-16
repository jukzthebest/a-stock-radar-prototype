# AI A股策略雷达 MVP 原型

一个用于 A 股实盘选股与买卖点提醒系统的高保真可交互原型。

## 内容

- 总览仪表盘
- 策略配置
- 候选股池
- 个股详情 / 买卖点
- 实时预警 / 通知中心
- 风控排雷
- 回测复盘
- 数据源设置
- 移动端通知详情
- AKShare 免费数据可行性边界

## 本地运行

前端：

```bash
npm install
npm run dev
```

AKShare 后端：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

前端开发服务器已在 `vite.config.js` 中将 `/api` 代理到 `http://127.0.0.1:8000`。GitHub Pages 静态页没有内置后端，生产构建会请求浏览器本机的 `http://127.0.0.1:8000`；打开 Pages 前必须先在同一台电脑启动 FastAPI。

## AKShare API

- `GET /api/health`
- `GET /api/market/snapshot?limit=50&refresh=true`
- `GET /api/stocks/{code}/history?days=280`
- `GET /api/stocks/{code}/signal`
- `GET /api/limit-up-pool`
- `GET /api/candidates/today?scan_limit=120&limit=30`
- `GET /api/strategy/config`

说明：AKShare 免费数据源无 SLA。当前后端对东方财富接口失败做了新浪行情/历史数据 fallback，但 fallback 缺少流通市值、换手率等字段，候选结果会标记风险。

## 构建

```bash
npm run build
```

## 风险声明

该项目是研究和产品原型，不构成投资建议，不承诺胜率或收益。实盘使用前必须做数据校验、回测、风控和人工复核。
