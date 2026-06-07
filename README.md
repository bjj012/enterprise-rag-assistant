# 智能文档检索助手

智能文档检索助手是一套面向企业私有知识库场景的 RAG 问答系统，支持用户上传 PDF、Word、TXT、Markdown 文档，自动完成父子粒度切分、向量化存储、文档元数据持久化，并基于所选知识源提供可追溯的文档问答。未选择知识源时，系统会切换为普通对话模式。

项目采用 Streamlit 前端界面、SQLAlchemy ORM、MySQL 持久化、Chroma 向量数据库、通义千问 qwen-plus 和 BAAI/bge-large-zh-v1.5 的全栈架构，完整覆盖企业级私有知识库从文档入库到问答检索的核心链路。

## 核心能力

- 多格式文档入库：支持 PDF、DOCX、TXT、Markdown 文档上传和文本解析。
- 父子文档切分：父块保存完整上下文，子块用于精准向量召回。
- Chroma 双集合：`parent_documents` 保存父级上下文，`child_documents` 保存检索子块。
- 上下文压缩召回：内置确定性压缩器，并保留 LangChain `ContextualCompressionRetriever + LLMChainExtractor` 扩展入口。
- MySQL 持久化：文档元数据、父子 chunk、向量 ID、对话历史完整落库。
- 双模式问答：选择知识源时走 RAG 模式，不选择知识源时走普通对话模式。
- 来源追溯：回答后展示召回的父级上下文片段，方便核对依据。
- 入库去重：同一文件成功入库后再次上传会复用已有文档，失败记录可重新处理。
- 检索调试：返回子块命中数、父块命中数、压缩片段数、向量后端和 Top-K 分数，便于排查召回质量。
- 企业级 UI：Streamlit + 深度定制 CSS，包含渐变主题、聊天气泡、文档卡片、状态标签和响应式布局。
- 工程化配置：dotenv 配置管理、`st.cache_resource` 组件缓存、错误处理、spinner 加载动画和会话状态管理。

## 技术架构

```mermaid
flowchart TD
    A[上传 PDF/Word/TXT/Markdown] --> B[DocumentProcessor]
    B --> C[父子粒度切分]
    C --> D[(MySQL: documents / parent_chunks / child_chunks)]
    C --> E[(Chroma: parent_documents)]
    C --> F[(Chroma: child_documents)]
    G[用户问题] --> H{是否选择知识源}
    H -->|是| I[子块向量召回]
    I --> J[父块上下文补全]
    J --> K[上下文压缩]
    K --> L[通义千问 qwen-plus]
    H -->|否| M[普通对话]
    M --> L
    L --> N[答案 + 来源片段 + 对话历史落库]
```

## 目录结构

```text
04-enterprise-rag-assistant/
  streamlit_app.py                 # Streamlit 应用入口
  app/
    config.py                      # dotenv 配置
    core/
      embeddings.py                # bge/hash 嵌入服务
      ingestion.py                 # 文档入库编排
      rag_system.py                # RAG 与普通对话引擎
      compression.py               # 上下文压缩召回
      llm.py                       # 通义千问 OpenAI 兼容接口
      langchain_adapter.py         # LangChain 压缩检索扩展入口
    database/
      models.py                    # SQLAlchemy ORM 模型
      repository.py                # 数据访问层
    document_processor/
      loader.py                    # PDF/DOCX/TXT 加载
      splitter.py                  # 父子切分策略
      processor.py                 # 文件保存与解析
    vector_store/
      chroma_store.py              # Chroma 双集合封装
    ui/
      styles.py                    # 定制 CSS
      components.py                # UI 组件
  sample_docs/
    enterprise_handbook.txt
  scripts/
    smoke_test.py
```

## 快速启动

建议使用 Python 3.10 或 3.11。

```bash
cd 04-enterprise-rag-assistant
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env
streamlit run streamlit_app.py --server.port 8501
```

访问：

```text
http://127.0.0.1:8501
```

## MySQL 配置

本地验证默认使用 SQLite，方便无外部依赖运行。切换到 MySQL 时，先启动数据库：

```bash
docker compose up -d mysql
```

然后在 `.env` 中配置：

```env
DATABASE_URL=mysql+pymysql://rag_user:rag_password@127.0.0.1:3306/rag_assistant?charset=utf8mb4
```

## 通义千问与嵌入模型

`.env` 中配置通义千问：

```env
DASHSCOPE_API_KEY=你的 DashScope API Key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
```

本地测试默认使用 `EMBEDDING_BACKEND=hash`，不需要下载模型。生产或展示机器资源允许时，建议切换：

```env
EMBEDDING_BACKEND=sentence-transformers
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
```

## 验证流程

项目内置离线冒烟测试，会重建本地 SQLite 和向量数据，导入示例制度文档，然后验证 RAG 问答、普通对话、重复文件去重、检索调试信息和向量统计。若当前机器暂未安装 `chromadb`，测试会自动使用本地 JSON 向量库兜底；生产运行仍推荐安装完整依赖并使用 Chroma。

```bash
pip install -r requirements-dev.txt
python scripts/smoke_test.py
```

完整依赖环境下也可以直接运行：

```bash
python scripts/smoke_test.py
```

通过后会看到：

```text
智能文档检索助手健康检查通过。
```

## 适用场景

- 企业制度、合同、报价单和技术手册问答
- 研发知识库、故障处理手册和复盘文档检索
- 法务、财务、人事等内部规范查询
- 研究文献、课程资料和项目文档智能检索

## 简历写法参考

智能文档检索助手：独立从 0 到 1 开发企业级 RAG 知识库问答系统，基于 Streamlit、SQLAlchemy、MySQL、Chroma、通义千问 qwen-plus 和 bge-large-zh-v1.5 实现 PDF/Word/TXT 文档上传解析、父子粒度切分、双集合向量存储、上下文压缩召回、知识库问答、普通对话、来源追溯和对话历史持久化；前端通过深度定制 CSS 实现类 ChatGPT 的现代化对话体验，可用于企业内部制度、合同、技术手册和研究文献智能检索。
