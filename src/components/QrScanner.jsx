/**
 * 二维码扫描器。
 * 优先使用浏览器原生的 BarcodeDetector（Chrome / Edge 支持，零依赖），
 * 不支持时自动降级为「手动粘贴二维码内容」。
 */
import { useCallback, useEffect, useRef, useState } from 'react'

export const hasBarcodeDetector = typeof window !== 'undefined' && 'BarcodeDetector' in window

export default function QrScanner({ onResult, onError }) {
  const videoRef = useRef(null)
  const rafRef = useRef(0)
  const streamRef = useRef(null)
  const [running, setRunning] = useState(false)
  const [manual, setManual] = useState('')
  const [supported] = useState(hasBarcodeDetector)

  const stop = useCallback(() => {
    cancelAnimationFrame(rafRef.current)
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setRunning(false)
  }, [])

  const start = useCallback(async () => {
    if (!supported) return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      })
      streamRef.current = stream
      videoRef.current.srcObject = stream
      await videoRef.current.play()
      setRunning(true)

      const detector = new window.BarcodeDetector({ formats: ['qr_code'] })
      const tick = async () => {
        if (!videoRef.current || !running) return
        try {
          const codes = await detector.detect(videoRef.current)
          if (codes?.length) {
            onResult?.(codes[0].rawValue)
            stop()
            return
          }
        } catch {
          /* 单帧失败忽略 */
        }
        rafRef.current = requestAnimationFrame(tick)
      }
      rafRef.current = requestAnimationFrame(tick)
    } catch (err) {
      onError?.(`无法打开摄像头：${err.message || err.name}`)
    }
  }, [onError, onResult, running, stop, supported])

  useEffect(() => () => stop(), [stop])

  return (
    <div>
      {supported ? (
        running ? (
          <div className="webcam-wrap">
            <video ref={videoRef} playsInline muted />
            <div className="webcam-overlay">
              <div
                style={{
                  width: '58%',
                  aspectRatio: '1 / 1',
                  border: '2px dashed rgba(255,255,255,.8)',
                  borderRadius: 14,
                }}
              />
            </div>
          </div>
        ) : (
          <div className="dropzone" onClick={start} style={{ minHeight: 170, display: 'grid', placeItems: 'center' }}>
            <div>
              <div className="dropzone__icon">🔍</div>
              <div className="dropzone__text">点击开启摄像头扫描二维码</div>
              <div className="dropzone__hint">浏览器原生 BarcodeDetector 识别，无需安装任何依赖</div>
            </div>
          </div>
        )
      ) : (
        <div className="alert alert--warn">
          当前浏览器不支持原生二维码识别（推荐使用 Chrome / Edge）。请在下方手动粘贴二维码里的链接或 token。
        </div>
      )}

      {running && (
        <div className="btn-row mt-12">
          <button type="button" className="btn" onClick={stop}>
            停止扫描
          </button>
        </div>
      )}

      <div className="divider" />
      <div className="field">
        <span className="field__label">手动输入二维码内容</span>
        <textarea
          className="textarea"
          placeholder="粘贴 http://127.0.0.1:8000/api/v1/qrcode/resolve?token=xxx 或直接粘贴 token"
          value={manual}
          onChange={(e) => setManual(e.target.value)}
        />
      </div>
      <button
        type="button"
        className="btn btn--primary"
        disabled={!manual.trim()}
        onClick={() => onResult?.(manual.trim())}
      >
        解析并获取人员数据
      </button>
    </div>
  )
}
