// 全局变量
let logs = [];

// Tab 切换功能
function switchTab(tabName) {
    // 隐藏所有 tab 内容
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    
    // 移除所有 tab 按钮的激活状态
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // 显示选中的 tab 内容
    document.getElementById(tabName).classList.add('active');
    
    // 激活对应的 tab 按钮
    event.target.classList.add('active');
    
    addLog(`📋 切换到: ${getTabDisplayName(tabName)}`, 'info');
}

// 获取 Tab 显示名称
function getTabDisplayName(tabName) {
    const names = {
        'collect': '文件名收集',
        'compress': '图片压缩',
        'convert': '格式转换'
    };
    return names[tabName] || tabName;
}

// 文件选择功能
function selectDirectory(inputId) {
    const input = document.createElement('input');
    input.type = 'file';
    input.webkitdirectory = true;
    input.directory = true;
    input.multiple = true;
    
    input.onchange = function(e) {
        const files = e.target.files;
        if (files.length > 0) {
            // 获取第一个文件的路径，提取目录部分
            const firstFile = files[0];
            const pathParts = firstFile.webkitRelativePath.split('/');
            const directoryName = pathParts[0];
            
            const targetInput = document.getElementById(inputId);
            targetInput.value = directoryName;
            targetInput.style.borderColor = 'var(--success-color)';
            
            // 存储文件列表供后续使用
            targetInput.dataset.files = JSON.stringify(Array.from(files).map(f => ({
                name: f.name,
                path: f.webkitRelativePath,
                size: f.size,
                type: f.type
            })));
            
            addLog(`📁 已选择目录: ${directoryName} (包含 ${files.length} 个文件)`, 'success');
        }
    };
    
    input.click();
}

function selectPath(inputId) {
    // 创建一个隐藏的选择器，支持文件和目录
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.multiple = true;
    fileInput.accept = 'image/*,.heic,.HEIC';
    
    const dirInput = document.createElement('input');
    dirInput.type = 'file';
    dirInput.webkitdirectory = true;
    dirInput.multiple = true;
    
    // 询问用户选择类型
    const choice = confirm('选择文件请点击"确定"，选择目录请点击"取消"');
    
    if (choice) {
        // 选择文件
        fileInput.onchange = function(e) {
            const files = e.target.files;
            if (files.length > 0) {
                const targetInput = document.getElementById(inputId);
                if (files.length === 1) {
                    targetInput.value = files[0].name;
                } else {
                    targetInput.value = `已选择 ${files.length} 个文件`;
                }
                targetInput.style.borderColor = 'var(--success-color)';
                
                // 存储文件列表
                targetInput.dataset.files = JSON.stringify(Array.from(files).map(f => ({
                    name: f.name,
                    size: f.size,
                    type: f.type
                })));
                
                addLog(`📄 已选择 ${files.length} 个文件`, 'success');
            }
        };
        fileInput.click();
    } else {
        // 选择目录
        dirInput.onchange = function(e) {
            const files = e.target.files;
            if (files.length > 0) {
                const firstFile = files[0];
                const pathParts = firstFile.webkitRelativePath.split('/');
                const directoryName = pathParts[0];
                
                const targetInput = document.getElementById(inputId);
                targetInput.value = directoryName;
                targetInput.style.borderColor = 'var(--success-color)';
                
                // 存储文件列表
                targetInput.dataset.files = JSON.stringify(Array.from(files).map(f => ({
                    name: f.name,
                    path: f.webkitRelativePath,
                    size: f.size,
                    type: f.type
                })));
                
                addLog(`📁 已选择目录: ${directoryName} (包含 ${files.length} 个文件)`, 'success');
            }
        };
        dirInput.click();
    }
}

// 表单提交处理
function submitForm(formId, endpoint) {
    const form = document.getElementById(formId);
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    // 添加复选框状态
    const checkboxes = form.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        data[checkbox.name] = checkbox.checked;
    });
    
    // 添加文件数据
    const sourceInput = form.querySelector('input[readonly]');
    if (sourceInput && sourceInput.dataset.files) {
        try {
            data.files_data = JSON.parse(sourceInput.dataset.files);
        } catch (e) {
            addLog('❌ 文件数据解析失败', 'error');
            return;
        }
    }
    
    // 禁用提交按钮并显示加载状态
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.classList.add('loading');
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 处理中...';
    
    addLog(`🚀 开始执行: ${endpoint}`, 'info');
    
    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            addLog(`✅ ${data.message}`, 'success');
        } else {
            addLog(`❌ ${data.message || data.error}`, 'error');
        }
    })
    .catch(error => {
        addLog(`❌ 网络错误: ${error.message}`, 'error');
    })
    .finally(() => {
        // 恢复按钮状态
        submitBtn.disabled = false;
        submitBtn.classList.remove('loading');
        submitBtn.innerHTML = originalText;
    });
}

// 日志管理
function addLog(message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = {
        message,
        type,
        timestamp
    };
    
    logs.push(logEntry);
    
    // 限制日志条数
    if (logs.length > 100) {
        logs = logs.slice(-100);
    }
    
    updateLogDisplay();
}

function updateLogDisplay() {
    const logsContent = document.getElementById('logsContent');
    
    // 获取图标
    const getIcon = (type) => {
        const icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️',
            'processing': '⚙️'
        };
        return icons[type] || 'ℹ️';
    };
    
    // 生成日志HTML
    const logsHtml = logs.map(log => `
        <div class="log-entry ${log.type}">
            <span class="status-indicator ${log.type}"></span>
            ${getIcon(log.type)} [${log.timestamp}] ${log.message}
        </div>
    `).join('');
    
    logsContent.innerHTML = logsHtml;
    
    // 自动滚动到底部
    logsContent.scrollTop = logsContent.scrollHeight;
}

function clearLogs() {
    logs = [];
    updateLogDisplay();
    addLog('🧹 日志已清除', 'info');
    addLog('💡 提示: 使用 Ctrl/Cmd + L 快速清除日志', 'info');
}

// 表单验证
function validateInput(input) {
    const value = input.value.trim();
    if (value) {
        input.style.borderColor = 'var(--success-color)';
    } else {
        input.style.borderColor = '#e5e7eb';
    }
}

// 文件名收集功能
function collectFilenames() {
    const submitBtn = event.target;
    const originalText = submitBtn.innerHTML;
    
    submitBtn.disabled = true;
    submitBtn.classList.add('loading');
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 收集中...';
    
    addLog('开始文件名收集...', 'processing');
    
    const collectDirInput = document.getElementById('collectDir');
    const formData = {
        directory: collectDirInput.value,
        include_subdirs: document.getElementById('includeSubdirs').checked,
        remove_extension: document.getElementById('removeExtension').checked,
        output_path: prompt('请输入输出文件路径:', 'filenames.txt') || 'filenames.txt'
    };
    
    // 添加文件数据
    if (collectDirInput.dataset.files) {
        try {
            formData.files_data = JSON.parse(collectDirInput.dataset.files);
        } catch (e) {
            addLog('❌ 文件数据解析失败', 'error');
            submitBtn.classList.remove('loading');
            submitBtn.disabled = false;
            return;
        }
    }
    
    fetch('/api/collect_filenames', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            addLog(`✅ ${data.message}`, 'success');
        } else {
            addLog(`❌ ${data.error || data.message}`, 'error');
        }
    })
    .catch(error => {
        addLog(`❌ 网络错误: ${error.message}`, 'error');
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.classList.remove('loading');
        submitBtn.innerHTML = originalText;
    });
}

// 图片压缩功能
function compressImages() {
    const submitBtn = event.target;
    const originalText = submitBtn.innerHTML;
    
    submitBtn.disabled = true;
    submitBtn.classList.add('loading');
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 压缩中...';
    
    addLog('开始图片压缩...', 'processing');
    
    const compressDirInput = document.getElementById('compressDir');
    const formData = {
        source_path: compressDirInput.value,
        output_path: document.getElementById('compressOutput').value,
        quality: parseInt(document.getElementById('quality').value),
        max_width: parseInt(document.getElementById('maxWidth').value) || null,
        max_height: parseInt(document.getElementById('maxHeight').value) || null
    };
    
    // 添加文件数据
    if (compressDirInput.dataset.files) {
        try {
            formData.files_data = JSON.parse(compressDirInput.dataset.files);
        } catch (e) {
            addLog('❌ 文件数据解析失败', 'error');
            submitBtn.classList.remove('loading');
            submitBtn.disabled = false;
            return;
        }
    }
    
    fetch('/api/compress_images', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            addLog(`✅ ${data.message}`, 'success');
        } else {
            addLog(`❌ ${data.error || data.message}`, 'error');
        }
    })
    .catch(error => {
        addLog(`❌ 网络错误: ${error.message}`, 'error');
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.classList.remove('loading');
        submitBtn.innerHTML = originalText;
    });
}

// 格式转换功能
function convertImages() {
    const submitBtn = event.target;
    const originalText = submitBtn.innerHTML;
    
    submitBtn.disabled = true;
    submitBtn.classList.add('loading');
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 转换中...';
    
    addLog('开始格式转换...', 'processing');
    
    const convertDirInput = document.getElementById('convertDir');
    const formData = {
        source_path: convertDirInput.value,
        output_path: document.getElementById('convertOutput').value,
        target_format: document.getElementById('targetFormat').value,
        quality: parseInt(document.getElementById('convertQuality').value)
    };
    
    // 添加文件数据
    if (convertDirInput.dataset.files) {
        try {
            formData.files_data = JSON.parse(convertDirInput.dataset.files);
        } catch (e) {
            addLog('❌ 文件数据解析失败', 'error');
            submitBtn.classList.remove('loading');
            submitBtn.disabled = false;
            return;
        }
    }
    
    fetch('/api/convert_images', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            addLog(`✅ ${data.message}`, 'success');
        } else {
            addLog(`❌ ${data.error || data.message}`, 'error');
        }
    })
    .catch(error => {
        addLog(`❌ 网络错误: ${error.message}`, 'error');
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.classList.remove('loading');
        submitBtn.innerHTML = originalText;
    });
}

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', function() {
    // 显示欢迎信息
    addLog('🎉 欢迎使用图片处理工具！', 'success');
    addLog('💡 请选择功能标签页开始使用', 'info');
    addLog('📁 点击"选择"按钮可以选择文件或目录', 'info');
    
    // 为所有输入框添加验证
    document.querySelectorAll('input[type="text"], input[type="number"]').forEach(input => {
        input.addEventListener('input', function() {
            validateInput(this);
        });
    });
    
    // 键盘快捷键
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + L 清除日志
        if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
            e.preventDefault();
            clearLogs();
        }
    });
    
    // 默认激活第一个标签页
    document.querySelector('.tab-btn').click();
});

// 导出函数供全局使用
window.switchTab = switchTab;
window.selectDirectory = selectDirectory;
window.selectPath = selectPath;
window.submitForm = submitForm;
window.clearLogs = clearLogs;
window.collectFilenames = collectFilenames;
window.compressImages = compressImages;
window.convertImages = convertImages;