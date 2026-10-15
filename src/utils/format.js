/** 格式化工具（时间、百分比、文件大小等） */

/** 后端返回 UTC ISO 字符串，这里统一转成本地时间展示 */
export function formatDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(
    d.getMinutes(),
  )}:${pad(d.getSeconds())}`
}

export function formatDate(iso) {
  if (!iso) return '—'
  return formatDateTime(iso).slice(0, 10)
}

export function formatTime(iso) {
  if (!iso) return '—'
  return formatDateTime(iso).slice(11)
}

/** 相对时间：3 分钟前 */
export function fromNow(iso) {
  if (!iso) return '—'
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (Number.isNaN(diff)) return '—'
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 2592000) return `${Math.floor(diff / 86400)} 天前`
  return formatDate(iso)
}

/** 0.8231 -> 82.3% */
export function percent(v, digits = 1) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '—'
  return `${(Number(v) * 100).toFixed(digits)}%`
}

export function fixed(v, digits = 4) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '—'
  return Number(v).toFixed(digits)
}

export function fileSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let n = bytes
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024
    i += 1
  }
  return `${n.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

export function genderText(g) {
  return { male: '男', female: '女', unknown: '未填写' }[g] || '未填写'
}

/** 置信度对应的语义颜色（低/中/高） */
export function confidenceLevel(v) {
  const n = Number(v) || 0
  if (n >= 0.85) return 'high'
  if (n >= 0.7) return 'mid'
  return 'low'
}

/** 把 File 转成 base64（去掉了 data: 前缀） */
export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result).split(',')[1] || '')
    reader.onerror = () => reject(new Error('图片读取失败'))
    reader.readAsDataURL(file)
  })
}

/** canvas / video 抽帧成 Blob */
export function captureFrame(videoEl, quality = 0.92) {
  const w = videoEl.videoWidth
  const h = videoEl.videoHeight
  if (!w || !h) throw new Error('摄像头尚未就绪')
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  canvas.getContext('2d').drawImage(videoEl, 0, 0, w, h)
  return new Promise((resolve) => {
    canvas.toBlob(
      (blob) => {
        const file = new File([blob], `capture_${Date.now()}.jpg`, { type: 'image/jpeg' })
        resolve({ file, dataUrl: canvas.toDataURL('image/jpeg', quality) })
      },
      'image/jpeg',
      quality,
    )
  })
}
