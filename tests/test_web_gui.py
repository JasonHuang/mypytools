from pathlib import Path
import tempfile
import unittest

from toolmist import create_app
from toolmist.tools.registry import get_available_tools


class WebGuiTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "UPLOAD_FOLDER": Path(self.temp_dir.name),
            "MAX_UPLOAD_MB": 10,
            "MAX_CONTENT_LENGTH": 10 * 1024 * 1024,
            "FILE_RETENTION_HOURS": 1,
            "ENABLE_ARTIFACT_CLEANUP": False,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_healthcheck(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})
        self.assertTrue(response.headers["X-Request-ID"])

    def test_public_home_uses_safe_tool_workspace_and_headers(self):
        response = self.client.get("/")
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Toolmist", page)
        self.assertIn("文件名提取完全在浏览器本地完成", page)
        self.assertIn('data-tool-target="image-compress"', page)
        self.assertNotIn("实时日志", page)
        self.assertNotIn("onclick=", page)
        self.assertNotIn("cdnjs.cloudflare.com", page)
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])

    def test_frontend_uses_v1_and_local_filename_workflows(self):
        script = (Path(__file__).parent.parent / "static/js/app.mjs").read_text(
            encoding="utf-8"
        )
        self.assertIn("/api/v1/tools/image-compress/jobs", script)
        self.assertIn("/api/v1/tools/image-convert/jobs", script)
        self.assertIn("new Blob", script)
        self.assertIn("URL.createObjectURL", script)
        self.assertNotIn("/api/collect_filenames", script)
        self.assertNotIn("/api/compress_images", script)
        self.assertNotIn("/api/convert_format", script)
        self.assertNotIn(".innerHTML", script)

        with self.client.get("/static/js/app.mjs") as app_module:
            self.assertEqual(app_module.status_code, 200)
            self.assertEqual(app_module.mimetype, "text/javascript")
        with self.client.get("/static/js/core.mjs") as core_module:
            self.assertEqual(core_module.status_code, 200)
            self.assertEqual(core_module.mimetype, "text/javascript")

    def test_tool_registry_contains_initial_tools(self):
        tool_ids = {tool.id for tool in get_available_tools()}
        self.assertEqual(tool_ids, {
            "filename-extract",
            "image-compress",
            "image-convert",
        })

    def test_legacy_public_routes_are_removed(self):
        for method, path in (
            ("get", "/api/logs"),
            ("post", "/api/clear_logs"),
            ("post", "/api/collect_filenames"),
            ("post", "/api/compress_images"),
            ("post", "/api/convert_format"),
            ("get", "/download/old-result.jpg"),
        ):
            response = getattr(self.client, method)(path)
            self.assertEqual(response.status_code, 404, path)


if __name__ == "__main__":
    unittest.main()
