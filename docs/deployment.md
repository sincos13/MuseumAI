# 模型与部署配置

## 哪些配置放在哪里

| 文件或位置 | 用途 |
| --- | --- |
| `instances/my-museum/app.env` | 数据库、缓存、搜索和模型连接；生成后由部署负责人配置 |
| `instances/my-museum/instance.env` | Compose 项目名、HTTP 端口、绑定地址和数据库密码 |
| 管理后台及资料包 `profile.json` | 馆名、身份、问卷、分类、路线、语音风格等馆方内容 |

实例目录在首次执行 `create-env` 时生成，本交付包不带任何实例凭据。重复生成同一目录会拒绝覆盖；已有实例直接启动。

## 聊天和报告模型

生成配置默认使用 OpenAI-compatible 协议连接宿主机 Ollama，聊天模型示例为 `qwen2.5:7b`。如果使用这一方案，需要自行安装 Ollama 并下载对应模型，确保容器能访问 `http://host.docker.internal:11434`。本包不会自动下载或启动大模型。

也可以接入馆方采购的兼容服务：

| 字段 | 设置方法 |
| --- | --- |
| `LLM_PROVIDER` | 兼容 API 可使用 `openai_compatible` |
| `LLM_COMPAT_MODE` | 按供应商适配；通用接口使用 `openai`，项目也支持 `qwen`、`deepseek` 等模式 |
| `LLM_BASE_URL` | 供应商给出的 API 基础地址 |
| `LLM_API_KEY` | 本馆的服务密钥 |
| `LLM_MODEL` | 兼容兜底模型名称 |
| `LLM_TOUR_MODEL` | 普通导览、问答等使用的模型名称 |
| `LLM_REPORT_MODEL` | 游览报告使用的模型名称 |

三个模型名称可以相同，也可按成本和能力分别设置。正式服务可将 `APP_ENV=production`、`DEBUG=false`；保持生成的长随机 `JWT_SECRET`。

## 嵌入模型

嵌入模型独立于聊天模型，负责将知识资料建立检索索引。必须确认输出维度。

| 方案 | 配置 |
| --- | --- |
| Ollama | `EMBEDDING_PROVIDER=ollama`，设置 `EMBEDDING_OLLAMA_BASE_URL`、`EMBEDDING_OLLAMA_MODEL`、`EMBEDDING_DIMS`；生成配置示例是 `nomic-embed-text` 与 768 维 |
| 兼容 API | `EMBEDDING_PROVIDER=openai`，设置 `EMBEDDING_OPENAI_BASE_URL`、`EMBEDDING_OPENAI_API_KEY`、`EMBEDDING_OPENAI_MODEL`、`EMBEDDING_DIMS` |

首次导入后更换嵌入模型/维度，需要安排索引迁移或重新建立索引；不能只修改数字并继续使用旧向量。模型服务不可用时，服务启动与资料索引也可能处于不同状态，应查看后台索引进度和日志。

## 重排与语音

默认 `RERANK_PROVIDER=mock` 是简化排序，不会调用真实重排服务。若启用供应商重排，配置 `RERANK_PROVIDER`、`RERANK_BASE_URL`、`RERANK_API_KEY`、`RERANK_MODEL`，并验证检索表现。

默认 `TTS_ENABLED=false`，文字导览可正常使用。启用当前语音适配时，设置 `TTS_ENABLED=true`、`TTS_PROVIDER=xiaomi`、供应商提供的 `TTS_BASE_URL`、`TTS_API_KEY`、`TTS_MODEL` 和可用声线 `TTS_DEFAULT_VOICE`；在后台配置身份语音并试听。具体可用字段以 `backend/app/config/settings.py` 为准。

## 网络与隔离

- 每次 `create-env` 生成独立 Compose 项目名、数据库密码、JWT 密钥和搜索索引名；同一馆后续使用同一个实例目录。
- 默认 `MUSEUM_BIND_ADDRESS=127.0.0.1`、HTTP 端口 8081，便于外层反向代理。数据库、缓存和搜索服务不发布宿主机端口。
- 远程游客访问应配置真实域名、HTTPS 和对应的 `CORS_ORIGINS`；前端部分浏览器功能依赖安全上下文。
- Linux Elasticsearch 8 的常见宿主机要求为 `vm.max_map_count` 至少 262144，部署负责人应依据实际镜像启动日志确认。
- 容器通过 `host.docker.internal` 访问宿主机模型。Linux 上需要让模型监听 Docker 能到达的地址，并按需配置防火墙。
- 默认模型示例不代表性能承诺；本地模型所需内存/GPU 和并发容量需要按实际模型规划。

## 数据保存与更新

Compose 为数据库、搜索、Redis、展品图片、导入资料和日志建立持久化卷。备份应至少覆盖 PostgreSQL、展品图片、导入资料和实例配置。保留原馆配置，更新源码后使用同一实例的 `start` 命令重新构建并迁移。

现有脚本不会删除数据卷；不要用 `docker compose down -v` 作为普通停止操作。馆方修改展品事实时也应同步知识文档，避免目录介绍与检索资料不一致。

项目内的 `pyproject.toml` 保留与锁文件对应的可选开发依赖元数据，但交付命令不选择开发 extra；容器使用 `--no-dev --no-install-project`。前端依赖清单只保留页面运行与 Vite 构建依赖。
