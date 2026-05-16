import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  AlertTriangle,
  Bell,
  CheckCircle2,
  ChevronRight,
  Database,
  Gauge,
  GitBranch,
  LayoutDashboard,
  LineChart,
  MonitorSmartphone,
  Radar,
  ShieldAlert,
  SlidersHorizontal,
  Smartphone,
  Table2,
  XCircle,
} from 'lucide-react';
import './styles.css';

const pages = [
  { id: 'overview', title: '总览仪表盘', subtitle: '实时扫描、候选池、买卖点与通知预览', img: '/prototypes/overview.png', icon: LayoutDashboard },
  { id: 'strategy', title: '策略配置', subtitle: '规则参数、权重、政策主题库', img: '/prototypes/strategy.png', icon: SlidersHorizontal },
  { id: 'candidates', title: '候选股池', subtitle: '评分、突破位、止损位、观察状态', img: '/prototypes/candidates.png', icon: Table2 },
  { id: 'stock-detail', title: '个股详情 / 买卖点', subtitle: 'K线、涨停整理、突破、止损止盈', img: '/prototypes/stock-detail.png', icon: LineChart },
  { id: 'alerts', title: '实时预警 / 通知中心', subtitle: '盘中触发、通知模板、发送日志', img: '/prototypes/alerts.png', icon: Bell },
  { id: 'risk', title: '风控排雷', subtitle: 'ST、减持、质押、违规、公告风险', img: '/prototypes/risk.png', icon: ShieldAlert },
  { id: 'backtest', title: '回测复盘', subtitle: '胜率、盈亏比、回撤、参数敏感性', img: '/prototypes/backtest.png', icon: Gauge },
  { id: 'data-sources', title: '数据源设置', subtitle: 'AKShare、Tushare、通知通道、调度', img: '/prototypes/data-sources.png', icon: Database },
  { id: 'mobile-alert', title: '移动端通知详情', subtitle: '微信 / 企业微信收到信号后的详情页', img: '/prototypes/mobile-alert.png', icon: Smartphone },
];

const akshareMatrix = [
  ['全A股票池 / 实时行情 / 流通市值', '可做', '适合 30-60 秒轮询观察池；不适合秒级高频。'],
  ['历史K线 / 低位区间 / 放量涨停 / 突破', '可做', 'MVP 技术形态主干基本可由 AKShare 支撑。'],
  ['行业概念 / 热点板块', '部分可做', '需叠加自建政策主题库和人工权重。'],
  ['成长性 / 分红 / 基础财务', '部分可做', '基础筛选可做；产能释放和订单爆发需公告解析。'],
  ['机构 / 外资 / 私募加仓', '部分可做', '季报滞后；著名私募和游资需自建名单。'],
  ['ST、减持、质押、违规风险', '部分可做', '需公告关键词 + NLP 复核，不能只看单一字段。'],
  ['短信 / 微信通知', '另接服务', '企业微信机器人、PushPlus、腾讯云短信等。'],
];

const milestones = [
  { name: '产品方案', status: 'done', note: '选股、买卖点、风控、通知、回测框架已定义' },
  { name: '静态高保真图', status: 'done', note: '总览 + 8 个核心子页面已生成' },
  { name: '可交互 Web 原型', status: 'done', note: '页面导航、图稿展示、数据边界说明' },
  { name: 'AKShare 数据服务', status: 'doing', note: 'FastAPI 已接入行情、K线、涨停池、候选股接口' },
  { name: '实盘通知', status: 'todo', note: '下一步接企业微信 + 短信，只推关键触发' },
];

function App() {
  const [active, setActive] = useState('overview');
  const [apiState, setApiState] = useState({ loading: true, health: null, candidates: [], snapshot: [], error: null });
  const current = useMemo(() => pages.find((p) => p.id === active) ?? pages[0], [active]);
  const Icon = current.icon;

  useEffect(() => {
    const controller = new AbortController();
    async function loadAkshareStatus() {
      try {
        const [healthRes, snapshotRes] = await Promise.all([
          fetch('/api/health', { signal: controller.signal }),
          fetch('/api/market/snapshot?limit=8&refresh=false', { signal: controller.signal }),
        ]);
        if (!healthRes.ok) throw new Error(`health ${healthRes.status}`);
        const health = await healthRes.json();
        const snapshotPayload = snapshotRes.ok ? await snapshotRes.json() : { items: [] };
        setApiState({ loading: false, health, candidates: [], snapshot: snapshotPayload.items ?? [], error: null });

        // 候选池计算会逐只拉 K 线，免费源下可能较慢；不要阻塞页面行情展示。
        fetch('/api/candidates/today?scan_limit=10&limit=5', { signal: controller.signal })
          .then((res) => (res.ok ? res.json() : { items: [] }))
          .then((candidatePayload) => {
            setApiState((prev) => ({ ...prev, candidates: candidatePayload.items ?? [] }));
          })
          .catch((error) => {
            if (error.name !== 'AbortError') {
              setApiState((prev) => ({ ...prev, error: `候选池计算失败：${error.message}` }));
            }
          });
      } catch (error) {
        if (error.name !== 'AbortError') {
          setApiState({ loading: false, health: null, candidates: [], snapshot: [], error: error.message });
        }
      }
    }
    loadAkshareStatus();
    return () => controller.abort();
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon"><Radar size={24} /></div>
          <div>
            <div className="brand-title">AI A股策略雷达</div>
            <div className="brand-subtitle">MVP Prototype</div>
          </div>
        </div>

        <nav className="nav-list">
          {pages.map((page) => {
            const NavIcon = page.icon;
            return (
              <button key={page.id} className={`nav-item ${active === page.id ? 'active' : ''}`} onClick={() => setActive(page.id)}>
                <NavIcon size={18} />
                <span>{page.title}</span>
                {active === page.id && <ChevronRight size={16} className="nav-arrow" />}
              </button>
            );
          })}
        </nav>

        <div className="risk-note">
          <AlertTriangle size={18} />
          <span>研究原型，不构成投资建议；实盘需回测、风控与人工复核。</span>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <div className="eyebrow">PUBLIC PROTOTYPE / A-SHARE SIGNAL SYSTEM</div>
            <h1><Icon size={28} /> {current.title}</h1>
            <p>{current.subtitle}</p>
          </div>
          <div className="status-cluster">
            <div className="status-pill live"><Activity size={16} /> 原型已生成</div>
            <div className="status-pill"><MonitorSmartphone size={16} /> Web + Mobile</div>
            <a className="status-pill link" href="https://github.com/" target="_blank" rel="noreferrer"><GitBranch size={16} /> GitHub Pages Ready</a>
          </div>
        </header>

        <section className="hero-grid">
          <div className="prototype-card">
            <div className="card-head">
              <div>
                <h2>{current.title}</h2>
                <p>{current.subtitle}</p>
              </div>
              <a className="open-btn" href={current.img} target="_blank" rel="noreferrer">打开原图</a>
            </div>
            <div className={`image-stage ${current.id === 'mobile-alert' ? 'mobile' : ''}`}>
              <img src={current.img} alt={current.title} />
            </div>
          </div>

          <aside className="side-panel">
            <div className="panel-card">
              <h3>当前完成度</h3>
              <div className="progress-list">
                {milestones.map((m) => (
                  <div className="progress-item" key={m.name}>
                    {m.status === 'done' ? <CheckCircle2 className="ok" size={18} /> : m.status === 'doing' ? <Activity className="doing" size={18} /> : <XCircle className="todo" size={18} />}
                    <div>
                      <strong>{m.name}</strong>
                      <span>{m.note}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="panel-card">
              <h3>核心原则</h3>
              <ul className="compact-list">
                <li>先盘后选股，再盘中监控观察池。</li>
                <li>买卖点必须可解释，不能黑箱追涨。</li>
                <li>风险过滤优先于收益想象。</li>
                <li>机构/游资数据只作为线索，不当作实时事实。</li>
              </ul>
            </div>
          </aside>
        </section>

        <section className="content-grid">
          <div className="matrix-card">
            <h2>AKShare 实时接入状态</h2>
            <p className="muted">前端会请求本地 FastAPI：<code>/api/health</code> 与 <code>/api/candidates/today</code>。GitHub Pages 静态部署时后端不可用，本地启动后显示真实数据。</p>
            <div className="api-status-card">
              <div className={`badge ${apiState.health?.ok ? 'green' : apiState.loading ? 'blue' : 'yellow'}`}>
                {apiState.loading ? '检测中' : apiState.health?.ok ? 'AKShare 可用' : '后端未连接'}
              </div>
              <div className="note">
                {apiState.health?.time ? `后端时间：${apiState.health.time}` : apiState.error ? `状态：${apiState.error}` : '本地启动 backend 后可获取实时行情和候选股。'}
              </div>
            </div>
            <div className="candidate-preview">
              <div className="section-label">行情快照 / AKShare API</div>
              {(apiState.snapshot.length ? apiState.snapshot : [
                { code: '------', name: apiState.loading ? '行情加载中' : '暂无行情数据', price: '-', pct_chg: '-', amount: '-' },
              ]).map((item) => (
                <div className="candidate-row" key={`snapshot-${item.code}`}>
                  <strong>{item.name} <span>{item.code}</span></strong>
                  <em>{item.pct_chg === '-' || item.pct_chg == null ? '涨跌幅 -' : `${Number(item.pct_chg).toFixed(2)}%`}</em>
                  <b>{item.price === '-' || item.price == null ? '价格 -' : `¥${Number(item.price).toFixed(2)}`}</b>
                  <span>{item.amount === '-' || item.amount == null ? '成交额 -' : `成交额 ${(Number(item.amount) / 1e8).toFixed(1)}亿`}</span>
                </div>
              ))}
            </div>
            <div className="candidate-preview">
              <div className="section-label">策略候选池 / 严格条件命中</div>
              {apiState.candidates.length ? apiState.candidates.map((item) => (
                <div className="candidate-row" key={`candidate-${item.code}`}>
                  <strong>{item.name} <span>{item.code}</span></strong>
                  <em>{item.technical?.status ?? 'watching'}</em>
                  <b>评分 {item.score}</b>
                  <span>{item.price === '-' ? '价格 -' : `价格 ${Number(item.price).toFixed(2)}`}</span>
                </div>
              )) : (
                <div className="empty-state">
                  {apiState.loading ? '正在计算候选股...' : '当前严格策略暂无命中；这不等于 API 没接入，行情快照已在上方显示。'}
                </div>
              )}
            </div>
          </div>

          <div className="matrix-card narrow">
            <h2>本地启动方式</h2>
            <ol className="ordered">
              <li><code>cd backend && python -m venv .venv</code></li>
              <li><code>source .venv/bin/activate && pip install -r requirements.txt</code></li>
              <li><code>uvicorn app.main:app --reload --port 8000</code></li>
              <li><code>npm run dev</code></li>
            </ol>
          </div>
        </section>

        <section className="content-grid">
          <div className="matrix-card">
            <h2>AKShare 免费数据可行性边界</h2>
            <p className="muted">结论：足够支撑 MVP 主干，不足以单独承载严肃实盘全链路。</p>
            <div className="matrix">
              {akshareMatrix.map(([feature, status, note]) => (
                <div className="matrix-row" key={feature}>
                  <div className="feature">{feature}</div>
                  <div className={`badge ${status === '可做' ? 'green' : status === '另接服务' ? 'blue' : 'yellow'}`}>{status}</div>
                  <div className="note">{note}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="matrix-card narrow">
            <h2>下一步工程化</h2>
            <ol className="ordered">
              <li>FastAPI 封装 AKShare：股票池、行情、K线、涨停池。</li>
              <li>实现盘后候选池：低位、涨停、整理、突破。</li>
              <li>盘中只监控观察池：突破价、量比、止损线。</li>
              <li>接企业微信 / 短信：买点、止损、收盘复盘。</li>
              <li>做历史回测，验证参数而不是相信视觉稿。</li>
            </ol>
          </div>
        </section>
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
