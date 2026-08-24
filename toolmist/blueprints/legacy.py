#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 1 compatibility routes for the existing image tools."""

from datetime import datetime, timedelta
import os
import uuid
import zipfile

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    request,
    send_from_directory,
    url_for,
)
from PIL import Image
import pillow_heif
from werkzeug.utils import secure_filename


pillow_heif.register_heif_opener()

bp = Blueprint("legacy", __name__)

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"
}

def add_log(message):
    """Write a concise compatibility-operation log to stdout."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry, flush=True)


def json_error(message, status=400):
    add_log(f"❌ {message}")
    return jsonify({"success": False, "error": message}), status


def clean_filename(filename, fallback="image"):
    """生成不包含路径信息的安全文件名。"""
    filename = secure_filename(filename or "")
    return filename or fallback


def upload_folder():
    return current_app.config["UPLOAD_FOLDER"]


def cleanup_expired_files():
    """清理超出保留时长的处理结果，避免容器磁盘无限增长。"""
    retention_hours = current_app.config["FILE_RETENTION_HOURS"]
    if retention_hours <= 0:
        return

    cutoff = datetime.now() - timedelta(hours=retention_hours)
    for path in upload_folder().iterdir():
        try:
            if path.name.startswith("."):
                continue
            if path.is_file() and datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
                path.unlink()
        except OSError as exc:
            add_log(f"⚠️ 临时文件清理失败: {type(exc).__name__}")


def download_payload(stored_name, download_name, message):
    """构造统一的前端下载响应。"""
    file_path = upload_folder() / stored_name
    size_mb = file_path.stat().st_size / 1024 / 1024
    return jsonify({
        "success": True,
        "message": message,
        "download_url": url_for(
            "legacy.download_file", filename=stored_name, name=download_name
        ),
        "filename": download_name,
        "size": f"{size_mb:.2f} MB",
    })


def handle_file_upload_compression():
    """处理上传的单张图片并生成 JPEG 压缩结果。"""
    input_path = None
    output_path = None
    keep_output = False
    try:
        target_size_mb = float(request.form.get("target_size_mb", 2.0))
        if not 0.1 <= target_size_mb <= 50:
            return json_error("目标大小必须在 0.1 MB 到 50 MB 之间")

        uploaded_file = request.files.get("file")
        if not uploaded_file or not uploaded_file.filename:
            return json_error("没有找到上传的文件")

        safe_filename = clean_filename(uploaded_file.filename)
        stem, extension = os.path.splitext(safe_filename)
        if extension.lower() not in ALLOWED_IMAGE_EXTENSIONS:
            return json_error("不支持该图片格式")

        cleanup_expired_files()
        job_id = uuid.uuid4().hex[:12]
        artifact_folder = upload_folder()
        input_path = artifact_folder / f"{job_id}_source{extension.lower()}"
        output_name = f"{stem}_compressed.jpg"
        stored_output_name = f"{job_id}_{output_name}"
        output_path = artifact_folder / stored_output_name

        uploaded_file.save(input_path)
        add_log(f"🗜️ 正在压缩 1 张图片，目标大小 {target_size_mb} MB")

        from compress_images import compress_image

        success = compress_image(
            str(input_path),
            str(output_path),
            target_size_mb=target_size_mb,
            log_func=add_log,
        )
        if not success:
            return json_error("图片压缩失败，请尝试调大目标大小", 422)

        add_log("✅ 图片压缩完成")
        keep_output = True
        return download_payload(stored_output_name, output_name, "图片压缩成功")
    except (TypeError, ValueError):
        return json_error("目标大小格式不正确")
    except Exception as exc:
        add_log(f"❌ 图片压缩失败: {type(exc).__name__}")
        return json_error("图片压缩失败，请稍后重试", 422)
    finally:
        if input_path:
            input_path.unlink(missing_ok=True)
        if output_path and not keep_output:
            output_path.unlink(missing_ok=True)


@bp.post("/api/collect_filenames")
def collect_filenames():
    """把浏览器提供的文件名列表生成文本文件供下载。"""
    try:
        data = request.get_json(silent=True) or {}
        include_subdirs = bool(data.get("include_subdirs", False))
        remove_extension = bool(data.get("remove_extension", False))
        files_data = data.get("files_data") or []
        requested_name = clean_filename(data.get("output_path"), "filenames.txt")
        if not requested_name.lower().endswith(".txt"):
            requested_name += ".txt"

        if not files_data:
            return json_error("请先选择文件或目录")

        filenames = []
        for file_info in files_data:
            filename = str(file_info.get("path") or file_info.get("name") or "")
            if not filename:
                continue
            normalized = filename.replace("\\", "/")
            if not include_subdirs and normalized.count("/") > 1:
                continue
            if remove_extension:
                filename = os.path.splitext(filename)[0]
            filenames.append(filename)

        if not filenames:
            return json_error("没有找到符合条件的文件")

        cleanup_expired_files()
        stored_name = f"{uuid.uuid4().hex[:12]}_{requested_name}"
        output_path = upload_folder() / stored_name
        output_path.write_text("\n".join(filenames) + "\n", encoding="utf-8")

        add_log(f"✅ 文件名收集完成，共 {len(filenames)} 个")
        return download_payload(
            stored_name,
            requested_name,
            f"文件名收集完成！共收集 {len(filenames)} 个文件名",
        )
    except Exception as exc:
        add_log(f"❌ 文件名收集失败: {type(exc).__name__}")
        return json_error("文件名收集失败，请稍后重试", 422)


@bp.post("/api/compress_images")
def compress_images():
    """远程部署仅接受真实文件上传，不接受服务器路径。"""
    if not request.mimetype or request.mimetype != "multipart/form-data":
        return json_error("请通过文件上传方式提交图片")
    return handle_file_upload_compression()


@bp.get("/download/<path:filename>")
def download_file(filename):
    safe_stored_name = clean_filename(filename, "")
    artifact_folder = upload_folder()
    file_path = artifact_folder / safe_stored_name
    if not safe_stored_name or not file_path.is_file():
        abort(404)

    requested_download_name = clean_filename(request.args.get("name"), safe_stored_name)
    add_log("📥 下载临时结果")
    return send_from_directory(
        artifact_folder,
        safe_stored_name,
        as_attachment=True,
        download_name=requested_download_name,
        max_age=0,
    )


def prepare_converted_image(image, output_format):
    """按目标格式处理色彩模式，避免透明图片转 JPEG 时报错。"""
    if output_format == "jpg":
        if image.mode in ("RGBA", "LA") or (
            image.mode == "P" and "transparency" in image.info
        ):
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.getchannel("A"))
            return background
        return image.convert("RGB")
    if output_format in {"png", "webp"} and image.mode not in ("RGB", "RGBA"):
        return image.convert("RGBA" if "transparency" in image.info else "RGB")
    return image.copy()


@bp.post("/api/convert_format")
def convert_format():
    """转换一张或多张上传图片；多张结果打包为 ZIP。"""
    input_paths = []
    output_paths = []
    try:
        uploaded_files = [item for item in request.files.getlist("files") if item.filename]
        if not uploaded_files:
            return json_error("请先选择要转换的图片")

        output_format = request.form.get("output_format", "jpg").lower()
        if output_format == "jpeg":
            output_format = "jpg"
        if output_format not in {"jpg", "png", "webp"}:
            return json_error("目标格式仅支持 JPG、PNG 和 WebP")

        quality = int(request.form.get("quality", 95))
        if not 1 <= quality <= 100:
            return json_error("转换质量必须在 1 到 100 之间")

        cleanup_expired_files()
        job_id = uuid.uuid4().hex[:12]
        archive_entries = []
        artifact_folder = upload_folder()

        for index, uploaded_file in enumerate(uploaded_files, start=1):
            safe_filename = clean_filename(uploaded_file.filename)
            stem, extension = os.path.splitext(safe_filename)
            if extension.lower() not in ALLOWED_IMAGE_EXTENSIONS:
                return json_error("上传内容包含不支持的图片格式")

            input_path = artifact_folder / f"{job_id}_{index}_source{extension.lower()}"
            output_name = f"{stem}.{output_format}"
            stored_output_name = f"{job_id}_{index}_{output_name}"
            output_path = artifact_folder / stored_output_name
            input_paths.append(input_path)
            output_paths.append(output_path)
            uploaded_file.save(input_path)

            with Image.open(input_path) as source_image:
                converted = prepare_converted_image(source_image, output_format)
                try:
                    save_options = {}
                    if output_format in {"jpg", "webp"}:
                        save_options["quality"] = quality
                    if output_format == "jpg":
                        save_options["optimize"] = True
                    pillow_format = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP"}[
                        output_format
                    ]
                    converted.save(output_path, format=pillow_format, **save_options)
                finally:
                    converted.close()

            archive_entries.append((output_path, output_name))
            add_log(f"✅ 已完成第 {index} 张图片的格式转换")

        if len(archive_entries) == 1:
            output_path, output_name = archive_entries[0]
            output_paths.remove(output_path)
            return download_payload(output_path.name, output_name, "格式转换完成")

        archive_name = "converted_images.zip"
        stored_archive_name = f"{job_id}_{archive_name}"
        archive_path = artifact_folder / stored_archive_name
        output_paths.append(archive_path)
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            used_names = set()
            for index, (output_path, output_name) in enumerate(archive_entries, start=1):
                archive_entry_name = output_name
                if archive_entry_name in used_names:
                    stem, extension = os.path.splitext(output_name)
                    archive_entry_name = f"{stem}_{index}{extension}"
                used_names.add(archive_entry_name)
                archive.write(output_path, arcname=archive_entry_name)

        add_log(f"✅ 已打包 {len(archive_entries)} 张转换后的图片")
        output_paths.remove(archive_path)
        return download_payload(stored_archive_name, archive_name, "格式转换完成")
    except (TypeError, ValueError):
        return json_error("转换质量格式不正确")
    except Exception as exc:
        add_log(f"❌ 格式转换失败: {type(exc).__name__}")
        return json_error("格式转换失败，请稍后重试", 422)
    finally:
        for path in input_paths + output_paths:
            path.unlink(missing_ok=True)
