<div align="center">

# 🐄 飞牛台账

**飞牛NAS专属 · 轻量级网页台账系统**

一个为飞牛NAS量身打造的台账管理工具，单容器部署，数据100%本地存储，开箱即用。

[![Release](https://img.shields.io/github/v/release/CHNMRLiu/ledger?color=4A90D9&label=版本&style=flat-square)](https://github.com/CHNMRLiu/ledger/releases)
[![Docker](https://img.shields.io/badge/docker-ghcr.io%2Fchnmrlieu%2Fledger-2496ED?style=flat-square&logo=docker)](https://github.com/CHNMRLiu/ledger/pkgs/container/ledger)
[![License](https://img.shields.io/github/license/CHNMRLiu/ledger?style=flat-square)](LICENSE)

</div>

---

## ✨ 功能一览

| 功能 | 说明 |
|------|------|
| 📋 台账管理 | 新增 / 编辑 / 删除 / 搜索 / 筛选 / 排序 |
| 📊 数据看板 | 总数、状态分布、分类统计、金额汇总、趋势图 |
| 🏷️ 分类系统 | 自定义图标、颜色、排序 |
| 💾 自动备份 | 每6小时自动备份，保留30份，一键恢复 |
| 🔄 GitHub同步 | 定时拉取最新代码，Actions自动生成更新日志 |
| 🔥 热更新 | 改代码后自动重载，无需重启容器 |
| 👥 多用户 | 局域网多设备同时访问 |

## 🚀 三步部署

```bash
# ① 克隆代码
cd /vol1/docker && git clone https://github.com/CHNMRLiu/ledger.git && cd ledger

# ② 创建数据目录
mkdir -p /vol1/docker/flybook-data/{db,logs,backups}

# ③ 启动
docker-compose up -d
```

打开浏览器访问 `http://飞牛IP:5000` ，完成。

> **数据安全**：所有业务数据存储在 `/vol1/docker/flybook-data/` ，与代码完全隔离，容器重建 / git pull 均不影响数据。

## 📦 使用预构建镜像（可选）

不想本地构建？直接拉取 GHCR 镜像：

```bash
docker pull ghcr.io/chnmrlieu/ledger:latest
```

将 `docker-compose.yml` 中的 `build` 替换为：

```yaml
image: ghcr.io/chnmrlieu/ledger:latest
```

## 🔧 版本更新

```bash
# 打 tag 自动触发：Docker镜像构建 + GitHub Release + CHANGELOG
git tag v1.1.0 && git push origin main --tags

# NAS 端更新
docker pull ghcr.io/chnmrlieu/ledger:latest
docker-compose up -d
```

## 📁 项目结构

```
flybook-ledger/
├── app/                        ← 应用代码（热更新）
│   ├── app.py                  Flask 主程序
│   ├── models.py               数据模型 + 备份逻辑
│   ├── templates/               页面模板（6个）
│   └── static/                  前端资源（CSS + JS）
├── docker-compose.yml           Docker 编排
├── docker-compose.image.yml     镜像版编排（可选）
├── Dockerfile                   构建文件
├── supervisord.conf             进程管理
├── sync.sh                      GitHub 同步脚本
└── .github/workflows/           CI/CD
    ├── docker-publish.yml       Docker 镜像自动发布
    ├── auto-release.yml         Release 自动创建
    └── auto-changelog.yml       CHANGELOG 自动更新
```

## 🛠️ 技术栈

`Python 3.12` · `Flask` · `SQLite` · `HTML/CSS/JS` · `Docker` · `Supervisor` · `GitHub Actions`

零外部依赖，零云服务，纯本地运行。

## 📖 更多文档

- [更新日志](./CHANGELOG.md)
- [维护指南](./MAINTENANCE.md)

## 📄 License

[MIT](./LICENSE)
