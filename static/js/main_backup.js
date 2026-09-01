// 课程管理系统 - 主JavaScript文件

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
    
    // 初始化数据表格（如果页面中有表格）
    initDataTables();
    
    // 为所有表单添加CSRF保护
    initCSRFProtection();
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

// 初始化数据表格
function initDataTables() {
    // 查找所有带有data-table类的表格
    const tables = document.querySelectorAll('.data-table');
    if (tables.length > 0) {
        tables.forEach(function(table) {
            // 检查是否已经初始化过DataTables
            if ($.fn.DataTable && $.fn.DataTable.isDataTable(table)) {
                console.log('⚠️ 表格已初始化，跳过:', table.id || 'unnamed table');
                return;
            }
            
            // 使用jQuery初始化DataTables
            if ($.fn.DataTable) {
                try {
                    $(table).DataTable({
                    // 分页设置
                    "pageLength": 10,  // 默认每页显示10条
                    "lengthMenu": [[10, 25, 50, 100, -1], [10, 25, 50, 100, "全部"]],
                    "paging": true,
                    "pagingType": "full_numbers",
                    
                    // 搜索和排序
                    "searching": true,
                    "ordering": true,
                    "order": [[0, 'desc']],
                    
                    // 性能优化
                    "deferRender": true,  // 延迟渲染，提高大数据集性能
                    "processing": true,   // 显示处理状态
                    
                    // 响应式设计
                    "responsive": true,
                    "autoWidth": false,
                    
                    // 中文语言包
                    language: {
                        "processing": "处理中...",
                        "lengthMenu": "显示 _MENU_ 项结果",
                        "zeroRecords": "没有匹配结果",
                        "info": "显示第 _START_ 至 _END_ 项结果，共 _TOTAL_ 项",
                        "infoEmpty": "显示第 0 至 0 项结果，共 0 项",
                        "infoFiltered": "(由 _MAX_ 项结果过滤)",
                        "search": "搜索:",
                        "emptyTable": "表中数据为空",
                        "loadingRecords": "载入中...",
                        "paginate": {
                            "first": "首页",
                            "previous": "上页",
                            "next": "下页",
                            "last": "末页"
                        },
                        "aria": {
                            "sortAscending": ": 以升序排列此列",
                            "sortDescending": ": 以降序排列此列"
                        }
                    }
                });
                console.log('✅ DataTable 初始化成功:', table.id || 'unnamed table');
                } catch (error) {
                    console.error('❌ DataTable 初始化失败:', error);
                }
            }
        });
    }
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
// 页面性能优化
功能
const PageOptimizer = {
    // 显示全局加载器
    showLoader: function() {
        const loader = document.getElementById('globalLoader');
        if (loader) {
            loader.style.display = 'flex';
        }
    },
    
    // 隐藏全局加载器
    hideLoader: function() {
        const loader = document.getElementById('globalLoader');
        if (loader) {
            loader.style.display = 'none';
        }
    },
    
    // 页面切换优化
    optimizeNavigation: function() {
        // 为所有导航链接添加加载状态
        const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                // 如果是当前页面，不需要加载
                if (this.classList.contains('active')) {
                    return;
                }
                
                // 显示加载器
                PageOptimizer.showLoader();
                
                // 设置超时，防止加载器一直显示
                setTimeout(() => {
                    PageOptimizer.hideLoader();
                }, 10000); // 10秒超时
            });
        });
        
        // 页面加载完成后隐藏加载器
        window.addEventListener('load', () => {
            PageOptimizer.hideLoader();
            
            // 添加页面切换动画
            document.body.classList.add('page-transition', 'loaded');
        });
    },
    
    // 优化DataTables性能
    optimizeDataTables: function() {
        // 直接调用已存在的initDataTables函数，避免重复定义
        if (typeof window.initDataTables === 'function') {
            console.log('✅ 使用现有的 initDataTables 函数');
        } else {
            console.log('⚠️ initDataTables 函数未找到');
        }
    },
    
    // 初始化所有优化
    init: function() {
        this.optimizeNavigation();
        
        // 延迟初始化DataTables，避免阻塞页面渲染
        setTimeout(() => {
            this.optimizeDataTables();
        }, 100);
        
        console.log('✅ 页面性能优化已启用');
    }
};

// 页面加载完成后初始化优化
document.addEventListener('DOMContentLoaded', function() {
    PageOptimizer.init();
});

// 预加载关键页面（可选）
const PreloadManager = {
    preloadedPages: new Set(),
    
    preloadPage: function(url) {
        if (this.preloadedPages.has(url)) {
            return;
        }
        
        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = url;
        document.head.appendChild(link);
        
        this.preloadedPages.add(url);
        console.log('🔄 预加载页面:', url);
    },
    
    init: function() {
        // 预加载常用页面
        const commonPages = [
            '/students',
            '/schedules', 
            '/records'
        ];
        
        // 延迟预加载，避免影响当前页面
        setTimeout(() => {
            commonPages.forEach(page => this.preloadPage(page));
        }, 2000);
    }
};

// 启用预加载（可选功能）
// PreloadManager.init();