/** 通用 UI 原子组件（无业务逻辑，可跨页面复用） */
import { useEffect } from 'react'
import { confidenceLevel, formatDateTime, percent } from '../utils/format'

export function Card({ title, desc, extra, children, flush, className = '' }) {
  return (
    <section className={`card ${className}`}>
      {(title || extra) && (
        <header className="card__head">
          <div>
            <div className="card__title">{title}</div>
            {desc && <div className="card__desc">{desc}</div>}
          </div>
          {extra}
        </header>
      )}
      <div className={`card__body ${flush ? 'card__body--flush' : ''}`}>{children}</div>
    </section>
  )
}

export function Stat({ label, value, hint, tone = '' }) {
  return (
    <div className={`stat ${tone ? `stat--${tone}` : ''}`}>
      <div className="stat__label">{label}</div>
      <div className="stat__value">{value}</div>
      {hint && <div className="stat__hint">{hint}</div>}
    </div>
  )
}

export function Badge({ tone = 'gray', children }) {
  return <span className={`badge badge--${tone}`}>{children}</span>
}

export function Alert({ tone = 'info', children }) {
  return <div className={`alert alert--${tone}`}>{children}</div>
}

export function Empty({ icon = '📭', title = '暂无数据', hint }) {
  return (
    <div className="empty">
      <div className="empty__icon">{icon}</div>
      <div className="empty__title">{title}</div>
      {hint && <div className="empty__hint">{hint}</div>}
    </div>
  )
}

export function Loading({ text = '加载中…', block = true }) {
  return (
    <div className={block ? 'loading-block' : 'row'}>
      <div className="spinner spinner--dark" />
      <span>{text}</span>
    </div>
  )
}

export function Field({ label, required, hint, children }) {
  return (
    <label className="field">
      <span className="field__label">
        {label} {required && <span>*</span>}
      </span>
      {children}
      {hint && <span className="muted" style={{ fontSize: 11.5 }}>{hint}</span>}
    </label>
  )
}

export function Modal({ open, title, onClose, children, footer, wide }) {
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => e.key === 'Escape' && onClose?.()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="modal-mask" onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}>
      <div className={`modal ${wide ? 'modal--wide' : ''}`}>
        <header className="modal__head">
          <div className="modal__title">{title}</div>
          <button type="button" className="modal__close" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </header>
        <div className="modal__body">{children}</div>
        {footer && <footer className="modal__foot">{footer}</footer>}
      </div>
    </div>
  )
}

export function Avatar({ src, name = '', size = '', className = '' }) {
  const cn = `avatar ${size ? `avatar--${size}` : ''} ${className}`
  if (src) return <img className={cn} src={src} alt={name || '人脸照片'} loading="lazy" />
  return <div className={`${cn} avatar--fallback`}>{(name || '?').slice(0, 1)}</div>
}

export function ConfidenceBar({ value, showText = true }) {
  const v = Math.max(0, Math.min(1, Number(value) || 0))
  const level = confidenceLevel(v)
  return (
    <div>
      <div className="confidence-bar">
        <div
          className={`confidence-bar__fill confidence-bar__fill--${level}`}
          style={{ width: `${(v * 100).toFixed(1)}%` }}
        />
      </div>
      {showText && (
        <div className="muted" style={{ fontSize: 11.5, marginTop: 3 }}>
          {percent(v)}（{level === 'high' ? '高' : level === 'mid' ? '达标' : '偏低'}）
        </div>
      )}
    </div>
  )
}

export function Pager({ meta, onChange }) {
  if (!meta || meta.pages <= 1) {
    return (
      <div className="pager">
        <span>共 {meta?.total ?? 0} 条</span>
      </div>
    )
  }
  const { page, pages, total, page_size: pageSize } = meta
  return (
    <div className="pager">
      <span>
        共 {total} 条 · 第 {page}/{pages} 页 · 每页 {pageSize}
      </span>
      <div className="pager__btns">
        <button type="button" className="btn btn--sm" disabled={page <= 1} onClick={() => onChange(1)}>
          首页
        </button>
        <button type="button" className="btn btn--sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          上一页
        </button>
        <button type="button" className="btn btn--sm" disabled={page >= pages} onClick={() => onChange(page + 1)}>
          下一页
        </button>
        <button type="button" className="btn btn--sm" disabled={page >= pages} onClick={() => onChange(pages)}>
          末页
        </button>
      </div>
    </div>
  )
}

export function KV({ items }) {
  return (
    <div className="kv">
      {items.map(([k, v]) => (
        <div key={k} style={{ display: 'contents' }}>
          <div className="kv__k">{k}</div>
          <div className="kv__v">{v}</div>
        </div>
      ))}
    </div>
  )
}

export function TimeText({ iso }) {
  return <span title={formatDateTime(iso)}>{formatDateTime(iso)}</span>
}
