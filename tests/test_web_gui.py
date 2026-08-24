import io
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from toolmist import create_app
from toolmist.tools.registry import get_available_tools


def image_bytes(image_format="PNG", color=(20, 80, 160, 255)):
    buffer = io.BytesIO()
    Image.new("RGBA", (32, 24), color).save(buffer, format=image_format)
    buffer.seek(0)
    return buffer


class WebGuiTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "UPLOAD_FOLDER": Path(self.temp_dir.name),
            "MAX_UPLOAD_MB": 10,
            "MAX_CONTENT_LENGTH": 10 * 1024 * 1024,
            "FILE_RETENTION_HOURS": 24,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_healthcheck(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_public_home_uses_safe_tool_workspace(self):
        response = self.client.get("/")
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Toolmist", page)
        self.assertIn("文件名提取完全在浏览器本地完成", page)
        self.assertIn('data-tool-target="image-compress"', page)
        self.assertNotIn("实时日志", page)
        self.assertNotIn("onclick=", page)
        self.assertNotIn("cdnjs.cloudflare.com", page)

    def test_tool_registry_contains_initial_tools(self):
        tool_ids = {tool.id for tool in get_available_tools()}
        self.assertEqual(tool_ids, {
            "filename-extract",
            "image-compress",
            "image-convert",
        })

    def test_collect_filenames_returns_download(self):
        response = self.client.post(
            "/api/collect_filenames",
            json={
                "include_subdirs": True,
                "remove_extension": True,
                "output_path": "/tmp/list.txt",
                "files_data": [
                    {"path": "album/one.jpg"},
                    {"path": "album/sub/two.png"},
                ],
            },
        )
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["filename"], "tmp_list.txt")

        with self.client.get(payload["download_url"]) as download:
            self.assertEqual(download.status_code, 200)
            self.assertEqual(download.data.decode(), "album/one\nalbum/sub/two\n")

    def test_compress_uploaded_image(self):
        response = self.client.post(
            "/api/compress_images",
            data={"target_size_mb": "1", "file": (image_bytes(), "sample.png")},
            content_type="multipart/form-data",
        )
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["filename"], "sample_compressed.jpg")
        with self.client.get(payload["download_url"]) as download:
            self.assertEqual(download.status_code, 200)

    def test_convert_multiple_images_to_zip(self):
        response = self.client.post(
            "/api/convert_format",
            data={
                "output_format": "webp",
                "quality": "80",
                "files": [
                    (image_bytes(), "one.png"),
                    (image_bytes(color=(180, 40, 20, 255)), "two.png"),
                ],
            },
            content_type="multipart/form-data",
        )
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["filename"], "converted_images.zip")
        with self.client.get(payload["download_url"]) as download:
            self.assertEqual(download.status_code, 200)

    def test_convert_transparent_png_to_jpeg(self):
        response = self.client.post(
            "/api/convert_format",
            data={
                "output_format": "jpg",
                "quality": "90",
                "files": (image_bytes(), "transparent.png"),
            },
            content_type="multipart/form-data",
        )
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["filename"], "transparent.jpg")
        with self.client.get(payload["download_url"]) as download:
            self.assertEqual(download.status_code, 200)
            with Image.open(io.BytesIO(download.data)) as converted:
                self.assertEqual(converted.format, "JPEG")

    def test_rejects_server_path_compression_requests(self):
        response = self.client.post(
            "/api/compress_images",
            json={"source_path": "/etc/passwd"},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
