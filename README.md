# 图片处理工具

这是一个 Flask Web 图片工具，支持：

- 收集浏览器所选目录中的图片文件名并下载为 TXT
- 上传图片并压缩为 JPEG
- 在 JPG、PNG、WebP 之间转换；多文件结果自动打包为 ZIP
- 读取 HEIC/HEIF 图片

Web 端采用“上传 → 容器处理 → 下载”的工作方式，不接受浏览器传入的服务器文件路径。

## 使用 Docker Compose 启动

服务器需要安装 Docker Engine 和 Docker Compose 插件。进入项目目录后执行：

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:5001/healthz
```

健康检查应返回：

```json
{"status":"ok"}
```

查看服务日志：

```bash
docker compose logs -f image-tools
```

停止服务：

```bash
docker compose down
```

默认只监听服务器的 `127.0.0.1:5001`，适合放在 Caddy 或 Nginx 后面。处理结果保存在 Docker 卷中，默认保留 24 小时，并在后续处理请求到达时清理过期文件。

## 上传到服务器

如果项目还没有放进 Git 仓库，可以从本机同步（替换服务器地址和账号）：

```bash
rsync -av --exclude .git --exclude myenv --exclude uploads ./ deploy@example.com:/opt/pytools/
ssh deploy@example.com
cd /opt/pytools
cp .env.example .env
docker compose up -d --build
```

如果服务器通过 Git 拉取项目，则在代码更新后执行：

```bash
git pull
docker compose up -d --build
```

## 配置域名与 HTTPS

Caddy 会自动申请和续期 HTTPS 证书。一个最小站点配置如下：

```caddyfile
tools.example.com {
    encode zstd gzip
    reverse_proxy 127.0.0.1:5001
}
```

Nginx 反向代理的核心配置如下；上传限制要与 `.env` 中的 `MAX_UPLOAD_MB` 协调：

```nginx
server {
    listen 443 ssl http2;
    server_name tools.example.com;

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 180s;
    }
}
```

证书部分需要按服务器现有的 Nginx/Certbot 方案补充。

如果只打算通过 IP 和端口访问，可把 `.env` 改成 `BIND_ADDRESS=0.0.0.0`，并放行对应防火墙端口。但该应用本身没有登录功能，不建议未经认证直接暴露到公网；至少应在反向代理层增加访问认证，并启用 HTTPS。

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | ---: | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Docker 映射到宿主机的监听地址 |
| `APP_PORT` | `5001` | 宿主机端口 |
| `MAX_UPLOAD_MB` | `50` | 单个 HTTP 请求总大小上限；多文件共享此额度 |
| `FILE_RETENTION_HOURS` | `24` | 处理结果保留时间 |
| `WEB_CONCURRENCY` | `2` | Gunicorn worker 数量 |
| `GUNICORN_THREADS` | `2` | 每个 worker 的线程数 |
| `GUNICORN_TIMEOUT` | `180` | 图片处理请求超时秒数 |

低内存服务器可以设为 `WEB_CONCURRENCY=1`、`GUNICORN_THREADS=2`。

## 本地测试

```bash
python -m unittest discover -s tests -v
docker compose config
docker compose build
```

Docker 镜像使用非 root 用户运行；Compose 还启用了只读根文件系统、移除 Linux capabilities 和 `no-new-privileges`。Web 镜像只包含运行页面所需的 `web_gui.py` 与 `compress_images.py`，项目中的其他命令行脚本不会进入该服务镜像。
