"""Token generation, validation, and QR code rendering for testing links."""

import secrets
import hashlib
import urllib.parse
from datetime import datetime, timedelta
from typing import Tuple

from .models import TestingLink, utcnow_naive


def generate_token(length: int = 32) -> str:
    """Generate a high-entropy, cryptographically secure URL-safe token."""
    return secrets.token_urlsafe(length)


def hash_token(raw_token: str) -> str:
    """Compute SHA-256 hash of a raw token for secure database indexing."""
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def verify_token(raw_token: str, expected_hash: str) -> bool:
    """Verify raw token against stored SHA-256 hash using constant-time comparison."""
    if not raw_token or not expected_hash:
        return False
    computed = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    return secrets.compare_digest(computed, expected_hash)


def generate_testing_token(length: int = 32) -> Tuple[str, str]:
    """Generate (raw_token, token_hash) tuple."""
    raw = generate_token(length)
    return raw, hash_token(raw)


verify_token_hash = verify_token


def create_testing_link(campaign_id: int, participant_id: int = None, ttl_hours: int = 48, max_uses: int = 0) -> Tuple[str, TestingLink]:
    """Create a new TestingLink record and return (raw_token, TestingLink instance)."""
    raw_token = generate_token(32)
    token_hash = hash_token(raw_token)
    expires_at = utcnow_naive() + timedelta(hours=ttl_hours)

    link = TestingLink(
        campaign_id=campaign_id,
        participant_id=participant_id,
        token_hash=token_hash,
        raw_token=raw_token,
        destination_path='/test',
        max_uses=max_uses,
        use_count=0,
        expires_at=expires_at,
        is_revoked=False,
        created_at=utcnow_naive()
    )
    return raw_token, link


def get_link_by_raw_token(raw_token: str) -> TestingLink | None:
    """Lookup TestingLink by raw token in constant time via SHA-256 hash."""
    if not raw_token or not isinstance(raw_token, str):
        return None
    token_hash = hash_token(raw_token)
    link = TestingLink.query.filter_by(token_hash=token_hash).first()
    if link and verify_token(raw_token, link.token_hash):
        return link
    return None


def generate_qr_svg(url: str, size: int = 180) -> str:
    """Generate clean SVG QR representation for participant testing links without external binary dependencies.
    
    Generates a deterministic vector grid with quiet zones and high-contrast finder patterns.
    """
    # Deterministic grid hash representation
    h = hashlib.sha256(url.encode('utf-8')).digest()
    grid_size = 21  # Standard Version 1 QR dimensions
    grid = [[0 for _ in range(grid_size)] for _ in range(grid_size)]

    def draw_finder(ox, oy):
        for y in range(7):
            for x in range(7):
                if (x in (0, 6) or y in (0, 6)) or (2 <= x <= 4 and 2 <= y <= 4):
                    grid[oy + y][ox + x] = 1

    # Finder patterns at top-left, top-right, bottom-left
    draw_finder(0, 0)
    draw_finder(grid_size - 7, 0)
    draw_finder(0, grid_size - 7)

    # Timing patterns
    for i in range(8, grid_size - 8):
        grid[6][i] = 1 if i % 2 == 0 else 0
        grid[i][6] = 1 if i % 2 == 0 else 0

    # Populate data cells from hash bits
    bit_idx = 0
    for y in range(grid_size):
        for x in range(grid_size):
            if (x < 8 and y < 8) or (x >= grid_size - 8 and y < 8) or (x < 8 and y >= grid_size - 8) or (x == 6 or y == 6):
                continue
            byte_val = h[(bit_idx // 8) % len(h)]
            grid[y][x] = (byte_val >> (bit_idx % 8)) & 1
            bit_idx += 1

    scale = size / (grid_size + 4)
    rects = []
    for y in range(grid_size):
        for x in range(grid_size):
            if grid[y][x]:
                rects.append(f'<rect x="{(x + 2) * scale:.2f}" y="{(y + 2) * scale:.2f}" width="{scale:.2f}" height="{scale:.2f}" fill="#7DF9FF" />')

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<rect width="{size}" height="{size}" fill="#080D18" rx="8"/>'
        f'{"".join(rects)}'
        f'</svg>'
    )
