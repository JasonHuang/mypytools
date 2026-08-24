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
                
                // 存储文件列表，包含File对象引用
                targetInput.dataset.files = JSON.stringify(Array.from(files).map(f => ({
                    name: f.name,
                    size: f.size,
                    type: f.type,
                    lastModified: f.lastModified
                })));
                
                // 存储实际的File对象供后续使用
                targetInput.fileObjects = Array.from(files);
                
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
    const sourceInput = form.querySelector('input[readonly]');
    
    // 对于压缩功能，检查用户选择的模式
    if (formId === 'compressForm' && endpoint === '/api/compress_images') {
        const fileMode = document.getElementById('compressSingleFile').checked;
        const hasFileObjects = sourceInput && sourceInput.fileObjects && sourceInput.fileObjects.length > 0;
        
        addLog(`🔍 压缩模式: ${fileMode ? '单个文件' : '目录'}`, 'info');
        addLog(`🔍 文件对象存在: ${hasFileObjects}`, 'info');
        
        if (fileMode && hasFileObjects) {
            addLog(`📤 使用文件上传方式处理单个文件`, 'info');
            // 单个文件模式，使用文件上传方式
            submitFormWithFileUpload(form, endpoint, sourceInput.fileObjects);
        } else {
            addLog(`📋 使用JSON方式处理目录`, 'info');
            // 目录模式，使用JSON方式
            submitFormWithJSON(form, endpoint, sourceInput);
        }
    } else {
        // 其他功能保持原有逻辑
        const hasFileObjects = sourceInput && sourceInput.fileObjects && sourceInput.fileObjects.length > 0;
        
        if (hasFileObjects && endpoint === '/api/compress_images') {
            submitFormWithFileUpload(form, endpoint, sourceInput.fileObjects);
        } else {
            submitFormWithJSON(form, endpoint, sourceInput);
        }
    }
}

function submitFormWithFileUpload(form, endpoint, fileObjects) {
    const formData = new FormData();
    
    // 添加单个文件（修改为单文件上传）
    if (fileObjects && fileObjects.length > 0) {
        formData.append('file', fileObjects[0]);
    }
    
    // 添加其他表单数据
    const inputs = form.querySelectorAll('input:not([readonly]), select, textarea');
    inputs.forEach(input => {
        if (input.type === 'checkbox') {
            formData.append(input.name, input.checked);
        } else if (input.type !== 'file') {
            formData.append(input.name, input.value);
        }
    });
    
    // 禁用提交按钮并显示加载状态
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.classList.add('loading');
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 处理中...';
    
    addLog(`🚀 开始执行文件上传: ${endpoint}`, 'info');
    
    fetch(endpoint, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            addLog(`✅ ${data.message}`, 'success');
            
            // 如果有下载链接，显示下载按钮
            if (data.download_url) {
                showDownloadLink(data.download_url, data.filename, data.size);
            }
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

function submitFormWithJSON(form, endpoint, sourceInput) {
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    // 添加复选框状态
    const checkboxes = form.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        data[checkbox.name] = checkbox.checked;
    });
    
    // 添加文件数据
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
            if (data.download_url) {
                showDownloadLink(
                    data.download_url,
                    data.filename,
                    data.size,
                    '文件名收集完成',
                    'collectForm'
                );
            }
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
    const fileInput = document.getElementById('compressFile');
    const targetSizeInput = document.getElementById('targetSize');
    
    // 检查是否选择了文件
    if (!fileInput.files || fileInput.files.length === 0) {
        addLog('❌ 请先选择要压缩的图片文件', 'error');
        return;
    }
    
    const file = fileInput.files[0];
    const targetSize = parseFloat(targetSizeInput.value);
    
    addLog(`🗜️ 开始压缩图片: ${file.name}`, 'info');
    addLog(`📏 目标大小: ${targetSize} MB`, 'info');
    
    // 创建FormData
    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_size_mb', targetSize);
    
    // 显示加载状态
    const btn = document.querySelector('#compressForm .btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 压缩中...';
    btn.disabled = true;
    
    // 发送请求
    fetch('/api/compress_images', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            addLog('✅ ' + data.message, 'success');
            if (data.download_url) {
                showDownloadLink(data.download_url, data.filename, data.size);
            }
        } else {
            addLog('❌ ' + (data.error || data.message || '压缩失败'), 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        addLog('❌ 网络错误: ' + error.message, 'error');
    })
    .finally(() => {
        // 恢复按钮状态
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

// 格式转换功能
function convertImages() {
    const submitBtn = event.target;
    const originalText = submitBtn.innerHTML;
    const fileInput = document.getElementById('convertFile');

    if (!fileInput.files || fileInput.files.length === 0) {
        addLog('❌ 请先选择要转换的图片文件', 'error');
        return;
    }
    
    submitBtn.disabled = true;
    submitBtn.classList.add('loading');
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 转换中...';
    
    addLog('开始格式转换...', 'processing');
    
    const formData = new FormData();
    Array.from(fileInput.files).forEach(file => formData.append('files', file));
    formData.append('output_format', document.getElementById('targetFormat').value);
    formData.append('quality', document.getElementById('convertQuality').value);
    
    fetch('/api/convert_format', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            addLog(`✅ ${data.message}`, 'success');
            if (data.download_url) {
                showDownloadLink(
                    data.download_url,
                    data.filename,
                    data.size,
                    '格式转换完成',
                    'convertForm'
                );
            }
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
    
    // 初始化文件上传功能
    setupFileUpload();
    setupConvertFileUpload();
    
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

// 设置输出路径为源路径
function setOutputToSource(sourceInputId, outputInputId) {
    const sourceInput = document.getElementById(sourceInputId);
    const outputInput = document.getElementById(outputInputId);
    
    if (!sourceInput.value.trim()) {
        addLog('❌ 请先选择源路径', 'error');
        return;
    }
    
    outputInput.value = sourceInput.value;
    outputInput.style.borderColor = 'var(--success-color)';
    
    addLog(`📁 输出路径已设置为源路径: ${sourceInput.value}`, 'success');
}

// 更新文件大小显示
function updateSizeDisplay(value) {
    const display = document.getElementById('sizeDisplay');
    display.textContent = `${parseFloat(value).toFixed(1)} MB`;
}

// 文件上传处理
function setupFileUpload() {
    const fileInput = document.getElementById('compressFile');
    const uploadArea = document.querySelector('.file-upload-area');
    const uploadLabel = document.querySelector('.file-upload-label');
    
    // 文件选择事件
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            showSelectedFile(file);
        }
    });
    
    // 拖拽事件
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (file.type.startsWith('image/')) {
                fileInput.files = files;
                showSelectedFile(file);
            } else {
                addLog('❌ 请选择图片文件', 'error');
            }
        }
    });
}

function setupConvertFileUpload() {
    const fileInput = document.getElementById('convertFile');
    const uploadArea = document.getElementById('convertUploadArea');

    fileInput.addEventListener('change', function(e) {
        const files = Array.from(e.target.files);
        const existingInfo = uploadArea.querySelector('.file-selected');
        if (existingInfo) {
            existingInfo.remove();
        }
        if (files.length === 0) {
            return;
        }

        const totalSize = files.reduce((sum, file) => sum + file.size, 0);
        const fileInfo = document.createElement('div');
        fileInfo.className = 'file-selected';
        fileInfo.innerHTML = `
            <i class="fas fa-file-image"></i>
            <span>已选择 ${files.length} 个文件</span>
            <small>(${(totalSize / 1024 / 1024).toFixed(2)} MB)</small>
        `;
        uploadArea.appendChild(fileInfo);
        addLog(`📁 已选择 ${files.length} 个待转换文件`, 'info');
    });
}

// 显示选中的文件
function showSelectedFile(file) {
    const uploadArea = document.querySelector('.file-upload-area');
    
    // 移除之前的文件信息
    const existingInfo = uploadArea.querySelector('.file-selected');
    if (existingInfo) {
        existingInfo.remove();
    }
    
    // 创建文件信息显示
    const fileInfo = document.createElement('div');
    fileInfo.className = 'file-selected';
    fileInfo.innerHTML = `
        <i class="fas fa-file-image"></i>
        <span>${file.name}</span>
        <small>(${(file.size / 1024 / 1024).toFixed(2)} MB)</small>
    `;
    
    uploadArea.appendChild(fileInfo);
    addLog(`📁 已选择文件: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`, 'info');
}

// 显示下载链接
function showDownloadLink(downloadUrl, filename, size, title = '压缩完成', targetFormId = 'compressForm') {
    // 查找或创建下载区域
    const downloadAreaId = `downloadArea-${targetFormId}`;
    let downloadArea = document.getElementById(downloadAreaId);
    if (!downloadArea) {
        downloadArea = document.createElement('div');
        downloadArea.id = downloadAreaId;
        downloadArea.className = 'download-area';
        
        const targetForm = document.getElementById(targetFormId);
        targetForm.parentNode.insertBefore(downloadArea, targetForm.nextSibling);
    }
    
    downloadArea.innerHTML = `
        <div class="download-card">
            <div class="download-header">
                <i class="fas fa-download"></i>
                <h3>${title}</h3>
            </div>
            <div class="download-info">
                <p><strong>文件名:</strong> ${filename}</p>
                <p><strong>大小:</strong> ${size}</p>
            </div>
            <a href="${downloadUrl}" class="download-btn" download>
                <i class="fas fa-download"></i> 下载处理结果
            </a>
        </div>
    `;
    
    // 滚动到下载区域
    downloadArea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    addLog(`📥 文件已准备好下载: ${filename} (${size})`, 'success');
}

// 导出函数供全局使用
window.switchTab = switchTab;
window.selectDirectory = selectDirectory;
window.selectPath = selectPath;
window.submitForm = submitForm;
window.clearLogs = clearLogs;
window.collectFilenames = collectFilenames;
window.compressImages = compressImages;
window.convertImages = convertImages;
window.setOutputToSource = setOutputToSource;
window.updateSizeDisplay = updateSizeDisplay;
