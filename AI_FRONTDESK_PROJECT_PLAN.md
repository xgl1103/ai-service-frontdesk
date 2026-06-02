# AI Service Frontdesk 项目规划

## 1. 项目目标

状态：未完成

在不超过 90 分钟的首版开发时间内，完成一个可运行、可演示的 AI 本地服务商询盘报价助手 MVP。

一句话定位：

> 给本地服务商用的 AI 前台，自动接待客户询价、追问关键信息、生成报价草稿，并把线索保存到看板里。

首版目标不是完整 SaaS，而是验证核心业务闭环：

1. 商家配置基础服务信息。
2. 客户发起咨询。
3. AI 根据商家资料自动追问缺失信息。
4. AI 抽取线索字段。
5. 信息足够时生成报价草稿。
6. 保存线索并展示在看板中。

## 2. 开发时间约束

状态：未完成

总开发时长：不超过 90 分钟。

时间分配建议：

| 时间 | 模块 | 目标 |
|---:|---|---|
| 0-10 分钟 | 环境与项目骨架 | 创建 conda 环境、安装依赖、生成文件结构 |
| 10-20 分钟 | Streamlit UI 骨架 | 页面布局、侧边栏、聊天区、线索区 |
| 20-35 分钟 | 商家配置模块 | 表单、默认配置、本地保存 |
| 35-55 分钟 | LangGraph 对话流程 | 状态定义、节点、路由、LLM 调用 |
| 55-70 分钟 | 线索抽取与报价 | 结构化抽取、缺失字段判断、报价草稿 |
| 70-80 分钟 | 线索看板 | 保存、读取、状态展示 |
| 80-90 分钟 | 联调与验收 | 跑通 demo、修复明显问题 |

## 3. 技术栈

状态：未完成

### 3.1 运行环境

- Conda
- Python 3.11

环境名：

```bash
ai-frontdesk
```

创建命令：

```bash
conda create -n ai-frontdesk python=3.11 -y
conda activate ai-frontdesk
```

### 3.2 Python 依赖

首版依赖：

```bash
pip install -U streamlit langgraph langchain langchain-openai pydantic python-dotenv
```

建议生成 `requirements.txt`：

```text
streamlit
langgraph
langchain
langchain-openai
pydantic
python-dotenv
```

### 3.3 前端

- Streamlit

选择原因：

- 90 分钟内最快做出完整交互界面。
- 能同时承载配置表单、聊天窗口、线索看板。
- 不需要额外拆前后端服务。

### 3.4 AI 编排

- LangGraph：负责对话状态、节点流程、条件路由。
- LangChain：负责 LLM 接入、Prompt、结构化输出。
- OpenAI：首版推荐 `gpt-4.1-mini` 或同级低成本模型。

### 3.5 数据存储

首版使用本地 JSON：

- `data/business.json`：保存商家配置。
- `data/leads.json`：保存客户线索。

暂不使用数据库，避免 90 分钟内增加复杂度。后续可升级为 SQLite、PostgreSQL 或 Supabase。

## 4. 环境变量

状态：已完成

`.env` 示例：

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

要求：

- 如果配置了 `OPENAI_API_KEY`，使用真实 LLM。
- 如果未配置，首版可以提供规则 fallback，保证 demo 不完全阻塞。

## 5. 项目目录结构

状态：已完成

建议结构：

```text
ai-frontdesk/
  app.py
  graph.py
  prompts.py
  schemas.py
  storage.py
  requirements.txt
  .env.example
  data/
    business.json
    leads.json
  AI_FRONTDESK_PROJECT_PLAN.md
```

文件职责：

| 文件 | 职责 | 可并行开发 |
|---|---|---|
| `app.py` | Streamlit 页面入口、UI 交互、调用图流程 | 是 |
| `graph.py` | LangGraph 状态图、节点、路由逻辑 | 是 |
| `prompts.py` | 系统提示词、抽取提示词、报价提示词 | 是 |
| `schemas.py` | Pydantic 数据结构 | 是 |
| `storage.py` | 本地 JSON 读写 | 是 |
| `.env.example` | 环境变量示例 | 是 |
| `requirements.txt` | Python 依赖 | 是 |

## 6. 可并行开发任务拆分

说明：

- 每个模块都有独立目标、输入输出和验收标准。
- 后续开发时，每完成一个模块，需要把对应状态从“未完成”更新为“已完成”。
- 如果模块只完成部分能力，标注为“进行中”并写明剩余事项。

### 6.1 模块 A：项目初始化与环境

状态：已完成

负责人建议：进程 1

目标：

- 创建项目文件结构。
- 创建 Conda 环境说明。
- 添加依赖文件。
- 添加 `.env.example`。

交付物：

- `requirements.txt`
- `.env.example`
- `data/` 目录
- 初始空数据文件

验收标准：

- 可以通过 `pip install -r requirements.txt` 安装依赖。
- 可以通过 `streamlit run app.py` 启动应用，哪怕页面还是空骨架。

依赖关系：

- 无前置依赖。

完成记录：

- 已创建 `requirements.txt`。
- 已创建 `.env.example`。
- 已创建 `data/` 目录。
- 已创建初始数据文件 `data/business.json` 和 `data/leads.json`。
- 未创建 `app.py` 空骨架，因为本子进程要求不写 UI。

### 6.2 模块 B：数据结构定义

状态：已完成

负责人建议：进程 2

目标：

- 使用 Pydantic 定义商家配置、客户线索、对话状态。

核心结构：

- `BusinessProfile`
- `Lead`
- `QuoteDraft`
- `GraphState`

建议字段：

`BusinessProfile`：

- `business_name`
- `industry`
- `service_area`
- `business_hours`
- `services`
- `pricing_rules`
- `faq`

`Lead`：

- `id`
- `name`
- `phone`
- `address`
- `service_need`
- `preferred_time`
- `urgency`
- `budget`
- `status`
- `summary`
- `quote`
- `created_at`
- `updated_at`

验收标准：

- 所有模型可被正常导入。
- 缺失字段有合理默认值。
- 可以序列化为 JSON。

依赖关系：

- 无前置依赖。

完成记录：

- 已创建 `schemas.py`。
- 已定义 `BusinessProfile`、`Lead`、`QuoteDraft`、`GraphState`。
- 所有模型均提供合理默认值。
- 所有模型均可通过 Pydantic 序列化为 JSON。
- 已放宽 MVP 兼容性：`pricing_rules` 支持 `str | list[str] | dict[str, str]`，`faq` 支持 `str | list[dict]`，`quote` 支持字符串或结构化对象。
- 已统一 `Lead.status` 英文状态值：`new`、`needs_info`、`quoted`、`handoff_required`、`closed`。

### 6.3 模块 C：本地存储

状态：已完成

负责人建议：进程 3

目标：

- 实现本地 JSON 读写。
- 保存商家配置。
- 保存和更新客户线索。

交付物：

- `storage.py`

核心函数：

- `load_business_profile()`
- `save_business_profile(profile)`
- `load_leads()`
- `save_lead(lead)`
- `update_lead(lead_id, patch)`

验收标准：

- 首次运行时自动创建默认数据。
- JSON 文件不存在时不报错。
- 多次保存不会破坏数据结构。

依赖关系：

- 建议依赖模块 B 的数据结构。

完成记录：

- 已创建 `storage.py`。
- 已实现 `load_business_profile()`、`save_business_profile(profile)`、`load_leads()`、`save_lead(lead)`、`update_lead(lead_id, patch)`。
- JSON 文件不存在或为空时会自动创建默认数据。
- 空数据、损坏 JSON 会回退为安全默认值，不阻塞应用启动。
- 支持 Pydantic 模型或普通字典的保存。
- 已对齐 schema：保存商家配置时兼容字符串、列表和字典形式的价格规则；保存线索时兼容字符串或结构化报价。
- `save_lead()` 更新已有线索时不会用空字段覆盖已有非空字段。
- 已将 `data/business.json` 调整为中文家政/维修 demo 数据。

### 6.4 模块 D：Prompt 设计

状态：已完成

负责人建议：进程 4

目标：

- 设计 AI 前台的系统提示词。
- 设计线索抽取提示词。
- 设计报价草稿提示词。
- 设计人工接管判断规则。

交付物：

- `prompts.py`

Prompt 要求：

- AI 不能承诺最终价格。
- AI 必须说明报价为参考，需要人工确认。
- AI 要主动追问缺失字段。
- AI 遇到投诉、危险、医疗/法律等高风险问题时提示人工接管。
- AI 回复要简短、像真实前台，不要长篇解释。

验收标准：

- 给定商家配置和用户输入，可以生成合适回复。
- 可以明确输出需要追问哪些字段。
- 可以生成可读的报价草稿。

依赖关系：

- 可独立开发。

完成记录：

- 已创建 `prompts.py`。
- 已编写 AI 前台系统提示词、线索抽取提示词、报价草稿提示词和回复提示词。
- 已定义人工接管判断规则。
- Prompt 已约束 AI 不能承诺最终价格，报价必须说明需要人工或现场确认。
- Prompt 已要求 AI 主动追问姓名、电话、地址/区域、服务需求、期望时间等缺失字段。

### 6.5 模块 E：LangGraph 对话流程

状态：已完成

负责人建议：进程 5

目标：

- 实现 LangGraph 状态图。
- 将对话拆成多个节点。
- 支持线索抽取、缺失字段判断、回复生成、报价生成、人工接管判断。

交付物：

- `graph.py`

推荐节点：

```text
user_input
  -> intent_node
  -> extract_node
  -> missing_fields_node
  -> reply_node
  -> quote_node
  -> save_node
```

首版可简化为：

```text
extract_node
  -> reply_node
  -> quote_node
```

状态字段：

- `messages`
- `business_profile`
- `lead`
- `missing_fields`
- `quote`
- `handoff_required`
- `assistant_reply`

验收标准：

- 输入一条客户消息后，图流程可以返回 AI 回复。
- 可以持续更新同一条线索。
- 信息足够时可以生成报价草稿。
- 信息不足时优先追问缺失字段。

依赖关系：

- 依赖模块 B。
- 依赖模块 D。
- 可暂时绕开模块 C，先返回内存结果。

完成记录：

- 已创建 `graph.py`。
- 已实现 `run_frontdesk_turn(user_message, business_profile, current_lead=None, chat_history=None)` 对外主函数。
- 已使用 LangGraph 定义 `extract_node`、`missing_fields_node`、`reply_node`、`quote_node` 基础状态图。
- 支持有 `DEEPSEEK_API_KEY` 时通过 `langchain-openai` 的 OpenAI 兼容接口调用 DeepSeek，默认模型为 `deepseek-v4-flash`。
- 保留 `OPENAI_API_KEY` 作为兼容兜底；没有聊天模型 API key 时继续使用内置规则 fallback。
- 支持无 API key 或依赖缺失时使用内置规则 fallback。
- 返回结构包含 `assistant_reply`、`lead`、`missing_fields`、`quote`、`handoff_required`。
- 信息不足时优先追问缺失字段，信息足够时生成参考报价草稿。
- 投诉、危险、法律/医疗等高风险或超范围关键词会触发人工接管。
- 已完成 AI 流程质量修复：增强中文服务关键词、地址抽取、时间抽取、人工接管关键词。
- 已优化规则报价，只引用当前服务相关价格规则，避免把所有价格规则塞进报价草稿。
- 已验证第二轮补充电话和地址时可沿用同一条 `lead` 并生成报价。
- 已新增 `smoke_test.py`，覆盖水管漏水、深度保洁、投诉、补充信息后报价等场景。
- 已集成可选 RAG 流程：新增 `retrieve_node`，状态中加入 `retrieved_context` 和 `retrieved_sources`。
- `run_frontdesk_turn(...)` 保持原接口不变，返回结果新增 `retrieved_context` 和 `retrieved_sources`。
- 回复节点会读取检索上下文；报价节点会优先引用 `pricing.md` 检索结果。
- 无 `rag.py`、RAG 抛错或禁用 RAG 时，原 fallback/LLM 流程照常运行。
- 投诉/危险场景仍优先人工接管，不执行知识检索报价。

### 6.6 模块 F：Streamlit 页面

状态：已完成

负责人建议：进程 6

目标：

- 实现可演示 UI。
- 页面包括商家配置、客户聊天、线索看板。

交付物：

- `app.py`

页面结构：

```text
左侧：商家配置
主区域上方：客户聊天窗口
主区域下方：线索看板
```

功能：

- 编辑商家配置并保存。
- 输入客户消息。
- 显示 AI 回复。
- 展示当前线索信息。
- 展示所有线索列表。

验收标准：

- `streamlit run app.py` 能启动。
- 可以保存配置。
- 可以输入客户消息并得到回复。
- 可以看到线索被保存或更新。

依赖关系：

- 依赖模块 C。
- 依赖模块 E。

完成记录：

- 已创建 `app.py`。
- 页面包含左侧商家配置、主区域客户聊天、当前线索和历史线索看板。
- 已支持保存商家配置、输入客户消息、展示 AI 回复、展示当前线索和历史线索。
- 已预留 `graph.run_frontdesk_turn(...)` 接入；当 `graph.py` 或 `storage.py` 未完成时，使用界面内置 JSON 存储和 mock/fallback 流程。
- 已完成 Streamlit UI 联调：页面可启动，商家配置可保存，客户消息可触发 AI 回复，当前线索和历史线索可展示。
- 已统一状态展示：`new` 显示为“新线索”，`needs_info` 显示为“待补充信息”，`quoted` 显示为“已生成报价”，`handoff_required` 显示为“需人工接管”。
- 已增加“清空当前会话”和“清空历史线索”按钮；清空历史线索只写空 `data/leads.json`，不删除文件。
- 已优化当前线索区域，明确展示服务需求、联系电话、地址、期望时间和报价草稿。
- 已增加 Streamlit RAG UI：知识库展示区域、“重建知识库索引”、“查看知识库状态”和本次命中的知识来源表格。
- 已兼容 `retrieve_knowledge()` 不存在或 RAG 模块不可用的 fallback 状态，页面不会因此报错。
- 已限制知识库入口只读取本地 `knowledge/*.md`，未加入文件上传、登录注册、支付或多商户功能。

### 6.7 模块 G：规则 Fallback

状态：已完成

负责人建议：进程 7

目标：

- 在没有 `OPENAI_API_KEY` 时，仍然可以演示基本流程。

交付物：

- 可放在 `graph.py` 或单独 `fallback.py`。

功能：

- 根据关键词识别服务需求。
- 追问姓名、电话、地址、时间。
- 生成简单报价草稿。

验收标准：

- 未配置 API key 时，应用不崩溃。
- 可以完成最基本的询盘演示。

依赖关系：

- 可独立开发。

完成记录：

- 已在 `graph.py` 内实现规则 fallback。
- 未配置 `OPENAI_API_KEY` 时应用不会因 LLM 不可用而阻塞。
- fallback 支持根据关键词识别服务需求、抽取电话、地址、期望时间、预算和紧急程度。
- fallback 支持追问缺失字段、生成简单报价草稿、识别投诉/危险等人工接管场景。
- 已通过 `conda run -n ai-frontdesk python smoke_test.py` 验证 fallback 主流程。
- 已通过 `smoke_test.py` 验证 RAG 抛错时可安全回落原流程。

### 6.8 模块 H：联调与验收

状态：已完成

负责人建议：主进程

目标：

- 跑通完整 demo。
- 修复首版明显问题。
- 确认 90 分钟内可交付。

验收测试用例：

```text
我家厨房水管漏水，明天上午能来修吗？
```

期望结果：

- AI 识别为维修询价。
- AI 追问地址、联系电话、漏水情况。
- 用户补充信息后生成线索。
- AI 给出参考报价草稿。
- 看板出现一条新线索。

第二条测试用例：

```text
你们周末能做深度保洁吗？大概 90 平。
```

期望结果：

- AI 识别为保洁服务。
- AI 询问地址、期望时间、联系方式。
- AI 根据价格规则生成参考报价。

第三条测试用例：

```text
刚才维修师傅把我家弄坏了，我要投诉。
```

期望结果：

- AI 不继续报价。
- AI 提示需要人工接管。
- 线索标记为需人工处理。

第二轮联调任务记录：

- 子进程 1 已检查 `requirements.txt`，当前覆盖 Streamlit、LangGraph、LangChain、OpenAI 集成、Pydantic 和 dotenv。
- 子进程 1 已检查 `.env.example`，并补充配置说明注释。
- 子进程 1 已确认规划文档内容按 UTF-8 读取正常；若终端出现乱码，应优先检查终端编码，不应改写为非 UTF-8。
- 子进程 1 已新增 `README.md`，包含项目简介、Conda 环境、依赖安装、`.env` 配置、启动命令和 Demo 测试话术。
- 模块 A/B/C/D/E/F/G 当前保持“已完成”。
- 模块 H 已完成主控联调验收。

主控验收记录：

- 已检查 `schemas.py`、`storage.py`、`graph.py`、`app.py` 的接口约定，当前无阻塞性冲突。
- 已执行 `conda run -n ai-frontdesk python -m py_compile schemas.py storage.py prompts.py graph.py app.py smoke_test.py`，编译通过。
- 已执行 `conda run -n ai-frontdesk python smoke_test.py`，测试通过。
- 已启动 Streamlit，并通过浏览器打开 `http://localhost:8501` 完成页面验收。
- 已验证商家配置保存，页面提示“商家配置已保存”。
- 已验证测试用例 1：水管漏水咨询可识别为水管维修，追问地址和电话，补充信息后生成参考报价。
- 已验证测试用例 2：深度保洁咨询可识别为深度保洁，并追问服务地址和联系电话。
- 已验证测试用例 3：投诉场景不会继续报价，会提示人工接管，并将线索状态显示为“需人工接管”。
- 已确认线索写入 `data/leads.json`；刷新后历史看板不显示“暂无历史线索”，数据持久化有效。

## 7. 首版功能清单

### 7.0 基础交付项

- [x] 创建项目依赖文件
- [x] 创建环境变量示例文件
- [x] 创建本地数据目录
- [x] 创建初始数据文件
- [x] 定义 Pydantic 数据模型

### 7.1 必须实现

- [x] 商家配置表单
- [x] 商家配置本地保存
- [x] 客户聊天输入
- [x] AI 自动回复
- [x] AI 追问缺失字段
- [x] 线索结构化抽取
- [x] 报价草稿生成
- [x] 本地保存线索
- [x] 线索看板
- [x] 人工接管提示

### 7.2 可以延后

- [ ] 登录注册
- [ ] 多商户管理
- [ ] 数据库
- [ ] WhatsApp 接入
- [ ] SMS 接入
- [ ] 支付系统
- [ ] 日历同步
- [ ] 部署上线
- [ ] 向量数据库
- [ ] 文件上传知识库

### 7.3 企业知识库资料

- [x] 创建 `knowledge/` 目录
- [x] 编写企业基础资料 `knowledge/company.md`
- [x] 编写服务价格资料 `knowledge/pricing.md`
- [x] 编写员工与师傅资料 `knowledge/staff.md`
- [x] 编写服务与售后政策 `knowledge/service_policy.md`
- [x] 编写常见问题资料 `knowledge/faq.md`
- [x] 明确 AI 禁止承诺最终价格
- [x] 明确最终价格、上门时间和派单需人工确认

### 7.4 RAG 检索功能

- [x] 新增 `rag.py`
- [x] 实现 `retrieve_knowledge(query: str, top_k: int = 4)`
- [x] 实现 `rebuild_knowledge_index()`
- [x] 实现 `get_knowledge_status()`
- [x] 支持无 API key 的关键词 fallback 检索
- [x] 支持可选本地 embedding 和 OpenAI embedding
- [x] 在 `graph.py` 中增加 RAG 检索节点
- [x] 在 `run_frontdesk_turn(...)` 返回 `retrieved_context` 和 `retrieved_sources`
- [x] 在知识类问题中优先基于 RAG 资料回答
- [x] 在 `app.py` 增加知识库状态、重建索引和命中来源展示
- [x] 新增 `rag_smoke_test.py`

## 8. 开发顺序建议

状态：已完成

如果单人开发，推荐顺序：

1. 模块 A：项目初始化与环境
2. 模块 B：数据结构定义
3. 模块 C：本地存储
4. 模块 D：Prompt 设计
5. 模块 E：LangGraph 对话流程
6. 模块 F：Streamlit 页面
7. 模块 G：规则 Fallback
8. 模块 H：联调与验收

如果多进程并行开发，推荐分组：

| 进程 | 模块 | 可并行原因 |
|---|---|---|
| 进程 1 | A 环境与骨架 | 无依赖 |
| 进程 2 | B 数据结构 | 无依赖 |
| 进程 3 | D Prompt 设计 | 无依赖 |
| 进程 4 | C 本地存储 | 只需要约定数据结构 |
| 进程 5 | E LangGraph | 依赖 B/D，可先 mock |
| 进程 6 | F Streamlit UI | 依赖 C/E，可先 mock |
| 进程 7 | G Fallback | 可独立 |
| 主进程 | H 联调验收 | 最后汇总 |

## 9. Demo 验收标准

状态：已完成

完成首版时，需要满足：

- [x] 应用可通过 `streamlit run app.py` 启动。
- [x] 首屏能看到商家配置、聊天区、线索看板。
- [x] 可以保存商家配置。
- [x] 输入客户询价后，AI 能回复并追问。
- [x] 客户补充信息后，线索字段能更新。
- [x] 信息足够后，能生成报价草稿。
- [x] 线索能保存到 `data/leads.json`。
- [x] 刷新页面后，线索仍能展示。
- [x] 没有 API key 时，有基本 fallback 或明确提示。

## 10. 后续版本规划

### V0.1：90 分钟 MVP

状态：已完成

- Streamlit 单页应用。
- 本地 JSON 存储。
- LangGraph 基础流程。
- 商家配置、聊天、线索、报价。

### V0.2：可试用版本

状态：进行中

- SQLite 存储。
- 多条会话管理。
- 线索状态流转。
- 导出 CSV。
- 更稳的结构化输出。
- 接入企业知识库检索，读取 `knowledge/` 下的 Markdown 资料。（已完成）

企业知识库资料准备记录：

- 子进程 1 已新增 `knowledge/company.md`，覆盖公司地址、营业时间、服务区域、服务范围和 AI 回复边界。
- 子进程 1 已新增 `knowledge/pricing.md`，覆盖家政保洁、家电清洗、水电维修、家居安装参考价格。
- 子进程 1 已新增 `knowledge/staff.md`，覆盖客服、保洁师傅、维修师傅姓名、专长和派单限制。
- 子进程 1 已新增 `knowledge/service_policy.md`，覆盖预约、售后、取消改约、投诉和安全合规政策。
- 子进程 1 已新增 `knowledge/faq.md`，使用短问答结构方便后续 RAG 检索。
- 子进程 2 已新增 `rag.py`，实现企业资料读取、chunk 切分、检索函数、索引重建和知识库状态查询。
- `rag.py` 支持三层检索策略：本地 embedding、OpenAI embedding、关键词 fallback；没有 API key 或本地 embedding 依赖时仍可用。
- 已暴露统一接口：`retrieve_knowledge(query: str, top_k: int = 4)`、`rebuild_knowledge_index()`、`get_knowledge_status()`。
- 子进程 3 已在 `graph.py` 集成 RAG：新增检索节点，状态中加入 `retrieved_context` 和 `retrieved_sources`，原 `run_frontdesk_turn(...)` 入参保持兼容。
- 子进程 4 已在 `app.py` 集成 RAG UI：知识库状态展示、重建索引、查看状态、本次命中来源展示。
- 主控已补充 `rag_smoke_test.py`，并修复知识类问题被误当成询盘追问的问题。
- 主控已执行编译、旧 smoke test、新 RAG smoke test，全部通过。
- 主控已验证 RAG 问题：公司地址、王师傅能否修水管、深度保洁价格、维修售后时长。
- 主控已新增 DeepSeek 聊天模型接入：使用 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL` 环境变量，密钥仅从本地 `.env` 读取。
- 主控已新增 `model_config_test.py`，验证 DeepSeek 优先级、OpenAI 兼容兜底和占位符密钥拦截；编译和完整回归测试均通过。

V0.2 剩余未完成：

- SQLite 存储。
- 多条会话管理。
- 线索状态流转。
- 导出 CSV。
- 更稳的结构化输出。

### V0.3：小范围商业验证

状态：未开始

- FastAPI 后端。
- React 前端。
- 多商家账号。
- 短信或 WhatsApp 接入。
- 简单部署。

### V1.0：正式 SaaS

状态：未开始

- 多租户。
- 计费系统。
- 日历预约。
- CRM 集成。
- 商家知识库。
- 监控和日志。

## 11. 开发过程更新规则

状态：已完成

后续开发时必须遵守：

1. 每完成一个模块，将该模块状态改为“已完成”。
2. 如果模块只完成一部分，将状态改为“进行中”，并在模块下写明剩余事项。
3. 每次新增功能，更新“首版功能清单”里的复选框。
4. 每次完成可运行版本，更新“Demo 验收标准”。
5. 如果实际实现偏离本规划，需要在对应模块下记录原因。
6. 不在 90 分钟 MVP 中加入无关复杂功能，除非明确调整范围。
