# Toolmist

Toolmist 是一个公开、无需注册、即开即用的轻量在线工具箱。

首期包含：

- 图片压缩：上传单张图片，按目标大小输出 JPEG。
- 图片格式转换：将最多 10 张图片转换为 JPG、PNG 或 WebP；多张结果打包为 ZIP。
- 文件名提取：完全在浏览器本地读取文件或目录并生成 TXT，不发送网络请求。

服务端文件按随机任务目录隔离，输入文件处理后立即删除，结果默认保留 1 小时。Toolmist 不建立账号、文件库或处理历史。

## 运行架构

```text
Browser -> HTTPS / Caddy -> 127.0.0.1:5001 -> Gunicorn / Flask
                                                   |
                                                   `-> temporary Docker volume
```

- Caddy 负责 HTTPS、证书、HTTP 跳转、请求体上限和反向代理。
- Flask 负责文件、格式、像素、频率与处理并发限制。
- Docker 服务使用非 root 用户、只读根文件系统和最小 Linux 权限。
- 临时结果保存在独立 Docker 卷，由后台线程和清理命令回收。

## 本地开发与测试

建议使用 Python 3.12 和 Node.js 20 或更新版本：

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
node --test tests/frontend_core.test.mjs
```

本地启动：

```bash
UPLOAD_FOLDER=/tmp/toolmist-uploads \
ENABLE_ARTIFACT_CLEANUP=false \
.venv/bin/flask --app wsgi:app run --host 127.0.0.1 --port 5001
```

## Docker Compose

首次启动：

```bash
cp .env.example .env
docker compose -p toolmist config
docker compose -p toolmist up -d --build
docker compose -p toolmist ps
curl --fail http://127.0.0.1:5001/healthz
```

健康检查应返回：

```json
{"status":"ok"}
```

查看日志：

```bash
docker compose -p toolmist logs -f --tail 200 image-tools
```

手动执行过期任务清理：

```bash
docker compose -p toolmist exec -T image-tools \
  flask --app wsgi:app cleanup-artifacts
```

正常停止不会删除临时结果卷：

```bash
docker compose -p toolmist down
```

只有明确需要删除 Toolmist 的全部临时结果时才使用 `down --volumes`。它不会影响其他 Compose 项目，但会永久删除 Toolmist 自己的结果卷。

## Caddy

生产容器默认只映射到 `127.0.0.1:5001`。Caddy 2.10 及以上可使用标准 `request_body` 指令限制上传体积；该值应与 `MAX_UPLOAD_MB` 保持一致。

```caddyfile
www.toolmist.com {
    redir https://toolmist.com{uri} permanent
}

toolmist.com {
    request_body {
        max_size 50MB
    }

    encode zstd gzip
    reverse_proxy 127.0.0.1:5001
}
```

修改配置后先校验再重载：

```bash
sudo caddy fmt --overwrite /etc/caddy/sites-available/toolmist.caddy
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo systemctl reload caddy
sudo systemctl is-active caddy
```

Caddy 配置语法可参考官方的 [`request_body` 文档](https://caddyserver.com/docs/caddyfile/directives/request_body)。应用内的频率限制只是单机轻量保护，不代替上游网络层 DDoS 防护。

## 生产更新

以下命令只操作 Toolmist 自己的仓库和 Compose 项目。先进入服务器上的实际仓库目录，例如：

```bash
cd /srv/apps/toolmist/mypytools
git status --short
git pull --ff-only origin main
sudo docker compose -p toolmist up -d --build
sudo docker compose -p toolmist ps
curl --fail --silent --show-error http://127.0.0.1:5001/healthz
sudo docker compose -p toolmist logs --tail 100 image-tools
```

如果 `git status --short` 显示服务器本地改动，应先停止更新并确认改动来源，不要强制覆盖。

发布后检查：

```bash
curl --fail --silent --show-error https://toolmist.com/ > /dev/null
curl --fail --silent --show-error https://toolmist.com/healthz
```

## 回滚

发布前记录当前提交：

```bash
git rev-parse HEAD
```

需要回滚时，把 `<known-good-sha>` 替换为已知正常提交：

```bash
cd /srv/apps/toolmist/mypytools
git switch --detach <known-good-sha>
sudo docker compose -p toolmist up -d --build
curl --fail --silent --show-error http://127.0.0.1:5001/healthz
```

恢复跟踪主分支：

```bash
git switch main
git pull --ff-only origin main
sudo docker compose -p toolmist up -d --build
```

临时处理结果不纳入版本回滚保证。

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | ---: | --- |
| `BIND_ADDRESS` | `127.0.0.1` | 宿主机监听地址 |
| `APP_PORT` | `5001` | 宿主机端口 |
| `MAX_UPLOAD_MB` | `50` | 单次 HTTP 请求总大小上限 |
| `MAX_FILES_PER_JOB` | `10` | 单次格式转换文件数 |
| `MAX_IMAGE_PIXELS` | `40000000` | 单张图片解码像素上限 |
| `MAX_TOTAL_PIXELS` | `100000000` | 多图任务总像素上限 |
| `PROCESSING_CONCURRENCY` | `2` | 每个 Gunicorn worker 的处理槽位 |
| `RATE_LIMIT_REQUESTS` | `20` | 每个进程、每个来源 IP 的短窗口任务数 |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | 频率限制窗口秒数 |
| `FILE_RETENTION_HOURS` | `1` | 结果保留小时数 |
| `ARTIFACT_CLEANUP_INTERVAL_SECONDS` | `600` | 后台清理间隔秒数 |
| `TRUST_PROXY_HEADERS` | `true` | Compose 中信任本机 Caddy 的最后一跳代理头 |
| `WEB_CONCURRENCY` | `2` | Gunicorn worker 数量 |
| `GUNICORN_THREADS` | `2` | 每个 worker 的线程数 |
| `GUNICORN_TIMEOUT` | `180` | 请求超时秒数 |

`TRUST_PROXY_HEADERS=true` 只适用于容器端口绑定回环地址并由受控反向代理访问的部署。如果设置 `BIND_ADDRESS=0.0.0.0` 直接暴露应用端口，必须将它改为 `false`，并重新评估防火墙和来源 IP 处理方式。

低内存服务器可从以下配置开始：

```text
WEB_CONCURRENCY=1
GUNICORN_THREADS=2
PROCESSING_CONCURRENCY=1
```

## API 与隐私边界

页面使用的接口只有：

```text
POST /api/v1/tools/image-compress/jobs
POST /api/v1/tools/image-convert/jobs
GET  /api/v1/jobs/{job_id}/artifacts/{artifact_id}
GET  /healthz
```

客户端不能提交服务器输入路径或输出目录。旧版 `/api/compress_images`、`/api/convert_format`、`/api/collect_filenames`、`/api/logs` 和 `/download/*` 已移除。
