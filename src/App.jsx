import { useEffect, useMemo, useState } from 'react'
import { matchPath, navigate, useRoute } from './router'
import { systemApi } from './api/client'
import './styles/app.css'

import Dashboard from './pages/dashboard'
import Persons from './pages/persons'
import PersonDetail from './pages/personDetail'
import Register from './pages/register'
import Recognize from './pages/recognize'
import Logs from './pages/logs'
import Scan from './pages/scan'
import Learn from './pages/learn'

const NAV = [
  {
    group: '业务功能',
    items: [
      { path: '/', label: '概览看板', icon: '📊', title: '概览看板' },
      { path: '/recognize', label: '人脸识别', icon: '🎯', title: '人脸识别（1:N）' },
      { path: '/faces/register', label: '人脸注册', icon: '🖼️', title: '人脸注册' },
      { path: '/persons', label: '人员档案', icon: '👥', title: '人员档案' },
      { path: '/logs', label: '识别记录', icon: '🕒', title: '识别记录（时间追溯）' },
      { path: '/scan', label: '扫码取数', icon: '🔍', title: '二维码扫码取数' },
    ],
  },
  {
    group: '原学习笔记',
    items: [
      { path: '/learn/teach', label: 'React 基础', icon: '📘', title: 'React 基础练习' },
      { path: '/learn/list', label: '列表渲染', icon: '📝', title: '列表渲染练习' },
    ],
  },
]

function resolvePage(path, params) {
  const personMatch = matchPath(path, '/persons/:id')
  if (personMatch) return { key: 'person-detail', node: <PersonDetail id={personMatch.id} />, title: '人员详情' }
  if (path === '/') return { key: 'dashboard', node: <Dashboard />, title: '概览看板' }
  if (path === '/recognize') return { key: 'recognize', node: <Recognize />, title: '人脸识别（1:N）' }
  if (path === '/faces/register') return { key: 'register', node: <Register />, title: '人脸注册' }
  if (path === '/persons') return { key: 'persons', node: <Persons />, title: '人员档案' }
  if (path === '/logs') return { key: 'logs', node: <Logs />, title: '识别记录（时间追溯）' }
  if (path === '/scan') return { key: 'scan', node: <Scan params={params} />, title: '二维码扫码取数' }
  if (path === '/learn/teach') return { key: 'learn-teach', node: <Learn mode="teach" />, title: 'React 基础练习' }
  if (path === '/learn/list') return { key: 'learn-list', node: <Learn mode="list" />, title: '列表渲染练习' }
  return { key: '404', node: <div className="empty"><div className="empty__icon">🧭</div><div className="empty__title">页面不存在</div></div>, title: '未找到' }
}

export default function App() {
  const { path, params, go } = useRoute()
  const [health, setHealth] = useState(null)
  const [online, setOnline] = useState(null)

  const page = useMemo(() => resolvePage(path, params), [path, params])

  useEffect(() => {
    let alive = true
    const load = () =>
      systemApi
        .health()
        .then((r) => {
          if (!alive) return
          setHealth(r.data)
          setOnline(true)
        })
        .catch(() => alive && setOnline(false))
    load()
    const t = setInterval(load, 20000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [])

  const isActive = (itemPath) =>
    itemPath === '/' ? path === '/' : path === itemPath || path.startsWith(`${itemPath}/`)

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <div className="sidebar__logo">🧠</div>
          <div>
            <div className="sidebar__title">FaceID 系统</div>
            <div className="sidebar__subtitle">矢量库 · 人脸识别</div>
          </div>
        </div>

        {NAV.map((g) => (
          <div key={g.group}>
            <div className="sidebar__group">{g.group}</div>
            {g.items.map((item) => (
              <button
                key={item.path}
                type="button"
                className={`nav-item ${isActive(item.path) ? 'nav-item--active' : ''}`}
                onClick={() => go(item.path)}
              >
                <span className="nav-item__icon">{item.icon}</span>
                {item.label}
              </button>
            ))}
          </div>
        ))}

        <div style={{ marginTop: 'auto', paddingTop: 16 }}>
          <div className="sidebar__group" style={{ padding: '0 10px 6px' }}>
            服务状态
          </div>
          <div style={{ padding: '0 10px', fontSize: 11.5, lineHeight: 1.9 }}>
            <div>
              {online === null ? '⏳ 检测中' : online ? '🟢 后端已连接' : '🔴 后端未连接'}
            </div>
            {health && (
              <>
                <div className="muted">矢量库：{health.vector_backend_ready ? '✅' : '❌'} {health.vector_backend}</div>
                <div className="muted">识别引擎：{health.engine_ready ? '✅' : '❌'} {health.face_engine}</div>
                <div className="muted">阈值：≥ {(health.confidence_floor * 100).toFixed(0)}%</div>
              </>
            )}
            {online === false && (
              <div className="muted" style={{ marginTop: 4 }}>
                请先启动后端：<br />
                <code style={{ fontSize: 10.5 }}>cd backend &amp;&amp; python run.py</code>
              </div>
            )}
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="topbar__title">{page.title}</div>
          <div className="topbar__right">
            {health && (
              <span className="badge badge--blue">
                余弦阈值 {health.cosine_threshold} · 置信度 ≥ {(health.confidence_floor * 100).toFixed(0)}%
              </span>
            )}
            <span className="badge badge--gray">{new Date().toLocaleDateString('zh-CN')}</span>
          </div>
        </header>
        <div className="content" key={page.key}>
          {page.node}
        </div>
      </main>
    </div>
  )
}

export { navigate }
