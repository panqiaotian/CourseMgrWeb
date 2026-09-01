/**
 * CSRF保护工具函数
 */

// CSRF令牌管理
const CSRFProtection = {
    // 获取CSRF令牌
    getToken() {
        // 优先从meta标签获取
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            return metaToken.getAttribute('content');
        }
        
        // 从隐藏表单字段获取
        const hiddenToken = document.querySelector('input[name="csrf_token"]');
        if (hiddenToken) {
            return hiddenToken.value;
        }
        
        console.warn('⚠️ 未找到CSRF令牌');
        return null;
    },
    
    // 为fetch请求添加CSRF令牌
    addToFetch(options = {}) {
        const token = this.getToken();
        if (!token) {
            console.warn('⚠️ 无法获取CSRF令牌，请求可能失败');
            return options;
        }
        
        // 如果是FormData，添加CSRF字段
        if (options.body instanceof FormData) {
            options.body.append('csrf_token', token);
        } 
        // 如果是JSON，添加到headers
        else if (options.headers && options.headers['Content-Type'] === 'application/json') {
            options.headers['X-CSRFToken'] = token;
        }
        // 其他情况，添加到headers
        else {
            options.headers = options.headers || {};
            options.headers['X-CSRFToken'] = token;
        }
        
        return options;
    },
    
    // 为表单添加CSRF令牌
    addToForm(form) {
        const token = this.getToken();
        if (!token) {
            console.warn('⚠️ 无法获取CSRF令牌');
            return false;
        }
        
        // 检查是否已有CSRF字段
        let csrfField = form.querySelector('input[name="csrf_token"]');
        if (!csrfField) {
            csrfField = document.createElement('input');
            csrfField.type = 'hidden';
            csrfField.name = 'csrf_token';
            form.appendChild(csrfField);
        }
        
        csrfField.value = token;
        return true;
    },
    
    // 安全的fetch包装器
    safeFetch(url, options = {}) {
        // 自动添加CSRF令牌
        const safeOptions = this.addToFetch(options);
        
        return fetch(url, safeOptions)
            .catch(error => {
                if (error.message.includes('403') || error.message.includes('400')) {
                    console.error('❌ CSRF验证失败，可能是令牌过期');
                    // 可以在这里添加令牌刷新逻辑
                }
                throw error;
            });
    }
};

// 全局暴露
window.CSRFProtection = CSRFProtection;

// 页面加载时验证CSRF令牌
document.addEventListener('DOMContentLoaded', function() {
    const token = CSRFProtection.getToken();
    if (token) {
        console.log('✅ CSRF保护已启用');
    } else {
        console.warn('⚠️ CSRF令牌未找到，保护可能未生效');
    }
});