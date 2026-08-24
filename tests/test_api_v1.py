import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from PIL import Image

from toolmist import create_app


def image_bytes(image_format="PNG", size=(32, 24), color=(20, 80, 160, 255)):
    buffer = io.BytesIO()
    Image.new("RGBA", size, color).save(buffer, format=image_format)
    buffer.seek(0)
    return buffer


class ApiV1TestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.upload_root = Path(self.temp_dir.name)
        self.app = create_app({
            "TESTING": True,
            "UPLOAD_FOLDER": self.upload_root,
            "MAX_UPLOAD_MB": 2,
            "MAX_CONTENT_LENGTH": 2 * 1024 * 1024,
            "MAX_FILES_PER_JOB": 3,
            "MAX_IMAGE_PIXELS": 1_000_000,
            "MAX_TOTAL_PIXELS": 2_000_000,
            "FILE_RETENTION_HOURS": 1,
            "ENABLE_ARTIFACT_CLEANUP": False,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def post_compression(self, filename="sample.png"):
        return self.client.post(
            "/api/v1/tools/image-compress/jobs",
            data={
                "target_size_mb": "1",
                "file": (image_bytes(), filename),
            },
            content_type="multipart/form-data",
        )

    def test_compression_creates_isolated_downloadable_job(self):
        first = self.post_compression()
        second = self.post_compression("second.png")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)

        first_payload = first.get_json()
        second_payload = second.get_json()
        self.assertTrue(first_payload["ok"])
        self.assertNotEqual(first_payload["job"]["id"], second_payload["job"]["id"])

        job_directories = [path for path in self.upload_root.iterdir() if path.is_dir()]
        self.assertEqual(len(job_directories), 2)
        for directory in job_directories:
            self.assertTrue((directory / "metadata.json").is_file())
            self.assertEqual(list((directory / "inputs").iterdir()), [])
            self.assertEqual(len(list((directory / "outputs").iterdir())), 1)

        artifact = first_payload["artifacts"][0]
        self.assertNotIn(str(self.upload_root), artifact["download_url"])
        with self.client.get(artifact["download_url"]) as download:
            self.assertEqual(download.status_code, 200)
            self.assertEqual(download.mimetype, "image/jpeg")
            with Image.open(io.BytesIO(download.data)) as image:
                self.assertEqual(image.format, "JPEG")

    def test_conversion_packages_multiple_outputs_without_internal_paths(self):
        response = self.client.post(
            "/api/v1/tools/image-convert/jobs",
            data={
                "output_format": "webp",
                "quality": "80",
                "files": [
                    (image_bytes(), "one.png"),
                    (image_bytes(color=(180, 40, 20, 255)), "one.png"),
                ],
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload["summary"]["input_count"], 2)
        self.assertEqual(payload["artifacts"][0]["name"], "converted-images.zip")

        with self.client.get(payload["artifacts"][0]["download_url"]) as download:
            with zipfile.ZipFile(io.BytesIO(download.data)) as archive:
                self.assertEqual(archive.namelist(), ["one.webp", "one-2.webp"])
                self.assertTrue(
                    all("input-" not in name for name in archive.namelist())
                )

    def test_rejects_file_with_spoofed_image_extension_and_removes_job(self):
        response = self.client.post(
            "/api/v1/tools/image-compress/jobs",
            data={
                "target_size_mb": "1",
                "file": (io.BytesIO(b"not an image"), "fake.jpg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "INVALID_IMAGE")
        self.assertEqual(
            [path for path in self.upload_root.iterdir() if path.is_dir()], []
        )

    def test_rejects_extension_that_does_not_match_real_format(self):
        response = self.client.post(
            "/api/v1/tools/image-compress/jobs",
            data={
                "target_size_mb": "1",
                "file": (image_bytes(), "actually-jpeg.jpg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"]["code"], "IMAGE_TYPE_MISMATCH"
        )

    def test_enforces_file_count_and_pixel_limits(self):
        too_many = self.client.post(
            "/api/v1/tools/image-convert/jobs",
            data={
                "output_format": "jpg",
                "files": [
                    (image_bytes(), f"{index}.png") for index in range(4)
                ],
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(too_many.status_code, 413)
        self.assertEqual(too_many.get_json()["error"]["code"], "TOO_MANY_FILES")

        limited_app = create_app({
            "TESTING": True,
            "UPLOAD_FOLDER": self.upload_root,
            "MAX_UPLOAD_MB": 2,
            "MAX_IMAGE_PIXELS": 100,
            "MAX_TOTAL_PIXELS": 200,
            "MAX_FILES_PER_JOB": 3,
            "FILE_RETENTION_HOURS": 1,
            "ENABLE_ARTIFACT_CLEANUP": False,
        })
        limited_client = limited_app.test_client()
        too_large = limited_client.post(
            "/api/v1/tools/image-compress/jobs",
            data={
                "target_size_mb": "1",
                "file": (image_bytes(size=(11, 10)), "large.png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(too_large.status_code, 413)
        self.assertEqual(too_large.get_json()["error"]["code"], "IMAGE_TOO_LARGE")

        total_limited_app = create_app({
            "TESTING": True,
            "UPLOAD_FOLDER": self.upload_root,
            "MAX_UPLOAD_MB": 2,
            "MAX_IMAGE_PIXELS": 150,
            "MAX_TOTAL_PIXELS": 150,
            "MAX_FILES_PER_JOB": 3,
            "FILE_RETENTION_HOURS": 1,
            "ENABLE_ARTIFACT_CLEANUP": False,
        })
        total_limited_client = total_limited_app.test_client()
        total_too_large = total_limited_client.post(
            "/api/v1/tools/image-convert/jobs",
            data={
                "output_format": "jpg",
                "files": [
                    (image_bytes(size=(10, 10)), "one.png"),
                    (image_bytes(size=(10, 10)), "two.png"),
                ],
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(total_too_large.status_code, 413)
        self.assertEqual(
            total_too_large.get_json()["error"]["code"],
            "TOTAL_PIXELS_EXCEEDED",
        )

    def test_expired_artifact_returns_gone_and_is_deleted(self):
        response = self.post_compression()
        payload = response.get_json()
        job_directory = self.upload_root / payload["job"]["id"]
        metadata_path = job_directory / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["expires_at"] = "2000-01-01T00:00:00Z"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        expired = self.client.get(payload["artifacts"][0]["download_url"])
        self.assertEqual(expired.status_code, 410)
        self.assertEqual(expired.get_json()["error"]["code"], "ARTIFACT_EXPIRED")
        self.assertFalse(job_directory.exists())

    def test_request_limit_uses_stable_error_shape(self):
        with self.client.post(
            "/api/v1/tools/image-compress/jobs",
            data=b"x" * (2 * 1024 * 1024 + 1),
            content_type="multipart/form-data; boundary=toolmist-test",
        ) as response:
            self.assertEqual(response.status_code, 413)
            self.assertEqual(
                response.get_json(),
                {
                    "ok": False,
                    "error": {
                        "code": "REQUEST_TOO_LARGE",
                        "message": "单次上传内容不能超过 2 MB",
                    },
                },
            )

    def test_public_log_endpoints_are_removed(self):
        self.assertEqual(self.client.get("/api/logs").status_code, 404)
        self.assertEqual(self.client.post("/api/clear_logs").status_code, 404)

    def test_server_paths_are_not_accepted_by_v1(self):
        response = self.client.post(
            "/api/v1/tools/image-compress/jobs",
            json={
                "source_path": "/etc/passwd",
                "output_path": "/tmp/result.jpg",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "UPLOAD_REQUIRED")
        self.assertEqual(
            [path for path in self.upload_root.iterdir() if path.is_dir()], []
        )

    def test_cleanup_cli_is_available(self):
        result = self.app.test_cli_runner().invoke(args=["cleanup-artifacts"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("removed_jobs=0", result.output)


if __name__ == "__main__":
    unittest.main()
