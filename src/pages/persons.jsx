import { useCallback, useEffect, useState } from 'react'
import { Alert, Avatar, Badge, Card, Empty, Field, Loading, Modal, Pager } from '../components/ui'
import { mediaUrl, personApi } from '../api/client'
import { formatDateTime, genderText } from '../utils/format'

export default function Persons({ onOpen }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [keyword, setKeyword] = useState('')
  const [department, setDepartment] = useState('')
  const [departments, setDepartments] = useState([])
  const [editing, setEditing] = useState(null)
  const [removing, setRemoving] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    personApi
      .list({ page, page_size: 15, keyword, department })
      .then((r) => {
        setData(r.data)
        setError('')
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [page, keyword, department])

  useEffect(() => {
    const t = setTimeout(load, 250)
    return () => clearTimeout(t)
  }, [load])

  useEffect(() => {
    personApi.departments().then((r) => setDepartments(r.data)).catch(() => {})
  }, [])

  const openDetail = (p) => {
    if (onOpen) onOpen(p)
    else window.location.hash = `#/persons/${p.id}`
  }

  const doRemove = async () => {
    setBusy(true)
    try {
      await personApi.remove(removing.id)
      setRemoving(null)
      load()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <Card
        title="人员档案"
        desc="按需求「看到相关人脸对应的数据和时间」，每张样本与识别记录均带精确时间"
        extra={
          <div className="btn-row">
            <button type="button" className="btn btn--sm" onClick={load}>
              刷新
            </button>
          </div>
        }
        flush
      >
        <div className="card__body" style={{ paddingBottom: 12 }}>
          <div className="search-bar">
            <input
              className="input"
              placeholder="搜索姓名 / 编号 / 工号 / 部门"
              value={keyword}
              onChange={(e) => {
                setKeyword(e.target.value)
                setPage(1)
              }}
            />
            <select
              className="select"
              value={department}
              onChange={(e) => {
                setDepartment(e.target.value)
                setPage(1)
              }}
            >
              <option value="">全部部门</option>
              {departments.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
            {(keyword || department) && (
              <button
                type="button"
                className="btn btn--sm btn--ghost"
                onClick={() => {
                  setKeyword('')
                  setDepartment('')
                }}
              >
                清除筛选
              </button>
            )}
          </div>
        </div>

        {error && (
          <div style={{ padding: '0 18px' }}>
            <Alert tone="error">{error}</Alert>
          </div>
        )}

        {loading && !data ? (
          <Loading text="加载人员列表…" />
        ) : !data?.items?.length ? (
          <Empty icon="👥" title="没有人员数据" hint="去「人脸注册」页面新建第一个人员档案吧" />
        ) : (
          <>
            <table className="table">
              <thead>
                <tr>
                  <th>人员</th>
                  <th>工号 / 学号</th>
                  <th>部门 / 职位</th>
                  <th>联系方式</th>
                  <th>人脸样本</th>
                  <th>建档时间</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.items.map((p) => (
                  <tr key={p.id}>
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
                    <td className="table__mono">{p.employee_no || '—'}</td>
                    <td>
                      {p.department || '未分组'}
                      <div className="muted" style={{ fontSize: 11.5 }}>
                        {p.title || '—'}
                      </div>
                    </td>
                    <td className="muted" style={{ fontSize: 12 }}>
                      {p.phone || '—'}
                      <div style={{ fontSize: 11.5 }}>{p.email || '—'}</div>
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
                    <td>
                      <div className="table__actions">
                        <button type="button" className="btn btn--sm" onClick={() => openDetail(p)}>
                          详情
                        </button>
                        <button type="button" className="btn btn--sm" onClick={() => setEditing(p)}>
                          编辑
                        </button>
                        <button
                          type="button"
                          className="btn btn--sm btn--ghost"
                          style={{ color: 'var(--c-danger)' }}
                          onClick={() => setRemoving(p)}
                        >
                          删除
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pager meta={data.meta} onChange={setPage} />
          </>
        )}
      </Card>

      <EditPersonModal
        person={editing}
        onClose={() => setEditing(null)}
        onSaved={() => {
          setEditing(null)
          load()
        }}
      />

      <Modal
        open={!!removing}
        title="确认删除人员？"
        onClose={() => setRemoving(null)}
        footer={
          <>
            <button type="button" className="btn" onClick={() => setRemoving(null)}>
              取消
            </button>
            <button type="button" className="btn btn--danger" onClick={doRemove} disabled={busy}>
              {busy ? '删除中…' : '确认删除'}
            </button>
          </>
        }
      >
        <Alert tone="warn">
          将删除 <strong>{removing?.name}</strong>（{removing?.person_code}）的档案，
          同时清理其 <strong>{removing?.face_count}</strong> 张人脸样本在矢量数据库中的向量与磁盘图片。
          该操作不可撤销。
        </Alert>
        <div className="muted" style={{ fontSize: 12 }}>
          提示：历史识别记录会保留（人员字段置空），便于审计追溯。
        </div>
      </Modal>
    </div>
  )
}

function EditPersonModal({ person, onClose, onSaved }) {
  const [form, setForm] = useState({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (person) {
      setForm({
        name: person.name || '',
        employee_no: person.employee_no || '',
        department: person.department || '',
        title: person.title || '',
        gender: person.gender || '',
        phone: person.phone || '',
        email: person.email || '',
        remark: person.remark || '',
      })
      setError('')
    }
  }, [person])

  if (!person) return null

  const bind = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const save = async () => {
    setBusy(true)
    setError('')
    try {
      const payload = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v.trim() || null]))
      payload.name = form.name.trim()
      await personApi.update(person.id, payload)
      onSaved()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open
      title={`编辑：${person.name}`}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="button" className="btn btn--primary" onClick={save} disabled={busy}>
            {busy ? '保存中…' : '保存'}
          </button>
        </>
      }
    >
      {error && <Alert tone="error">{error}</Alert>}
      <div className="grid grid--2">
        <Field label="姓名" required>
          <input className="input" value={form.name} onChange={bind('name')} />
        </Field>
        <Field label="工号 / 学号">
          <input className="input" value={form.employee_no} onChange={bind('employee_no')} />
        </Field>
        <Field label="部门">
          <input className="input" value={form.department} onChange={bind('department')} />
        </Field>
        <Field label="职位">
          <input className="input" value={form.title} onChange={bind('title')} />
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
