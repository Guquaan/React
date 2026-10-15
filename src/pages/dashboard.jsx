import { useCallback, useEffect, useState } from 'react'
import { systemApi } from '../api/client'
import { Alert, Card, Empty, Loading, Stat } from '../components/ui'
import { formatDate, fromNow, percent } from '../utils/format'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [health, setHealth] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([systemApi.stats(), systemApi.health()])
      .then(([s, h]) => {
        setStats(s.data)
        setHealth(h.data)
        setError('')
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(load, [load])

  if (loading && !stats) return <Loading text="正在加载看板数据…" />
  if (error) return <Alert tone="error">无法连接后端：{error}</Alert>
  if (!stats) return null

  const trend = stats.trend_7d || []
  const maxTrend = Math.max(1, ...trend.map((d) => d.total))

  return (
    <div>
      {health && !health.engine_ready && (
        <Alert tone="warn">
          <strong>人脸引擎未就绪</strong>：请在后端执行 <code>python scripts/download_models.py</code> 下载模型，
          或在 <code>backend/.env</code> 中设置 <code>FACE_ENGINE=mock</code> 先做链路联调。
        </Alert>
      )}

      <div className="grid grid--4">
        <Stat label="👥 人员总数" value={stats.person_count} hint={`部门 ${stats.department_distribution.length} 个`} tone="primary" />
        <Stat label="🖼️ 人脸样本" value={stats.face_count} hint={`平均每人 ${(stats.face_count / Math.max(1, stats.person_count)).toFixed(1)} 张`} tone="purple" />
        <Stat label="🎯 识别次数" value={stats.recognition_total} hint={`今日 ${stats.recognition_today} 次`} tone="success" />
        <Stat
          label="📈 平均置信度"
          value={percent(stats.avg_confidence)}
          hint={`阈值 ≥ ${percent(stats.confidence_floor, 0)}`}
          tone="warn"
        />
      </div>

      <div className="grid grid--sidebar mt-16">
        <Card title="近 7 日识别趋势" desc="绿色为命中，灰色为未命中" >
          {trend.length === 0 ? (
            <Empty icon="📉" title="暂无识别数据" hint="去「人脸识别」页面试一次吧" />
          ) : (
            <div className="bars">
              {trend.map((d) => {
                const h = (d.total / maxTrend) * 100
                const matchedRatio = d.total ? d.matched / d.total : 0
                return (
                  <div className="bars__col" key={d.date} title={`${d.date}：${d.total} 次，命中 ${d.matched} 次`}>
                    <div className="bars__stack" style={{ height: `${Math.max(h, 2)}%` }}>
                      <div
                        className="bars__seg bars__seg--miss"
                        style={{ height: `${(1 - matchedRatio) * 100}%` }}
                      />
                      <div
                        className="bars__seg bars__seg--matched"
                        style={{ height: `${matchedRatio * 100}%` }}
                      />
                    </div>
                    <div className="bars__label">{d.date.slice(5)}</div>
                  </div>
                )
              })}
            </div>
          )}
        </Card>

        <Card title="运行状态" desc="后端实时探针">
          <div className="kv">
            <div className="kv__k">服务</div>
            <div className="kv__v">{health ? '🟢 正常' : '🔴 异常'}</div>
            <div className="kv__k">矢量数据库</div>
            <div className="kv__v">
              {health?.vector_backend_ready ? '✅' : '❌'} {health?.vector_backend}
            </div>
            <div className="kv__k">人脸引擎</div>
            <div className="kv__v">
              {health?.engine_ready ? '✅' : '❌'} {health?.face_engine}
            </div>
            <div className="kv__k">余弦阈值</div>
            <div className="kv__v">{stats.cosine_threshold}</div>
            <div className="kv__k">置信度下限</div>
            <div className="kv__v">{percent(stats.confidence_floor, 0)}</div>
            <div className="kv__k">平均识别耗时</div>
            <div className="kv__v">{stats.avg_elapsed_ms} ms</div>
            <div className="kv__k">扫码次数</div>
            <div className="kv__v">{stats.qr_scan_total} 次</div>
          </div>
        </Card>
      </div>

      <div className="grid grid--2 mt-16">
        <Card title="部门人员分布">
          {stats.department_distribution.length === 0 ? (
            <Empty icon="🏢" title="还没有人员数据" />
          ) : (
            <div className="rank-list">
              {stats.department_distribution.map((d, i) => (
                <div className="rank-item" key={d.name}>
                  <span className="rank-item__idx">{i + 1}</span>
                  <span className="rank-item__name">{d.name}</span>
                  <span className="rank-item__val">{d.count} 人</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="识别次数 Top 5" desc="含最近一次识别时间来自识别记录">
          {stats.top_recognized.length === 0 ? (
            <Empty icon="🏆" title="暂无识别记录" />
          ) : (
            <div className="rank-list">
              {stats.top_recognized.map((d, i) => (
                <div className="rank-item" key={d.name}>
                  <span className="rank-item__idx">{i + 1}</span>
                  <span className="rank-item__name">{d.name}</span>
                  <span className="rank-item__val">{d.count} 次</span>
                </div>
              ))}
            </div>
          )}
          <div className="divider" />
          <div className="muted" style={{ fontSize: 12 }}>
            数据更新时间：{fromNow(new Date().toISOString())}（页面每 20 秒自动刷新）
          </div>
        </Card>
      </div>
    </div>
  )
}
