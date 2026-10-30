"""Object storage behind one interface (Part 2 §9.1).

- `local`: files under LOCAL_STORAGE_DIR/{private,public}; multipart parts are PUT to the
  API with a signed token; public files are served by the API at /media/...
- `s3`: S3-compatible (AWS S3 ap-south-1, Cloudflare R2, MinIO). Presigned multipart parts,
  private bucket for originals, public bucket (behind CDN) for derivatives.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.core.security import sign_payload

PART_SIZE = 5 * 1024 * 1024


class Storage(Protocol):
    async def put_private(self, key: str, data: bytes, mime: str) -> None: ...
    async def put_public(self, key: str, data: bytes, mime: str) -> None: ...
    async def get_private(self, key: str) -> bytes: ...
    async def get_public(self, key: str) -> bytes: ...
    async def delete_private(self, key: str) -> None: ...
    def public_url(self, key: str) -> str: ...
    async def start_multipart(self, key: str, mime: str) -> str | None: ...
    def part_url(self, media_id: str, key: str, upload_id: str | None, part_number: int) -> str: ...
    async def complete_multipart(self, key: str, upload_id: str | None, parts: list[dict], part_count: int) -> None: ...
    async def write_part(self, key: str, part_number: int, data: bytes) -> str: ...


class LocalStorage:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        (self.root / "private").mkdir(parents=True, exist_ok=True)
        (self.root / "public").mkdir(parents=True, exist_ok=True)
        (self.root / "parts").mkdir(parents=True, exist_ok=True)

    def _path(self, area: str, key: str) -> Path:
        path = (self.root / area / key).resolve()
        if not str(path).startswith(str(self.root / area)):
            raise ValueError("invalid storage key")
        return path

    async def _write(self, path: Path, data: bytes) -> None:
        def _do():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await asyncio.to_thread(_do)

    async def put_private(self, key, data, mime):
        await self._write(self._path("private", key), data)

    async def put_public(self, key, data, mime):
        await self._write(self._path("public", key), data)

    async def get_private(self, key):
        return await asyncio.to_thread(self._path("private", key).read_bytes)

    async def get_public(self, key):
        return await asyncio.to_thread(self._path("public", key).read_bytes)

    async def delete_private(self, key):
        p = self._path("private", key)
        if p.exists():
            await asyncio.to_thread(p.unlink)

    def public_url(self, key):
        return f"{get_settings().media_public_base}/{key}"

    async def start_multipart(self, key, mime):
        return None

    def part_url(self, media_id, key, upload_id, part_number):
        token = sign_payload({"m": media_id, "p": part_number}, minutes=120)
        return f"{get_settings().api_base_url}/api/v1/media/uploads/{media_id}/parts/{part_number}?token={token}"

    async def write_part(self, key, part_number, data):
        await self._write(self._path("parts", f"{key}.part{part_number:05d}"), data)
        return f"local-{part_number}"

    async def complete_multipart(self, key, upload_id, parts, part_count):
        def _do():
            dest = self._path("private", key)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("wb") as out:
                for n in range(1, part_count + 1):
                    part = self._path("parts", f"{key}.part{n:05d}")
                    if not part.exists():
                        raise FileNotFoundError(f"missing part {n}")
                    with part.open("rb") as src:
                        shutil.copyfileobj(src, out)
            for n in range(1, part_count + 1):
                self._path("parts", f"{key}.part{n:05d}").unlink(missing_ok=True)

        await asyncio.to_thread(_do)


class S3Storage:
    def __init__(self):
        import boto3  # optional dependency in local mode

        s = get_settings()
        self.s = s
        self.client = boto3.client(
            "s3",
            endpoint_url=s.s3_endpoint or None,
            region_name=s.s3_region,
            aws_access_key_id=s.s3_access_key or None,
            aws_secret_access_key=s.s3_secret_key or None,
        )

    async def put_private(self, key, data, mime):
        await asyncio.to_thread(self.client.put_object, Bucket=self.s.s3_bucket_private, Key=key, Body=data, ContentType=mime)

    async def put_public(self, key, data, mime):
        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.s.s3_bucket_public,
            Key=key,
            Body=data,
            ContentType=mime,
            CacheControl="public, max-age=31536000, immutable",
        )

    async def get_private(self, key):
        obj = await asyncio.to_thread(self.client.get_object, Bucket=self.s.s3_bucket_private, Key=key)
        return await asyncio.to_thread(obj["Body"].read)

    async def get_public(self, key):
        obj = await asyncio.to_thread(self.client.get_object, Bucket=self.s.s3_bucket_public, Key=key)
        return await asyncio.to_thread(obj["Body"].read)

    async def delete_private(self, key):
        await asyncio.to_thread(self.client.delete_object, Bucket=self.s.s3_bucket_private, Key=key)

    def public_url(self, key):
        return f"{self.s.media_public_base}/{key}"

    async def start_multipart(self, key, mime):
        res = await asyncio.to_thread(
            self.client.create_multipart_upload, Bucket=self.s.s3_bucket_private, Key=key, ContentType=mime
        )
        return res["UploadId"]

    def part_url(self, media_id, key, upload_id, part_number):
        return self.client.generate_presigned_url(
            "upload_part",
            Params={"Bucket": self.s.s3_bucket_private, "Key": key, "UploadId": upload_id, "PartNumber": part_number},
            ExpiresIn=7200,
        )

    async def write_part(self, key, part_number, data):
        raise NotImplementedError("S3 parts are uploaded directly with presigned URLs")

    async def complete_multipart(self, key, upload_id, parts, part_count):
        await asyncio.to_thread(
            self.client.complete_multipart_upload,
            Bucket=self.s.s3_bucket_private,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={"Parts": [{"ETag": p["etag"], "PartNumber": p["part_number"]} for p in parts]},
        )


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        s = get_settings()
        _storage = S3Storage() if s.storage_backend == "s3" else LocalStorage(s.local_storage_dir)
    return _storage


def reset_storage() -> None:
    global _storage
    _storage = None
