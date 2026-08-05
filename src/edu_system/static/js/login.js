// 登录页面专用 JavaScript

document.addEventListener('alpine:init', () => {
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
                    // Token 会通过 HttpOnly Cookie 自动存储
                    // 这里可以存储用户信息到 localStorage
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