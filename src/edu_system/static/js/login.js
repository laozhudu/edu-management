// 登录页面专用 JavaScript

document.addEventListener('alpine:init', () => {
    // 全局错误存储
    Alpine.store('error', null);
    
    // 监听全局错误事件
    window.addEventListener('notify', (e) => {
        Alpine.store('error', e.detail.message);
    });

    // 认证头辅助函数（供全局使用）
    window.authHeaders = function() {
        const token = localStorage.getItem('access_token');
        return token ? { 'Authorization': 'Bearer ' + token } : {};
    };

    Alpine.data('loginForm', () => ({
        form: {
            username: '',
            password: '',
            remember: false,
            auto_login: false
        },
        loading: false,
        error: null,
        
        async handleLogin(e) {
            e.preventDefault();
            this.error = null;
            this.loading = true;
            
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include',
                    body: JSON.stringify(this.form)
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.detail || '登录失败');
                }
                
                // 登录成功，保存 token
                if (data.access_token) {
                    // Token 存 localStorage（页面 fetch 时通过 Authorization header 携带）
                    localStorage.setItem('access_token', data.access_token);
                    if (data.user) {
                        localStorage.setItem('user', JSON.stringify(data.user));
                    }
                }
                
                // 登录成功，跳转到主页
                window.location.href = '/';
                
            } catch (error) {
                this.error = error.message;
            } finally {
                this.loading = false;
            }
        },
        
        // 处理回车键
        handleKeyDown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleLogin(new Event('submit'));
            }
        }
    }));
    
    // 全局错误处理
    window.addEventListener('error', (e) => {
        console.error('Login page error:', e.error);
    });
    
    window.addEventListener('unhandledrejection', (e) => {
        console.error('Unhandled rejection:', e.reason);
    });
});