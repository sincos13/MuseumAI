# 馆方资料配置

`data/museum_template/` 是一个已通过结构校验的最小模板：1 个占位展厅、1 件占位展品和 1 份占位知识文本。它没有真实历史事实，不会随部署自动导入。请替换占位内容后再用于正式馆。

## 资料包目录

```text
manifest.json             资料清单、稳定馆 ID、知识来源与图片对应关系
profile.json              馆名、导览身份、问卷、分类、路线和业务配置
halls.csv                 展厅目录
exhibits.csv              展品目录
knowledge/exhibit-001.txt  对应展品的馆方讲解资料
images/                   可选；展品图片
```

ZIP 内应直接出现这些文件，不要多套一层 `museum_template/`。所有 JSON 和知识文本采用 UTF-8 编码；编辑 CSV 时保持列名、稳定编号及编码不变。

## 推荐编辑顺序

1. **馆身份**：同时修改 `manifest.json` 的 `museum_id` 和 `profile.json` 的 `museum.museum_id`，两者必须相同。使用小写字母、数字、连字符或下划线；首次导入后不随意更换。修改馆名、简称、简介和 Logo。
2. **展厅**：编辑 `halls.csv`。每厅的 `slug` 使用稳定的小写编码，例如 `history-hall`，其他文件使用同一个编码关联。`is_active=true` 表示开放。
3. **展品**：编辑 `exhibits.csv`。`source_record_id` 是稳定编号；`hall` 对应展厅 `slug`；`category` 必须来自 `profile.json` 的 `museum.business.categories`。
4. **知识资料**：替换 `knowledge/` 中的文本，并在 `manifest.json` 的 `knowledge` 列表登记文件、标题、来源和适用展厅。展品专属文档标题应与展品名一致，并关联同一个厅。
5. **导览配置**：保留 A/B/C/D 四种身份的代码，可调整名称、描述和提示词。修改 `business.questionnaire`、`categories`、`rhythms`、`routes`、`route_durations` 等内容；路线的 `preferred_halls` 只能引用包内启用的展厅。
6. **图片**：可以在展品 CSV 填合法 HTTPS `image_url`，也可以增加 `images/` 并登记映射，或导入后在后台上传。

`suggested_questions` 留空时由程序生成；不要填字面值 `[]`。`profile.json` 必须保留所有业务配置分区，不能只留下馆名；模板已经列全。某些默认话题面向历史/考古馆，部署其他类型馆时应连同问卷、分类和提示词一起审阅。

模板未配置高级 `visitor_experience`。它是可选的精细展品卡片/时间预算路线数据，普通馆方配置和路线可直接使用；需要精细路线时按后端模型结构填写，并重新校验。

## 知识与图片清单示例

```json
{
  "schema_version": 1,
  "museum_id": "my-museum",
  "knowledge": [
    {
      "id": "exhibit-001",
      "file": "knowledge/exhibit-001.txt",
      "title": "与展品目录一致的名称",
      "source_label": "馆方讲解稿，第 1 版",
      "source_url": "",
      "hall_slug": "main-hall"
    }
  ],
  "images": [
    { "source_record_id": "E001", "file": "images/E001.jpg" }
  ]
}
```

上例只有在 `images/E001.jpg` 实际存在时才可使用。没有图片时保持模板中的 `images: []`。图片支持 JPEG、PNG、WebP；单张不超过 10 MB，像素不超过 2000 万。网页上传的 ZIP 不超过 100 MB，解压总量不超过 250 MB。

## 校验、上传与验收

在项目根目录执行：

```text
uv run --frozen --no-dev python scripts/museum_instance.py validate data/museum_template
```

离线校验不会连接数据库或模型。通过意味着结构、引用与内容格式符合要求，不代表馆藏事实经过核实。

压缩包上传到 `/admin/import` 后，核对展厅、展品、文档和图片数量，再确认导入。等待索引全部完成，进入 `/tour`，用馆方已知答案的问题核对回答与来源；检查无资料的问题能否正确表达未知。然后核对路线、图片、报告和后台维护流程。

首次导入后用后台维护，不要通过换包覆盖整个已使用实例。要模拟或上线另一家馆，创建新的实例目录和端口。管理员网页可维护日常资料；整理 Word/PDF、扫描件和来源核实仍需人工完成。
