// 课程管理系统 - 优化版主JavaScript文件

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化Bootstrap工具提示
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })
    
    // 初始化日期选择器（如果页面中有日期输入框）
    initDatePickers();
    
    // 初始化表单验证
    initFormValidation();
    
    // 初始化搜索框优化（替代DataTables）
    initSearchOptimization();
    
    // 为所有表单添加CSRF保护
    initCSRFProtection();
    
    // 初始化页面优化
    PageOptimizer.init();
});

// 初始化CSRF保护
function initCSRFProtection() {
    if (window.CSRFProtection) {
        // 为现有表单添加CSRF令牌
        const forms = document.querySelectorAll('form');
        forms.forEach(function(form) {
            // 跳过已有CSRF令牌的表单
            if (!form.querySelector('input[name="csrf_token"]')) {
                CSRFProtection.addToForm(form);
            }
        });
        
        // 为动态创建的表单添加CSRF保护
        document.addEventListener('submit', function(e) {
            const form = e.target;
            if (form.tagName === 'FORM' && !form.querySelector('input[name="csrf_token"]')) {
                if (!CSRFProtection.addToForm(form)) {
                    e.preventDefault();
                    alert('安全验证失败，请刷新页面重试');
                    return false;
                }
            }
        });
        
        console.log('✅ CSRF保护已为所有表单启用');
    }
}

// 初始化日期选择器
function initDatePickers() {
    // 查找所有带有date-picker类的输入框
    const datePickers = document.querySelectorAll('.date-picker');
    if (datePickers.length > 0) {
        datePickers.forEach(function(input) {
            // 这里可以添加日期选择器初始化代码
            // 如果使用第三方库如flatpickr或bootstrap-datepicker
        });
    }
}

// 初始化表单验证
function initFormValidation() {
    // 获取所有需要验证的表单
    const forms = document.querySelectorAll('.needs-validation');
    
    // 遍历表单并添加验证
    Array.from(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
}

// 初始化搜索框优化（替代DataTables）
function initSearchOptimization() {
    // 为所有搜索框添加回车提交优化
    const searchInputs = document.querySelectorAll('input[name="search"]');
    searchInputs.forEach(function(input) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                this.closest('form').submit();
            }
        });
    });
    
    // 为搜索表单添加防抖功能（可选）
    const searchForms = document.querySelectorAll('form:has(input[name="search"])');
    searchForms.forEach(function(form) {
        const searchInput = form.querySelector('input[name="search"]');
        if (searchInput) {
            let searchTimeout;
            
            // 添加实时搜索（可选，需要AJAX支持）
            searchInput.addEventListener('input', function() {
                clearTimeout(searchTimeout);
                const searchTerm = this.value;
                
                // 如果搜索词为空或长度小于2，不执行搜索
                if (searchTerm.length === 0 || searchTerm.length >= 2) {
                    searchTimeout = setTimeout(() => {
                        // 这里可以添加AJAX实时搜索功能
                        // 目前使用表单提交方式
                        if (searchTerm.length >= 2) {
                            // form.submit(); // 取消自动提交，避免频繁请求
                        }
                    }, 500); // 500ms 防抖
                }
            });
        }
    });
    
    console.log('✅ 搜索框优化已启用，DataTables已移除');
}

// 确认删除对话框
function confirmDelete(url, itemName) {
    if (confirm(`确定要删除${itemName || '此项'}吗？此操作不可恢复！`)) {
        // 创建一个表单来提交删除请求
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = url;
        document.body.appendChild(form);
        form.submit();
    }
    return false;
}

// 动态加载学生列表（用于课程安排和记录表单）
function loadStudents(gradeOrSubject, targetElementId) {
    const targetElement = document.getElementById(targetElementId);
    if (!targetElement) return;
    
    // 这里可以添加AJAX请求代码，根据年级或科目获取学生列表
    // 然后更新目标元素（如下拉框）的选项
}

// 带密码确认的删除对话框
function confirmDeleteWithPassword(url, itemName) {
    // 设置模态框中的确认信息和表单提交地址
    document.getElementById('confirmMessage').textContent = `确定要删除${itemName || '此项'}吗？此操作不可恢复！`;
    document.getElementById('passwordConfirmForm').action = url;
    
    // 显示模态框
    const modalElement = document.getElementById('passwordConfirmModal');
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
    
    return false;
}

// 页面性能优化功能
const PageOptimizer = {
    // 加载器状态管理
    _isLoaderVisible: false,
    
    // 显示全局加载器
    showLoader: function() {
        const loader = document.getElementById('globalLoader');
        if (loader) {
            loader.style.display = 'flex';
            this._isLoaderVisible = true;
            // 记录显示时间用于兜底超时判断
            this._lastShowTime = Date.now();
            console.log('🔄 加载器显示');
        }
    },
    
    // 隐藏全局加载器
    hideLoader: function() {
        const loader = document.getElementById('globalLoader');
        if (loader) {
            loader.style.display = 'none';
            this._isLoaderVisible = false;
            // 清理时间戳，避免误判为超时
            this._lastShowTime = undefined;
            console.log('✅ 加载器隐藏');
        }
    },
    
    // 页面切换优化
    optimizeNavigation: function() {
        // 重置加载器状态
        this.hideLoader();
        
        // 处理页面内导航点击
        const handleNavigationClick = (event) => {
            // 记录点击时间
            this._lastNavigationTime = Date.now();
            // 显示加载器
            this.showLoader();
            
            // 设置全局超时隐藏，确保无论如何都会隐藏
            setTimeout(() => {
                this.hideLoader();
            }, 3000);
        };
        
        // 为所有导航链接添加统一的事件处理
        document.querySelectorAll('a:not([href="#"]):not([data-bs-toggle]):not([data-toggle])').forEach(link => {
            // 排除外部链接
            const href = link.getAttribute('href');
            if (href && (href.startsWith('http://') || href.startsWith('https://'))) {
                return;
            }
            
            // 排除特定操作按钮
            if (link.classList.contains('btn') && 
                !link.classList.contains('nav-link') && 
                !link.classList.contains('dropdown-item')) {
                return;
            }
            
            // 排除下拉菜单项（避免干扰Bootstrap下拉功能）
            if (link.closest('.dropdown-menu')) {
                return;
            }
            
            // 添加统一的点击事件处理
            link.addEventListener('click', handleNavigationClick);
        });
        
        // 为所有GET表单添加统一的提交处理
        document.querySelectorAll('form[method="get"]').forEach(form => {
            form.addEventListener('submit', handleNavigationClick);
        });
        
        // 页面加载完成后隐藏加载器
        window.addEventListener('load', () => {
            setTimeout(() => {
                this.hideLoader();
            }, 300);
        });
        
        // 处理往返缓存（bfcache）恢复的情况，确保返回页不显示加载器
        window.addEventListener('pageshow', (event) => {
            if (event.persisted) {
                this.hideLoader();
            }
        });
        
        // 为DOMContentLoaded添加隐藏加载器的事件
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => {
                this.hideLoader();
            }, 500);
        });
        
        // 改进的URL变化检测 - 只在页面真正切换时处理
        let currentURL = window.location.href;
        let urlChangeDetected = false;
        
        const checkURLChange = () => {
            const newURL = window.location.href;
            if (newURL !== currentURL) {
                // 只有在页面真正切换时才处理（避免hash变化、参数变化等）
                const currentPath = new URL(currentURL).pathname;
                const newPath = new URL(newURL).pathname;
                
                // 只有当路径发生变化时才认为是真正的页面切换
                if (currentPath !== newPath && !urlChangeDetected && this._isLoaderVisible) {
                    urlChangeDetected = true;
                    currentURL = newURL;
                    console.log('🔄 页面切换完成，隐藏加载器');
                    this.hideLoader();
                    
                    // 重置检测状态
                    setTimeout(() => {
                        urlChangeDetected = false;
                    }, 1000);
                } else if (currentPath === newPath) {
                    // 只是参数变化，不认为是页面切换，更新当前URL但不隐藏加载器
                    currentURL = newURL;
                }
            }
        };
        
        // 降低检测频率，避免性能问题
        setInterval(checkURLChange, 500);
        
        // 添加基于页面内容加载状态的检测
        this._setupContentLoadDetection();
        
        // 添加全局的调试和紧急隐藏功能
        window.loaderDebug = {
            show: () => this.showLoader(),
            hide: () => this.hideLoader(),
            toggle: () => this._isLoaderVisible ? this.hideLoader() : this.showLoader(),
            status: () => this._isLoaderVisible
        };
        
        // 添加紧急隐藏函数的别名
        window.forceHideLoader = () => this.hideLoader();
        
        // 添加页面自动清理函数，确保加载器在任何情况下都会隐藏
        setInterval(() => {
            // 如果加载器已经显示超过5秒，强制隐藏
            if (this._isLoaderVisible) {
                const now = Date.now();
                if (!this._lastShowTime || now - this._lastShowTime > 5000) {
                    console.log('⏰ 加载器显示超时，强制隐藏');
                    this.hideLoader();
                }
            }
        }, 1000);
    },
    
    // 基于页面内容加载状态的检测
    _setupContentLoadDetection: function() {
        // 检测主内容区域是否已加载
        const checkContentLoaded = () => {
            const mainContent = document.querySelector('.container.mt-4');
            if (mainContent && mainContent.children.length > 0 && this._isLoaderVisible) {
                // 检查是否有实际内容（不仅仅是空容器）
                const hasRealContent = Array.from(mainContent.children).some(child => {
                    return child.textContent && child.textContent.trim().length > 10;
                });
                
                if (hasRealContent) {
                    // 主内容区域有实际内容且加载器正在显示，隐藏加载器
                    console.log('📄 页面内容已加载完成，隐藏加载器');
                    this.hideLoader();
                    return true;
                }
            }
            return false;
        };
        
        // 使用MutationObserver监听DOM变化
        const observer = new MutationObserver((mutations) => {
            mutations.forEach(mutation => {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    // 有新的DOM节点添加，检查内容是否已加载
                    setTimeout(checkContentLoaded, 50);
                }
            });
        });
        
        // 观察主内容区域
        const mainContent = document.querySelector('.container.mt-4');
        if (mainContent) {
            observer.observe(mainContent, {
                childList: true,
                subtree: true
            });
        }
        
        // 初始检查
        setTimeout(checkContentLoaded, 100);
        
        // 定期检查页面内容状态（备用机制）
        const contentCheckInterval = setInterval(() => {
            if (checkContentLoaded()) {
                // 如果内容已加载，停止检查
                clearInterval(contentCheckInterval);
                observer.disconnect();
            }
        }, 500);
        
        // 8秒后自动停止检查（防止无限循环）
        setTimeout(() => {
            clearInterval(contentCheckInterval);
            observer.disconnect();
            if (this._isLoaderVisible) {
                console.log('⚠️  内容加载检测超时，强制隐藏加载器');
                this.hideLoader();
            }
        }, 8000);
    },
    
    // 初始化所有优化
    init: function() {
        this.optimizeNavigation();
        console.log('✅ 页面性能优化已启用 - 加载器管理系统已重置');
    }
};