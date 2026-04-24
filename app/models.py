# -*- coding: utf-8 -*-
"""
数据模型层 - SQLite数据库操作
飞牛NAS台账系统核心数据结构与CRUD操作
"""

import sqlite3
import os
import json
import shutil
import glob
from datetime import datetime, timedelta
from contextlib import contextmanager

# 数据库路径：挂载到NAS宿主机，容器重建不丢失
DB_PATH = os.environ.get('DB_PATH', '/app/data/ledger.db')


def get_db_path():
    """获取数据库文件路径"""
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    return DB_PATH


@contextmanager
def get_db():
    """
    数据库连接上下文管理器
    自动提交/回滚，确保连接正确关闭
    """
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row  # 返回字典风格的结果
    conn.execute("PRAGMA journal_mode=WAL")  # WAL模式：提升并发性能
    conn.execute("PRAGMA foreign_keys=ON")   # 启用外键约束
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """
    初始化数据库表结构
    首次运行时自动创建所有表和默认数据
    """
    with get_db() as db:
        # ========== 分类表 ==========
        db.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                icon TEXT DEFAULT '📁',
                color TEXT DEFAULT '#4A90D9',
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ========== 台账记录主表 ==========
        db.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category_id INTEGER,
                status TEXT DEFAULT '待处理',
                priority TEXT DEFAULT '普通',
                amount REAL DEFAULT 0,
                record_date DATE,
                due_date DATE,
                description TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                extra_data TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            )
        ''')

        # ========== 操作日志表 ==========
        db.execute('''
            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER,
                action TEXT NOT NULL,
                detail TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ========== 系统设置表 ==========
        db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ========== 创建索引提升查询性能 ==========
        db.execute('CREATE INDEX IF NOT EXISTS idx_records_category ON records(category_id)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_records_status ON records(status)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_records_date ON records(record_date)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_records_created ON records(created_at)')

        # ========== 插入默认分类（仅首次） ==========
        default_categories = [
            ('财务收支', '💰', '#E74C3C', 1),
            ('库存管理', '📦', '#3498DB', 2),
            ('设备维护', '🔧', '#2ECC71', 3),
            ('人事考勤', '👥', '#9B59B6', 4),
            ('项目跟踪', '📋', '#F39C12', 5),
            ('合同管理', '📄', '#1ABC9C', 6),
        ]
        for name, icon, color, sort in default_categories:
            db.execute(
                'INSERT OR IGNORE INTO categories (name, icon, color, sort_order) VALUES (?, ?, ?, ?)',
                (name, icon, color, sort)
            )

        # ========== 插入默认设置 ==========
        default_settings = [
            ('app_name', '飞牛台账系统'),
            ('page_size', '20'),
            ('auto_sync_enabled', 'false'),
            ('auto_sync_interval', '3600'),
            ('github_repo', ''),
            ('last_sync_time', ''),
        ]
        for key, value in default_settings:
            db.execute(
                'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
                (key, value)
            )


# ============================================================
# 台账记录 CRUD 操作
# ============================================================

def create_record(data):
    """
    新增台账记录
    参数: data字典，包含title, category_id, status, priority, amount, record_date等
    返回: 新记录的ID
    """
    with get_db() as db:
        cursor = db.execute('''
            INSERT INTO records (title, category_id, status, priority, amount,
                                 record_date, due_date, description, tags, extra_data)
            VALUES (:title, :category_id, :status, :priority, :amount,
                    :record_date, :due_date, :description, :tags, :extra_data)
        ''', {
            'title': data.get('title', ''),
            'category_id': data.get('category_id'),
            'status': data.get('status', '待处理'),
            'priority': data.get('priority', '普通'),
            'amount': data.get('amount', 0),
            'record_date': data.get('record_date', datetime.now().strftime('%Y-%m-%d')),
            'due_date': data.get('due_date'),
            'description': data.get('description', ''),
            'tags': json.dumps(data.get('tags', []), ensure_ascii=False),
            'extra_data': json.dumps(data.get('extra_data', {}), ensure_ascii=False),
        })
        record_id = cursor.lastrowid

        # 记录操作日志
        db.execute(
            'INSERT INTO operation_logs (record_id, action, detail) VALUES (?, ?, ?)',
            (record_id, '创建', f'创建记录: {data.get("title", "")}')
        )
        return record_id


def get_records(page=1, per_page=20, category_id=None, status=None,
                priority=None, search=None, sort_by='created_at', sort_order='desc',
                date_from=None, date_to=None):
    """
    获取台账记录列表（支持分页、筛选、搜索、排序）
    返回: (记录列表, 总数)
    """
    with get_db() as db:
        # 构建查询条件
        conditions = []
        params = []

        if category_id:
            conditions.append('r.category_id = ?')
            params.append(category_id)
        if status:
            conditions.append('r.status = ?')
            params.append(status)
        if priority:
            conditions.append('r.priority = ?')
            params.append(priority)
        if search:
            conditions.append('(r.title LIKE ? OR r.description LIKE ?)')
            params.extend([f'%{search}%', f'%{search}%'])
        if date_from:
            conditions.append('r.record_date >= ?')
            params.append(date_from)
        if date_to:
            conditions.append('r.record_date <= ?')
            params.append(date_to)

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        # 允许的排序字段（防SQL注入）
        allowed_sorts = {'created_at', 'updated_at', 'record_date', 'amount', 'title', 'priority'}
        if sort_by not in allowed_sorts:
            sort_by = 'created_at'
        sort_dir = 'ASC' if sort_order.lower() == 'asc' else 'DESC'

        # 查询总数
        count_sql = f'SELECT COUNT(*) FROM records r WHERE {where_clause}'
        total = db.execute(count_sql, params).fetchone()[0]

        # 查询分页数据（关联分类表获取分类名）
        offset = (page - 1) * per_page
        data_sql = f'''
            SELECT r.*, c.name as category_name, c.icon as category_icon, c.color as category_color
            FROM records r
            LEFT JOIN categories c ON r.category_id = c.id
            WHERE {where_clause}
            ORDER BY r.{sort_by} {sort_dir}
            LIMIT ? OFFSET ?
        '''
        rows = db.execute(data_sql, params + [per_page, offset]).fetchall()

        # 转换为字典列表
        records = []
        for row in rows:
            record = dict(row)
            record['tags'] = json.loads(record.get('tags', '[]'))
            record['extra_data'] = json.loads(record.get('extra_data', '{}'))
            records.append(record)

        return records, total


def get_record_by_id(record_id):
    """根据ID获取单条记录详情"""
    with get_db() as db:
        row = db.execute('''
            SELECT r.*, c.name as category_name, c.icon as category_icon, c.color as category_color
            FROM records r
            LEFT JOIN categories c ON r.category_id = c.id
            WHERE r.id = ?
        ''', (record_id,)).fetchone()

        if row:
            record = dict(row)
            record['tags'] = json.loads(record.get('tags', '[]'))
            record['extra_data'] = json.loads(record.get('extra_data', '{}'))
            return record
        return None


def update_record(record_id, data):
    """
    更新台账记录
    参数: record_id记录ID, data更新字段字典
    返回: 是否更新成功
    """
    with get_db() as db:
        # 构建动态UPDATE语句
        update_fields = []
        params = []
        field_map = {
            'title': 'title', 'category_id': 'category_id', 'status': 'status',
            'priority': 'priority', 'amount': 'amount', 'record_date': 'record_date',
            'due_date': 'due_date', 'description': 'description',
        }

        for field, column in field_map.items():
            if field in data:
                update_fields.append(f'{column} = ?')
                params.append(data[field])

        # tags和extra_data需要JSON序列化
        if 'tags' in data:
            update_fields.append('tags = ?')
            params.append(json.dumps(data['tags'], ensure_ascii=False))
        if 'extra_data' in data:
            update_fields.append('extra_data = ?')
            params.append(json.dumps(data['extra_data'], ensure_ascii=False))

        if not update_fields:
            return False

        # 自动更新updated_at时间戳
        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        params.append(record_id)

        sql = f'UPDATE records SET {", ".join(update_fields)} WHERE id = ?'
        cursor = db.execute(sql, params)

        # 记录操作日志
        db.execute(
            'INSERT INTO operation_logs (record_id, action, detail) VALUES (?, ?, ?)',
            (record_id, '更新', f'更新记录字段: {", ".join(data.keys())}')
        )
        return cursor.rowcount > 0


def delete_record(record_id):
    """
    删除台账记录（软删除提示后物理删除）
    返回: 是否删除成功
    """
    with get_db() as db:
        # 先获取记录标题用于日志
        row = db.execute('SELECT title FROM records WHERE id = ?', (record_id,)).fetchone()
        if not row:
            return False

        db.execute('DELETE FROM records WHERE id = ?', (record_id,))
        db.execute(
            'INSERT INTO operation_logs (record_id, action, detail) VALUES (?, ?, ?)',
            (record_id, '删除', f'删除记录: {row["title"]}')
        )
        return True


def get_stats():
    """
    获取仪表盘统计数据
    返回: 包含总数、分类统计、状态统计、金额统计等的字典
    """
    with get_db() as db:
        stats = {}

        # 记录总数
        stats['total_records'] = db.execute('SELECT COUNT(*) FROM records').fetchone()[0]

        # 各状态数量
        status_rows = db.execute(
            'SELECT status, COUNT(*) as count FROM records GROUP BY status'
        ).fetchall()
        stats['by_status'] = {row['status']: row['count'] for row in status_rows}

        # 各分类数量（含分类名和颜色）
        category_rows = db.execute('''
            SELECT c.name, c.icon, c.color, COUNT(r.id) as count
            FROM categories c
            LEFT JOIN records r ON c.id = r.category_id
            GROUP BY c.id
            ORDER BY c.sort_order
        ''').fetchall()
        stats['by_category'] = [dict(row) for row in category_rows]

        # 各优先级数量
        priority_rows = db.execute(
            'SELECT priority, COUNT(*) as count FROM records GROUP BY priority'
        ).fetchall()
        stats['by_priority'] = {row['priority']: row['count'] for row in priority_rows}

        # 金额统计
        amount_row = db.execute(
            'SELECT SUM(amount) as total, AVG(amount) as avg_amount FROM records WHERE amount > 0'
        ).fetchone()
        stats['total_amount'] = round(amount_row['total'] or 0, 2)
        stats['avg_amount'] = round(amount_row['avg_amount'] or 0, 2)

        # 今日新增
        today = datetime.now().strftime('%Y-%m-%d')
        stats['today_count'] = db.execute(
            'SELECT COUNT(*) FROM records WHERE DATE(created_at) = ?', (today,)
        ).fetchone()[0]

        # 本周新增
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        stats['week_count'] = db.execute(
            'SELECT COUNT(*) FROM records WHERE DATE(created_at) >= ?', (week_ago,)
        ).fetchone()[0]

        # 最近7天每日新增趋势
        trend_rows = db.execute('''
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM records
            WHERE DATE(created_at) >= DATE('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        ''').fetchall()
        stats['daily_trend'] = [dict(row) for row in trend_rows]

        # 最近10条操作日志
        log_rows = db.execute('''
            SELECT ol.*, r.title as record_title
            FROM operation_logs ol
            LEFT JOIN records r ON ol.record_id = r.id
            ORDER BY ol.created_at DESC
            LIMIT 10
        ''').fetchall()
        stats['recent_logs'] = [dict(row) for row in log_rows]

        return stats


# ============================================================
# 分类管理操作
# ============================================================

def get_categories():
    """获取所有分类（按排序字段升序）"""
    with get_db() as db:
        rows = db.execute(
            'SELECT * FROM categories ORDER BY sort_order, id'
        ).fetchall()
        return [dict(row) for row in rows]


def create_category(data):
    """新增分类"""
    with get_db() as db:
        cursor = db.execute(
            'INSERT INTO categories (name, icon, color, sort_order) VALUES (?, ?, ?, ?)',
            (data['name'], data.get('icon', '📁'), data.get('color', '#4A90D9'),
             data.get('sort_order', 0))
        )
        return cursor.lastrowid


def update_category(category_id, data):
    """更新分类"""
    with get_db() as db:
        fields = []
        params = []
        for key in ['name', 'icon', 'color', 'sort_order']:
            if key in data:
                fields.append(f'{key} = ?')
                params.append(data[key])
        if not fields:
            return False
        params.append(category_id)
        db.execute(f'UPDATE categories SET {", ".join(fields)} WHERE id = ?', params)
        return True


def delete_category(category_id):
    """
    删除分类
    注意：关联的记录的category_id会被置为NULL（外键ON DELETE SET NULL）
    """
    with get_db() as db:
        # 检查是否有记录使用此分类
        count = db.execute(
            'SELECT COUNT(*) FROM records WHERE category_id = ?', (category_id,)
        ).fetchone()[0]

        db.execute('DELETE FROM categories WHERE id = ?', (category_id,))
        return count  # 返回受影响的记录数，供前端提示


# ============================================================
# 系统设置操作
# ============================================================

def get_settings():
    """获取所有设置为字典"""
    with get_db() as db:
        rows = db.execute('SELECT key, value FROM settings').fetchall()
        return {row['key']: row['value'] for row in rows}


def update_settings(data):
    """批量更新设置"""
    with get_db() as db:
        for key, value in data.items():
            db.execute(
                'INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
                (key, str(value))
            )


def get_setting(key, default=None):
    """获取单个设置值"""
    with get_db() as db:
        row = db.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
        return row['value'] if row else default


# ============================================================
# 操作日志
# ============================================================

def get_operation_logs(page=1, per_page=50):
    """获取操作日志（分页）"""
    with get_db() as db:
        offset = (page - 1) * per_page
        total = db.execute('SELECT COUNT(*) FROM operation_logs').fetchone()[0]
        rows = db.execute('''
            SELECT ol.*, r.title as record_title
            FROM operation_logs ol
            LEFT JOIN records r ON ol.record_id = r.id
            ORDER BY ol.created_at DESC
            LIMIT ? OFFSET ?
        ''', (per_page, offset)).fetchall()
        return [dict(row) for row in rows], total


# ============================================================
# 数据库备份（自动 + 手动）
# ============================================================

BACKUP_DIR = os.environ.get('BACKUP_DIR', '/app/backups')
MAX_BACKUPS = 30  # 保留最近30份备份


def backup_database():
    """
    对SQLite数据库执行安全备份
    使用SQLite的.backup()方法，即使数据库正在写入也不会损坏
    返回: 备份文件路径
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f'ledger_{timestamp}.db')

    try:
        src_conn = sqlite3.connect(DB_PATH)
        dst_conn = sqlite3.connect(backup_file)
        src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()

        # 清理旧备份，只保留最新的MAX_BACKUPS份
        cleanup_old_backups()

        return backup_file
    except Exception as e:
        print(f'备份失败: {e}')
        return None


def cleanup_old_backups():
    """清理过期备份，保留最近MAX_BACKUPS份"""
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, 'ledger_*.db')))
    while len(backups) > MAX_BACKUPS:
        old = backups.pop(0)
        try:
            os.remove(old)
        except OSError:
            pass


def get_backup_list():
    """获取所有备份文件列表"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backups = []
    for f in sorted(glob.glob(os.path.join(BACKUP_DIR, 'ledger_*.db')), reverse=True):
        stat = os.stat(f)
        backups.append({
            'filename': os.path.basename(f),
            'size': round(stat.st_size / 1024, 1),  # KB
            'created': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        })
    return backups


def restore_database(backup_filename):
    """
    从备份恢复数据库
    恢复前会先备份当前数据库
    """
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    if not os.path.exists(backup_path):
        return False, '备份文件不存在'

    # 先备份当前状态
    backup_database()

    try:
        shutil.copy2(backup_path, DB_PATH)
        return True, '恢复成功'
    except Exception as e:
        return False, f'恢复失败: {e}'
