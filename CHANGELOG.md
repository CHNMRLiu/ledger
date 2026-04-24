# 📋 更新日志

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)，所有重要变更均记录在此。

---

## [1.0.0](https://github.com/CHNMRLiu/ledger/releases/tag/v1.0.0) — 2026-04-24

> 🎉 首个正式版本，飞牛NAS台账系统完整功能上线。

### ✨ 新增

**台账管理**
- 完整CRUD：新增、编辑、删除、列表查看
- 多条件筛选：分类 / 状态 / 优先级 / 日期范围
- 全文搜索：标题和描述模糊匹配
- 列排序：创建时间、更新时间、金额、日期等
- 快速编辑：列表页弹窗编辑，无需跳转
- 标签系统：自由打标，逗号分隔

**数据看板**
- 统计卡片：总记录数、已完成、待处理、今日新增
- 金额统计：总金额、平均金额、本周新增
- 分类分布：柱状图展示各分类记录数量
- 状态分布：待处理 / 进行中 / 已完成 / 已取消
- 操作日志：最近10条操作记录

**分类管理**
- 自定义名称、Emoji图标、颜色、排序
- 删除分类时自动解除关联记录

**数据安全**
- SQLite WAL 模式，读写并发安全
- 独立数据目录 `/vol1/docker/flybook-data/`，与代码完全隔离
- 自动备份：每6小时执行，保留最近30份
- 手动备份 / 一键恢复，恢复前自动备份当前状态
- `.dockerignore` 防止数据被构建进镜像

**系统设置**
- 自定义系统名称、分页数量
- GitHub 同步配置（仓库地址、间隔、开关）
- 数据导入导出（JSON 格式）

**部署与运维**
- Dockerfile + docker-compose.yml，飞牛NAS一键部署
- docker-compose.image.yml，使用 GHCR 预构建镜像版
- Supervisor 进程管理（Flask + 同步脚本）
- Docker 健康检查（`/health`）
- 响应式界面，PC + 移动端适配

**CI/CD**
- GitHub Actions：推送 tag 自动构建 Docker 镜像（amd64 + arm64）
- GitHub Actions：自动创建 Release 并附带更新日志
- GitHub Actions：自动更新 CHANGELOG.md

### 🔧 技术栈

- 后端：Python 3.12 + Flask 3.1
- 数据库：SQLite（WAL模式）
- 前端：原生 HTML / CSS / JavaScript（零依赖）
- 部署：Docker + Supervisor
- CI/CD：GitHub Actions → ghcr.io
