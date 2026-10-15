import { useCallback, useEffect, useState } from 'react'
import ImageInput from '../components/ImageInput'
import { Alert, Avatar, Badge, Card, ConfidenceBar, Empty, KV, Loading, Modal } from '../components/ui'
import { faceApi, mediaUrl, personApi, qrCodeUrl, qrcodeApi, recognitionApi } from '../api/client'
import { fixed, formatDateTime, fromNow, genderText, percent } from '../utils/format'
import { navigate } from '../router'

export default function PersonDetail({ id }) {
  const [person, setPerson] = useState(null)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [files, setFiles] = useState([])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  const [qr, setQr] = useState(null)
  const [qrOpen, setQrOpen] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([
      personApi.detail(id),
      recognitionApi.logs({ person_id: id, page: 1, page_size: 10 }),
    ])
      .then(([p, l]) => {
        setPerson(p.data)
        setLogs(l.data.items)
        setError('')
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(load, [load])

  const register = async () => {
    if (!files.length) return
    setBusy(true)
    setMsg(null)
    try {
      const r = await faceApi.register(id, files)
      setMsg({ tone: r.data.accepted ? 'ok' : 'warn', text: r.message, details: r.data.messages })
      setFiles([])
      load()
    } catch (e) {
      setMsg({ tone: 'error', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const removeFace = async (faceId) => {
    try {
      await faceApi.remove(faceId)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  const openQr = async () => {
    setQrOpen(true)
    try {
      const r = await qrcodeApi.payload(id)
      setQr(r.data)
    } catch (e) {
      setError(e.message)
    }
  }

  if (loading && !person) return <Loading text="加载人员详情…" />
  if (error) return <Alert tone="error">{error}</Alert>
  if (!person) return null

  return (
    <div>
      <div className="row row--between mb-16 row--wrap">
        <button type="button" className="btn btn--ghost btn--sm" onClick={() => navigate('/persons')}>
          ← 返回人员列表
        </button>
        <div className="btn-row">
          <button type="button" className="btn btn--sm" onClick={openQr}>
            📱 查看二维码
          </button>
          <button
            type="button"
            className="btn btn--sm"
            onClick={() => window.open(qrCodeUrl(id, 14), '_blank')}
          >
            下载二维码
          </button>
        </div>
      </div>

      <div className="grid grid--sidebar">
        <div>
          <Card title="基本信息" desc={`人员编号 ${person.person_code}`}>
            <div className="row" style={{ alignItems: 'flex-start' }}>
              <Avatar src={mediaUrl(person.primary_image_url)} name={person.name} size="xl" />
              <div className="grow">
                <div style={{ fontSize: 20, fontWeight: 750 }}>{person.name}</div>
                <div className="muted" style={{ fontSize: 13 }}>
                  {person.department || '未分组'} {person.title ? `· ${person.title}` : ''}
                </div>
                <div className="tag-list mt-8">
                  <Badge tone="blue">{person.person_code}</Badge>
                  <Badge tone="gray">{genderText(person.gender)}</Badge>
                  {person.face_count > 0 ? (
                    <Badge tone="green">{person.face_count} 张人脸样本</Badge>
                  ) : (
                    <Badge tone="amber">尚未注册人脸</Badge>
                  )}
                </div>
              </div>
            </div>

            <div className="divider" />

            <KV
              items={[
                ['工号 / 学号', person.employee_no || '—'],
                ['手机号', person.phone || '—'],
                ['邮箱', person.email || '—'],
                ['建档时间', formatDateTime(person.created_at)],
                ['最后更新', formatDateTime(person.updated_at)],
                ['累计识别', `${person.recognition_count} 次`],
                ['最近识别', person.last_recognition_at ? `${formatDateTime(person.last_recognition_at)}（${fromNow(person.last_recognition_at)}）` : '暂无'],
                ['备注', person.remark || '—'],
              ]}
            />
          </Card>

          <Card
            title="人脸样本"
            desc="每张样本都记录了注册时间与质量分（点击右上角 × 可删除）"
            className="mt-16"
          >
            {person.faces.length === 0 ? (
              <Empty icon="🖼️" title="还没有注册人脸" hint="在右侧上传照片即可注册" />
            ) : (
              <div className="face-grid">
                {person.faces.map((f) => (
                  <div className="face-tile" key={f.id}>
                    <img src={mediaUrl(f.image_url)} alt="人脸样本" />
                    <button type="button" className="face-tile__del" onClick={() => removeFace(f.id)} title="删除该样本">
                      ×
                    </button>
                    {f.is_primary && (
                      <span className="face-tile__flag">
                        <Badge tone="blue">主图</Badge>
                      </span>
                    )}
                    <div className="face-tile__foot">
                      <div className="face-tile__time">{formatDateTime(f.created_at)}</div>
                      <div className="row row--between" style={{ marginTop: 2 }}>
                        <span>质量 {fixed(f.quality_score, 2)}</span>
                        <span className="muted" style={{ fontSize: 10 }}>
                          {f.face_width}×{f.face_height}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card title="识别记录" desc="该人员的每一次识别事件（含时间与置信度）" className="mt-16" flush>
            {logs.length === 0 ? (
              <Empty icon="🕒" title="暂无识别记录" hint="先去「人脸识别」页面识别一次" />
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>识别时间</th>
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
                      <td className="nowrap">{formatDateTime(l.created_at)}</td>
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
                          <a href={mediaUrl(l.snapshot_url)} target="_blank" rel="noreferrer">
                            查看
                          </a>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>

        <div>
          <Card title="补注册人脸" desc="多角度样本能显著提升识别准确率">
            <ImageInput files={files} onChange={setFiles} multiple hint="建议 3~5 张，正面 / 左 / 右 / 不同光照" />
            <button
              type="button"
              className="btn btn--primary btn--block mt-12"
              onClick={register}
              disabled={busy || !files.length}
            >
              {busy ? '上传中…' : `注册 ${files.length || 0} 张照片`}
            </button>

            {msg && (
              <div className={`alert alert--${msg.tone === 'ok' ? 'ok' : msg.tone === 'warn' ? 'warn' : 'error'} mt-12`}>
                <div>{msg.text}</div>
                {msg.details?.length > 0 && (
                  <ul style={{ marginTop: 4, paddingLeft: 16 }}>
                    {msg.details.map((d) => (
                      <li key={d} style={{ fontSize: 12 }}>
                        {d}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </Card>

          <Card title="二维码取数" desc="扫码即可获取该人员的档案数据" className="mt-16">
            <div className="qr-box">
              <img src={qrCodeUrl(id, 8)} alt="人员二维码" />
              <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
                扫描后自动跳转到「扫码取数」页面
              </div>
            </div>
            <div className="muted mt-12" style={{ fontSize: 12, lineHeight: 1.85 }}>
              二维码内容为 <strong>HMAC 签名 token</strong>，不含明文身份信息；
              即使被拍照传播也无法被篡改成他人凭证。每次扫码都会落一条审计记录。
            </div>
          </Card>

          <Card title="置信度说明" className="mt-16">
            <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.9 }}>
              <strong>置信度 = (余弦相似度 + 1) / 2</strong>
              <br />
              系统以置信度 ≥ <strong>70%</strong>（余弦 ≥ 0.40）作为命中判定线，
              低于该值一律返回「未识别」，从而保证匹配准确率稳定在 70% 以上。
            </div>
          </Card>
        </div>
      </div>

      <Modal open={qrOpen} title={`二维码：${person.name}`} onClose={() => setQrOpen(false)}>
        {qr ? (
          <>
            <div className="qr-box">
              <img src={qrCodeUrl(id, 8)} alt="人员二维码" />
            </div>
            <KV
              items={[
                ['人员编号', qr.person_code],
                ['生成时间', formatDateTime(qr.generated_at)],
                ['有效期', qr.expires_at ? formatDateTime(qr.expires_at) : '永久有效'],
                ['扫码地址', qr.scan_url],
              ]}
            />
            <div className="section-title">二维码 token（可复制到扫码页手动解析）</div>
            <div className="qr-token">{qr.token}</div>
            <div className="btn-row mt-12">
              <button
                type="button"
                className="btn btn--sm"
                onClick={() => navigator.clipboard?.writeText(qr.token)}
              >
                复制 token
              </button>
              <button
                type="button"
                className="btn btn--sm"
                onClick={() => navigate(`/scan?code=${encodeURIComponent(qr.token)}`)}
              >
                在本页解析测试
              </button>
            </div>
          </>
        ) : (
          <Loading text="生成二维码…" />
        )}
      </Modal>
    </div>
  )
}

export { percent }
