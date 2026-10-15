/**
 * 后端接口客户端 —— 前端唯一与后端通信的地方。
 * 所有页面都通过这里访问 API，方便统一改动前缀 / 加 token / 加拦截。
 */

const BASE = (import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000').replace(/\/$/, '')
export const API_PREFIX = '/api/v1'

/** 后端静态资源（人脸图片、抓拍快照）前缀 */
export const MEDIA_BASE = BASE

function url(path, params) {
  const u = new URL(BASE + API_PREFIX + path)
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') u.searchParams.set(k, v)
    })
  }
  return u.toString()
}

export class ApiError extends Error {
  constructor(message, code, detail) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.detail = detail
  }
}

async function handle(resp) {
  let body = null
  try {
    body = await resp.json()
  } catch {
    /* 非 JSON 响应 */
  }
  if (!resp.ok) {
    const msg = body?.message || `请求失败（HTTP ${resp.status}）`
    throw new ApiError(msg, body?.code || `HTTP_${resp.status}`, body?.detail)
  }
  return body
}

export const api = {
  base: BASE,

  /** GET */
  get(path, params) {
    return fetch(url(path, params)).then(handle)
  },

  /** POST JSON */
  post(path, body) {
    return fetch(url(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body ?? {}),
    }).then(handle)
  },

  /** PATCH JSON */
  patch(path, body) {
    return fetch(url(path), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body ?? {}),
    }).then(handle)
  },

  /** POST multipart（图片上传） */
  upload(path, files, params) {
    const fd = new FormData()
    const list = Array.isArray(files) ? files : [files]
    list.forEach((f) => fd.append('files', f, f.name || 'upload.jpg'))
    return fetch(url(path, params), { method: 'POST', body: fd }).then(handle)
  },

  /** POST 单文件字段名 upload 的接口 */
  uploadOne(path, file, params) {
    const fd = new FormData()
    fd.append('upload', file, file.name || 'upload.jpg')
    return fetch(url(path, params), { method: 'POST', body: fd }).then(handle)
  },

  del(path) {
    return fetch(url(path), { method: 'DELETE' }).then(handle)
  },
}

/** 把后端返回的相对地址补全成可访问 URL */
export function mediaUrl(u) {
  if (!u) return ''
  if (/^https?:\/\//i.test(u)) return u
  return MEDIA_BASE + (u.startsWith('/') ? u : `/${u}`)
}

/** 二维码图片地址 */
export function qrCodeUrl(personId, boxSize = 10) {
  return url(`/qrcode/persons/${personId}.png`, { box_size: boxSize })
}

/* ---------------- 领域接口（按业务分组，页面不拼路径） ---------------- */

export const personApi = {
  list: (params) => api.get('/persons', params),
  detail: (id) => api.get(`/persons/${id}`),
  byCode: (code) => api.get(`/persons/code/${code}`),
  create: (data) => api.post('/persons', data),
  update: (id, data) => api.patch(`/persons/${id}`, data),
  remove: (id) => api.del(`/persons/${id}`),
  departments: () => api.get('/persons/departments'),
}

export const faceApi = {
  register: (personId, files) => api.upload(`/faces/persons/${personId}/register`, files),
  detect: (file) => api.uploadOne('/faces/detect', file),
  remove: (faceId) => api.del(`/faces/${faceId}`),
  sync: () => api.post('/faces/sync-vectors'),
}

export const recognitionApi = {
  identify: (file, params) => api.uploadOne('/recognition/identify', file, params),
  identifyBase64: (image, params) => api.post(`/recognition/identify-base64?${new URLSearchParams(params)}`, { image }),
  verify: (personId, file) => api.uploadOne(`/recognition/verify/${personId}`, file),
  logs: (params) => api.get('/recognition/logs', params),
  logDetail: (id) => api.get(`/recognition/logs/${id}`),
}

export const qrcodeApi = {
  payload: (personId) => api.get(`/qrcode/persons/${personId}/payload`),
  resolve: (token) => api.get('/qrcode/resolve', { token }),
  parse: (raw) => api.get('/qrcode/parse', { url: raw }),
  scans: (params) => api.get('/qrcode/scans', params),
}

export const systemApi = {
  health: () => api.get('/health'),
  stats: () => api.get('/stats/overview'),
  config: () => api.get('/config'),
}
