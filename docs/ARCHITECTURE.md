# Toolmist 技术架构

## 1. 架构目标

重构后的架构需要同时满足：

- 公开匿名访问下的资源边界和文件安全。
- 新工具能够以独立模块接入，而不是继续扩大单文件路由。
- 保持单容器、单机部署的运维简单度。
- 浏览器端与服务端工具可以使用一致的产品外观。
- 在确有规模需求前，不引入数据库、消息队列和前端构建工具链。

## 2. 总体结构

```text
Browser
  |
  | HTTPS
  v
Caddy
  |  request body limit / TLS / reverse proxy
  v
Gunicorn + Flask application
  |-- Site routes and templates
  |-- Tool API blueprints
  |-- Image processing services
  |-- Job-scoped artifact storage
  `-- Health and error handling
       |
       v
Docker volume: temporary artifacts only
```

Caddy 继续负责 TLS、HTTP 到 HTTPS 跳转和反向代理。应用负责工具级输入校验、处理配额、临时文件生命周期和业务错误响应。

## 3. 建议代码结构

```text
toolmist/
  __init__.py              # create_app
  config.py                # 环境变量与限制
  errors.py                # 统一网页/API 错误
  blueprints/
    site.py                # 首页和静态页面
    health.py              # 健康检查
    downloads.py           # 结果下载
  tools/
    registry.py            # 工具元数据注册表
    image_compress/
      routes.py
      service.py
      schema.py
    image_convert/
      routes.py
      service.py
      schema.py
  services/
    artifacts.py           # job 目录、TTL、清理
    images.py              # 通用图片加载、像素检查、色彩转换
    limits.py              # 文件数、并发和请求限制
  templates/
    index.html
  static/
    css/app.css
    js/app.js
tests/
  unit/
  integration/
wsgi.py
```

现有 CLI 文件暂时不删除。可复用算法先迁入服务模块，CLI 再调用相同服务，避免 Web 和命令行维护两套实现。

## 4. 工具注册模型

页面工具列表由服务端注册表提供，不在模板中重复硬编码工具元数据。

每个工具注册项包含：

- `id`：稳定标识，例如 `image-compress`。
- `name`：展示名称。
- `description`：一句话用途。
- `category`：首期为 `image-file`。
- `execution`：`browser` 或 `server`。
- `limits`：扩展名、文件数、总大小等公开限制。
- `availability`：是否上线。

注册表只描述产品能力，不动态导入任意用户代码，不设计成第三方插件系统。

## 5. API 约定

首期使用版本化路径：

```text
POST /api/v1/tools/image-compress/jobs
POST /api/v1/tools/image-convert/jobs
GET  /api/v1/jobs/{job_id}/artifacts/{artifact_id}
GET  /healthz
```

文件名提取为浏览器本地工具，不调用 API。

### 5.1 成功响应

```json
{
  "ok": true,
  "job": {
    "id": "opaque-random-id",
    "expires_at": "2026-08-24T10:00:00Z"
  },
  "artifacts": [
    {
      "id": "result",
      "name": "photo-compressed.jpg",
      "size": 123456,
      "download_url": "/api/v1/jobs/.../artifacts/result"
    }
  ]
}
```

### 5.2 错误响应

```json
{
  "ok": false,
  "error": {
    "code": "IMAGE_TOO_LARGE",
    "message": "图片像素超过当前工具允许的范围"
  }
}
```

错误响应不包含服务器绝对路径、异常堆栈、依赖版本或原始子进程输出。

## 6. 临时文件模型

每次服务端处理创建独立随机任务目录：

```text
/app/uploads/{opaque_job_id}/
  inputs/
  outputs/
  metadata.json
```

约束：

- `job_id` 使用加密安全随机值，不使用时间戳或可枚举自增 ID。
- 用户原始文件名只作为展示信息，磁盘文件使用内部名称。
- 所有路径由服务端构造；客户端不能传入输出目录或服务器路径。
- 下载路由通过任务目录和服务端元数据定位文件。
- 首期默认 TTL 从 24 小时缩短到 1 小时。
- 后台轻量清理线程或独立容器命令定期删除过期任务；请求触发清理只作为补充。
- 任务失败时立即删除输入和不完整输出。

## 7. 资源与安全边界

### 7.1 请求限制

首期建议默认值：

| 项目 | 限制 |
| --- | ---: |
| 单次 HTTP 请求 | 50 MB |
| 压缩工具文件数 | 1 |
| 转换工具文件数 | 10 |
| 单张图片像素 | 40 MP |
| 解码后总像素 | 100 MP |
| Gunicorn 请求超时 | 180 秒 |
| 结果保留 | 1 小时 |

前端限制用于及时提示，后端限制才是最终安全边界。

### 7.2 图片安全

- 使用 Pillow 解码后校验实际格式，而不是只信任扩展名或 MIME。
- 将 `DecompressionBombWarning` 提升为受控错误或使用更低的显式像素上限。
- 限制多文件总像素，防止多个合法小文件叠加造成内存压力。
- 输出文件统一由服务端决定格式和扩展名，避免内容与扩展名不一致。
- 不保留用户提供的 EXIF GPS 等元数据，除非工具明确说明。

### 7.3 匿名滥用控制

首期不在 Caddy 中加入非标准插件。应用保留以下渐进措施：

1. 严格的文件、像素、时长和并发限制。
2. 每 IP 的短窗口请求频率限制。
3. 全局处理槽位，资源繁忙时快速返回 `429` 或 `503`。
4. 指标确认确有需要后，再评估 Redis 或上游防护。

获取客户端 IP 时只信任来自本机 Caddy 的转发头，不能直接信任公网请求提供的 `X-Forwarded-For`。

### 7.4 页面安全

- 前端不把文件名或服务端消息直接拼接为未转义 HTML。
- 移除 HTML 内联事件处理器，允许部署更严格的 Content Security Policy。
- 不向公众提供 `/api/logs` 和 `/api/clear_logs`。
- 详细错误只进入容器日志，并避免记录原始文件内容和敏感路径。

## 8. 并发模型

首期继续同步处理，不立即引入任务队列：

- 图片任务规模受控，交互上需要即时返回结果。
- Gunicorn 使用少量 worker/thread，应用另设处理并发信号量。
- 当处理槽位耗尽时快速失败，避免请求无限堆积。

以下任一条件持续出现时再引入异步队列：

- 正常任务经常超过反向代理请求时长。
- 需要进度查询或断线后恢复。
- 需要跨多台处理节点扩容。
- 音视频等长任务正式上线。

## 9. 配置

建议配置项：

```text
MAX_UPLOAD_MB=50
MAX_FILES_PER_JOB=10
MAX_IMAGE_PIXELS=40000000
MAX_TOTAL_PIXELS=100000000
FILE_RETENTION_HOURS=1
PROCESSING_CONCURRENCY=2
GUNICORN_TIMEOUT=180
```

生产配置继续通过 Compose 环境变量注入。代码提供安全默认值，并在启动时验证不合法配置。

## 10. 兼容与迁移

- 保持 `GET /healthz` 不变，避免影响 Docker 和 Caddy 健康检查。
- 首次迁移期间可保留旧 API 的薄兼容层，但新页面只使用 `/api/v1`。
- 稳定后删除旧 `/api/logs`、路径式接口和未使用的前端函数。
- Docker 服务名、容器端口 `5001` 和 Caddy 上游保持不变。
- 数据卷只存临时任务；迁移不承诺保留旧处理结果。

## 11. 可观测性

首期使用结构化应用日志，至少记录：

- 请求 ID、工具 ID、结果状态和耗时。
- 输入文件数、总字节和像素量级，不记录原始文件名全文。
- 失败错误码，不记录用户文件内容。
- 清理任务删除的任务数和回收字节数。

健康检查只验证进程可响应；后续可增加仅本机访问的就绪检查，用于验证临时目录可写。

## 12. 架构决策记录

### ADR-001：保持 Flask 服务端渲染

现阶段页面规模小，不引入 React/Vue 和 Node 构建链。使用 Jinja、原生 JavaScript 和 CSS，减少镜像复杂度。

### ADR-002：首期不使用数据库

任务状态随临时目录存在，下载链接只在短 TTL 内有效。没有用户、历史和长期任务，因此数据库暂不产生足够价值。

### ADR-003：浏览器能完成的工具不上送数据

文件名提取改为纯前端实现，减少服务器资源消耗，也让“本地处理”成为可验证的产品能力。

### ADR-004：Silk 转 MP3 延后

先把公开图片处理的输入边界和运行模型做稳定，再评估二进制解码器与音频任务。
