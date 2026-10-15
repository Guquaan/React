import { useCallback, useEffect, useState } from 'react'
import QrScanner from '../components/QrScanner'
import { Alert, Avatar, Badge, Card, ConfidenceBar, Empty, KV, Loading } from '../components/ui'
import { mediaUrl, qrcodeApi } from '../api/client'
import { fixed, formatDateTime, fromNow, genderText, percent } from '../utils/format'

export default function Scan({ params }) {
  const [resolved, setResolved] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [source, setSource] = useState('')

  const resolve = useCallback(async (raw) => {
    if (!raw || !raw.trim()) return
    setLoading(true)
    setError('')
    try {
      const r = await qrcodeApi.parse(raw.trim())
      setResolved(r.data)
      setSource(raw)
    } catch (e) {
      setResolved(null)
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  // 从「二维码详情」页「在本页解析测试」带 token 跳转过来时，自动解析
  useEffect(() => {
    const code = params.get('code')
    const url = params.get('url')
    if (code || url) resolve(code || url)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const p = resolved?.person

  return (
    <div className="grid grid--sidebar">
      <div>
        <Card
          title="扫描二维码"
          desc="用摄像头对准人员二维码，或用手机扫码后粘贴链接 / token（需求 4：通过二维码获取人员数据）"
        >
          <QrScanner onResult={resolve} onError={setError} />
          {error && <Alert tone="error" className="mt-12">{error}</Alert>}
          {loading && <Loading text="解析中…" className="mt-12" />}
        </Card>
      </div>

      <div>
        <Card title="解析结果" desc="扫码后获取到的人员档案与关联数据">
          {!resolved && !loading && (
            <Empty icon="🔍" title="等待扫码" hint="扫描或粘贴二维码内容后，这里会显示人员数据" />
          )}

          {resolved && !resolved.valid && (
            <Alert tone="error">二维码无效、已过期或被篡改，无法获取数据。</Alert>
          )}

          {resolved && resolved.valid && p && (
            <>
              <div className="row" style={{ alignItems: 'flex-start' }}>
                <Avatar src={mediaUrl(p.primary_image_url)} name={p.name} size="xl" />
                <div className="grow">
                  <div style={{ fontSize: 22, fontWeight: 750 }}>{p.name}</div>
                  <div className="muted" style={{ fontSize: 13 }}>
                    {p.department || '未分组'} {p.title ? `· ${p.title}` : ''}
                  </div>
                  <div className="tag-list mt-8">
                    <Badge tone="blue">{p.person_code}</Badge>
                    <Badge tone="gray">{genderText(p.gender)}</Badge>
                    <Badge tone="green">{p.face_count} 张样本</Badge>
                  </div>
                </div>
              </div>

              <div className="divider" />

              <KV
                items={[
                  ['工号 / 学号', p.employee_no || '—'],
                  ['手机号', p.phone || '—'],
                  ['邮箱', p.email || '—'],
                  ['建档时间', formatDateTime(p.created_at)],
                  ['最近识别', p.last_recognition_at ? `${formatDateTime(p.last_recognition_at)}（${fromNow(p.last_recognition_at)}）` : '暂无'],
                  ['备注', p.remark || '—'],
                ]}
              />

              <div className="section-title mt-16">已注册人脸样本</div>
              {p.faces && p.faces.length > 0 ? (
                <div className="face-grid">
                  {p.faces.map((f) => (
                    <div className="face-tile" key={f.id}>
                      <img src={mediaUrl(f.image_url)} alt="人脸样本" />
                      {f.is_primary && (
                        <span className="face-tile__flag">
                          <Badge tone="blue">主图</Badge>
                        </span>
                      )}
                      <div className="face-tile__foot">
                        <div className="face-tile__time">{formatDateTime(f.created_at)}</div>
                        <div className="row row--between" style={{ marginTop: 2 }}>
                          <span>质量 {fixed(f.quality_score, 2)}</span>
                          <span className="muted" style={{ fontSize: 10 }}>{f.face_width}×{f.face_height}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <Empty icon="🖼️" title="该人员未注册人脸" />
              )}

              <div className="section-title mt-16">最近识别记录</div>
              {resolved.recent_recognitions && resolved.recent_recognitions.length > 0 ? (
                <table className="table">
                  <thead>
                    <tr>
                      <th>识别时间</th>
                      <th>相似度</th>
                      <th>置信度</th>
                      <th>结果</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resolved.recent_recognitions.map((r) => (
                      <tr key={r.id}>
                        <td className="nowrap">{formatDateTime(r.created_at)}</td>
                        <td className="table__mono">{fixed(r.similarity)}</td>
                        <td style={{ minWidth: 110 }}>
                          <ConfidenceBar value={r.confidence} />
                        </td>
                        <td>{r.is_matched ? <Badge tone="green">命中</Badge> : <Badge tone="red">未命中</Badge>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <Empty icon="🕒" title="暂无识别记录" />
              )}

              <div className="muted mt-12" style={{ fontSize: 11.5 }}>
                数据解析时间：{formatDateTime(resolved.scanned_at)} · 来源：{source ? '扫码/粘贴' : '页面跳转'}
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  )
}
