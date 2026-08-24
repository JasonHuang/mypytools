"""Safe image validation and transformations shared by public tools."""

from dataclasses import dataclass
import io
import math
from pathlib import Path
import re
import warnings

from PIL import Image, UnidentifiedImageError
import pillow_heif

from ..errors import ApiError


pillow_heif.register_heif_opener()

EXTENSION_FORMATS = {
    ".jpg": {"JPEG"},
    ".jpeg": {"JPEG"},
    ".png": {"PNG"},
    ".webp": {"WEBP"},
    ".bmp": {"BMP"},
    ".tif": {"TIFF"},
    ".tiff": {"TIFF"},
    ".heic": {"HEIF", "HEIC"},
    ".heif": {"HEIF", "HEIC"},
}
CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


@dataclass(frozen=True)
class ValidatedImage:
    path: Path
    original_name: str
    size: int
    width: int
    height: int
    pixels: int
    image_format: str


def public_filename(filename, fallback="image"):
    name = Path((filename or "").replace("\\", "/")).name
    name = CONTROL_CHARACTERS.sub("", name).strip().strip(".")
    name = name or fallback
    suffix = Path(name).suffix[:16]
    stem_limit = max(1, 160 - len(suffix))
    stem = name[:-len(suffix)] if suffix else name
    return f"{stem[:stem_limit]}{suffix}"


def upload_extension(filename):
    extension = Path(public_filename(filename)).suffix.lower()
    if extension not in EXTENSION_FORMATS:
        raise ApiError(
            "UNSUPPORTED_IMAGE_TYPE",
            "仅支持 JPG、PNG、WebP、BMP、TIFF、HEIC 和 HEIF 图片",
        )
    return extension


def save_and_validate_upload(upload, destination, max_pixels):
    original_name = public_filename(upload.filename)
    extension = upload_extension(original_name)
    destination = Path(destination)
    upload.save(destination)
    size = destination.stat().st_size
    if size == 0:
        raise ApiError("EMPTY_FILE", "上传的图片是空文件")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(destination) as image:
                width, height = image.size
                pixels = width * height
                image_format = (image.format or "").upper()
                if pixels > max_pixels:
                    raise ApiError(
                        "IMAGE_TOO_LARGE",
                        "图片像素超过当前工具允许的范围",
                        413,
                    )
                if image_format not in EXTENSION_FORMATS[extension]:
                    raise ApiError(
                        "IMAGE_TYPE_MISMATCH",
                        "文件扩展名与实际图片格式不一致",
                    )
                image.load()
    except ApiError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ApiError("INVALID_IMAGE", "文件不是可读取的有效图片") from None
    except Image.DecompressionBombWarning:
        raise ApiError(
            "IMAGE_TOO_LARGE",
            "图片像素超过当前工具允许的范围",
            413,
        ) from None

    return ValidatedImage(
        destination,
        original_name,
        size,
        width,
        height,
        pixels,
        image_format,
    )


def image_stem(filename):
    return public_filename(filename).rsplit(".", 1)[0] or "image"


def as_rgb(image):
    if image.mode in {"RGBA", "LA"} or (
        image.mode == "P" and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        rgba.close()
        return background
    return image.convert("RGB")


def compress_to_jpeg(source, destination, target_size_mb):
    target_bytes = math.floor(target_size_mb * 1024 * 1024)
    with Image.open(source) as image:
        converted = as_rgb(image)
        try:
            best = None
            low, high = 10, 95
            while low <= high:
                quality = (low + high) // 2
                buffer = io.BytesIO()
                converted.save(buffer, format="JPEG", quality=quality, optimize=True)
                candidate = buffer.getvalue()
                if len(candidate) <= target_bytes:
                    best = candidate
                    low = quality + 1
                else:
                    high = quality - 1
            if best is None:
                raise ApiError(
                    "TARGET_TOO_SMALL",
                    "目标大小过小，当前图片无法在质量下限内达到",
                    422,
                )
            Path(destination).write_bytes(best)
        finally:
            converted.close()


def convert_image(source, destination, output_format, quality):
    with Image.open(source) as image:
        if output_format == "jpg":
            converted = as_rgb(image)
        elif image.mode not in {"RGB", "RGBA"}:
            converted = image.convert(
                "RGBA" if "transparency" in image.info else "RGB"
            )
        else:
            converted = image.copy()
        try:
            pillow_format = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP"}[
                output_format
            ]
            options = {}
            if output_format in {"jpg", "webp"}:
                options["quality"] = quality
            if output_format == "jpg":
                options["optimize"] = True
            converted.save(destination, format=pillow_format, **options)
        finally:
            converted.close()
