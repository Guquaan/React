/**
 * 极简 hash 路由 —— 不引入任何第三方依赖（保持原学习项目的依赖整洁）。
 *   #/recognize          普通路径
 *   #/scan?code=xxx      带参数
 */
import { useCallback, useEffect, useState } from 'react'

function current() {
  const raw = window.location.hash.replace(/^#/, '')
  return raw || '/'
}

export function navigate(to, { replace = false } = {}) {
  const target = to.startsWith('#') ? to : `#${to}`
  if (replace) {
    window.history.replaceState(null, '', target)
    window.dispatchEvent(new HashChangeEvent('hashchange'))
  } else {
    window.location.hash = target
  }
}

export function useRoute() {
  const [hash, setHash] = useState(current)

  useEffect(() => {
    const onChange = () => setHash(current())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  const [path, search = ''] = hash.split('?')
  const params = new URLSearchParams(search)

  const go = useCallback((to, opts) => navigate(to, opts), [])

  return {
    /** 形如 /persons/abc123 的路径部分 */
    path: path || '/',
    /** URLSearchParams */
    params,
    /** 当前 hash 原文 */
    hash,
    go,
  }
}

/** 匹配 /persons/:id 这类路径，返回参数对象或 null */
export function matchPath(path, pattern) {
  const p = path.split('/').filter(Boolean)
  const t = pattern.split('/').filter(Boolean)
  if (p.length !== t.length) return null
  const out = {}
  for (let i = 0; i < t.length; i += 1) {
    if (t[i].startsWith(':')) out[t[i].slice(1)] = decodeURIComponent(p[i])
    else if (t[i] !== p[i]) return null
  }
  return out
}
