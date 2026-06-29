"""
Laraflask Security Module
CSRF protection, XSS prevention, secure headers, password policy, and encryption.
"""

from __future__ import annotations
import os
import re
import hmac
import time
import base64
import hashlib
import secrets
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger('laraflask.security')


# ─── CSRF Protection ─────────────────────────────────────────────────────────

class CsrfToken:
    """CSRF token generation and verification."""

    @staticmethod
    def generate(session: Dict = None) -> str:
        """Generate a new CSRF token and store it in session."""
        token = secrets.token_hex(32)
        if session is not None:
            session['_token'] = token
        return token

    @staticmethod
    def verify(token: str, session: Dict) -> bool:
        """Verify CSRF token against session."""
        session_token = session.get('_token', '')
        if not token or not session_token:
            return False
        return hmac.compare_digest(str(token), str(session_token))

    @staticmethod
    def regenerate(session: Dict) -> str:
        """Regenerate CSRF token (call after login)."""
        return CsrfToken.generate(session)


class PreventRequestForgery:
    """
    [ID] Versi yang ditingkatkan dari `CsrfToken`: selain verifikasi token
    berbasis session seperti biasa, kelas ini menambahkan layer
    origin-aware verification — mengecek header `Origin`/`Referer` request
    terhadap daftar host yang dipercaya. Ini meniru perlindungan CSRF
    Laravel 13 yang membandingkan origin permintaan, sebagai pertahanan
    berlapis (defense-in-depth) di atas token, BUKAN penggantinya.

    Tetap 100% backward compatible: `CsrfMiddleware` lama yang hanya
    memanggil `CsrfToken.verify()`/perbandingan token manual tidak perlu
    diubah apa pun dan akan tetap berfungsi seperti sebelumnya. Middleware
    baru bisa memilih memakai `PreventRequestForgery.verify()` sebagai
    pengganti untuk perlindungan ekstra.

    [EN] An upgraded version of `CsrfToken`: in addition to the usual
    session-based token verification, this class adds an origin-aware
    verification layer — checking the request's `Origin`/`Referer` header
    against a list of trusted hosts. This mirrors Laravel 13's CSRF
    protection that compares the request's origin, as defense-in-depth on
    top of the token, NOT a replacement for it.

    Fully backward compatible: the old `CsrfMiddleware` that only calls
    `CsrfToken.verify()`/a manual token comparison needs no changes and
    keeps working exactly as before. New middleware can opt into
    `PreventRequestForgery.verify()` instead for extra protection.
    """

    def __init__(self, trusted_origins: List[str] = None):
        """
        [ID] `trusted_origins` adalah daftar host yang dipercaya (tanpa
        scheme), mis. `['myapp.test', '*.myapp.test']`. Jika kosong,
        origin/referer hanya dibandingkan terhadap `request.host` Flask
        secara otomatis (same-origin check).

        [EN] `trusted_origins` is a list of trusted hosts (without scheme),
        e.g. `['myapp.test', '*.myapp.test']`. If empty, the origin/referer
        is compared only against Flask's `request.host` automatically
        (a same-origin check).
        """
        self.trusted_origins = trusted_origins or []

    def verify(self, token: str, session: Dict, request: Any = None) -> bool:
        """
        [ID] Verifikasi dua layer: (1) token CSRF berbasis session seperti
        `CsrfToken.verify()`, DAN (2) header Origin/Referer request cocok
        dengan host yang dipercaya. Kedua layer harus lolos. Jika
        `request` tidak diberikan, hanya layer token yang dijalankan
        (fallback aman untuk pemanggilan di luar konteks HTTP, mis. test).

        [EN] Two-layer verification: (1) the session-based CSRF token, just
        like `CsrfToken.verify()`, AND (2) the request's Origin/Referer
        header matches a trusted host. Both layers must pass. If `request`
        is not provided, only the token layer runs (a safe fallback for
        calls outside an HTTP context, e.g. tests).
        """
        if not CsrfToken.verify(token, session):
            return False

        if request is not None and not self.verify_origin(request):
            return False

        return True

    def verify_origin(self, request: Any) -> bool:
        """
        [ID] Cek apakah header `Origin` (atau `Referer` sebagai fallback)
        pada request cocok dengan host yang dipercaya. Request tanpa kedua
        header ini dianggap GAGAL verifikasi (browser modern selalu
        mengirim salah satunya pada permintaan state-changing) — ini
        sengaja strict untuk mencegah request forgery dari klien non-browser
        yang memalsukan header lain tapi tidak menyertakan origin.

        [EN] Check whether the request's `Origin` header (or `Referer` as a
        fallback) matches a trusted host. A request missing both headers
        is treated as a FAILED verification (modern browsers always send
        one of these on state-changing requests) — this is intentionally
        strict to prevent forgery from non-browser clients that spoof
        other headers but omit the origin.
        """
        origin_host = self._extract_host(request.headers.get('Origin'))
        referer_host = self._extract_host(request.headers.get('Referer'))
        candidate_host = origin_host or referer_host

        if not candidate_host:
            return False

        allowed_hosts = list(self.trusted_origins)
        allowed_hosts.append(getattr(request, 'host', None))

        return any(
            allowed is not None and self._host_matches(candidate_host, allowed)
            for allowed in allowed_hosts
        )

    @staticmethod
    def _extract_host(value: Optional[str]) -> Optional[str]:
        """Extract just the host[:port] portion from a URL-like header value."""
        if not value:
            return None
        import urllib.parse
        parsed = urllib.parse.urlparse(value)
        return parsed.netloc or None

    @staticmethod
    def _host_matches(candidate: str, pattern: str) -> bool:
        """
        [ID] Cocokkan host terhadap pattern, mendukung wildcard subdomain
        sederhana (`*.example.com` cocok dengan `api.example.com` dan
        `example.com` sendiri).

        [EN] Match a host against a pattern, supporting simple subdomain
        wildcards (`*.example.com` matches `api.example.com` as well as
        `example.com` itself).
        """
        candidate = candidate.lower()
        pattern = pattern.lower()

        if pattern.startswith('*.'):
            suffix = pattern[1:]  # '.example.com'
            return candidate == pattern[2:] or candidate.endswith(suffix)

        return candidate == pattern


# ─── XSS Prevention ──────────────────────────────────────────────────────────

class XSS:
    """XSS prevention helpers."""

    DANGEROUS_TAGS = re.compile(
        r'<(script|iframe|object|embed|applet|form|input|button|'
        r'link|meta|base|style|frame|frameset)[^>]*>.*?</\1>|'
        r'<(script|iframe|object|embed|applet|form|input|button|'
        r'link|meta|base|style|frame|frameset)[^>]*/?>',
        re.IGNORECASE | re.DOTALL,
    )
    EVENTS = re.compile(
        r'\s+on\w+\s*=\s*["\'][^"\']*["\']',
        re.IGNORECASE,
    )
    JAVASCRIPT = re.compile(
        r'javascript\s*:',
        re.IGNORECASE,
    )

    @classmethod
    def clean(cls, text: str) -> str:
        """Strip dangerous HTML from a string."""
        if not isinstance(text, str):
            return text
        text = cls.DANGEROUS_TAGS.sub('', text)
        text = cls.EVENTS.sub('', text)
        text = cls.JAVASCRIPT.sub('', text)
        return text

    @staticmethod
    def escape(text: str) -> str:
        """HTML-escape a string."""
        return (str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))

    @staticmethod
    def sanitize_url(url: str) -> str:
        """Sanitize a URL to prevent javascript: attacks."""
        url = url.strip()
        if re.match(r'javascript:', url, re.IGNORECASE):
            return '#'
        if re.match(r'data:', url, re.IGNORECASE):
            return '#'
        return url

    @staticmethod
    def strip_tags(html: str, allowed: List[str] = None) -> str:
        """Strip HTML tags, optionally keeping allowed ones."""
        if not allowed:
            return re.sub(r'<[^>]+>', '', html)
        allowed_pattern = '|'.join(allowed)
        return re.sub(
            rf'<(?!/?\s*(?:{allowed_pattern})\b)[^>]+>',
            '',
            html,
            flags=re.IGNORECASE,
        )


# ─── SQL Injection Protection ─────────────────────────────────────────────────

class SqlSafe:
    """Helpers for detecting/preventing raw SQL injection."""

    PATTERNS = [
        r"('|--|\*|;|=|union|select|insert|update|delete|drop|"
        r"create|alter|exec|execute|declare|cast|convert|char|"
        r"nchar|varchar|nvarchar|script|javascript)",
    ]

    @classmethod
    def is_suspicious(cls, value: str) -> bool:
        """Heuristic check for SQL injection patterns."""
        for pattern in cls.PATTERNS:
            if re.search(pattern, str(value), re.IGNORECASE):
                return True
        return False

    @staticmethod
    def quote(value: str) -> str:
        """Escape single quotes in a SQL string (prefer parameterized queries)."""
        return str(value).replace("'", "''")


# ─── Encryption ───────────────────────────────────────────────────────────────

class Crypt:
    """
    AES-256-CBC encryption/decryption.
    Requires: pip install cryptography
    """

    def __init__(self, key: str = None):
        raw = key or os.getenv('APP_KEY', '')
        if raw.startswith('base64:'):
            raw = raw[7:]
        try:
            self._key = base64.b64decode(raw)
        except Exception:
            self._key = raw.encode('utf-8').ljust(32)[:32]

    def encrypt(self, value: Any) -> str:
        """Encrypt a value and return base64-encoded ciphertext."""
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            import json, struct

            plaintext = json.dumps(value).encode('utf-8')
            iv = secrets.token_bytes(16)
            padded = self._pad(plaintext)

            cipher = Cipher(
                algorithms.AES(self._key[:32]),
                modes.CBC(iv),
                backend=default_backend(),
            )
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(padded) + encryptor.finalize()

            mac = self._mac(iv, ciphertext)
            payload = {
                'iv': base64.b64encode(iv).decode(),
                'value': base64.b64encode(ciphertext).decode(),
                'mac': mac,
            }
            return base64.b64encode(json.dumps(payload).encode()).decode()

        except ImportError:
            # Fallback: simple XOR (NOT secure for production)
            import json
            plaintext = json.dumps(value)
            key_bytes = (self._key * (len(plaintext) // len(self._key) + 1))[:len(plaintext)]
            xored = bytes(a ^ b for a, b in zip(plaintext.encode(), key_bytes))
            return base64.b64encode(xored).decode()

    def decrypt(self, payload: str) -> Any:
        """Decrypt a base64-encoded ciphertext."""
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            import json

            raw = json.loads(base64.b64decode(payload))
            iv = base64.b64decode(raw['iv'])
            ciphertext = base64.b64decode(raw['value'])

            expected_mac = self._mac(iv, ciphertext)
            if not hmac.compare_digest(expected_mac, raw.get('mac', '')):
                raise ValueError("Message authentication failed")

            cipher = Cipher(
                algorithms.AES(self._key[:32]),
                modes.CBC(iv),
                backend=default_backend(),
            )
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            return json.loads(self._unpad(plaintext))

        except ImportError:
            import json
            decoded = base64.b64decode(payload)
            key_bytes = (self._key * (len(decoded) // len(self._key) + 1))[:len(decoded)]
            plaintext = bytes(a ^ b for a, b in zip(decoded, key_bytes))
            return json.loads(plaintext.decode())

    def encrypt_string(self, value: str) -> str:
        return self.encrypt(value)

    def decrypt_string(self, payload: str) -> str:
        return self.decrypt(payload)

    def _pad(self, data: bytes) -> bytes:
        pad_len = 16 - (len(data) % 16)
        return data + bytes([pad_len] * pad_len)

    def _unpad(self, data: bytes) -> bytes:
        pad_len = data[-1]
        return data[:-pad_len]

    def _mac(self, iv: bytes, ciphertext: bytes) -> str:
        message = base64.b64encode(iv) + base64.b64encode(ciphertext)
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()


# ─── Password Policy ──────────────────────────────────────────────────────────

class PasswordPolicy:
    """Enforce password strength requirements."""

    def __init__(self, min_length: int = 8, require_uppercase: bool = True,
                 require_lowercase: bool = True, require_numbers: bool = True,
                 require_symbols: bool = False, max_length: int = 128):
        self.min_length = min_length
        self.max_length = max_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_numbers = require_numbers
        self.require_symbols = require_symbols

    def validate(self, password: str) -> List[str]:
        """Return list of violation messages (empty = passes)."""
        errors = []
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters.")
        if len(password) > self.max_length:
            errors.append(f"Password must not exceed {self.max_length} characters.")
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter.")
        if self.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter.")
        if self.require_numbers and not re.search(r'\d', password):
            errors.append("Password must contain at least one number.")
        if self.require_symbols and not re.search(r'[^a-zA-Z0-9]', password):
            errors.append("Password must contain at least one special character.")
        return errors

    def passes(self, password: str) -> bool:
        return len(self.validate(password)) == 0

    def strength_score(self, password: str) -> int:
        """Return a strength score 0-5."""
        score = 0
        if len(password) >= 8:  score += 1
        if len(password) >= 12: score += 1
        if re.search(r'[A-Z]', password): score += 1
        if re.search(r'\d', password): score += 1
        if re.search(r'[^a-zA-Z0-9]', password): score += 1
        return score

    def strength_label(self, password: str) -> str:
        score = self.strength_score(password)
        labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong']
        return labels[min(score, 5)]


# ─── Signed URLs ──────────────────────────────────────────────────────────────

class SignedUrl:
    """Generate and verify tamper-proof signed URLs."""

    def __init__(self, secret: str = None):
        self._secret = secret or os.getenv('APP_KEY', 'laraflask')

    def create(self, url: str, expiry: int = 3600) -> str:
        """Create a signed URL with optional expiry (seconds)."""
        expires = int(time.time()) + expiry
        base = f"{url}?expires={expires}"
        sig = self._sign(base)
        return f"{base}&signature={sig}"

    def verify(self, url: str) -> bool:
        """Verify a signed URL has not been tampered with and has not expired."""
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        sig = params.get('signature', [None])[0]
        expires = params.get('expires', [None])[0]

        if not sig or not expires:
            return False

        if time.time() > float(expires):
            return False

        # Rebuild the URL without the signature to verify
        clean_query = '&'.join(
            f"{k}={v[0]}" for k, v in params.items() if k != 'signature'
        )
        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{clean_query}"
        expected_sig = self._sign(base)
        return hmac.compare_digest(sig, expected_sig)

    def _sign(self, value: str) -> str:
        return hmac.new(
            self._secret.encode('utf-8'),
            value.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()


# ─── Global Crypt Instance ────────────────────────────────────────────────────

_crypt: Optional[Crypt] = None


def encrypt(value: Any) -> str:
    global _crypt
    if _crypt is None:
        _crypt = Crypt()
    return _crypt.encrypt(value)


def decrypt(payload: str) -> Any:
    global _crypt
    if _crypt is None:
        _crypt = Crypt()
    return _crypt.decrypt(payload)
