# AI Service Frontdesk React + FastAPI 重构任务编排

## 1. 本轮目标

状态：未开始

在保留现有 LangGraph、RAG、storage 能力的前提下，将当前 Streamlit 调试界面升级为：

```text
React + TypeScript + Vite + Tailwind CSS 前端
FastAPI 后端
现有 LangGraph + RAG + JSON 存储
```

页面结构仍遵循 `PAGE_STRUCTURE_PLAN.md`：

```text
/chat                 客户咨询页
/admin/leads          线索看板
/admin/knowledge      知识库管理
/admin/profile        商家资料
/admin/test           系统测试
```

本轮不删除 Streamlit 版本。新前端和 FastAPI 作为并行升级版本，确保旧 demo 仍可运行。

## 2. 设计方向

状态：未开始

### 2.1 客户咨询页

参考 Mainframe 风格，但调整为本项目的真实业务入口：

- 首屏使用全屏居家服务视觉素材。
- 顶部导航简洁：品牌、服务范围、服务保障、联系客服。
- 首屏直接展示 AI 欢迎语、快捷问题和聊天输入框。
- 支持打字机效果。
- 快捷问题使用胶囊按钮。
- 用户首次输入后，在首屏内自然展开聊天记录。
- 不展示后台配置、RAG 技术状态、原始 JSON 或历史线索。

快捷问题：

```text
深度保洁多少钱？
你们服务哪些区域？
维修后保修多久？
帮我预约水管维修
```

### 2.2 商家后台

后台不使用全屏视频和营销式排版，采用适合重复操作的工作台：

- 左侧窄导航。
- 右侧主工作区。
- 清晰的页面标题、筛选器、表格和详情区。
- 重点保证线索查看、知识库维护和系统测试效率。

### 2.3 视觉素材原则

- 不直接依赖参考提示词中的创意机构视频作为正式素材。
- 视频地址通过 `VITE_HERO_VIDEO_URL` 配置。
- 前端必须提供本地 poster 图片 fallback。
- 视频缺失时，客户咨询页仍可正常使用。
- 正式素材应为自有或授权的家政、维修、清洁服务视觉内容。

## 3. 目录结构

状态：未开始

建议新增：

```text
backend/
  __init__.py
  api.py

frontend/
  package.json
  vite.config.ts
  tsconfig.json
  tailwind.config.js
  postcss.config.js
  index.html
  public/
    images/
      home-service-poster.jpg
  src/
    main.tsx
    App.tsx
    index.css
    api/
      client.ts
    types/
      api.ts
    components/
      layout/
        AdminShell.tsx
      chat/
        ChatComposer.tsx
        ChatMessageList.tsx
        QuickPrompts.tsx
    pages/
      CustomerChatPage.tsx
      LeadsBoardPage.tsx
      KnowledgeBasePage.tsx
      BusinessProfilePage.tsx
      SystemTestPage.tsx
```

保留：

```text
app.py
graph.py
rag.py
storage.py
schemas.py
knowledge/
data/
smoke_test.py
rag_smoke_test.py
```

## 4. 前后端接口契约

状态：未开始

所有进程必须优先遵守以下接口，不随意改字段名。

### 4.1 健康检查

```http
GET /api/health
```

响应：

```json
{
  "status": "ok"
}
```

### 4.2 AI 对话

```http
POST /api/chat
```

请求：

```json
{
  "message": "我家厨房水管漏水，明天上午能来修吗？",
  "current_lead": {},
  "chat_history": []
}
```

响应：

```json
{
  "assistant_reply": "可以的，我先帮您登记水管维修……",
  "lead": {},
  "missing_fields": ["address", "phone"],
  "quote": "",
  "handoff_required": false,
  "retrieved_context": "",
  "retrieved_sources": []
}
```

要求：

- 后端内部调用现有 `run_frontdesk_turn(...)`。
- `business_profile` 默认从 `data/business.json` 读取。
- 有线索时自动保存或更新。

### 4.3 线索

```http
GET /api/leads
DELETE /api/leads
```

响应：

```json
{
  "items": []
}
```

### 4.4 商家资料

```http
GET /api/business-profile
PUT /api/business-profile
```

### 4.5 知识库

```http
GET  /api/knowledge/status
POST /api/knowledge/rebuild
GET  /api/knowledge/files
GET  /api/knowledge/files/{filename}
POST /api/knowledge/search
```

检索请求：

```json
{
  "query": "深度保洁多少钱？",
  "top_k": 4
}
```

检索响应：

```json
{
  "items": [
    {
      "source": "knowledge/faq.md",
      "title": "安心到家服务 FAQ",
      "content": "……",
      "score": 1.2
    }
  ]
}
```

## 5. 四进程并行编排

状态：未开始

说明：

- 每个进程只编辑自己负责的文件。
- 不允许多个进程同时重写同一文件。
- 进程 2、3 可以先使用 mock 数据，待进程 1 和进程 4 完成后再由主控联调。

### 5.1 子进程 1：前端基础设施与应用壳

状态：未开始

文件所有权：

```text
frontend/package.json
frontend/vite.config.ts
frontend/tsconfig.json
frontend/tailwind.config.js
frontend/postcss.config.js
frontend/index.html
frontend/src/main.tsx
frontend/src/App.tsx
frontend/src/index.css
frontend/src/api/client.ts
frontend/src/types/api.ts
frontend/src/components/layout/AdminShell.tsx
```

任务：

- 创建 Vite + React + TypeScript + Tailwind 项目。
- 安装并使用 `react-router-dom`。
- 安装并使用 `lucide-react`。
- 建立路由：
  - `/chat`
  - `/admin/leads`
  - `/admin/knowledge`
  - `/admin/profile`
  - `/admin/test`
- 建立统一 API client。
- 建立 TypeScript API 类型。
- 建立后台左侧导航 `AdminShell`。
- 设置字体变量、基础颜色、响应式基础样式。

接口要求：

- API base URL 使用：

```text
VITE_API_BASE_URL=http://localhost:8000
```

- 视频 URL 使用：

```text
VITE_HERO_VIDEO_URL=
```

不做：

- 不实现具体页面业务。
- 不修改 Python 文件。
- 不复制参考网站品牌名或文案。

验收：

```bash
cd frontend
npm install
npm run build
```

### 5.2 子进程 2：客户沉浸式咨询页

状态：已完成

文件所有权：

```text
frontend/src/pages/CustomerChatPage.tsx
frontend/src/components/chat/ChatComposer.tsx
frontend/src/components/chat/ChatMessageList.tsx
frontend/src/components/chat/QuickPrompts.tsx
frontend/src/styles/customer-chat.css
frontend/public/images/home-service-poster.jpg
```

任务：

- 实现 `/chat` 客户咨询页。
- 参考 Mainframe 风格，但内容改成“安心到家服务”。
- 使用全屏视频层，读取 `VITE_HERO_VIDEO_URL`。
- 视频无效时使用 poster 图片。
- 实现鼠标横向移动控制视频进度。
- 实现打字机欢迎语。
- 实现快捷问题胶囊按钮。
- 实现聊天输入框、消息列表、发送中状态。
- 调用 `POST /api/chat`。
- 会话期间保留 `current_lead` 和 `chat_history`。
- 人工接管时展示明确但克制的提示。

客户页文案建议：

```text
您好，我是安心到家 AI 服务顾问。
需要保洁、维修，还是想先了解价格？
```

快捷问题：

```text
深度保洁多少钱？
你们服务哪些区域？
维修后保修多久？
帮我预约水管维修
```

不做：

- 不显示 RAG 命中来源。
- 不显示原始 JSON。
- 不显示后台导航。
- 不显示商家配置表单。

验收：

- 打开 `/chat` 首屏即可输入问题。
- 视频缺失时 poster 正常显示。
- 知识问题能得到回答。
- 询盘问题能继续追问。
- 手机和桌面宽度下文本不重叠。

完成记录：

- 已创建 `CustomerChatPage.tsx`、`ChatComposer.tsx`、`ChatMessageList.tsx`、`QuickPrompts.tsx` 和 `customer-chat.css`。
- 已实现全屏视频层，视频地址读取 `VITE_HERO_VIDEO_URL`；视频缺失或加载失败时，页面使用 poster 路径和 CSS 背景兜底。
- 已实现鼠标横向移动控制视频进度、打字机欢迎语、快捷问题、消息列表、发送中状态、错误状态和人工接管提示。
- 已通过 `POST /api/chat` 保留会话期间的 `current_lead` 与 `chat_history`。
- 客户页未展示后台导航、RAG 来源、原始 JSON、商家编辑表单或历史线索。
- 已添加桌面端、平板和手机宽度响应式处理。
- `frontend/public/images/home-service-poster.jpg` 尚缺正式图片资源；当前 CSS fallback 可用，主控后续可补充授权图片。
- 当前前端骨架尚未包含 `package.json`、`App.tsx` 等文件，因此本子进程无法独立执行 `npm run build`。

### 5.3 子进程 3：商家后台页面

状态：未开始

文件所有权：

```text
frontend/src/pages/LeadsBoardPage.tsx
frontend/src/pages/KnowledgeBasePage.tsx
frontend/src/pages/BusinessProfilePage.tsx
frontend/src/pages/SystemTestPage.tsx
frontend/src/styles/admin.css
```

任务：

- 实现 `/admin/leads`：
  - 线索表格
  - 状态筛选
  - 关键字段展示
  - 清空历史线索
- 实现 `/admin/knowledge`：
  - 知识库状态
  - Markdown 文件列表
  - 文件内容预览
  - 重建索引
  - 测试检索
  - 检索命中片段、来源和分数
- 实现 `/admin/profile`：
  - 商家资料读取和编辑
  - 保存配置
- 实现 `/admin/test`：
  - 测试 AI 对话
  - 展示回复、线索、缺失字段、人工接管状态
  - 展示 `retrieved_sources`
  - 展示 `retrieved_context`

设计要求：

- 后台为工作台风格。
- 左侧窄导航由进程 1 提供。
- 表格紧凑、可扫描。
- 不使用客户页全屏视频。
- 不使用夸张大字号。

不做：

- 不修改 API client。
- 不修改 Python 文件。
- 不实现登录。

验收：

- 四个后台页面均能通过导航访问。
- 知识库文档可查看。
- 知识库测试检索可用。
- 商家资料可保存。

### 5.4 子进程 4：FastAPI 后端适配层

状态：未开始

文件所有权：

```text
backend/__init__.py
backend/api.py
backend/api_test.py
requirements.txt
README.md
```

任务：

- 新增 FastAPI 应用。
- 提供第 4 节约定的全部 API。
- 为 Vite 开发服务器配置 CORS：

```text
http://localhost:5173
```

- 复用现有：
  - `graph.run_frontdesk_turn(...)`
  - `storage.load_leads()`
  - `storage.save_lead(...)`
  - `storage.load_business_profile()`
  - `storage.save_business_profile(...)`
  - `rag.retrieve_knowledge(...)`
  - `rag.rebuild_knowledge_index()`
  - `rag.get_knowledge_status()`
- 安全读取 `knowledge/*.md`，禁止目录穿越。
- 编写 API 测试。
- 更新 `requirements.txt`：
  - `fastapi`
  - `uvicorn`
  - `httpx`

启动命令：

```bash
conda activate ai-frontdesk
uvicorn backend.api:app --reload --port 8000
```

验收：

```bash
conda run -n ai-frontdesk python -m py_compile backend/api.py backend/api_test.py
conda run -n ai-frontdesk python backend/api_test.py
```

## 6. 主控联调任务

状态：已完成

四个子进程完成后，主控执行：

1. 检查文件所有权是否冲突。
2. 跑 Python 编译。
3. 跑旧测试：

```bash
conda run -n ai-frontdesk python smoke_test.py
conda run -n ai-frontdesk python rag_smoke_test.py
```

4. 跑 FastAPI 测试：

```bash
conda run -n ai-frontdesk python backend/api_test.py
```

5. 跑前端构建：

```bash
cd frontend
npm install
npm run build
```

6. 启动 FastAPI：

```bash
uvicorn backend.api:app --reload --port 8000
```

7. 启动 Vite：

```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

8. 浏览器验收：
   - `/chat`
   - `/admin/leads`
   - `/admin/knowledge`
   - `/admin/profile`
   - `/admin/test`

9. 在 `/chat` 验证：

```text
你们公司地址在哪？
深度保洁多少钱？
我家厨房水管漏水，明天上午能来修吗？
地址在浦东新区张江花园小区，电话13800138000
刚才维修师傅把我家弄坏了，我要投诉。
```

10. 在 `/admin/knowledge` 验证：

```text
维修后保修多久？
```

11. 更新本文件状态。
12. 更新 `PAGE_STRUCTURE_PLAN.md` 状态。

## 7. 分阶段节奏

### 第一轮：并行开发

状态：已完成

| 进程 | 任务 | 是否可立即开始 |
|---|---|---|
| 子进程 1 | 前端基础设施与应用壳 | 可以 |
| 子进程 2 | 客户沉浸式咨询页 | 可以，按约定接口开发 |
| 子进程 3 | 商家后台页面 | 可以，按约定接口开发 |
| 子进程 4 | FastAPI 后端适配层 | 可以 |

### 第二轮：主控联调

状态：已完成

- 合并接口差异。
- 修复构建错误。
- 验证视觉与响应式。
- 验证 API 和 RAG。

### 第三轮：可选优化

状态：未开始

- 生成或替换自有 hero poster。
- 添加授权视频。
- 优化移动端导航。
- 加入加载状态、空状态和错误状态。

## 8. 本轮完成标准

状态：已完成

- [x] FastAPI 可启动。
- [x] Vite 前端可启动。
- [x] React 前端构建通过。
- [x] `/chat` 客户咨询页独立可用。
- [x] `/chat` 不显示后台配置和 RAG 调试信息。
- [x] 客户页视觉接近参考风格，但内容属于安心到家服务。
- [x] 视频缺失时 poster fallback 正常。
- [x] `/admin/leads` 可查看线索。
- [x] `/admin/knowledge` 可查看 Markdown 和测试检索。
- [x] `/admin/profile` 可编辑商家资料。
- [x] `/admin/test` 可展示完整调试信息。
- [x] 旧 Streamlit 版本仍可运行。
- [x] `smoke_test.py` 通过。
- [x] `rag_smoke_test.py` 通过。
- [x] `backend/api_test.py` 通过。

## 10. 主控联调记录

状态：已完成

- 子进程 1 的前端基础设施未落盘，主控已补齐 `package.json`、Vite 配置、React 入口、路由、API client、TypeScript 类型和后台导航壳。
- 发现 `5173` 已被旧 `mainframe-landing` 项目占用，新前端改用 `http://localhost:5174`。
- FastAPI 使用 `http://localhost:8000`，CORS 同时允许 `5173` 和 `5174`。
- 已生成并接入客户咨询页 poster：`frontend/public/images/home-service-poster.png`。
- 已执行 `npm install` 和 `npm run build`，构建通过。
- 已执行 Python 编译、`smoke_test.py`、`rag_smoke_test.py`、`backend/api_test.py`，全部通过。
- 已通过浏览器从首页逐个点击进入 `/chat`、`/admin/leads`、`/admin/knowledge`、`/admin/profile`、`/admin/test`。
- 已验证客户页快捷问题“深度保洁多少钱？”可返回 `8-15 元/平方米`。
- 已验证知识库检索“维修后保修多久？”可返回命中片段。
- 已验证线索看板加载、商家资料保存和系统测试运行。

## 9. 暂不纳入本轮

- 登录注册。
- 多租户。
- PostgreSQL 或 SQLite 迁移。
- 支付。
- WhatsApp/SMS 接入。
- 在线编辑知识库。
- 上传知识库文件。
- 正式生产部署。
