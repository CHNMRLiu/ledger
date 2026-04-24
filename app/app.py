# -*- coding: utf-8 -*-
"""
飞牛NAS台账系统 - Flask主程序
轻量级Web应用，适配飞牛NAS Docker环境
支持热更新：代码修改后自动重载
"""

import os
import json
import subprocess
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
import models

# ============================================================
# 应用初始化
# ============================================================

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 支持中文JSON响应
app.config['JSON_SORT_KEYS'] = False  # 保持字段顺序

# 初始化数据库（首次运行自动建表+默认数据）
models.init_db()


# ============================================================
# 页面路由 - 服务端渲染
# ============================================================

@app.route('/')
def index():
    """首页重定向到仪表盘"""
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    """仪表盘页面 - 数据概览与统计"""
    stats = models.get_stats()
    settings = models.get_settings()
    return render_template('dashboard.html',
                           stats=stats,
                           settings=settings,
                           page_title='仪表盘')


@app.route('/records')
def records_page():
    """台账记录列表页面"""
    categories = models.get_categories()
    settings = models.get_settings()
    return render_template('records.html',
                           categories=categories,
                           settings=settings,
                           page_title='台账记录')


@app.route('/records/new')
def record_new():
    """新增台账记录页面"""
    categories = models.get_categories()
    return render_template('record_form.html',
                           categories=categories,
                           record=None,
                           page_title='新增记录')


@app.route('/records/<int:record_id>/edit')
def record_edit(record_id):
    """编辑台账记录页面"""
    record = models.get_record_by_id(record_id)
    if not record:
        return redirect(url_for('records_page'))
    categories = models.get_categories()
    return render_template('record_form.html',
                           categories=categories,
                           record=record,
                           page_title='编辑记录')


@app.route('/categories')
def categories_page():
    """分类管理页面"""
    categories = models.get_categories()
    return render_template('categories.html',
                           categories=categories,
                           page_title='分类管理')


@app.route('/settings')
def settings_page():
    """系统设置页面"""
    settings = models.get_settings()
    return render_template('settings.html',
                           settings=settings,
                           page_title='系统设置')


# ============================================================
# RESTful API - 台账记录
# ============================================================

@app.route('/api/records', methods=['GET'])
def api_get_records():
    """
    获取台账记录列表
    查询参数:
        page: 页码（默认1）
        per_page: 每页数量（默认20）
        category_id: 分类ID筛选
        status: 状态筛选
        priority: 优先级筛选
        search: 搜索关键词
        sort_by: 排序字段
        sort_order: 排序方向（asc/desc）
        date_from: 开始日期
        date_to: 结束日期
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = min(per_page, 100)  # 限制最大每页数量

        records, total = models.get_records(
            page=page,
            per_page=per_page,
            category_id=request.args.get('category_id', type=int),
            status=request.args.get('status'),
            priority=request.args.get('priority'),
            search=request.args.get('search'),
            sort_by=request.args.get('sort_by', 'created_at'),
            sort_order=request.args.get('sort_order', 'desc'),
            date_from=request.args.get('date_from'),
            date_to=request.args.get('date_to'),
        )

        return jsonify({
            'success': True,
            'data': records,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/records', methods=['POST'])
def api_create_record():
    """新增台账记录"""
    try:
        data = request.get_json()
        if not data or not data.get('title'):
            return jsonify({'success': False, 'error': '标题不能为空'}), 400

        record_id = models.create_record(data)
        record = models.get_record_by_id(record_id)
        return jsonify({'success': True, 'data': record}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/records/<int:record_id>', methods=['GET'])
def api_get_record(record_id):
    """获取单条记录详情"""
    record = models.get_record_by_id(record_id)
    if not record:
        return jsonify({'success': False, 'error': '记录不存在'}), 404
    return jsonify({'success': True, 'data': record})


@app.route('/api/records/<int:record_id>', methods=['PUT'])
def api_update_record(record_id):
    """更新台账记录"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        success = models.update_record(record_id, data)
        if not success:
            return jsonify({'success': False, 'error': '记录不存在或无更新'}), 404

        record = models.get_record_by_id(record_id)
        return jsonify({'success': True, 'data': record})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/records/<int:record_id>', methods=['DELETE'])
def api_delete_record(record_id):
    """删除台账记录"""
    try:
        success = models.delete_record(record_id)
        if not success:
            return jsonify({'success': False, 'error': '记录不存在'}), 404
        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/records/stats', methods=['GET'])
def api_get_stats():
    """获取统计数据（仪表盘用）"""
    try:
        stats = models.get_stats()
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# RESTful API - 分类管理
# ============================================================

@app.route('/api/categories', methods=['GET'])
def api_get_categories():
    """获取所有分类"""
    categories = models.get_categories()
    return jsonify({'success': True, 'data': categories})


@app.route('/api/categories', methods=['POST'])
def api_create_category():
    """新增分类"""
    try:
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({'success': False, 'error': '分类名称不能为空'}), 400

        category_id = models.create_category(data)
        return jsonify({'success': True, 'data': {'id': category_id}}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/categories/<int:category_id>', methods=['PUT'])
def api_update_category(category_id):
    """更新分类"""
    try:
        data = request.get_json()
        success = models.update_category(category_id, data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
def api_delete_category(category_id):
    """删除分类"""
    try:
        affected = models.delete_category(category_id)
        msg = f'分类已删除，{affected}条记录的分类已置空' if affected > 0 else '分类已删除'
        return jsonify({'success': True, 'message': msg})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# RESTful API - 系统设置
# ============================================================

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """获取系统设置"""
    settings = models.get_settings()
    return jsonify({'success': True, 'data': settings})


@app.route('/api/settings', methods=['PUT'])
def api_update_settings():
    """更新系统设置"""
    try:
        data = request.get_json()
        models.update_settings(data)
        return jsonify({'success': True, 'message': '设置已保存'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# RESTful API - 操作日志
# ============================================================

@app.route('/api/logs', methods=['GET'])
def api_get_logs():
    """获取操作日志"""
    try:
        page = request.args.get('page', 1, type=int)
        logs, total = models.get_operation_logs(page=page)
        return jsonify({
            'success': True,
            'data': logs,
            'pagination': {'page': page, 'total': total}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# RESTful API - GitHub同步
# ============================================================

@app.route('/api/sync', methods=['POST'])
def api_trigger_sync():
    """手动触发GitHub同步"""
    try:
        result = subprocess.run(
            ['/app/sync.sh', '--now'],
            capture_output=True, text=True, timeout=60
        )
        return jsonify({
            'success': True,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else None
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': '同步超时（60秒）'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sync/status', methods=['GET'])
def api_sync_status():
    """获取同步状态"""
    settings = models.get_settings()
    return jsonify({
        'success': True,
        'data': {
            'enabled': settings.get('auto_sync_enabled', 'false'),
            'interval': settings.get('auto_sync_interval', '3600'),
            'github_repo': settings.get('github_repo', ''),
            'last_sync': settings.get('last_sync_time', ''),
        }
    })


# ============================================================
# 工具路由
# ============================================================

@app.route('/api/export', methods=['GET'])
def api_export_data():
    """导出全部数据为JSON"""
    try:
        records, _ = models.get_records(per_page=99999)
        categories = models.get_categories()
        settings = models.get_settings()

        export = {
            'export_time': datetime.now().isoformat(),
            'version': '1.0.0',
            'records': records,
            'categories': categories,
            'settings': settings,
        }

        response = app.response_class(
            response=json.dumps(export, ensure_ascii=False, indent=2),
            status=200,
            mimetype='application/json'
        )
        response.headers['Content-Disposition'] = 'attachment; filename=ledger_export.json'
        return response
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/import', methods=['POST'])
def api_import_data():
    """导入JSON数据"""
    try:
        data = request.get_json()
        if not data or 'records' not in data:
            return jsonify({'success': False, 'error': '无效的导入数据'}), 400

        imported = 0
        for record in data['records']:
            try:
                # 移除id字段，让数据库自动生成新ID
                record_data = {k: v for k, v in record.items()
                               if k not in ('id', 'created_at', 'updated_at',
                                           'category_name', 'category_icon', 'category_color')}
                models.create_record(record_data)
                imported += 1
            except Exception:
                continue

        return jsonify({
            'success': True,
            'message': f'成功导入 {imported}/{len(data["records"])} 条记录'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health')
def health_check():
    """健康检查端点（Docker健康检测用）"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


# ============================================================
# 数据备份 API
# ============================================================

@app.route('/api/backup', methods=['POST'])
def api_backup():
    """手动触发数据库备份"""
    try:
        backup_file = models.backup_database()
        if backup_file:
            return jsonify({'success': True, 'message': '备份成功', 'file': backup_file})
        return jsonify({'success': False, 'error': '备份失败'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/backups', methods=['GET'])
def api_list_backups():
    """获取备份列表"""
    try:
        backups = models.get_backup_list()
        return jsonify({'success': True, 'data': backups})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/backup/restore', methods=['POST'])
def api_restore_backup():
    """从备份恢复数据库"""
    try:
        data = request.get_json()
        filename = data.get('filename', '')
        if not filename:
            return jsonify({'success': False, 'error': '未指定备份文件'}), 400

        success, msg = models.restore_database(filename)
        if success:
            return jsonify({'success': True, 'message': msg})
        return jsonify({'success': False, 'error': msg}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# 自动定时备份（每6小时）
# ============================================================

def auto_backup_worker():
    """后台自动备份线程：每6小时执行一次"""
    import time
    while True:
        time.sleep(6 * 3600)  # 6小时
        try:
            backup_file = models.backup_database()
            if backup_file:
                print(f'[自动备份] 完成: {backup_file}')
        except Exception as e:
            print(f'[自动备份] 失败: {e}')


# 启动自动备份线程
backup_thread = threading.Thread(target=auto_backup_worker, daemon=True)
backup_thread.start()


# ============================================================
# 错误处理
# ============================================================

@app.errorhandler(404)
def not_found(e):
    """404错误处理"""
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': '接口不存在'}), 404
    return render_template('base.html', page_title='页面不存在',
                           content='<div class="empty-state"><h2>404</h2><p>页面不存在</p></div>'), 404


@app.errorhandler(500)
def server_error(e):
    """500错误处理"""
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500
    return '服务器错误', 500


# ============================================================
# 模板全局变量
# ============================================================

@app.context_processor
def inject_globals():
    """注入全局模板变量"""
    return {
        'app_name': models.get_setting('app_name', '飞牛台账系统'),
        'now': datetime.now(),
        'version': '1.0.0',
    }


# ============================================================
# 启动入口
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'

    print(f'🐄 飞牛台账系统启动中...')
    print(f'📡 监听地址: http://0.0.0.0:{port}')
    print(f'🔄 热更新: {"开启" if debug else "关闭"}')
    print(f'💾 数据库: {models.DB_PATH}')

    # Flask内置热更新：代码修改后自动重载
    # templates/ 和 static/ 的修改也会触发重载
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        use_reloader=debug,
        use_debugger=debug,
    )
