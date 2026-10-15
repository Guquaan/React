import { useCallback, useEffect, useState } from 'react'
import { Alert, Badge, Card, ConfidenceBar, Empty, KV, Loading, Pager } from '../components/ui'
import { mediaUrl, recognitionApi, qrcodeApi } from '../api/client'
import { fixed, formatDateTime, fromNow, percent } from '../utils/format'
import { navigate } from '../router'

const FILTERS = [
  { key: 'all', label: '全部' },
  { key: 'matched', label: '仅命中' },
  { key: 'unmatched', label: '仅未命中' },
]

export default function Logs() {
  const [logs, setLogs] = useState([])
  const [meta, setMeta] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState('all')

  const [tab, setTab] = useState('recognition')
  const [scans, setScans] = useState([])
  const [scanMeta, setScanMeta] = useState(null)
  const [scanLoading, setScanLoading] = useState(false)

  const pageSize = 15

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    const params = { page, page_size: pageSize }
    if (filter === 'matched') params.is_matched = true
    if (filter === 'unmatched') params.is_matched = false
    recognitionApi
      .logs(params)
      .then((r) => {
        setLogs(r.data.items)
        setMeta(r.data.meta)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [page, filter])

  const loadScans = useCallback(() => {
    setScanLoading(true)
    qrcodeApi
      .scans({ page: 1, page_size: 15 })
      .then((r) => {
        setScans(r.data.items)
        setScanMeta(r.data.meta)
      })
      .catch(() => setScans([]))
      .finally(() => setScanLoading(false))
  }, [])

  useEffect(load, [load])
  useEffect(() => {
    if (tab === 'qr') loadScans()
  }, [tab, loadScans])

  const onFilter = (key) => {
    setFilter(key)
    setPage(1)
  }

  return (
    <div>
      <div className="btn-row mb-16">
        <button type="button" className={`btn btn--sm ${tab === 'recognition' ? 'btn--primary' : ''}`} onClick={() => setTab('recognition')}>
          🎯 识别记录
        </button>
        <button type="button" className={`btn btn--sm ${tab === 'qr' ? 'btn--primary' : ''}`} onClick={() => setTab('qr')}>
          🔍 扫码记录
        </button>
      </div>

      {tab === 'recognition' ? (
        <Card
          title="识别记录"
          desc="每一次识别都留存时间、人员、相似度、置信度与抓拍快照（需求 2：看到人脸对应的数据和时间）"
          flush
        >
          {error && <Alert tone="error">{error}</Alert>}

          {loading && !meta ? (
            <Loading text="加载识别记录…" />
          ) : logs.length === 0 ? (
            <Empty icon="🕒" title="暂无识别记录" hint="去「人脸识别」页面试一次" />
          ) : (
            <>
              <div className="btn-row mt-12 mb-8" style={{ padding: '0 16px', flexWrap: 'wrap' }}>
                {FILTERS.map((f) => (
                  <button
                    key={f.key}
                    type="button"
                    className={`btn btn--sm ${filter === f.key ? 'btn--primary' : ''}`}
                    onClick={() => onFilter(f.key)}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
              <table className="table">
                <thead>
                  <tr>
                    <th>识别时间</th>
                    <th>人员 / 编号</th>
                    <th>结果</th>
                    <th>相似度</th>
                    <th>置信度</th>
                    <th>模式</th>
                    <th>耗时</th>
                    <th>抓拍</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((l) => (
                    <tr key={l.id}>
                      <td className="nowrap">
                        {formatDateTime(l.created_at)}
                        <div className="muted" style={{ fontSize: 10.5 }}>{fromNow(l.created_at)}</div>
                      </td>
                      <td>
                        {l.is_matched ? (
                          <button type="button" className="link-btn" onClick={() => l.person_id && navigate(`/persons/${l.person_id}`)}>
                            {l.person_name}
                          </button>
                        ) : (
                          <span className="muted">—</span>
                        )}
                        <div className="muted" style={{ fontSize: 11 }}>{l.person_code || '—'}</div>
                      </td>
                      <td>
                        {l.is_matched ? <Badge tone="green">命中</Badge> : <Badge tone="red">未命中</Badge>}
                      </td>
                      <td className="table__mono">{fixed(l.similarity)}</td>
                      <td style={{ minWidth: 110 }}>
                        <ConfidenceBar value={l.confidence} />
                      </td>
                      <td className="muted">{l.mode === 'verify' ? '1:1' : '1:N'}</td>
                      <td className="muted nowrap">{l.elapsed_ms} ms</td>
                      <td>
                        {l.snapshot_url ? (
                          <a href={mediaUrl(l.snapshot_url)} target="_blank" rel="noreferrer">查看</a>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {meta && (
                <div style={{ padding: '12px 16px' }}>
                  <Pager meta={meta} onChange={setPage} />
                </div>
              )}
            </>
          )}
        </Card>
      ) : (
        <Card title="扫码记录" desc="每一次「二维码取数」都会落一条审计记录（含时间与来源 IP）" flush>
          {scanLoading && scans.length === 0 ? (
            <Loading text="加载扫码记录…" />
          ) : scans.length === 0 ? (
            <Empty icon="🔍" title="暂无扫码记录" hint="去「扫码取数」页面扫一次二维码" />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>扫码时间</th>
                  <th>人员</th>
                  <th>是否有效</th>
                  <th>来源 IP</th>
                </tr>
              </thead>
              <tbody>
                {scans.map((s) => (
                  <tr key={s.id}>
                    <td className="nowrap">{formatDateTime(s.created_at)}</td>
                    <td>
                      {s.person_name || <span className="muted">未知</span>}
                    </td>
                    <td>
                      {s.is_valid ? <Badge tone="green">有效</Badge> : <Badge tone="red">无效 / 已过期</Badge>}
                    </td>
                    <td className="muted nowrap">{s.client_ip || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {scanMeta && (
            <div style={{ padding: '12px 16px' }}>
              <Pager meta={scanMeta} onChange={() => {}} />
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
