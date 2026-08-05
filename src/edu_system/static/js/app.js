// 基础 JavaScript 功能

// 全局应用状态
window.App = {
    // 当前用户信息
    user: null,
    // 当前学期
    semester: null,
    // 服务状态
    services: {},
    // 主题
    theme: 'light',
    // 侧边栏状态
    sidebarOpen: false,
    
    // 初始化
    init() {
        this.loadUser();
        this.loadSemester();
        this.loadServices();
        this.initTheme();
        this.initKeyboardShortcuts();
        this.initCommandPalette();
    },
    
    // 加载用户信息
    async loadUser() {
        try {
            const resp = await fetch('/api/auth/me', {
                credentials: 'include'
            });
            if (resp.ok) {
                this.user = await resp.json();
                this.updateUserUI();
            }
        } catch (e) {
            console.warn('Failed to load user:', e);
        }
    },
    
    // 更新用户界面
    updateUserUI() {
        const userEl = document.getElementById('user-menu');
        if (userEl && this.user) {
            userEl.innerHTML = `
                <div class="flex items-center gap-2">
                    <span class="text-sm font-medium">${this.user.username}</span>
                    <span class="px-2 py-0.5 text-xs bg-primary-100 dark:bg-primary-900/30 text-primary-800 dark:text-primary-300 rounded">${this.user.role_name || this.user.role}</span>
                </div>
            `;
        }
    },
    
    // 加载当前学期
    async loadSemester() {
        try {
            const resp = await fetch('/api/meta/semester/active', {
                credentials: 'include'
            });
            if (resp.ok) {
                this.semester = await resp.json();
                this.updateSemesterUI();
            }
        } catch (e) {
            console.warn('Failed to load semester:', e);
        }
    },
    
    // 更新学期 UI
    updateSemesterUI() {
        const semesterEl = document.getElementById('current-semester');
        if (semesterEl && this.semester) {
            semesterEl.textContent = this.semester.label || this.semester.name;
            semesterEl.classList.remove('hidden');
        }
    },
    
    // 加载服务状态
    async loadServices() {
        try {
            const resp = await fetch('/api/services', {
                credentials: 'include'
            });
            if (resp.ok) {
                this.services = await resp.json();
                this.updateServicesUI();
            }
        } catch (e) {
            console.warn('Failed to load services:', e);
        }
    },
    
    updateServicesUI() {
        // 更新服务状态指示器
        const container = document.getElementById('services-status');
        if (container && this.services) {
            container.innerHTML = Object.entries(this.services).map(([key, service]) => `
                <span class="flex items-center gap-1 px-2 py-1 text-xs rounded-full ${
                    service.enabled 
                        ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' 
                        : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                }">
                    ${service.name}: ${service.enabled ? '运行中' : '已停用'}
                </span>
            `).join('');
        }
    },
    
    // 初始化主题
    initTheme() {
        const saved = localStorage.getItem('theme');
        if (saved) {
            this.theme = saved;
        } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            this.theme = 'dark';
        }
        this.applyTheme();
        
        // 监听系统主题变化
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('theme')) {
                this.theme = e.matches ? 'dark' : 'light';
                this.applyTheme();
            }
        });
    },
    
    applyTheme() {
        document.documentElement.classList.toggle('dark', this.theme === 'dark');
        localStorage.setItem('theme', this.theme);
        
        // 更新主题切换按钮
        const btn = document.getElementById('theme-toggle');
        if (btn) {
            btn.innerHTML = this.theme === 'dark' 
                ? '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M17.657 17.657l.707.707M4 12a8 8 0 018-8v1a8 8 0 01-8 8z"/></svg>'
                : '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9 9 0 008.354-5.646z"/></svg>';
            btn.setAttribute('aria-label', this.theme === 'dark' ? '切换到浅色模式' : '切换到深色模式');
        }
    },
    
    toggleTheme() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        this.applyTheme();
    },
    
    // 侧边栏切换
    toggleSidebar() {
        this.sidebarOpen = !this.sidebarOpen;
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('main-content');
        if (sidebar) {
            sidebar.classList.toggle('collapsed');
        }
        if (mainContent) {
            mainContent.classList.toggle('sidebar-collapsed');
        }
        localStorage.setItem('sidebarOpen', this.sidebarOpen);
    },
    
    // 键盘快捷键
    initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Cmd/Ctrl + K: 命令面板
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                this.openCommandPalette();
            }
            // Escape: 关闭模态框/侧边栏
            if (e.key === 'Escape') {
                this.sidebarOpen = false;
                this.closeModals();
            }
            // Cmd/Ctrl + /: 搜索
            if ((e.metaKey || e.ctrlKey) && e.key === '/') {
                e.preventDefault();
                this.focusSearch();
            }
        });
    },
    
    openCommandPalette() {
        this.$dispatch('open-command-palette');
    },
    
    closeModals() {
        this.$dispatch('close-modals');
    },
    
    focusSearch() {
        const searchInput = document.querySelector('[data-search-input]');
        if (searchInput) {
            searchInput.focus();
        }
    },
    
    // 权限检查
    hasPermission(perm) {
        return this.user?.permissions?.includes(perm) ?? false;
    },
    
    // 格式化工具
    formatDate(dateStr) {
        if (!dateStr) return '';
        return new Date(dateStr).toLocaleDateString('zh-CN');
    },
    
    formatDateTime(dateStr) {
        if (!dateStr) return '';
        return new Date(dateStr).toLocaleString('zh-CN');
    },
    
    // 通知
    notify(message, type = 'info', duration = 3000) {
        const container = document.getElementById('toast-container') || this.createToastContainer();
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content flex-1">
                <div class="toast-title font-medium text-sm">${type === 'error' ? '错误' : type === 'success' ? '成功' : type === 'warning' ? '警告' : '提示'}</div>
                <div class="toast-message text-sm text-gray-600 dark:text-gray-300 mt-0.5">${message}</div>
            </div>
            <button class="toast-close ml-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors" onclick="this.parentElement.remove()">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
        `;
        
        container.appendChild(toast);
        
        // 自动移除
        setTimeout(() => {
            toast.classList.add('exiting');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },
    
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.App.init();
});

// 全局错误处理
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
    window.App?.notify(e.error?.message || '发生未知错误', 'error');
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled rejection:', e.reason);
    window.App?.notify(e.reason?.message || '发生未知错误', 'error');
});

// Alpine.js 全局存储
document.addEventListener('alpine:init', () => {
    Alpine.store('error', null);
    Alpine.store('theme', 'light');
    Alpine.store('sidebarOpen', false);
});