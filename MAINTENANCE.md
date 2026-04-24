# 🔧 维护指南

## 版本管理

### 版本号规范

采用语义化版本 `v主版本.次版本.修订号`：

| 类型 | 格式 | 说明 | 示例 |
|------|------|------|------|
| 主版本 | v**X**.0.0 | 重大架构变更、不兼容更新 | v2.0.0 |
| 次版本 | v1.**X**.0 | 新增功能、向后兼容 | v1.1.0 |
| 修订号 | v1.0.**X** | Bug修复、小改动 | v1.0.1 |

### 发布新版本

```bash
# 1. 修改代码并提交
git add -A
git commit -m "feat: 新功能描述"

# 2. 更新 CHANGELOG.md（可手动补充，GitHub Actions也会自动更新）

# 3. 打tag并推送，自动触发Release + Docker镜像构建
git tag v1.1.0
git push origin main --tags
```

推送tag后，GitHub Actions 会自动：
- ✅ 构建 Docker 镜像（amd64 + arm64 双架构）
- ✅ 推送到 GitHub Container Registry (`ghcr.io/chnmrlieu/ledger`)
- ✅ 创建 GitHub Release（附带更新日志）
- ✅ 更新 CHANGELOG.md

### 自动发布的产物

每次推送 `v*` tag 后自动生成：

| 产物 | 地址 | 用途 |
|------|------|------|
| Docker镜像 | `ghcr.io/chnmrlieu/ledger:1.0.0` | NAS直接拉取部署 |
| Docker镜像 | `ghcr.io/chnmrlieu/ledger:latest` | 始终指向最新版 |
| GitHub Release | github.com/CHNMRLiu/ledger/releases | 版本下载+更新日志 |
| Source code | Release 自动附带 | zip/tar.gz 源码包 |

## NAS端更新方式

### 方式一：使用Docker镜像（推荐，无需本地构建）

```bash
cd /vol1/docker/ledger

# 拉取最新镜像
docker pull ghcr.io/chnmrlieu/ledger:latest

# 重启容器
docker-compose down
docker-compose up -d
```

### 方式二：Git拉取代码（支持热更新）

```bash
cd /vol1/docker/ledger
git pull origin main

# 代码更新会自动热重载，无需重启
# 如果依赖变化，需要重建：
docker-compose up -d --build
```

### 方式三：使用Release包

1. 前往 [Releases页面](https://github.com/CHNMRLiu/ledger/releases)
2. 下载最新版本的 `Source code (zip)`
3. 解压后按部署步骤操作

## docker-compose 使用镜像版（无需本地构建）

如果想直接使用GHCR镜像而非本地构建，修改 `docker-compose.yml`：

```yaml
services:
  flybook-ledger:
    image: ghcr.io/chnmrlieu/ledger:latest  # 替换 build 部分
    container_name: flybook-ledger
    # ... 其余配置不变
```

## 日常维护

### 查看日志

```bash
# 应用日志
docker exec flybook-ledger cat /app/logs/flask-stdout.log

# 同步日志
docker exec flybook-ledger cat /app/logs/sync-stdout.log

# 实时跟踪
docker logs -f flybook-ledger
```

### 手动备份

```bash
# 通过API
curl -X POST http://localhost:5000/api/backup

# 直接复制数据库
cp /vol1/docker/flybook-data/db/ledger.db /vol1/docker/flybook-data/backups/manual_$(date +%Y%m%d).db
```

### 数据恢复

```bash
# 停止服务
docker-compose down

# 恢复备份
cp /vol1/docker/flybook-data/backups/ledger_XXXXXXXX_XXXXXX.db /vol1/docker/flybook-data/db/ledger.db

# 重启
docker-compose up -d
```

### 重置容器（数据不丢失）

```bash
docker-compose down
docker-compose up -d --build
```

### 完全重建（数据不丢失）

```bash
docker-compose down
docker rmi flybook-ledger
docker-compose up -d --build
```

## 发布检查清单

发布新版本前确认：

- [ ] 代码已测试通过
- [ ] `version.json` 版本号已更新
- [ ] `CHANGELOG.md` 已更新（或依赖Actions自动生成）
- [ ] `README.md` 无过时内容
- [ ] 数据库兼容性确认（新版本能读旧版本数据）
