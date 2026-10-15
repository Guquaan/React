import { useCallback, useEffect, useState } from 'react'
import ImageInput from '../components/ImageInput'
import Webcam from '../components/Webcam'
import { Alert, Avatar, Badge, Card, Empty, Field, Loading, Modal } from '../components/ui'
import { mediaUrl, personApi, faceApi } from '../api/client'
import { formatDateTime, genderText } from '../utils/format'

function NewPersonModal({ open, onClose, onCreated }) {
  const empty = { name: '', employee_no: '', department: '', title: '', gender: '', phone: '', email: '', remark: '' }
  const [form, setForm] = useState(empty)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (!form.name.trim()) return setError('请填写姓名')
    setBusy(true)
    setError('')
    try {
      const payload = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v.trim() || null]))
      payload.name = form.name.trim()
      const r = await personApi.create(payload)
      setForm(empty)
      onCreated(r.data)
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const bind = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  return (
    <Modal
      open={open}
      title="新建人员档案"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="button" className="btn btn--primary" onClick={submit} disabled={busy}>
            {busy ? '创建中…' : '创建并继续'}
          </button>
        </>
      }
    >
      {error && <Alert tone="error">{error}</Alert>}
      <div className="grid grid--2">
        <Field label="姓名" required>
          <input className="input" value={form.name} onChange={bind('name')} placeholder="张三" />
        </Field>
        <Field label="工号 / 学号" hint="唯一，可用于去重">
          <input className="input" value={form.employee_no} onChange={bind('employee_no')} placeholder="EMP0001" />
        </Field>
        <Field label="部门">
          <input className="input" value={form.department} onChange={bind('department')} placeholder="研发部" />
        </Field>
        <Field label="职位">
          <input className="input" value={form.title} onChange={bind('title')} placeholder="前端工程师" />
        </Field>
        <Field label="性别">
          <select className="select" value={form.gender} onChange={bind('gender')}>
            <option value="">未填写</option>
            <option value="male">男</option>
            <option value="female">女</option>
          </select>
        </Field>
        <Field label="手机号">
          <input className="input" value={form.phone} onChange={bind('phone')} />
        </Field>
      </div>
      <Field label="邮箱">
        <input className="input" value={form.email} onChange={bind('email')} />
      </Field>
      <Field label="备注">
        <textarea className="textarea" value={form.remark} onChange={bind('remark')} />
      </Field>
    </Modal>
  )
}

export default function Register() {
  const [persons, setPersons] = useState([])
  const [loading, setLoading] = useState(true)
  const [keyword, setKeyword] = useState('')
  const [selected, setSelected] = useState(null)
  const [files, setFiles] = useState([])
  const [mode, setMode] = useState('upload')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [showNew, setShowNew] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    personApi
      .list({ page: 1, page_size: 100, keyword })
      .then((r) => setPersons(r.data.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [keyword])

  useEffect(() => {
    const t = setTimeout(load, 250)
    return () => clearTimeout(t)
  }, [load])

  const submit = async () => {
    if (!selected) return setError('请先选择要注册的人员')
    if (!files.length) return setError('请至少提供一张人脸照片')
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const r = await faceApi.register(selected.id, files)
      setResult(r.data)
      setFiles([])
      load()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid grid--sidebar">
      <div>
        <Card
          title="1. 选择人员"
          desc="搜索并选中有档案的人员；没有档案就先新建"
          extra={
            <button type="button" className="btn btn--sm btn--primary" onClick={() => setShowNew(true)}>
              + 新建人员
            </button>
          }
          flush
        >
          <div className="card__body" style={{ paddingBottom: 12 }}>
            <div className="search-bar">
              <input
                className="input"
                placeholder="搜索姓名 / 编号 / 工号 / 部门"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
              />
              <button type="button" className="btn btn--sm" onClick={load}>
                刷新
              </button>
            </div>
          </div>

          {loading && persons.length === 0 ? (
            <Loading text="加载人员…" />
          ) : persons.length === 0 ? (
            <Empty icon="👤" title="没有找到人员" hint="点击右上角「新建人员」建立第一个档案" />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>人员</th>
                  <th>部门 / 职位</th>
                  <th>已注册样本</th>
                  <th>建档时间</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {persons.map((p) => (
                  <tr
                    key={p.id}
                    style={selected?.id === p.id ? { background: 'var(--c-primary-soft)' } : undefined}
                  >
                    <td>
                      <div className="person-cell">
                        <Avatar src={mediaUrl(p.primary_image_url)} name={p.name} />
                        <div>
                          <div className="person-cell__name">{p.name}</div>
                          <div className="person-cell__meta">
                            {p.person_code} · {genderText(p.gender)}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td>
                      {p.department || '未分组'}
                      <div className="muted" style={{ fontSize: 11.5 }}>
                        {p.title || '—'}
                      </div>
                    </td>
                    <td>
                      {p.face_count > 0 ? (
                        <Badge tone="green">{p.face_count} 张</Badge>
                      ) : (
                        <Badge tone="amber">未注册</Badge>
                      )}
                    </td>
                    <td className="muted nowrap" style={{ fontSize: 12 }}>
                      {formatDateTime(p.created_at)}
                    </td>
                    <td className="text-right">
                      <button
                        type="button"
                        className={`btn btn--sm ${selected?.id === p.id ? 'btn--primary' : ''}`}
                        onClick={() => setSelected(p)}
                      >
                        {selected?.id === p.id ? '✓ 已选中' : '选择'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card
          title="2. 上传人脸照片"
          desc="同一人建议注册 3~5 张不同角度、不同光照的照片，可显著提升识别准确率"
          className="mt-16"
          extra={
            <div className="btn-row">
              <button
                type="button"
                className={`btn btn--sm ${mode === 'upload' ? 'btn--primary' : ''}`}
                onClick={() => setMode('upload')}
              >
                上传图片
              </button>
              <button
                type="button"
                className={`btn btn--sm ${mode === 'camera' ? 'btn--primary' : ''}`}
                onClick={() => setMode('camera')}
              >
                摄像头
              </button>
            </div>
          }
        >
          {mode === 'upload' ? (
            <ImageInput files={files} onChange={setFiles} multiple />
          ) : (
            <Webcam
              onCapture={(file) => setFiles((prev) => [...prev, file].slice(0, 10))}
              onError={setError}
            />
          )}

          {files.length > 1 && (
            <div className="alert alert--info mt-12">
              已选择 {files.length} 张照片，注册时每一张都会独立校验质量并通过/拒绝。
            </div>
          )}

          {error && <Alert tone="error">{error}</Alert>}

          <div className="btn-row mt-12">
            <button
              type="button"
              className="btn btn--primary btn--lg"
              onClick={submit}
              disabled={busy || !selected || !files.length}
            >
              {busy ? '注册中…' : `注册到「${selected?.name || '未选择'}」`}
            </button>
            {files.length > 0 && (
              <button type="button" className="btn" onClick={() => setFiles([])} disabled={busy}>
                清空
              </button>
            )}
          </div>
        </Card>

        {result && (
          <Card title="3. 注册结果" className="mt-16">
            <div className="row row--wrap mb-12">
              <Badge tone="green">成功 {result.accepted} 张</Badge>
              <Badge tone="red">拒绝 {result.rejected} 张</Badge>
            </div>
            <div className="timeline">
              {result.messages.map((m, i) => {
                const ok = m.includes('成功')
                return (
                  <div className="timeline__item" key={m}>
                    <div className={`timeline__dot ${ok ? '' : 'timeline__dot--fail'}`} />
                    <div className="timeline__title">{m}</div>
                  </div>
                )
              })}
            </div>
          </Card>
        )}
      </div>

      <div>
        <Card title="当前选中">
          {selected ? (
            <div className="row" style={{ alignItems: 'flex-start' }}>
              <Avatar src={mediaUrl(selected.primary_image_url)} name={selected.name} size="lg" />
              <div className="grow">
                <div style={{ fontWeight: 700, fontSize: 15 }}>{selected.name}</div>
                <div className="muted" style={{ fontSize: 12.5 }}>
                  {selected.person_code} · {selected.department || '未分组'}
                </div>
                <div className="mt-8">
                  {selected.face_count > 0 ? (
                    <Badge tone="green">已有 {selected.face_count} 张样本</Badge>
                  ) : (
                    <Badge tone="amber">尚无样本</Badge>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <Empty icon="👆" title="尚未选择人员" hint="在上方列表中点击「选择」" />
          )}
        </Card>

        <Card title="注册质量要求" className="mt-16">
          <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.9 }}>
            · 人脸最短边 ≥ <strong>48px</strong>；
            <br />
            · 综合质量分 ≥ <strong>0.35</strong>（检测置信度 + 清晰度 + 尺寸）；
            <br />
            · 不满足的照片会被拒绝并给出原因，请重拍；
            <br />
            · 只保留画质最好的那张作为人员主图。
          </div>
        </Card>

        <Card title="为什么建议多张" className="mt-16">
          <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.9 }}>
            识别时会对同一人的所有注册样本取<strong>最高相似度</strong>（max pooling）。
            样本角度越丰富，同一个人在不同姿态下被命中的概率就越高，
            这是把准确率稳定做到 70% 以上最有效的办法。
          </div>
        </Card>
      </div>

      <NewPersonModal
        open={showNew}
        onClose={() => setShowNew(false)}
        onCreated={(p) => {
          setSelected(p)
          load()
        }}
      />
    </div>
  )
}
