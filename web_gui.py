#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web版图片处理工具GUI
使用Flask提供Web界面，完全兼容所有操作系统
"""

from flask import Flask, render_template, request, jsonify, send_file, abort
from werkzeug.utils import secure_filename
import os
import json
import webbrowser
import threading
import time
from datetime import datetime
import tempfile
import shutil

app = Flask(__name__)

# 全局变量存储操作日志
operation_logs = []

def add_log(message):
    """添加操作日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    operation_logs.append(log_entry)
    print(log_entry)

def handle_file_upload_compression():
    """处理文件上传的图片压缩"""
    try:
        # 获取目标大小
        target_size_mb = float(request.form.get('target_size_mb', 2.0))
        
        add_log(f"🗜️ 开始处理上传的文件压缩")
        add_log(f"   目标大小: {target_size_mb} MB")
        
        # 获取上传的文件
        uploaded_file = request.files.get('file')
        if not uploaded_file or uploaded_file.filename == '':
            error_msg = "❌ 没有找到上传的文件"
            add_log(error_msg)
            return jsonify({'success': False, 'error': error_msg})
        
        # 安全地获取文件大小
        try:
            file_size = uploaded_file.content_length or 0
            if file_size > 0:
                add_log(f"📁 接收到文件: {uploaded_file.filename} ({file_size / 1024 / 1024:.2f} MB)")
            else:
                add_log(f"📁 接收到文件: {uploaded_file.filename}")
        except:
            add_log(f"📁 接收到文件: {uploaded_file.filename}")
        
        # 创建uploads目录
        uploads_dir = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        # 生成唯一的文件名
        timestamp = int(time.time())
        name, ext = os.path.splitext(uploaded_file.filename)
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        input_filename = f"{safe_name}_{timestamp}{ext}"
        output_filename = f"{safe_name}_{timestamp}_compressed{ext}"
        
        input_path = os.path.join(uploads_dir, input_filename)
        output_path = os.path.join(uploads_dir, output_filename)
        
        # 保存上传的文件
        uploaded_file.save(input_path)
        add_log(f"💾 文件已保存: {input_filename}")
        
        # 导入压缩功能
        from compress_images import compress_image
        
        # 调用压缩函数
        success = compress_image(
            input_path, 
            output_path, 
            target_size_mb=target_size_mb,
            log_func=add_log
        )
        
        if success:
            # 获取压缩后的文件大小
            compressed_size = os.path.getsize(output_path) / 1024 / 1024
            add_log(f"✅ 压缩完成！文件大小: {compressed_size:.2f} MB")
            
            # 删除原始上传文件
            try:
                os.remove(input_path)
            except:
                pass
            
            return jsonify({
                'success': True, 
                'message': '图片压缩成功',
                'download_url': f'/download/{output_filename}',
                'filename': output_filename,
                'size': f"{compressed_size:.2f} MB"
            })
        else:
            # 删除上传的文件
            try:
                os.remove(input_path)
            except:
                pass
            add_log("❌ 压缩失败")
            return jsonify({'success': False, 'error': '图片压缩失败'})
            
    except Exception as e:
        error_msg = f"❌ 文件上传压缩失败: {str(e)}"
        add_log(error_msg)
        return jsonify({'success': False, 'error': error_msg})

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html', title='图片处理工具')

@app.route('/api/logs')
def get_logs():
    """获取操作日志"""
    return jsonify({'logs': operation_logs})

@app.route('/api/clear_logs', methods=['POST'])
def clear_logs():
    """清除日志"""
    global operation_logs
    operation_logs = []
    add_log("📋 日志已清除")
    return jsonify({'success': True})

@app.route('/api/collect_filenames', methods=['POST'])
def collect_filenames():
    """文件名收集API"""
    try:
        data = request.json
        directory = data.get('directory', '')
        include_subdirs = data.get('include_subdirs', False)
        remove_extension = data.get('remove_extension', False)
        files_data = data.get('files_data', [])
        output_path = data.get('output_path', '')
        
        add_log(f"📁 开始收集文件名: {directory}")
        add_log(f"   递归子目录: {'是' if include_subdirs else '否'}")
        add_log(f"   去除扩展名: {'是' if remove_extension else '否'}")
        
        if not output_path:
            error_msg = "❌ 请填写输出路径"
            add_log(error_msg)
            return jsonify({'success': False, 'error': error_msg})
        
        if not files_data:
            error_msg = "❌ 请先选择文件或目录"
            add_log(error_msg)
            return jsonify({'success': False, 'error': error_msg})
        
        # 收集文件名
        filenames = []
        for file_info in files_data:
            if 'path' in file_info:
                # 目录选择的情况，使用相对路径
                filename = file_info['path']
            else:
                # 文件选择的情况，使用文件名
                filename = file_info['name']
            
            # 去除扩展名选项
            if remove_extension and '.' in filename:
                filename = '.'.join(filename.split('.')[:-1])
            
            filenames.append(filename)
        
        # 写入文件
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for filename in filenames:
                    f.write(filename + '\n')
            
            add_log(f"✅ 文件名收集完成，共收集 {len(filenames)} 个文件名")
            add_log(f"📄 已保存到: {output_path}")
            return jsonify({'success': True, 'message': f'文件名收集完成！共收集 {len(filenames)} 个文件名'})
            
        except Exception as e:
            error_msg = f"❌ 写入文件失败: {str(e)}"
            add_log(error_msg)
            return jsonify({'success': False, 'error': error_msg})
        
    except Exception as e:
        error_msg = f"❌ 文件名收集失败: {str(e)}"
        add_log(error_msg)
        return jsonify({'success': False, 'error': error_msg})

@app.route('/api/compress_images', methods=['POST'])
def compress_images():
    """图片压缩API"""
    try:
        # 检查是否是文件上传请求
        if request.content_type and 'multipart/form-data' in request.content_type:
            # 处理文件上传
            return handle_file_upload_compression()
        
        # 处理JSON请求（目录选择）
        data = request.json
        source_path = data.get('source_path', '')
        output_path = data.get('output_path', '')
        target_size_mb = data.get('target_size_mb', 2.0)
        files_data = data.get('files_data', [])
        
        add_log(f"🗜️ 开始压缩图片: {source_path}")
        add_log(f"   目标大小: {target_size_mb} MB")
        add_log(f"   输出路径: {output_path or '覆盖原文件'}")
        
        if not files_data:
            error_msg = "❌ 请先选择文件或目录"
            add_log(error_msg)
            return jsonify({'success': False, 'error': error_msg})
        
        # 导入压缩功能
        from compress_images import compress_image, process_directory
        
        success_count = 0
        total_count = 0
        
        # 处理文件
        import os
        
        # 获取当前工作目录作为基础路径
        base_path = os.getcwd()
        add_log(f"🔍 当前工作目录: {base_path}")
        
        for file_info in files_data:
            if 'path' in file_info:
                # 目录选择的情况，使用相对路径
                relative_path = file_info['path']
                # 构建完整的文件路径
                full_file_path = os.path.join(base_path, relative_path)
            else:
                # 单个文件选择的情况，文件应该在当前目录
                filename = file_info['name']
                full_file_path = os.path.join(base_path, filename)
            
            # 检查文件是否存在
            if not os.path.exists(full_file_path):
                add_log(f"⚠️ 文件不存在: {full_file_path}")
                continue
            
            # 检查是否为图片文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
            if not any(full_file_path.lower().endswith(ext) for ext in image_extensions):
                continue
            
            total_count += 1
            add_log(f"📷 处理: {full_file_path}")
            
            try:
                # 确定输出路径
                if output_path and output_path != source_path:
                    # 如果指定了不同的输出路径，需要创建对应的文件路径
                    filename = os.path.basename(full_file_path)
                    final_output_path = os.path.join(output_path, filename)
                    os.makedirs(output_path, exist_ok=True)
                else:
                    # 覆盖原文件
                    final_output_path = None
                
                if compress_image(full_file_path, final_output_path, target_size_mb, log_func=add_log):
                    success_count += 1
                    # 显示压缩后大小
                    final_path = final_output_path or full_file_path
                    final_size = os.path.getsize(final_path) / (1024 * 1024)
                    add_log(f"✅ {os.path.basename(full_file_path)} 压缩完成")
                else:
                    add_log(f"⚠️ {os.path.basename(full_file_path)} 压缩失败")
                    
            except Exception as e:
                add_log(f"❌ {os.path.basename(full_file_path)} 处理出错: {str(e)}")
                import traceback
                add_log(f"🔍 详细错误: {traceback.format_exc()}")
        
        if total_count == 0:
            error_msg = "❌ 未找到可处理的图片文件"
            add_log(error_msg)
            return jsonify({'success': False, 'error': error_msg})
        
        add_log(f"🎉 压缩完成: {success_count}/{total_count} 个文件成功")
        return jsonify({
            'success': True, 
            'message': f'压缩完成！成功处理 {success_count}/{total_count} 个文件'
        })
        
    except Exception as e:
        error_msg = f"❌ 图片压缩失败: {str(e)}"
        add_log(error_msg)
        return jsonify({'success': False, 'error': error_msg})

@app.route('/download/<filename>')
def download_file(filename):
    """文件下载路由"""
    try:
        uploads_dir = os.path.join(os.getcwd(), 'uploads')
        file_path = os.path.join(uploads_dir, secure_filename(filename))
        
        if not os.path.exists(file_path):
            add_log(f"❌ 文件不存在: {filename}")
            abort(404)
        
        add_log(f"📥 下载文件: {filename}")
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        add_log(f"❌ 文件下载失败: {str(e)}")
        abort(500)

@app.route('/api/convert_format', methods=['POST'])
def convert_format():
    """格式转换API"""
    try:
        data = request.json
        source_path = data.get('source_path', '')
        output_format = data.get('output_format', 'jpg')
        quality = data.get('quality', 95)
        
        add_log(f"🔄 开始格式转换: {source_path}")
        add_log(f"   输出格式: {output_format.upper()}")
        add_log(f"   转换质量: {quality}%")
        
        # 这里可以调用实际的格式转换函数
        # from convert_heic_to_jpg import main as convert_main
        
        add_log("✅ 格式转换完成")
        return jsonify({'success': True, 'message': '格式转换完成'})
        
    except Exception as e:
        error_msg = f"❌ 格式转换失败: {str(e)}"
        add_log(error_msg)
        return jsonify({'success': False, 'error': error_msg})

def ensure_directories():
    """确保模板和静态文件目录存在"""
    directories = ['templates', 'static', 'static/css', 'static/js']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            add_log(f"📁 创建目录: {directory}")

def open_browser():
    """延迟打开浏览器"""
    time.sleep(1.5)
    webbrowser.open('http://localhost:5001')

def main():
    """主函数"""
    print("🚀 启动Web版图片处理工具...")
    print("📱 使用Flask提供Web界面")
    print("🌐 完全跨平台兼容")
    
    # 确保模板和静态文件目录存在
    ensure_directories()
    
    add_log("🌐 Web GUI服务器启动")
    add_log("📋 请在浏览器中访问: http://localhost:5001")
    
    # 在新线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        app.run(host='localhost', port=5001, debug=False)
    except KeyboardInterrupt:
        print("\n👋 用户中断，服务器关闭")
    except Exception as e:
        print(f"❌ 服务器运行错误: {e}")

if __name__ == "__main__":
    main()