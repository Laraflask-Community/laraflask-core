"""
Laraflask File Storage
Multi-driver storage: Local, AWS S3, MinIO, Cloudflare R2.
"""

from __future__ import annotations
import os
import shutil
import hashlib
import mimetypes
import logging
from abc import ABC, abstractmethod
from typing import Any, BinaryIO, Dict, List, Optional, Union

logger = logging.getLogger('laraflask.storage')


class StorageDriver(ABC):
    """Abstract storage driver interface."""

    @abstractmethod
    def exists(self, path: str) -> bool: pass

    @abstractmethod
    def get(self, path: str) -> Optional[bytes]: pass

    @abstractmethod
    def put(self, path: str, contents: Union[str, bytes, BinaryIO],
            options: Dict = None) -> bool: pass

    @abstractmethod
    def delete(self, path: Union[str, List[str]]) -> bool: pass

    @abstractmethod
    def copy(self, from_: str, to: str) -> bool: pass

    @abstractmethod
    def move(self, from_: str, to: str) -> bool: pass

    @abstractmethod
    def size(self, path: str) -> int: pass

    @abstractmethod
    def url(self, path: str) -> str: pass

    @abstractmethod
    def files(self, directory: str = '') -> List[str]: pass

    @abstractmethod
    def directories(self, directory: str = '') -> List[str]: pass

    @abstractmethod
    def make_directory(self, path: str) -> bool: pass

    @abstractmethod
    def delete_directory(self, directory: str) -> bool: pass


class LocalDriver(StorageDriver):
    """Local filesystem storage driver."""

    def __init__(self, root: str = None, url: str = None, visibility: str = 'private'):
        self._root = root or os.path.join(os.getcwd(), 'storage', 'app')
        self._url_base = url or '/storage'
        self._visibility = visibility
        os.makedirs(self._root, exist_ok=True)

    def _full_path(self, path: str) -> str:
        return os.path.join(self._root, path.lstrip('/'))

    def exists(self, path: str) -> bool:
        return os.path.exists(self._full_path(path))

    def missing(self, path: str) -> bool:
        return not self.exists(path)

    def get(self, path: str) -> Optional[bytes]:
        full = self._full_path(path)
        if not os.path.exists(full):
            return None
        with open(full, 'rb') as f:
            return f.read()

    def get_string(self, path: str) -> Optional[str]:
        data = self.get(path)
        return data.decode('utf-8') if data else None

    def put(self, path: str, contents: Union[str, bytes, BinaryIO],
            options: Dict = None) -> bool:
        full = self._full_path(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)

        try:
            if hasattr(contents, 'read'):
                with open(full, 'wb') as f:
                    shutil.copyfileobj(contents, f)
            elif isinstance(contents, str):
                with open(full, 'w', encoding='utf-8') as f:
                    f.write(contents)
            else:
                with open(full, 'wb') as f:
                    f.write(contents)
            return True
        except Exception as e:
            logger.error(f"Storage put error [{path}]: {e}")
            return False

    def put_file(self, directory: str, file: Any, name: str = None) -> Optional[str]:
        """Store an uploaded file."""
        filename = name or self._hash_name(file)
        path = f"{directory}/{filename}"
        if self.put(path, file):
            return path
        return None

    def put_file_as(self, directory: str, file: Any, name: str) -> Optional[str]:
        return self.put_file(directory, file, name)

    def prepend(self, path: str, data: str) -> bool:
        existing = self.get_string(path) or ''
        return self.put(path, data + existing)

    def append(self, path: str, data: str) -> bool:
        existing = self.get_string(path) or ''
        return self.put(path, existing + data)

    def delete(self, path: Union[str, List[str]]) -> bool:
        if isinstance(path, list):
            return all(self.delete(p) for p in path)
        full = self._full_path(path)
        if os.path.exists(full):
            os.remove(full)
            return True
        return False

    def copy(self, from_: str, to: str) -> bool:
        try:
            src = self._full_path(from_)
            dst = self._full_path(to)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            return True
        except Exception as e:
            logger.error(f"Storage copy error: {e}")
            return False

    def move(self, from_: str, to: str) -> bool:
        try:
            src = self._full_path(from_)
            dst = self._full_path(to)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            return True
        except Exception:
            return False

    def size(self, path: str) -> int:
        full = self._full_path(path)
        return os.path.getsize(full) if os.path.exists(full) else 0

    def last_modified(self, path: str) -> Optional[float]:
        full = self._full_path(path)
        return os.path.getmtime(full) if os.path.exists(full) else None

    def mime_type(self, path: str) -> Optional[str]:
        mime, _ = mimetypes.guess_type(path)
        return mime

    def url(self, path: str) -> str:
        return f"{self._url_base}/{path.lstrip('/')}"

    def temporary_url(self, path: str, expiry: int = 3600) -> str:
        """Generate a temporary signed URL."""
        import time, hmac, hashlib
        expires = int(time.time()) + expiry
        key = os.getenv('APP_KEY', 'laraflask')
        sig = hmac.new(key.encode(), f"{path}:{expires}".encode(), hashlib.sha256).hexdigest()
        return f"{self.url(path)}?expires={expires}&signature={sig}"

    def files(self, directory: str = '') -> List[str]:
        full = self._full_path(directory)
        if not os.path.isdir(full):
            return []
        return [
            os.path.join(directory, f)
            for f in os.listdir(full)
            if os.path.isfile(os.path.join(full, f))
        ]

    def all_files(self, directory: str = '') -> List[str]:
        full = self._full_path(directory)
        result = []
        for root, dirs, files in os.walk(full):
            for fname in files:
                rel = os.path.relpath(os.path.join(root, fname), self._root)
                result.append(rel)
        return result

    def directories(self, directory: str = '') -> List[str]:
        full = self._full_path(directory)
        if not os.path.isdir(full):
            return []
        return [
            os.path.join(directory, d)
            for d in os.listdir(full)
            if os.path.isdir(os.path.join(full, d))
        ]

    def make_directory(self, path: str) -> bool:
        try:
            os.makedirs(self._full_path(path), exist_ok=True)
            return True
        except Exception:
            return False

    def delete_directory(self, directory: str) -> bool:
        try:
            shutil.rmtree(self._full_path(directory))
            return True
        except Exception:
            return False

    def visibility(self, path: str) -> str:
        return self._visibility

    def set_visibility(self, path: str, visibility: str) -> bool:
        full = self._full_path(path)
        if visibility == 'public':
            os.chmod(full, 0o644)
        else:
            os.chmod(full, 0o600)
        return True

    def _hash_name(self, file: Any) -> str:
        if hasattr(file, 'filename'):
            ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else ''
            import secrets
            return secrets.token_hex(20) + (f'.{ext}' if ext else '')
        return hashlib.md5(str(id(file)).encode()).hexdigest()


class S3Driver(StorageDriver):
    """Amazon S3 / MinIO / R2 storage driver."""

    def __init__(self, bucket: str = None, region: str = None,
                 key: str = None, secret: str = None,
                 endpoint: str = None, url: str = None):
        self._bucket = bucket or os.getenv('AWS_BUCKET', '')
        self._region = region or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        self._key = key or os.getenv('AWS_ACCESS_KEY_ID', '')
        self._secret = secret or os.getenv('AWS_SECRET_ACCESS_KEY', '')
        self._endpoint = endpoint or os.getenv('AWS_ENDPOINT_URL')
        self._url_base = url or os.getenv('AWS_URL', '')
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3
            kwargs = {
                'aws_access_key_id': self._key,
                'aws_secret_access_key': self._secret,
                'region_name': self._region,
            }
            if self._endpoint:
                kwargs['endpoint_url'] = self._endpoint
            self._client = boto3.client('s3', **kwargs)
        return self._client

    def exists(self, path: str) -> bool:
        try:
            self._get_client().head_object(Bucket=self._bucket, Key=path)
            return True
        except Exception:
            return False

    def get(self, path: str) -> Optional[bytes]:
        try:
            response = self._get_client().get_object(Bucket=self._bucket, Key=path)
            return response['Body'].read()
        except Exception as e:
            logger.error(f"S3 get error [{path}]: {e}")
            return None

    def put(self, path: str, contents: Union[str, bytes, BinaryIO],
            options: Dict = None) -> bool:
        try:
            options = options or {}
            if isinstance(contents, str):
                contents = contents.encode('utf-8')

            extra_args = {}
            if 'visibility' in options:
                extra_args['ACL'] = 'public-read' if options['visibility'] == 'public' else 'private'
            if 'content_type' in options:
                extra_args['ContentType'] = options['content_type']
            else:
                mime, _ = mimetypes.guess_type(path)
                if mime:
                    extra_args['ContentType'] = mime

            self._get_client().put_object(
                Bucket=self._bucket,
                Key=path,
                Body=contents,
                **extra_args,
            )
            return True
        except Exception as e:
            logger.error(f"S3 put error [{path}]: {e}")
            return False

    def delete(self, path: Union[str, List[str]]) -> bool:
        try:
            if isinstance(path, list):
                objects = [{'Key': p} for p in path]
                self._get_client().delete_objects(
                    Bucket=self._bucket,
                    Delete={'Objects': objects}
                )
            else:
                self._get_client().delete_object(Bucket=self._bucket, Key=path)
            return True
        except Exception as e:
            logger.error(f"S3 delete error: {e}")
            return False

    def copy(self, from_: str, to: str) -> bool:
        try:
            self._get_client().copy_object(
                Bucket=self._bucket,
                CopySource={'Bucket': self._bucket, 'Key': from_},
                Key=to,
            )
            return True
        except Exception:
            return False

    def move(self, from_: str, to: str) -> bool:
        return self.copy(from_, to) and self.delete(from_)

    def size(self, path: str) -> int:
        try:
            response = self._get_client().head_object(Bucket=self._bucket, Key=path)
            return response['ContentLength']
        except Exception:
            return 0

    def url(self, path: str) -> str:
        if self._url_base:
            return f"{self._url_base}/{path}"
        if self._endpoint:
            return f"{self._endpoint}/{self._bucket}/{path}"
        return f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{path}"

    def temporary_url(self, path: str, expiry: int = 3600) -> str:
        return self._get_client().generate_presigned_url(
            'get_object',
            Params={'Bucket': self._bucket, 'Key': path},
            ExpiresIn=expiry,
        )

    def files(self, directory: str = '') -> List[str]:
        try:
            prefix = directory + '/' if directory and not directory.endswith('/') else directory
            response = self._get_client().list_objects_v2(
                Bucket=self._bucket, Prefix=prefix, Delimiter='/'
            )
            return [obj['Key'] for obj in response.get('Contents', [])]
        except Exception:
            return []

    def directories(self, directory: str = '') -> List[str]:
        try:
            prefix = directory + '/' if directory and not directory.endswith('/') else directory
            response = self._get_client().list_objects_v2(
                Bucket=self._bucket, Prefix=prefix, Delimiter='/'
            )
            return [p['Prefix'].rstrip('/') for p in response.get('CommonPrefixes', [])]
        except Exception:
            return []

    def make_directory(self, path: str) -> bool:
        return self.put(f"{path}/.keep", b'')

    def delete_directory(self, directory: str) -> bool:
        files = self.files(directory)
        return self.delete(files) if files else True

    def put_file(self, directory: str, file: Any, name: str = None) -> Optional[str]:
        import secrets
        if hasattr(file, 'filename'):
            ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else ''
            filename = name or (secrets.token_hex(20) + (f'.{ext}' if ext else ''))
        else:
            filename = name or secrets.token_hex(20)

        path = f"{directory}/{filename}"
        contents = file.read() if hasattr(file, 'read') else file
        return path if self.put(path, contents) else None


# ─── Storage Manager ──────────────────────────────────────────────────────────

class Storage:
    """
    File storage facade with multi-disk support.
    Works like Laravel's Storage facade.
    """

    _disks: Dict[str, StorageDriver] = {}
    _default: str = 'local'

    @classmethod
    def configure(cls, default: str = 'local', disks: Dict = None):
        cls._default = default

    @classmethod
    def disk(cls, name: str = None) -> StorageDriver:
        name = name or cls._default
        if name not in cls._disks:
            cls._disks[name] = cls._make_disk(name)
        return cls._disks[name]

    @classmethod
    def _make_disk(cls, name: str) -> StorageDriver:
        if name == 'local':
            return LocalDriver(
                root=os.path.join(os.getcwd(), 'storage', 'app'),
                url='/storage',
            )
        elif name == 'public':
            return LocalDriver(
                root=os.path.join(os.getcwd(), 'storage', 'app', 'public'),
                url='/storage',
                visibility='public',
            )
        elif name in ('s3', 'minio', 'r2'):
            return S3Driver()
        raise ValueError(f"Unknown storage disk [{name}]")

    # ─── Delegate to default disk ─────────────────────────────────────────────

    @classmethod
    def exists(cls, path: str) -> bool:
        return cls.disk().exists(path)

    @classmethod
    def missing(cls, path: str) -> bool:
        return not cls.exists(path)

    @classmethod
    def get(cls, path: str) -> Optional[bytes]:
        return cls.disk().get(path)

    @classmethod
    def put(cls, path: str, contents: Any, options: Dict = None) -> bool:
        return cls.disk().put(path, contents, options)

    @classmethod
    def put_file(cls, directory: str, file: Any, name: str = None) -> Optional[str]:
        return cls.disk().put_file(directory, file, name)

    @classmethod
    def put_file_as(cls, directory: str, file: Any, name: str) -> Optional[str]:
        return cls.disk().put_file(directory, file, name)

    @classmethod
    def delete(cls, path: Union[str, List[str]]) -> bool:
        return cls.disk().delete(path)

    @classmethod
    def copy(cls, from_: str, to: str) -> bool:
        return cls.disk().copy(from_, to)

    @classmethod
    def move(cls, from_: str, to: str) -> bool:
        return cls.disk().move(from_, to)

    @classmethod
    def size(cls, path: str) -> int:
        return cls.disk().size(path)

    @classmethod
    def url(cls, path: str) -> str:
        return cls.disk().url(path)

    @classmethod
    def temporary_url(cls, path: str, expiry: int = 3600) -> str:
        return cls.disk().temporary_url(path, expiry)

    @classmethod
    def files(cls, directory: str = '') -> List[str]:
        return cls.disk().files(directory)

    @classmethod
    def directories(cls, directory: str = '') -> List[str]:
        return cls.disk().directories(directory)

    @classmethod
    def make_directory(cls, path: str) -> bool:
        return cls.disk().make_directory(path)

    @classmethod
    def delete_directory(cls, directory: str) -> bool:
        return cls.disk().delete_directory(directory)

    @classmethod
    def append(cls, path: str, data: str) -> bool:
        return cls.disk().append(path, data)

    @classmethod
    def prepend(cls, path: str, data: str) -> bool:
        return cls.disk().prepend(path, data)

    @classmethod
    def register_disk(cls, name: str, driver: StorageDriver):
        cls._disks[name] = driver
