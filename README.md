# MuseAI 馆方部署、配置与资料包制作指南

适用版本：MuseAI 馆方精简部署版，2026-10-31。

本指南用于把 MuseAI 部署为一家博物馆独立使用的网页导览与管理后台。完成后的流程是：馆方登录后台，导入展厅、展品、知识和导览配置，游客通过网页参观、提问并查看报告。

本指南中的命令，以解压后的 `MuseAI-museum-core` 为项目根目录。文中的 `my-museum`、示例馆名、邮箱和域名都应替换为本馆信息。模型密钥由馆方自行申请或由部署负责人提供。本交付不包含原生微信小程序工程。

## 先明确两类文件

| 文件 | 用途 | 使用位置 |
| --- | --- | --- |
| `MuseAI-museum-core.zip` | 应用源码和部署文件 | 解压到运行 MuseAI 的电脑或服务器 |
| 自己制作的 `my-museum-package.zip` | 本馆展厅、展品、知识、图片和配置 | 部署完成后，在“资料包导入”页面上传 |

后台需要上传的是第二种资料包。不要把整个应用源码压缩包上传到馆藏导入页面。

建议技术负责人完成第 1—3 节；馆方内容负责人和技术负责人共同完成第 4 节；馆方工作人员完成第 5—7 节。需要远程游客访问时，由技术负责人完成第 8 节。

## 1. 准备运行环境

### 1.1 准备工具与服务

| 项目 | 要求 |
| --- | --- |
| 运行设备 | 可运行 Linux 容器的服务器或电脑；Windows 使用 Docker Desktop 的 Linux 容器模式 |
| Docker | Docker Engine 或 Docker Desktop，并具备 Docker Compose v2 或更高版本 |
| uv | 用于安装 Python、应用依赖和运行部署命令 |
| 聊天模型 | 一个可访问的 OpenAI-compatible 服务，或自行运行的 Ollama |
| 嵌入模型 | 用于知识检索向量化；需要确认模型名称、服务地址和实际输出维度 |
| 网络 | 能下载 Python/npm 依赖、Docker 镜像与 Elasticsearch 中文分词插件，并能访问所选模型服务 |

安装入口：[Docker Engine](https://docs.docker.com/engine/install/)、[Docker Desktop](https://docs.docker.com/desktop/)、[uv](https://docs.astral.sh/uv/getting-started/installation/)。Windows 安装完成后先打开 Docker Desktop，等待引擎启动；Linux 确认当前账号能够使用 Docker。

PostgreSQL、Redis、Elasticsearch、网页服务和后端由 Compose 启动，无需另行安装。Node.js 在前端镜像构建时提供，宿主机无需单独安装。聊天与嵌入模型服务需要另外准备。

使用云端模型时，可将 4 核 CPU、8 GB 内存作为小规模试运行的资源预算起点；这不是已验证的并发承诺。若在本机运行大模型，还要另行规划模型所需的内存、磁盘和 GPU。

### 1.2 解压并确认目录

解压后，进入同时包含 `pyproject.toml`、`backend/`、`frontend/`、`scripts/` 的目录。例如：

```text
cd MuseAI-museum-core
```

后续命令除特别说明外，都在这里执行。Windows 使用 PowerShell，Linux 使用 Bash。

先检查工具：

```text
uv --version
docker --version
docker compose version
docker info
```

`docker info` 应能显示服务端信息。若提示连接不到 Docker 引擎，先启动或修复 Docker，再继续。

安装 Python 和应用依赖：

```text
uv python install 3.12
uv sync --frozen --no-dev --python 3.12
```

这一步会在本机生成 `.venv/`。这些运行库由工具安装，无需馆方手工整理或随源码复制。

Linux 服务器还应检查 Elasticsearch 所需参数：

```bash
sysctl vm.max_map_count
```

如果结果低于 262144，由服务器管理员执行以下命令并确认生效；已有更高数值时保留现有配置：

```bash
printf 'vm.max_map_count=262144\n' | sudo tee /etc/sysctl.d/99-museai.conf
sudo sysctl --system
```

Windows Docker Desktop 的 Linux 内核参数应在其实际运行环境中处理；若 Elasticsearch 报此项错误，请交给部署负责人按 Docker Desktop 环境设置。

## 2. 创建本馆实例并配置模型

### 2.1 创建空白实例

```text
uv run --frozen --no-dev python scripts/museum_portal.py create-env --output instances/my-museum --port 8081
```

成功后生成：

```text
instances/my-museum/
├── app.env       应用、数据库、检索和模型配置
└── instance.env  Compose 项目名、端口和数据库密码
```

这一步生成随机凭据和隔离配置，不会导入任何馆藏。相同目录再次执行会拒绝覆盖；已有实例直接使用原目录启动。另一家馆应使用新的目录和未占用的端口。

这里的 `my-museum` 是本机实例目录名；资料包里的 `museum_id` 是馆身份。二者可以同名，但用途不同。

### 2.2 编辑配置文件

Windows 可执行：

```powershell
notepad instances/my-museum/app.env
```

Linux 可执行：

```bash
nano instances/my-museum/app.env
```

保留系统生成的 `DATABASE_URL`、数据库密码、`REDIS_URL`、`ELASTICSEARCH_URL`、`ELASTICSEARCH_INDEX` 和 `JWT_SECRET`，并保持：

```dotenv
MUSEUM_SELF_SERVICE_IMPORT=true
EXPECTED_MUSEUM_ID=
DEBUG=false
```

这表示先启动空白后台，随后由首次资料包导入绑定实际馆身份。

### 2.3 选择模型接入方式

聊天模型负责回答与报告；嵌入模型负责知识向量化。两者都要配置，不能只填写聊天模型密钥。

**方式 A：馆方采购的兼容 API 服务。** 在 `app.env` 中修改或补充以下字段。所有 `REPLACE_WITH_...` 都必须替换为供应商提供的实际值；维度填写整数。修改已有字段时替换原行，避免同名字段重复。

```dotenv
LLM_PROVIDER=openai_compatible
LLM_COMPAT_MODE=openai
LLM_BASE_URL=REPLACE_WITH_CHAT_BASE_URL
LLM_API_KEY=REPLACE_WITH_CHAT_API_KEY
LLM_MODEL=REPLACE_WITH_CHAT_MODEL
LLM_TOUR_MODEL=REPLACE_WITH_TOUR_MODEL
LLM_REPORT_MODEL=REPLACE_WITH_REPORT_MODEL

EMBEDDING_PROVIDER=openai
EMBEDDING_OPENAI_BASE_URL=REPLACE_WITH_EMBEDDING_BASE_URL
EMBEDDING_OPENAI_API_KEY=REPLACE_WITH_EMBEDDING_API_KEY
EMBEDDING_OPENAI_MODEL=REPLACE_WITH_EMBEDDING_MODEL
EMBEDDING_DIMS=REPLACE_WITH_INTEGER_DIMENSIONS

RERANK_PROVIDER=mock
TTS_ENABLED=false
```

填写要点：

- `LLM_BASE_URL` 是供应商给出的 API 基础地址，常见形式以 `/v1` 结尾；不要擅自附加 `/chat/completions`。
- 三个聊天模型名称可以相同，也可以分别选择普通导览和报告模型。
- 如果供应商需要 Qwen、DeepSeek 等特定兼容模式，由技术负责人按实际服务调整 `LLM_COMPAT_MODE`。
- 嵌入维度必须与嵌入模型实际输出一致，不能按聊天模型名称推测。导入后更换嵌入模型或维度，需要安排索引迁移/重建。
- `RERANK_PROVIDER=mock` 使用简化排序；`TTS_ENABLED=false` 暂时关闭语音。可先验收文字导览，再接入真实重排和语音服务。

**方式 B：自行运行 Ollama。** 生成的配置默认采用此方式，聊天模型为 `qwen2.5:7b`，嵌入模型为 `nomic-embed-text`、768 维。宿主机安装并运行 Ollama 后执行：

```text
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
ollama list
```

确认 `app.env` 中使用：

```dotenv
LLM_PROVIDER=openai_compatible
LLM_COMPAT_MODE=openai
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_API_KEY=ollama-local
LLM_MODEL=qwen2.5:7b
LLM_TOUR_MODEL=qwen2.5:7b
LLM_REPORT_MODEL=qwen2.5:7b
EMBEDDING_PROVIDER=ollama
EMBEDDING_OLLAMA_BASE_URL=http://host.docker.internal:11434
EMBEDDING_OLLAMA_MODEL=nomic-embed-text
EMBEDDING_DIMS=768
```

`ollama-local` 是本地服务的兼容占位值，不是云端服务密钥。容器必须能连接宿主机的 11434 端口；Linux 上通常需要为 Ollama 设置可被 Docker 网络访问的监听地址，并按需配置防火墙。`ollama list` 成功只说明宿主机有模型，容器连通情况仍需部署时确认。

两种方式配置完毕后保存文件。模型密钥留在实例配置中，不放入馆藏资料包、知识文本或馆方公开文件。

## 3. 启动空白后台

在项目根目录执行，将邮箱替换为本馆管理员登录标识：

```text
uv run --frozen --no-dev python scripts/deploy_museum.py start --portal --instance instances/my-museum --admin-email curator@example.com
```

按终端提示输入管理员密码：至少 12 个字符，包含大写、小写、数字和特殊字符。输入时不显示字符是正常现象。

脚本依次构建镜像、启动数据库/缓存/搜索、执行数据库迁移、创建空白管理员后台，再启动前后端。首次运行需要下载依赖与镜像。成功时出现：

```text
PORTAL_READY: log in at /admin/import and upload your ZIP package
```

在部署机器的浏览器打开 [本机资料包导入页面](http://127.0.0.1:8081/admin/import)。如果先进入首页，先用刚设置的管理员邮箱和密码登录，再访问 `/admin/import`。

如果部署在远端服务器，可先在自己电脑的终端建立隧道，并保持此终端开启：

```text
ssh -L 8081:127.0.0.1:8081 user@server
```

将 `user@server` 替换为服务器账号和地址，再在自己电脑打开 `http://127.0.0.1:8081/admin/import`。默认端口只绑定服务器本机，其他电脑直接访问服务器 IP 的 8081 端口不会自动生效；正式公网访问见第 8 节。

**本步骤完成的标志：** 管理员能登录“资料包导入”页面，实例等待导入本馆资料。此时没有馆藏、游客暂不能开始完整导览是正常状态。

## 4. 准备本馆资料包

### 4.1 馆方先准备什么

| 资料 | 至少需要的内容 | 谁确认 |
| --- | --- | --- |
| 馆基本信息 | 正式名称、简称、简介，Logo 可选 | 馆方负责人 |
| 展厅目录 | 名称、介绍、顺序、楼层、开放情况、建议停留时间 | 展陈负责人 |
| 展品目录 | 稳定编号、名称、所属厅、分类、简介、年代 | 藏品或展陈负责人 |
| 知识资料 | 展签、讲解稿、研究说明、参观须知，保留出处和版本 | 内容审核人员 |
| 图片 | 对应展品编号的图片与使用说明 | 图片或内容负责人 |
| 导览设计 | 受众、导览身份、兴趣选项、路线、希望引导的问题 | 教育或策展人员 |

现成 Word、扫描 PDF 和图片可以作为整理原料。当前首次导入要求整理成下列结构，不会从一份 Word 中自动推断所有展厅、路线和图片关系。

### 4.2 复制可编辑模板

包内 `data/museum_template/` 已含完整配置骨架、1 个占位展厅、1 件占位展品、1 份占位知识文本。先复制，保留原模板用于对照；目标目录不存在时执行。

Windows PowerShell：

```powershell
Copy-Item -LiteralPath data/museum_template -Destination data/my-museum -Recurse
```

Linux：

```bash
cp -R data/museum_template data/my-museum
```

编辑后的目录应是：

```text
data/my-museum/
├── manifest.json
├── profile.json
├── halls.csv
├── exhibits.csv
├── knowledge/
│   └── exhibit-001.txt
└── images/                 可选，有图片时再创建
    └── E001.jpg
```

JSON 和知识文本使用 UTF-8 编码。CSV 可以用 Excel 编辑，保存时选择“CSV UTF-8（逗号分隔）”，保留英文列名；有前导零的编号按文本处理。

### 4.3 填写 `profile.json`：馆名与导览配置

在模板已有结构上编辑，不删除其他分区，也不要把整个文件替换成只包含馆名的 JSON。

| 字段路径 | 填写方法 |
| --- | --- |
| `schema_version` | 保持 `1` |
| `revision` | 首次资料包保持模板的 `0` |
| `museum.museum_id` | 本馆稳定 ID，例如 `my-museum`；小写字母/数字开头，可含连字符和下划线 |
| `museum.name`、`short_name` | 正式名称、页面使用的简称 |
| `museum.description` | 馆方审核后的简介，替换占位文字 |
| `museum.logo_url` | 可留空；填写可访问的 HTTP(S) 地址或本站已有资源路径，不填写电脑上的文件路径 |
| `museum.language`、`timezone` | 中文馆可保留 `zh-CN`、`Asia/Shanghai` |
| `museum.personas` | 保留 A/B/C/D 四种身份的编号；修改名称、介绍、开场白、报告标题和讲解风格 |
| `museum.business.categories` | 分类编号和显示名称；展品 CSV 的 `category` 必须使用其中的编号 |
| `museum.business.routes` | 保留 `A`、`B`、`C`、`D`、`default` 五条规则；维护主题、介绍、问题和优先展厅 |
| `museum.business.route_durations` | 参观分钟上限与推荐站数；分钟上限须递增且不重复 |
| `museum.business.questionnaire` | 调整关注方向、兴趣线索及文案；相关选项保留各自 A/B/C/D 编号 |

每条路线的 `preferred_halls` 填展厅编码，例如 `["main-hall"]`。如果把模板展厅编码改为 `history-hall`，必须同步修改五条路线和知识清单中的关联。路线表示推荐顺序和观察任务，不是室内定位导航。

身份文案可沿用模板中的 `{museum_name}`、`{persona_name}` 等占位符。问卷选项的编号和身份编号属于不同配置，不要仅因字母相同就推断二者的推荐关系。

初次上线可保留模板的 `rhythms`、`dialogue`、`reflection`、`suggestions`、`tts` 结构，逐项审阅文案是否适合本馆；已有字段不能整体删除。模板部分分类和话题面向历史/考古馆，其他类型馆应一并调整。

`visitor_experience` 是可选的精细展品卡片与预算路线配置，最小模板保持 `null` 即可使用基础导览。需要精确指定各身份、各时长的展品组合时再由技术人员扩展；扩展后的时间预算和展厅/展品引用须通过校验。

### 4.4 填写 `halls.csv`：展厅

每行一个展厅，保留模板列名。

| 列 | 填写说明 |
| --- | --- |
| `source_record_id` | 稳定展厅记录编号，例如 `H001`，不要重复 |
| `slug` | 稳定展厅编码，例如 `main-hall`；使用小写英文、数字和连字符 |
| `name` | 游客看到的展厅名称 |
| `description` | 经审核的展厅介绍 |
| `short_description` | 卡片上的简短介绍，最多 48 字 |
| `floor` | 楼层，沿用模板整数格式 |
| `estimated_duration_minutes` | 建议停留分钟数 |
| `display_order` | 排序，使用整数 |
| `is_active` | 开放填 `true`，关闭填 `false`；首次包至少有一个开放展厅 |
| `is_temporary` | 临展填 `true`，常设厅填 `false` |
| `aliases` | 别名的 JSON 数组，无别名保留 `[]` |
| `suggested_questions` | 初次可以留空，由程序生成；不要填字面值 `[]` |

`slug` 用于关联展品、知识和路线。调整展示名称时，通常保留原编码。

### 4.5 填写 `exhibits.csv`：展品

每行一件展品；默认占位条目需要替换或移除。

| 列 | 填写说明 |
| --- | --- |
| `source_record_id` | 稳定展品编号，例如 `E001`；图片和精细导览通过此编号对应 |
| `name` | 正式展品名称 |
| `description` | 经审核的简介；更完整的讲解放入知识文档 |
| `hall` | 所属展厅的 `slug`，例如 `main-hall`，不是中文厅名 |
| `category` | 配置中的分类编号，例如模板已有的 `pottery` |
| `era` | 已确认年代；资料不明时明确标注未知 |
| `floor` | 展品所在楼层 |
| `importance` | 重要度，沿用模板的 1—5 数值范围 |
| `estimated_visit_time` | 建议观看分钟数 |
| `display_order` | 排序整数 |
| `is_active` | 启用填 `true`，停用填 `false` |
| `suggested_questions` | 初次可留空，程序自动生成 |
| `image_url` | 可留空；使用外部图片时填写可访问的 HTTPS 地址 |
| `location_x`、`location_y` | 没有经确认的位置数据时留空；填写坐标不会自动生成导航能力 |

若要新增“金属器”等分类，先在 `profile.json` 的 `business.categories` 中定义编号和名称，再让展品使用这个编号；不要只在 CSV 中写一个模板里没有的分类。

### 4.6 整理 `knowledge/`：AI 回答依据

每份文件使用 UTF-8 的 `.txt`、`.md` 或 `.markdown`。展品专属文档建议一件一份，保留名称、编号、可确认事实、出处、研究解释和未知事项；全馆参观须知可单独建文件。

下面是供内容人员填写的文本结构。实际导入前替换所有方括号内容，不要把示例当作真实馆藏事实：

```text
展品名称：[与 exhibits.csv 完全一致]
展品编号：E001
所属展厅：[本馆展厅名称]

可确认事实
[年代、材质、尺寸、外观、用途，以及证据来源]

讲解与研究说明
[馆方审核后的解释；有争议的解释应注明]

目前未知
[未提供或未确定的信息，不为补齐文本而推测]

来源与版本
[展签、讲解稿或研究资料的名称、版本、页码/链接及审核日期]
```

仅修改展品简介不会自动替换知识文档。事实变更时，两处都需要同步。

### 4.7 填写 `manifest.json`：关联知识和图片

`museum_id` 必须与 `profile.json` 相同。每份知识文件都要登记，文件路径相对于资料包根目录。下面示例可用于一个展厅、一件展品、一份知识文件的包；名称和来源需改成本馆内容。

```json
{
  "schema_version": 1,
  "museum_id": "my-museum",
  "knowledge": [
    {
      "id": "exhibit-001",
      "file": "knowledge/exhibit-001.txt",
      "title": "请填写与展品目录完全一致的名称",
      "source_label": "请填写馆方审核资料名称与版本",
      "source_url": "",
      "hall_slug": "main-hall"
    }
  ],
  "images": []
}
```

`knowledge.id` 不重复；展品专属文档的 `title` 与展品名称一致，`hall_slug` 与展品所属厅一致。全馆资料可将 `hall_slug` 填为 `null`。避免在同一厅为同一展品留下多个同名、互相矛盾的文档。

有图片时，在资料包里创建 `images/`，例如放入 `images/E001.jpg`，并把清单中的 `images` 改为：

```json
[
  { "source_record_id": "E001", "file": "images/E001.jpg" }
]
```

这是 `images` 字段的值，不是完整的 `manifest.json`。清单中的文件必须真实存在；无图时保留空数组。首次资料包图片支持 JPEG、PNG、WebP，单张最多 10 MB、2000 万像素。后台日后单独上传图片的默认上限是 5 MiB、4000 万像素，以页面提示和部署配置为准。

### 4.8 离线校验

在项目根目录执行：

```text
uv run --frozen --no-dev python scripts/museum_instance.py validate data/my-museum
```

成功输出含 `"status": "validated"`，并列出馆 ID 和内容数量。失败时根据提示修正 JSON、字段或关联后重试。这一步不连接业务数据库或模型；结构通过后仍需馆方确认事实正确、占位内容已替换。

### 4.9 压缩为可上传 ZIP

以下命令在 Windows PowerShell 和 Linux Bash 中均可执行，先从项目根目录进入资料目录：

```text
cd data/my-museum
uv run --frozen --no-dev python -m zipfile -c ../../my-museum-package.zip manifest.json profile.json halls.csv exhibits.csv knowledge
cd ../..
```

如果确实创建了 `images/` 并在清单中登记了图片，则使用下面这一组命令，把图片目录也放进去：

```text
cd data/my-museum
uv run --frozen --no-dev python -m zipfile -c ../../my-museum-package.zip manifest.json profile.json halls.csv exhibits.csv knowledge images
cd ../..
```

两组选择一组即可；再次执行会重新生成同名资料 ZIP。查看压缩内容：

```text
uv run --frozen --no-dev python -m zipfile -l my-museum-package.zip
```

应直接看到 `manifest.json`、`profile.json`、`halls.csv`、`exhibits.csv` 和 `knowledge/...`，而不是 `my-museum/manifest.json`。上传 ZIP 上限 100 MB，解压内容合计上限 250 MB。

## 5. 网页上传并完成首次导入

1. 用管理员账号进入 `/admin/import`，点击“选择资料包 ZIP”，选择自己生成的 `my-museum-package.zip`。
2. 核对预览中的馆名、展厅数、展品数、知识文档数、图片数；展开目录和来源，确认没有占位条目或其他馆资料。
3. 点击“确认导入本馆”。预览阶段不写入馆藏；确认后才开始写入内容、图片和知识索引。
4. 等待页面提示导入完成，并确认知识文档完成数等于总数。页码或等待时间不能代替索引完成状态。
5. 点击“进入游客导览”，或打开 `/tour`。

如果导入失败，先检查错误原因；模型或搜索服务恢复后，使用“重试未完成的导入”。服务中途重启时，可使用“服务重启后继续导入”。保留原资料包继续同一次导入，不要在任务进行中修改文件再上传替代包。

首次导入将空实例绑定到本馆。后续日常更新使用后台各管理页面；如果要换一家馆，创建新实例。

## 6. 在后台维护本馆配置

### 6.1 常用入口

以下路径都加在本馆网站地址后。例如网站是 `https://guide.example.org`，馆方配置页就是 `https://guide.example.org/admin/museum`。

| 页面 | 可维护内容 |
| --- | --- |
| `/admin/museum` | 馆名、简介、Logo、四种导览身份、问卷、分类、身份路线、报告主题和语音风格 |
| `/admin/halls` | 展厅名称、别名、介绍、顺序、临展和开放状态 |
| `/admin/exhibits` | 展品、所属展厅、分类、简介、年代、图片和启用状态 |
| `/admin/documents` | 知识文档上传、正文和来源编辑、索引状态、重建索引、检索预览 |
| `/admin/tour-paths` | 路线管理入口；馆方身份路线在馆方配置中统一维护 |
| `/admin/prompts` | 提示词管理，适合由熟悉讲解规则的人员维护 |
| `/admin/tts-personas` | 语音角色与试听；需技术负责人先启用语音服务 |

高级设置中仍有部分 JSON 编辑区域。初次使用可先维护普通表单，对高级规则的调整应保留完整结构并经过验收。

### 6.2 正确保存、导入与发布

在“馆方配置”页面，先点击“导出已发布配置”留存当前版本，再修改需要的内容。点击“保存并发布”，看到成功提示后，用一个新的游客导览验证效果。

页面上的“选择 JSON 导入”用于读入馆方配置文件；它只把内容填进表单，还需要点击“导入并发布”。它不负责导入展厅 CSV、知识文档和图片。

新导览使用发布后的配置；已有导览保留创建时的问卷、身份、路线和报告规则，展厅开放状态仍实时更新。验收新身份或路线时，应新建导览，不要只刷新旧会话。

若提示配置已被其他管理员更新，先“导出当前草稿”，再“重新加载最新配置”，合并修改后保存。不要通过反复点击发布覆盖别人的更新。

“导出已发布配置”只保存馆方配置，不包含完整数据库、展品图片和全部知识文件；整馆备份由技术负责人维护。

### 6.3 更新知识、展厅和图片

- 知识库支持 UTF-8 TXT/Markdown，单文件最大 50 MB；扫描件、Word 或 PDF 先整理成可核对的文字。上传并完成索引后即可参与问答，无需另找发布按钮。
- 编辑知识文档后确认索引状态，必要时重建；在“检索预览”输入一个有已知答案的问题，核对命中文本和来源。
- 修改展品名称或归属时，同步检查对应知识文档的标题和展厅关系；修改历史事实时同步简介与知识正文。
- 临时关闭展厅优先调整“开放”状态，并检查路线效果。新增展厅后需要补充展品和知识，不能仅增加名称就期待完整讲解。
- 上传替换图片会改变当前图片，保留馆方原图；日常馆方素材与数据库备份应单独保存。

## 7. 上线前完成一次完整验收

至少用一个全新的游客会话走完以下流程，记录出现问题的页面、时间和问题内容：

| 检查 | 通过标准 |
| --- | --- |
| 馆身份 | 首页、后台与导览显示本馆名称，无模板占位馆名 |
| 展厅与展品 | 数量、名称、分类、归属及开放状态与馆方目录一致 |
| 图片 | 能打开，且与展品对应；无图条目有合理显示 |
| 问卷与身份 | 选项文案符合本馆受众，四种身份可选择 |
| 路线 | 展厅开放、顺序合理，时长与现场条件相符 |
| 有资料的问题 | 回答与馆方确认的资料一致，展开检索依据能找到相关来源 |
| 无资料的问题 | 不将缺失的年代、出土地点、人物关系等编成确定事实 |
| 连续追问 | 围绕当前展品追问时保持对象和语境一致 |
| 切换与恢复 | 能切换展厅/展品，刷新后会话恢复符合预期 |
| 游览报告 | 反映实际浏览和问答，不把计划路线当作已经参观的记录 |
| 手机访问 | 输入、滚动、图片、报告可正常使用 |
| 语音（如启用） | 能试听和播放，声线与角色符合馆方要求 |

检查结果由内容负责人确认事实、由技术负责人确认服务可用。报告描述页面中的交互记录，不用于证明实际到馆、步行时长或学习能力提升。

## 8. 正式域名、HTTPS 与外部访问

本机测试可以使用 `http://127.0.0.1:8081`。远程游客访问应使用 HTTPS；部分浏览器能力需要安全上下文。

推荐保留 `instance.env` 的 `MUSEUM_BIND_ADDRESS=127.0.0.1`，由宿主机反向代理接入正式域名。由技术负责人完成：

1. 将本馆导览域名解析到服务器，准备符合所在地要求的域名与网站手续。
2. 安装或配置 Nginx/Caddy，开放对外 80/443 端口，把请求代理到 `127.0.0.1:8081`。
3. 为域名配置有效证书，并确保长连接、流式回答和资料上传能够正常通过代理。
4. 将 `app.env` 的 `CORS_ORIGINS` 改为正式站点地址，例如 `https://guide.example.org`，并设置 `APP_ENV=production`。
5. 使用同一实例的 `start` 命令重启应用，再从外部手机网络重新走第 7 节验收。

例如服务器已安装 Caddy 时，可将下面配置合并到其 Caddyfile；把域名替换为本馆域名，并保留服务器上其他站点的配置：

```caddyfile
guide.example.org {
    reverse_proxy 127.0.0.1:8081 {
        flush_interval -1
    }
}
```

确认 DNS、80/443 端口和证书申请条件满足后，验证并加载配置：

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

现有内层 Nginx 已为 API 关闭缓冲，上传限制为 101 MB；外层代理的上传限制不能更小。数据库、Redis、Elasticsearch 不需要直接向公网开放。

## 9. 日常运行、重启与更新

查看状态：

```text
uv run --frozen --no-dev python scripts/deploy_museum.py status --portal --instance instances/my-museum
```

查看近期应用日志：

```text
uv run --frozen --no-dev python scripts/deploy_museum.py logs --portal --instance instances/my-museum
```

停止服务并保留数据：

```text
uv run --frozen --no-dev python scripts/deploy_museum.py stop --portal --instance instances/my-museum
```

再次启动或修改模型配置后重启：

```text
uv run --frozen --no-dev python scripts/deploy_museum.py start --portal --instance instances/my-museum --admin-email curator@example.com
```

当前启动脚本仍会询问密码，但已初始化的账号不会因此被重置。不要重新生成已有实例的配置，也不要为了重启而删除 `instances/` 或数据卷。

服务数据保存在 Compose 持久化卷中，包括 PostgreSQL、Elasticsearch、Redis、展品图片、导入任务资料和日志。技术负责人应为数据库、图片、导入资料和实例配置安排备份，并确认恢复方法。普通停止使用上面的 `stop` 命令；`docker compose down -v` 会删除数据卷，不能当作常规重启。

更新应用源码前先备份；更新后保留同一个实例目录和 Compose 项目名，按新版本说明运行 `start`。数据库迁移属于运行所需文件，升级时保留完整迁移历史。

## 10. 常见问题

| 现象 | 先检查什么 |
| --- | --- |
| `uv` 或 `docker` 找不到 | 工具是否安装、是否重新打开终端；Docker Desktop 是否已启动 |
| 镜像或依赖下载失败 | 服务器对包源、镜像仓库及中文分词插件地址的网络访问；按日志定位失败阶段 |
| 提示实例目录已存在 | 若是原馆，直接启动；若是新馆，使用新目录和新端口 |
| 数据库/搜索启动失败 | Docker 状态、端口和资源，Elasticsearch 的 `vm.max_map_count`；必要时由技术人员查看对应容器日志 |
| 另一台电脑打不开 8081 | 默认只绑定本机；使用 SSH 隧道或第 8 节的 HTTPS 入口 |
| 提示缺少 `manifest.json` | 是否上传了源码 ZIP，或资料 ZIP 最外层多套了一层目录 |
| JSON/分类/路线校验失败 | JSON 格式、完整业务分区、分类编号、五条路线中的展厅编码、馆 ID 是否一致 |
| 上传成功但游客仍不能开始 | 查看导入任务是否全部完成，尤其是知识文档索引进度 |
| 索引失败 | 嵌入模型地址、密钥、模型名、维度及 Elasticsearch 可用性；修复后重试同一任务 |
| 回答失败或一直等待 | 聊天模型连接、余额/额度、模型名称，以及代理是否保持流式连接 |
| 回答不准确或找不到来源 | 原始资料是否齐全，文档是否索引完成，标题/展厅是否匹配，是否存在矛盾版本；用检索预览核对 |
| 修改配置后旧会话没变化 | 新建导览验证；已有会话保留创建时的配置 |
| “配置已被其他管理员更新” | 导出当前草稿，重新加载最新版本，合并后再发布 |
| 没有语音 | 初始配置默认关闭语音；需要先配置供应商服务，再到后台试听 |

交给技术人员排查时，提供站点地址、发生时间、所在页面、操作步骤和错误提示；不要把管理员密码或模型密钥放进公开反馈。

## 11. 交接时记录这些信息

| 项目 | 馆方填写 |
| --- | --- |
| 本馆正式名称 / 稳定 `museum_id` |  |
| 网站地址 / 管理后台地址 |  |
| 服务器与技术负责人 |  |
| 实例目录 / HTTP 端口 |  |
| 管理员邮箱 / 账号保管人 |  |
| 内容负责人 / 资料审核日期 |  |
| 原始资料包文件名 / 版本 / 保存位置 |  |
| 聊天和嵌入服务提供方 / 账号负责人 |  |
| 备份位置 / 备份与恢复负责人 |  |
| 完整流程验收日期 / 验收人 |  |

密码和密钥通过馆方约定的私密方式交接，不填在此表。

交付包已完成后端模块加载与健康接口、前端独立安装与构建、配置生成、资料模板、迁移链和 Compose 配置检查。实际服务器上的镜像构建、模型连通、HTTPS 和目标并发需要按上述步骤完成验收；检查记录在交付包 `docs/validation.json`。
