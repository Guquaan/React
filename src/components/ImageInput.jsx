/** 图片选择器：点击选择 + 拖拽上传 + 预览 */
import { useCallback, useEffect, useRef, useState } from 'react'

export default function ImageInput({ files, onChange, multiple = false, hint }) {
  const inputRef = useRef(null)
  const [over, setOver] = useState(false)
  const [previews, setPreviews] = useState([])

  useEffect(() => {
    const list = files || []
    const urls = list.map((f) => URL.createObjectURL(f))
    setPreviews(urls)
    return () => urls.forEach((u) => URL.revokeObjectURL(u))
  }, [files])

  const accept = useCallback(
    (list) => {
      const imgs = Array.from(list).filter((f) => f.type.startsWith('image/'))
      if (!imgs.length) return
      onChange(multiple ? [...(files || []), ...imgs].slice(0, 10) : [imgs[0]])
    },
    [files, multiple, onChange],
  )

  const remove = (idx) => onChange((files || []).filter((_, i) => i !== idx))

  return (
    <div>
      <div
        className={`dropzone ${over ? 'dropzone--over' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setOver(true)
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setOver(false)
          accept(e.dataTransfer.files)
        }}
      >
        <div className="dropzone__icon">🖼️</div>
        <div className="dropzone__text">点击选择图片{multiple ? '（可多选，建议 3~5 张不同角度）' : ''}</div>
        <div className="dropzone__hint">{hint || '支持 JPG / PNG / BMP / WEBP，单张不超过 8MB；也可直接把图片拖进来'}</div>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple={multiple}
        style={{ display: 'none' }}
        onChange={(e) => {
          accept(e.target.files)
          e.target.value = ''
        }}
      />

      {previews.length > 0 && (
        <div className="face-grid mt-12">
          {previews.map((url, i) => (
            <div className="face-tile" key={url}>
              <img src={url} alt={`待上传 ${i + 1}`} />
              <button type="button" className="face-tile__del" onClick={() => remove(i)} title="移除">
                ×
              </button>
              <div className="face-tile__foot">
                <div className="mono" style={{ fontSize: 10.5 }}>
                  {(files[i]?.size / 1024).toFixed(0)} KB
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
