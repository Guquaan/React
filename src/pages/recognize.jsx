import { useCallback, useState } from 'react'
import ImageInput from '../components/ImageInput'
import Webcam from '../components/Webcam'
import { Alert, Avatar, Badge, Card, ConfidenceBar, Empty, KV } from '../components/ui'
import { mediaUrl, personApi, recognitionApi } from '../api/client'
import { fixed, formatDateTime, percent } from '../utils/format'

function ResultPanel({ result }) {
  if (!result) return null
  const { matched, best, person, candidates, elapsed_ms: elapsed, recognized_at: at, face_count: faceCount } = result

  return (
    <div className={`result-panel ${matched ? 'result-panel--ok' : 'result-panel--fail'} mt-16`}>
      <div className="result-panel__head">
        <div>
          {matched ? (
            <>
              <Badge tone="green">✅ 识别成功</Badge>
              <div className="result-panel__name mt-8">{person?.name || best?.person_name}</div>
              <div className="muted">
                {person?.person_code} · {person?.department || '未分组'} {person?.title ? `· ${person.title}` : ''}
              </div>
            </>
          ) : (
            <>
              <Badge tone="red">❌ 未匹配到人员</Badge>
              <div className="result-panel__name mt-8">未识别</div>
              <div className="muted">最高置信度未达到阈值，系统按“不认识”处理（避免误报）</div>
            </>
          )}
        </div>
      </div>

      <div className="divider" />

      <div className="grid grid--2">
        <div>
          <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>
            匹配置信度
          </div>
          <ConfidenceBar value={best?.confidence ?? 0} />
        </div>
        <KV
          items={[
            ['余弦相似度', best ? fixed(best.similarity) : '—'],
            ['置信度阈值', `${percent(result.confidence_floor, 0)}（cosine ≥ ${result.threshold}）`],
            ['识别时间', formatDateTime(at)],
            ['处理耗时', `${elapsed} ms`],
            ['画面中检测到人脸', `${faceCount} 张`],
          ]}
        />
      </div>

      {person && (
        <div className="row mt-12" style={{ alignItems: 'flex-start' }}>
          <Avatar src={mediaUrl(person.primary_image_url)} name={person.name} size="lg" />
          <div className="grow">
            <KV
              items={[
                ['工号/学号', person.employee_no || '—'],
                ['手机', person.phone || '—'],
                ['邮箱', person.email || '—'],
                ['已注册样本', `${person.face_count} 张`],
                ['建档时间', formatDateTime(person.created_at)],
              ]}
            />
          </div>
        </div>
      )}

      {candidates?.length > 0 && (
        <>
          <div className="section-title">检索候选（Top {candidates.length}）</div>
          <table className="table">
            <thead>
              <tr>
                <th>#</th>
                <th>人员</th>
                <th>相似度</th>
                <th>置信度</th>
                <th>判定</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((c, i) => (
                <tr key={c.person_id}>
                  <td>{i + 1}</td>
                  <td>
                    <div className="person-cell">
                      <Avatar src={mediaUrl(c.image_url)} name={c.person_name} />
                      <div>
                        <div className="person-cell__name">{c.person_name}</div>
                        <div className="person-cell__meta">
                          {c.person_code} · {c.department || '未分组'}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="table__mono">{fixed(c.similarity)}</td>
                  <td>{percent(c.confidence)}</td>
                  <td>{c.passed ? <Badge tone="green">达标</Badge> : <Badge tone="gray">低于阈值</Badge>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}

export default function Recognize() {
  const [tab, setTab] = useState('upload')
  const [files, setFiles] = useState([])
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [notReady, setNotReady] = useState(false)

  // 1:1 比对
  const [personId, setPersonId] = useState('')
  const [personOptions, setPersonOptions] = useState([])
  const [verifyResult, setVerifyResult] = useState(null)

  const loadPersons = useCallback(() => {
    personApi
      .list({ page: 1, page_size: 200 })
      .then((r) => setPersonOptions(r.data.items))
      .catch(() => setPersonOptions([]))
  }, [])

  const identifyFile = useCallback(async (file) => {
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const r = await recognitionApi.identify(file, { top_k: 5 })
      setResult(r.data)
    } catch (e) {
      if (e.code === 'NO_FACE_DETECTED') setError('未在图片中检测到人脸，请上传清晰的正面照片。')
      else if (e.message?.includes('模型未就绪')) {
        setNotReady(true)
        setError('人脸引擎未就绪：请先下载模型（python scripts/download_models.py），或把 FACE_ENGINE 设为 mock。')
      } else setError(e.message)
    } finally {
      setBusy(false)
    }
  }, [])

  const handleIdentify = async () => {
    if (!files[0]) return setError('请先选择一张图片')
    await identifyFile(files[0])
  }

  const handleVerify = async () => {
    if (!personId) return setError('请选择要比对的人员')
    if (!files[0]) return setError('请先选择一张图片')
    setBusy(true)
    setError('')
    setVerifyResult(null)
    try {
      const r = await recognitionApi.verify(personId, files[0])
      setVerifyResult(r.data)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const switchTab = (t) => {
    setTab(t)
    if (t === 'camera') setFiles([])
  }

  return (
    <div className="grid grid--sidebar">
      <div>
        <Card
          title="输入人脸图片"
          desc="支持上传照片或直接调用摄像头；识别结果会同时写入识别记录"
          extra={
            <div className="btn-row">
              <button
                type="button"
                className={`btn btn--sm ${tab === 'upload' ? 'btn--primary' : ''}`}
                onClick={() => switchTab('upload')}
              >
                上传图片
              </button>
              <button
                type="button"
                className={`btn btn--sm ${tab === 'camera' ? 'btn--primary' : ''}`}
                onClick={() => switchTab('camera')}
              >
                摄像头
              </button>
            </div>
          }
        >
          {error && <Alert tone={notReady ? 'warn' : 'error'}>{error}</Alert>}

          {tab === 'upload' ? (
            <ImageInput files={files} onChange={setFiles} hint="建议正脸、光线均匀、人脸占画面 1/3 以上" />
          ) : (
            <Webcam onCapture={(file) => identifyFile(file)} onError={setError} />
          )}

          <div className="btn-row mt-12">
            <button type="button" className="btn btn--primary" onClick={handleIdentify} disabled={busy || !files[0]}>
              {busy ? '识别中…' : '开始识别（1:N）'}
            </button>
            {files.length > 0 && (
              <button type="button" className="btn" onClick={() => { setFiles([]); setResult(null) }} disabled={busy}>
                清空
              </button>
            )}
          </div>
        </Card>

        <ResultPanel result={result} />
      </div>

      <div>
        <Card title="1:1 人脸比对" desc="判断某张照片是否属于指定人员">
          <div className="field">
            <span className="field__label">选择人员</span>
            <select
              className="select"
              value={personId}
              onFocus={loadPersons}
              onChange={(e) => setPersonId(e.target.value)}
            >
              <option value="">请选择…</option>
              {personOptions.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}（{p.person_code}）
                </option>
              ))}
            </select>
          </div>
          <button type="button" className="btn btn--block" onClick={handleVerify} disabled={busy}>
            与当前图片比对
          </button>

          {verifyResult && (
            <div className={`result-panel ${verifyResult.matched ? 'result-panel--ok' : 'result-panel--fail'} mt-12`}>
              <Badge tone={verifyResult.matched ? 'green' : 'red'}>
                {verifyResult.matched ? '✅ 同一人' : '❌ 非同一人'}
              </Badge>
              <ConfidenceBar value={verifyResult.confidence} />
              <KV
                items={[
                  ['余弦相似度', fixed(verifyResult.similarity)],
                  ['判定阈值', `cosine ≥ ${verifyResult.threshold}`],
                  ['比对时间', formatDateTime(verifyResult.recognized_at)],
                  ['耗时', `${verifyResult.elapsed_ms} ms`],
                ]}
              />
            </div>
          )}
        </Card>

        <Card title="判定规则说明" className="mt-16">
          <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.85 }}>
            1. 提取待识别人脸的 512 维 ArcFace 特征；
            <br />
            2. 在矢量数据库里做余弦相似度近邻检索；
            <br />
            3. 相似度 ≥ <strong>0.40</strong>（约等于置信度 <strong>70%</strong>）判定为命中；
            <br />
            4. 低于阈值一律返回“未识别”，不做猜测 —— 这是保证准确率的关键。
          </div>
        </Card>

        {!result && (
          <Card title="还没有识别结果" className="mt-16">
            <Empty icon="🎯" title="等待识别" hint="选择图片后点击「开始识别（1:N）」" />
          </Card>
        )}
      </div>
    </div>
  )
}
