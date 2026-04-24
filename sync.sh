#!/bin/bash
# ============================================================
# 飞牛NAS台账系统 - GitHub自动同步脚本
# 功能：定时拉取GitHub仓库最新代码，更新本地运行的系统
#
# 使用方式：
#   ./sync.sh          # 后台持续运行，按设置间隔自动同步
#   ./sync.sh --now    # 立即执行一次同步
# ============================================================

set -e

# 配置
APP_DIR="/app"
SYNC_LOG="/app/logs/sync.log"
SETTINGS_DB="/app/data/ledger.db"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$SYNC_LOG"
}

# 从SQLite读取设置值（用Python，不依赖sqlite3命令行）
get_setting() {
    local key=$1
    local default=$2
    if [ -f "$SETTINGS_DB" ]; then
        local value=$(python3 -c "
import sqlite3, sys
try:
    conn = sqlite3.connect('$SETTINGS_DB')
    row = conn.execute('SELECT value FROM settings WHERE key=?', ('$key',)).fetchone()
    conn.close()
    print(row[0] if row else '')
except:
    print('')
" 2>/dev/null)
        echo "${value:-$default}"
    else
        echo "$default"
    fi
}

# 更新设置值（用Python）
set_setting() {
    local key=$1
    local value=$2
    if [ -f "$SETTINGS_DB" ]; then
        python3 -c "
import sqlite3
conn = sqlite3.connect('$SETTINGS_DB')
conn.execute('INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)', ('$key', '$value'))
conn.commit()
conn.close()
" 2>/dev/null
    fi
}

# 执行同步
do_sync() {
    local repo_url=$(get_setting "github_repo" "")
    if [ -z "$repo_url" ]; then
        log "⚠️  未配置GitHub仓库地址，跳过同步"
        return 0
    fi

    log "🔄 开始同步: $repo_url"

    # 检查是否是git仓库
    if [ ! -d "$APP_DIR/.git" ]; then
        log "📥 首次克隆仓库..."
        cd /tmp
        git clone "$repo_url" flybook-temp 2>&1 | tee -a "$SYNC_LOG"
        if [ $? -eq 0 ]; then
            rsync -av --exclude='data/' --exclude='logs/' --exclude='backups/' \
                /tmp/flybook-temp/ "$APP_DIR/" 2>&1 | tee -a "$SYNC_LOG"
            rm -rf /tmp/flybook-temp
            log "✅ 克隆完成"
        else
            log "❌ 克隆失败"
            return 1
        fi
    else
        cd "$APP_DIR"
        local local_changes=$(git status --porcelain 2>/dev/null)
        if [ -n "$local_changes" ]; then
            log "📦 检测到本地修改，暂存中..."
            git stash push -m "auto-stash-$(date +%Y%m%d%H%M%S)" 2>&1 | tee -a "$SYNC_LOG"
        fi

        git fetch origin 2>&1 | tee -a "$SYNC_LOG"
        local current=$(git rev-parse HEAD 2>/dev/null)
        local remote=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master 2>/dev/null)

        if [ "$current" = "$remote" ]; then
            log "✅ 代码已是最新版本"
        else
            log "📥 检测到远程更新，拉取中..."
            local branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
            git pull origin "$branch" 2>&1 | tee -a "$SYNC_LOG"

            if [ $? -eq 0 ]; then
                log "✅ 同步成功，代码已更新"
                if [ -n "$local_changes" ]; then
                    log "📦 恢复本地修改..."
                    git stash pop 2>&1 | tee -a "$SYNC_LOG" || log "⚠️  部分本地修改冲突，已保留在stash中"
                fi
                if git diff "$current" "$remote" --name-only | grep -q "requirements.txt"; then
                    log "📦 检测到依赖变化，重新安装..."
                    pip install --no-cache-dir -r requirements.txt 2>&1 | tee -a "$SYNC_LOG"
                fi
            else
                log "❌ 拉取失败"
                git checkout . 2>/dev/null
                return 1
            fi
        fi
    fi

    set_setting "last_sync_time" "$(date '+%Y-%m-%d %H:%M:%S')"
    log "✅ 同步流程完成"
}

# 主逻辑
if [ "$1" = "--now" ]; then
    do_sync
else
    log "🚀 GitHub同步服务启动"
    while true; do
        interval=$(get_setting "auto_sync_interval" "3600")
        enabled=$(get_setting "auto_sync_enabled" "false")
        if [ "$enabled" = "true" ]; then
            do_sync
        fi
        log "⏳ 下次同步: ${interval}秒后"
        sleep "$interval"
    done
fi
