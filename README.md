# MuseAI 馆方部署版

这是 MuseAI 网页导览与馆方管理后台的精简源码交付包。先创建空白馆方后台，再在网页上传本馆资料、配置导览并开放给游客。馆名、展厅、展品和知识资料不需要通过修改程序代码来设置。

包含 158 个后端应用文件、126 个前端应用文件，以及数据库迁移、页面资源、依赖锁定文件、4 个部署/初始化脚本和可编辑资料模板。没有开发测试、历史报告、绘图脚本、个人实例、账号密钥、虚拟环境或 `node_modules`。本包不包含原生微信小程序客户端。

依赖在安装或容器构建时下载；安装后产生的库文件属于运行环境。交付源码包无需携带这些文件。

## 第一次部署

由技术负责人准备 Python 3.12、uv、Docker Engine/Desktop 和 Docker Compose v2 以上。服务器需要能下载依赖和容器镜像、连接所选模型服务；Elasticsearch 需要满足宿主机的 `vm.max_map_count` 要求。默认部署不包含本地大模型服务。

解压本包，在包含本 README 的目录执行（PowerShell 与 Bash 均可）：

```text
uv sync --frozen --no-dev
uv run --frozen --no-dev python scripts/museum_portal.py create-env --output instances/my-museum --port 8081
```

编辑生成的 `instances/my-museum/app.env`，设置本馆要使用的聊天模型和嵌入模型服务；具体字段见 [模型与部署配置](docs/deployment.md)。保留随机生成的数据库密码、JWT 密钥和实例隔离字段。默认连接宿主机 Ollama，只是配置起点，未安装和运行模型时不能直接完成问答与索引。

然后启动：

```text
uv run --frozen --no-dev python scripts/deploy_museum.py start --portal --instance instances/my-museum --admin-email curator@example.com
```

将邮箱替换为本馆管理员登录标识；终端会要求输入管理员密码，至少 12 位，包含大小写字母、数字、特殊字符。脚本构建镜像、启动 PostgreSQL/Redis/Elasticsearch、迁移数据库、创建空白后台，再启动前后端。看到 `PORTAL_READY` 表示空馆服务就绪。

本机打开 `http://127.0.0.1:8081/admin/import` 并登录。部署在远端时，先配置 HTTPS 反向代理，或使用 SSH 隧道访问：

```text
ssh -L 8081:127.0.0.1:8081 user@server
```

## 馆方配置内容

1. 按 [馆方资料配置](docs/museum-content.md) 编辑 `data/museum_template/`；其中只有占位内容，必须换成馆方确认的真实资料。
2. 校验资料：`uv run --frozen --no-dev python scripts/museum_instance.py validate data/museum_template`。
3. 将模板目录里的文件与 `knowledge/` 等子目录压成 ZIP，确保 ZIP 根目录直接包含 `manifest.json`。
4. 在 `/admin/import` 上传，核对预览后确认导入，等待资料和索引全部完成。
5. 在 `/tour` 检查问卷、路线、展品问答、检索依据和游览报告。

初次资料导入把空实例绑定到本馆。换另一家馆应创建新实例；日常修改使用后台管理页面。

| 后台地址 | 馆方可维护的内容 |
| --- | --- |
| `/admin/museum` | 馆名、简介、Logo、四种导览身份和业务配置 |
| `/admin/halls` | 展厅名称、介绍、顺序、启用状态 |
| `/admin/exhibits` | 展品、所属厅、类别、介绍、图片 |
| `/admin/documents` | 讲解资料、来源、文档内容、索引与检索预览 |
| `/admin/tour-paths` | 路线管理入口，结合馆方配置维护路线 |
| `/admin/prompts` | 模型提示词 |
| `/admin/tts-personas` | 语音角色与试听，需先启用语音服务 |

部分高级业务项仍通过结构化 JSON 编辑，不是所有字段都有单独表单。任意 Word/PDF 不等同于完整资料包；首次导入需要整理好的目录、配置、UTF-8 知识文本及图片关系。

## 代码结构

```text
backend/app/          后端接口、业务服务、领域配置和数据库/AI 适配
backend/alembic/      数据库升级历史，不能删除
frontend/src/         游客页面、馆方后台及交互逻辑
frontend/public/      页面实际使用的图片、字体及字体许可证
scripts/              4 个部署、初始化和资料校验脚本
deploy/standalone/    Docker Compose、后端/前端镜像和 Nginx 配置
docker/elasticsearch/ 中文检索插件镜像定义
data/museum_template/ 馆方可编辑的资料包模板，不会自动导入
docs/                 部署配置与资料配置两份说明
```

阅读入口：后端 `backend/app/main.py` → `api/tour.py` → `application/`；前端 `frontend/src/main.js` → `router/index.js` → `views/TourView.vue` 与 `components/admin/`。

## 停止、重启和查看状态

```text
uv run --frozen --no-dev python scripts/deploy_museum.py status --portal --instance instances/my-museum
uv run --frozen --no-dev python scripts/deploy_museum.py logs --portal --instance instances/my-museum
uv run --frozen --no-dev python scripts/deploy_museum.py stop --portal --instance instances/my-museum
```

重启使用前面的 `start` 命令。当前脚本仍会询问密码，但已有账号不会被重置。停止容器保留数据；不要删除持久化数据卷。生产域名、HTTPS、模型额度和数据库/图片备份需要由部署负责人配置。

本交付包经过文件依赖、配置生成、资料模板、前端构建和后端加载验证；具体结果见 `docs/validation.json`。这不代替目标服务器的模型连通、HTTPS 和负载验收。
