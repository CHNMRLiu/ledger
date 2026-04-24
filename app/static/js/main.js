/**
 * 飞牛NAS台账系统 - 前端交互逻辑
 * 全局工具函数、Toast通知、确认对话框、侧边栏控制
 */

// ============================================================
// 初始化
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    initSidebar();
});

// ============================================================
// 侧边栏控制
// ============================================================

function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebarToggle');
    const mobileBtn = document.getElementById('mobileMenuBtn');

    // 桌面端：折叠/展开侧边栏
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            // 保存状态到localStorage
            localStorage.setItem('sidebar_collapsed', sidebar.classList.contains('collapsed'));
        });

        // 恢复上次状态
        if (localStorage.getItem('sidebar_collapsed') === 'true') {
            sidebar.classList.add('collapsed');
        }
    }

    // 移动端：汉堡菜单切换
    if (mobileBtn) {
        mobileBtn.addEventListener('click', function() {
            sidebar.classList.toggle('mobile-open');
        });

        // 点击主内容区关闭移动端菜单
        document.getElementById('mainContent').addEventListener('click', function() {
            sidebar.classList.remove('mobile-open');
        });
    }
}

// ============================================================
// Toast 通知系统
// ============================================================

/**
 * 显示Toast通知
 * @param {string} message - 通知内容
 * @param {string} type - 类型：success/error/info/warning
 * @param {number} duration - 显示时长（毫秒），默认3000
 */
function showToast(message, type, duration) {
    type = type || 'info';
    duration = duration || 3000;

    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    // 图标映射
    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️',
        warning: '⚠️'
    };

    toast.innerHTML = `<span>${icons[type] || ''}</span><span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    // 自动消失
    setTimeout(function() {
        toast.style.animation = 'toastOut 0.3s ease forwards';
        setTimeout(function() {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, duration);
}

// ============================================================
// 确认对话框
// ============================================================

let confirmCallback = null;

/**
 * 显示确认对话框
 * @param {string} title - 对话框标题
 * @param {string} message - 确认信息
 * @param {Function} onConfirm - 确认后的回调函数
 */
function showConfirm(title, message, onConfirm) {
    document.getElementById('confirmTitle').textContent = title;
    document.getElementById('confirmMessage').textContent = message;
    confirmCallback = onConfirm;
    document.getElementById('confirmModal').style.display = 'flex';
}

function closeConfirm() {
    document.getElementById('confirmModal').style.display = 'none';
    confirmCallback = null;
}

function doConfirm() {
    if (typeof confirmCallback === 'function') {
        confirmCallback();
    }
    closeConfirm();
}

// ESC键关闭模态框
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeConfirm();
        // 同时关闭其他可能打开的模态框
        const editModal = document.getElementById('editModal');
        if (editModal) editModal.style.display = 'none';
    }
});

// ============================================================
// 工具函数
// ============================================================

/**
 * HTML转义（防XSS）
 */
function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/**
 * 格式化日期时间
 */
function formatDateTime(dateStr) {
    if (!dateStr) return '-';
    var d = new Date(dateStr);
    var year = d.getFullYear();
    var month = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    var hour = String(d.getHours()).padStart(2, '0');
    var min = String(d.getMinutes()).padStart(2, '0');
    return year + '-' + month + '-' + day + ' ' + hour + ':' + min;
}

/**
 * 格式化金额
 */
function formatAmount(amount) {
    if (!amount || amount <= 0) return '-';
    return '¥' + parseFloat(amount).toFixed(2);
}

/**
 * 防抖函数
 */
function debounce(func, wait) {
    var timeout;
    return function() {
        var context = this;
        var args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(function() {
            func.apply(context, args);
        }, wait);
    };
}

/**
 * 发送API请求的通用封装
 * @param {string} url - 请求地址
 * @param {string} method - 请求方法
 * @param {Object} data - 请求数据（POST/PUT时使用）
 * @returns {Promise}
 */
function apiRequest(url, method, data) {
    var options = {
        method: method || 'GET',
        headers: {
            'Content-Type': 'application/json',
        }
    };

    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }

    return fetch(url, options)
        .then(function(response) {
            return response.json();
        })
        .then(function(result) {
            if (!result.success) {
                throw new Error(result.error || '操作失败');
            }
            return result;
        });
}

/**
 * 复制文本到剪贴板
 */
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            showToast('已复制到剪贴板', 'success');
        });
    } else {
        // 降级方案
        var textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('已复制到剪贴板', 'success');
    }
}
