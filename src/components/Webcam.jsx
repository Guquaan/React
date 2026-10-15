/** 摄像头面板：实时预览 + 抽帧抓拍 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { captureFrame } from '../utils/format'

export default function Webcam({ onCapture, onError, autoStart = false, intervalMs = 0 }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const timerRef = useRef(null)
  const [running, setRunning] = useState(false)
  const [busy, setBusy] = useState(false)

  const stop = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setRunning(false)
  }, [])

  const start = useCallback(async () => {
    setBusy(true)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setRunning(true)
    } catch (err) {
      onError?.(`无法打开摄像头：${err.message || err.name}。请检查浏览器权限，或改用「上传图片」方式。`)
    } finally {
      setBusy(false)
    }
  }, [onError])

  useEffect(() => () => stop(), [stop])
  useEffect(() => {
    if (autoStart) start()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const shoot = useCallback(async () => {
    if (!videoRef.current || !running) return
    try {
      const { file, dataUrl } = await captureFrame(videoRef.current)
      onCapture?.(file, dataUrl)
    } catch (err) {
      onError?.(err.message)
    }
  }, [onCapture, onError, running])

  useEffect(() => {
    if (intervalMs > 0 && running) {
      timerRef.current = setInterval(shoot, intervalMs)
      return () => clearInterval(timerRef.current)
    }
    return undefined
  }, [intervalMs, running, shoot])

  return (
    <div>
      {running ? (
        <div className="webcam-wrap">
          <video ref={videoRef} playsInline muted />
          <div className="webcam-overlay">
            <div className="webcam-frame" />
          </div>
        </div>
      ) : (
        <div
          className="dropzone"
          style={{ minHeight: 190, display: 'grid', placeItems: 'center' }}
          onClick={busy ? undefined : start}
        >
          <div>
            <div className="dropzone__icon">📷</div>
            <div className="dropzone__text">{busy ? '正在请求摄像头权限…' : '点击开启摄像头'}</div>
            <div className="dropzone__hint">需要浏览器允许摄像头权限；建议在 localhost 或 https 下使用</div>
          </div>
        </div>
      )}
      <div className="btn-row mt-12">
        {running ? (
          <>
            <button type="button" className="btn btn--primary" onClick={shoot}>
              抓拍并识别
            </button>
            <button type="button" className="btn" onClick={stop}>
              关闭摄像头
            </button>
          </>
        ) : (
          <button type="button" className="btn btn--primary" onClick={start} disabled={busy}>
            开启摄像头
          </button>
        )}
      </div>
    </div>
  )
}
