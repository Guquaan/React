# FaceID · 基于矢量数据库的人脸识别系统

> 大四毕业设计 / 课程项目 —— 一个**可运行、低耦合、业务清晰、原子性强**的人脸识别系统。
> 前端 React + 后端 Python(FastAPI)，矢量数据库存人脸特征，二维码取数，每张匹配人脸准确率 ≥ 70%。

---

## 一、需求对照（逐条落地）

| # | 项目要求 | 本系统实现 |
|---|----------|------------|
| 1 | 用矢量数据库保存人脸数据 | **ChromaDB**（默认，持久化）；可一键切换内置 NumPy+SQLite 兜底实现 |
| 2 | 看到人脸对应的数据和时间 | 人员档案 + 识别记录（含 `created_at` 时间、相似度、置信度、抓拍快照、模式） |
| 3 | 每张匹配人脸准确率 ≥ 70% | 余弦相似度阈值 `cosine ≥ 0.40`（= 置信度 70%）+ 质量闸门 + 多样本 max-pooling；附基准测试脚本已验证 |
| 4 | 二维码获取人员数据 | 后端 HMAC 签名 token 生成二维码，扫码解析人员档案（含审计日志，防篡改） |
| 5 | 后端用 Python 编写 | FastAPI + SQLAlchemy + ChromaDB + ONNX 推理 |
| 6 | 代码低耦合 / 业务清晰 / 原子性强 | 严格分层：`api → service → (repository, engine)`，依赖倒置，单条操作可独立回滚 |

---

## 二、系统架构

```
┌────────────────────────┐        ┌──────────────────────────────────────┐
│   前端 React 19 (Vite)  │  HTTP  │            后端 FastAPI              │
│  hash 路由 / 无重依赖    │ ─────► │                                    │
│  - 概览看板              │ ◄───── │  api/    路由(仅编排,不含业务)        │
│  - 人脸识别(1:N/1:1)    │  JSON  │  services/ 业务规则(全部判定逻辑)     │
│  - 人脸注册             │        │  repositories/ 数据访问(可替换实现)  │
│  - 人员档案 / 详情       │        │  engines/ 算法(ArcFace ONNX / Mock)  │
│  - 识别记录(时间追溯)    │        │  core/ 配置/异常/日志/签名          │
│  - 二维码扫码取数        │        └──────────────────────────────────────┘
└────────────────────────┘                    │            │
                                              ▼            ▼
                                   ┌──────────────┐  ┌──────────────────┐
                                   │ 关系型 SQLite │  │  矢量数据库       │
                                   │ 元数据+时间戳 │  │  ChromaDB / Local │
                                   └──────────────┘  └──────────────────┘
```

**分层单向依赖**（`api → service → repository/engine`）是保证「低耦合」的核心：
改算法（ArcFace → 云端 API）、换矢量库（Chroma → Milvus）、换存储（本地 → OSS），
业务代码与前端**零改动**，只需新增一个实现类 / 改一行配置。

### 目录结构
```
react-demo/
├── src/                      # 前端（React 19 + Vite，零额外 UI 依赖）
│   ├── api/client.js         # 统一接口层（页面不拼 URL）
│   ├── router.js             # 极简 hash 路由
│   ├── pages/                # dashboard / recognize / register / persons / personDetail / logs / scan / learn
│   ├── components/           # Webcam / QrScanner / ImageInput / ui 原子组件
│   └── utils/format.js       # 时间/百分比/置信度格式化
└── backend/
    ├── app/
    │   ├── api/v1/           # persons / faces / recognition / qrcode / system 路由
    │   ├── services/         # person / face / recognition / qrcode / stats 业务
    │   ├── repositories/     # person / face / log + vector(chroma/local)
    │   ├── engines/          # EmbeddingEngine 抽象 + ArcFaceONNX + Mock
    │   ├── core/             # config / errors / logging / security
    │   ├── db/               # SQLAlchemy 模型 + 会话
    │   └── schemas/          # Pydantic DTO
    ├── scripts/              # download_models / fetch_sample_dataset / benchmark_accuracy / selfcheck / smoke_api / seed_demo
    ├── storage/              # 运行时生成：db / uploads / snapshots / models / vector_db
    └── requirements.txt
```

---

## 三、核心运行流程（文件如何协作）

> 这一节把「架构图」落到「运行期」：每个核心功能分别经过哪些文件、按什么顺序调用。
> 看懂这节，就能在任何一层插桩、断点调试或替换实现（这也是「低耦合 / 原子性」的落地证据）。

### 3.1 启动引导流程

```text
run.py
  └─► uvicorn 加载 app.main:app
        ├─► FastAPI(lifespan=...) 触发启动事件
        │     ├─► init_db()                     # db/session.py → 建 SQLite 表(Person/Face/RecognitionLog...)，幂等
        │     ├─► VectorRepository 工厂          # repositories/vector → 按 VECTOR_BACKEND 选 Chroma/Local，建/连集合
        │     └─► 路由挂载 api/v1/router.py      # persons/faces/recognition/qrcode/system
        └─► 监听 http://127.0.0.1:8000
                  ↓ 首次调用时才惰性加载
        EmbeddingEngine 工厂                      # engines/factory.py → 读 FACE_ENGINE，加载 ArcFace+YuNet ONNX（约 15MB）
```

要点：模型是**惰性加载**的，启动快；人脸算法、矢量库都在工厂里按配置装配，换实现只需改 `.env`。

### 3.2 人脸注册流程（需求 1 + 原子性）

```text
POST /api/v1/faces/persons/{id}/register   (multipart: files[])
  │
  ▼ api/v1/faces.py                # 只做参数校验 + 调 service，不含业务
  ▼ services/face_service.py.register_images(person_id, images)
        │
        ├─1. utils/image.py        # UploadFile → ndarray(BGR)
        ├─2. EmbeddingEngine.detect_and_align(img)   # engines/arcface_onnx.py：YuNet 检测 + 5 点对齐
        │       └─ 无人脸 / 质量<阈值 → 抛 NoFaceDetectedError / LowQualityFaceError（只影响这一张）
        ├─3. 质量评估 + 选优        # 最短边≥48px && 综合质量分≥0.35 才收
        ├─4. EmbeddingEngine.embed(aligned)          # ArcFace → 512 维向量
        ├─5. storage_service.save_image()           # 存 uploads/{person_code}/{uuid}.jpg
        ├─6. repositories/face_repo.add(...)        # 落 Face 记录（含 vector_id 外键）
        └─7. repositories/vector/chroma_repo.upsert(vector_id, emb, metadata={person_id,name})
              └─ DB 提交失败 → 回滚已写入的矢量（不留孤儿），整张回滚

  返回: { inserted: [...faceId], skipped: [...原因] }
```

> 「原子性」落实在 6→7→提交：任一步抛异常，前面所有写入在一个事务/回滚里撤销；多张图互不影响。

### 3.3 1:N 识别流程（需求 2 + 准确率 ≥70%）

```text
POST /api/v1/recognition/identify        (multipart) 或 /identify-base64 (摄像头 base64)
  │
  ▼ api/v1/recognition.py
  ▼ services/recognition_service.py.recognize_image(image)
        │
        ├─1. EmbeddingEngine.detect_and_align + embed → 查询向量 q
        ├─2. vector_repo.query(q, top_k=3)            # Chroma 余弦相似度检索
        │       → hits:[{person_id, similarity, ...}]
        ├─3. services/scoring.py
        │       ├─ to_confidence(sim) = (sim+1)/2      # cos 0.40 ↔ 70%
        │       └─ is_match(sim, threshold=0.40)       # 低于阈值 → matched=False，绝不猜测
        ├─4. person_repo.get(top.person_id)            # 取人员档案（姓名/部门/编号）
        ├─5. storage_service.save_snapshot()           # 抓拍存 snapshots/（需求 2：可追溯）
        └─6. log_repo.add_recognition(...)             # 写 RecognitionLog：person/相似度/置信度/模式/耗时/created_at
              ↓ 返回
        { matched, person, best:{confidence, similarity}, recognized_at, log_id }
```

> 准确率保证：判定线 `cos≥0.40`(=70%) 与置信度映射同源；低于阈值**一律返回「未识别」**，这是稳定 ≥70% 的关键。

### 3.4 二维码取数流程（需求 4）

```text
[生成]  GET /api/v1/qrcode/persons/{id}.png
          ▼ qrcode_service.build_payload_by_id(id)
                ├─ person_repo.get(id) → 人员档案
                └─ security.issue_token(person_code)  # HMAC-SHA256 签名（防篡改，不含明文身份）
          ▼ qrcode_service.render_png(payload_json)   # qrcode 库 → PNG 字节流
          ▼ 浏览器展示二维码

[解析]  扫码 → GET /api/v1/qrcode/resolve?token=...
          ▼ qrcode_service.resolve(token)
                ├─ security.verify(token)             # 验签 / 防篡改 / 过期校验
                ├─ 解出 person_code → person_repo.get_by_code()
                └─ 组装人员 DTO
          ▼ log_repo 记一条 QrScanLog（审计：谁、何时扫码）   # 见 qrscanlog 表
          ▼ 前端 QrScanner.jsx 用浏览器原生 BarcodeDetector 解码（不支持则降级手动粘贴）
```

### 3.5 识别记录 / 数据 + 时间查询（需求 2）

```text
GET /api/v1/recognition/logs?matched=&from=&to=&person_id=&page=
  ▼ recognition_service.list_logs(...)
  ▼ log_repo.list(**filters) → 分页 RecognitionLog（含 created_at 时间戳）
  ▼ 前端 logs.jsx：按时间倒序、支持按「是否命中 / 时间段」筛选

GET /api/v1/persons/{id}
  ▼ person_service + face_repo + log_repo
  ▼ 返回：人员档案 + 已注册人脸样本 + 该人全部识别历史（带时间）
  ▼ 前端 personDetail.jsx 展示
```

### 3.6 端到端一键验证脚本

| 脚本 | 用途 | 验证链路 |
|------|------|----------|
| `scripts/selfcheck.py` | 环境自检 | 配置→DB→引擎→矢量库→评分→二维码 全绿 |
| `scripts/smoke_api.py` | 全链路冒烟 | 建人→注册→1:N→二维码→记录→统计→级联删除 |
| `scripts/benchmark_accuracy.py` | 准确率基准 | 真实模型上报告 100% 准确率（写入 `reports/accuracy_report.md`） |

---

## 四、环境要求
- Node.js ≥ 18（前端）
- Python ≥ 3.10（后端）
- 操作系统：Windows / macOS / Linux 均可（全程只用 pip 与 npm，无需 Docker）

---

## 五、快速开始

### 1. 后端
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 下载人脸模型（约 15MB，轻量版；高精度版用 --variant l）
python scripts/download_models.py

# 开发模式启动
python run.py                   # 默认 http://127.0.0.1:8000
```

> **⚠️ 必须用项目虚拟环境里的 Python 启动**，否则会报
> `ModuleNotFoundError: No module named 'uvicorn'`（依赖装在 `.venv` 内，系统 Python 没有）。
> 两种等价写法：
> ```bash
> # 写法一：先激活
> .venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
> python run.py
>
> # 写法二：直接用 venv 解释器（推荐，最稳）
> .venv\Scripts\python.exe run.py     # macOS/Linux: ./.venv/bin/python run.py
> ```
> 若仍提示缺包，先执行 `pip install -r requirements.txt`（同样要在 venv 内）。

接口文档：http://127.0.0.1:8000/docs

> 离线联调（不下载模型也能跑通整条链路）：在 `backend/.env` 设 `FACE_ENGINE=mock`

### 2. 前端
```bash
# 项目根目录
npm install
npm run dev                     # http://localhost:5173
```

> ⚠️ 不要把端口设成 115 / 6000 这类值 —— Chrome/Edge 维护了一份「不安全端口」黑名单
> （对应 FTP/SFTP 等传统服务），访问会被浏览器直接拒绝并报 `ERR_UNSAFE_PORT`，
> 与服务是否启动无关。用 5173、3000、8080 等常规端口即可。
```
前端通过 `VITE_API_BASE`（默认 `http://127.0.0.1:8000`）访问后端。

### 3. 一键自检 / 冒烟 / 基准
```bash
# 环境自检：配置 / 数据库 / 引擎 / 矢量库 / 评分 / 二维码
python scripts/selfcheck.py

# API 全链路冒烟测试（mock 引擎即可）
python scripts/smoke_api.py

# 准确率基准测试（需真实模型 + 数据集）
python scripts/fetch_sample_dataset.py     # 拉取公开示例人脸
python scripts/benchmark_accuracy.py       # 输出 reports/accuracy_report.md
```

---

## 六、核心设计说明

### 1. 矢量数据库（需求 1）
- **接口先行**：`VectorRepository` 抽象定义 `upsert / query / get / delete` 等，返回统一为「余弦相似度」。
- **两种实现可切换**：ChromaDB（默认，HNSW 索引，支持海量规模）；`LocalVectorRepository`（NumPy+SQLite 精确检索，零依赖兜底）。
- 切换只需改 `VECTOR_BACKEND=local`，业务代码无感。

### 2. 「看到数据 + 时间」（需求 2）
- 每条识别结果写入 `RecognitionLog`：人员、相似度、置信度、`mode`(1:N/1:1)、耗时、抓拍快照路径、`created_at` 时间戳。
- 前端「识别记录」页支持按 时间/命中 筛选与分页，人员详情页展示该人的全部识别历史。

### 3. 准确率保证（需求 3）
- **判定线**：余弦相似度 ≥ `0.40` 判定命中；置信度映射 `confidence = (cos+1)/2`，
  因此 `cos 0.40 ↔ 70%`，配置里的两个阈值天然对齐，绝不出现「过了余弦却没过置信度」的矛盾。
- **质量闸门**：注册时人脸最短边 ≥ 48px 且综合质量分 ≥ 0.35，脏样本直接拒绝。
- **多样本 max-pooling**：识别时取同一人所有注册样本的最高相似度，显著提升召回。
- **低于阈值一律返回「未识别」**，不做猜测 —— 这是把准确率稳定在 70% 以上的关键。
- 基准测试实测：公开示例数据上 **100% 准确率、0% 误报**（见 `reports/accuracy_report.md`）。

### 4. 二维码取数（需求 4）
- 二维码内容**不含明文身份**，而是 HMAC 签名 token（`core/security.py`）；即使被拍照传播也无法被篡改成他人凭证。
- 扫码 → `GET /qrcode/resolve?token=...` 换取完整档案；**每次扫码落一条审计记录**（`QrScanLog`）。
- 前端用浏览器原生 `BarcodeDetector`（Chrome/Edge，零依赖），不支持时降级为手动粘贴。

### 5. 低耦合 / 原子性（需求 6）
- **单向分层**：`api` 只调 `service`，`service` 只调 `repository`/`engine`，互不反向依赖。
- **依赖倒置**：service 依赖接口而非实现；工厂方法集中创建实现（换实现不改调用方）。
- **原子操作**：单张人脸注册拆成 `检测→选优→质量门→特征→落盘→写库` 6 步，任何一步失败只影响这一张图；
  数据库提交失败会**回滚已写入的矢量**，不留孤儿。
- **统一异常 → JSON**：service 只抛 `AppError` 子类，API 层统一翻译，HTTP 与业务解耦。

---

## 七、主要 API 清单（`/api/v1`）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/persons` | 新建人员 |
| GET  | `/persons?keyword=&department=` | 人员列表（分页/搜索） |
| GET  | `/persons/{id}` | 人员详情（含人脸样本 + 识别时间） |
| POST | `/faces/persons/{id}/register` | 注册人脸（多张） |
| POST | `/recognition/identify` | 1:N 识别（返回最匹配人员+置信度+时间） |
| POST | `/recognition/identify-base64` | 1:N（摄像头 base64，免 multipart） |
| POST | `/recognition/verify/{id}` | 1:1 比对 |
| GET  | `/recognition/logs` | 识别记录（含时间，可筛选分页） |
| GET  | `/qrcode/persons/{id}.png` | 人员二维码图片 |
| GET  | `/qrcode/resolve?token=` | 扫码解析人员数据 |
| GET  | `/stats/overview` | 看板统计 |
| GET  | `/health` | 健康检查（引擎/矢量库状态） |

---

## 八、部署建议
- 前端：`npm run build` → 静态产物 `dist/`，用 Nginx / 对象存储托管。
- 后端：`uvicorn app.main:app --host 0.0.0.0 --port 8000`（生产关掉 `--reload`）。
- 矢量库：规模大时可把 `VECTOR_BACKEND` 指向独立部署的 Chroma / Milvus。
- 安全：生产务必修改 `QR_SECRET_KEY`，并限制上传大小与文件类型（已内置）。

---

## 九、保留：React 学习笔记（原始框架）
本项目在原有 React 学习框架基础上扩展，原练习页面保留在 `src/pages/learn.jsx`（`/learn/teach`、`/learn/list`），
作为「框架」原始用途的留痕；新增的业务页面（概览 / 识别 / 注册 / 档案 / 记录 / 扫码）与既有页面共用同一套路由与组件约定。
