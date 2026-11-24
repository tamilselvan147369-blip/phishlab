"""Browser telemetry, device category detection, and privacy-conscious analytics."""

import re
import hashlib
from flask import Request


def parse_user_agent(user_agent: str, ip_address: str = '') -> dict:
    """Analyze User-Agent header and return browser family, OS family, and device category."""
    ua = user_agent or ''
    ua_lower = ua.lower()

    # Device Category
    device_category = 'Desktop'
    if 'tablet' in ua_lower or 'ipad' in ua_lower:
        device_category = 'Tablet'
    elif 'mobile' in ua_lower or 'iphone' in ua_lower or 'android' in ua_lower:
        device_category = 'Mobile'

    # Operating System Family
    os_family = 'Unknown OS'
    if 'windows nt 10.0' in ua_lower or 'windows nt 11.0' in ua_lower:
        os_family = 'Windows 10/11'
    elif 'windows nt' in ua_lower:
        os_family = 'Windows'
    elif 'iphone' in ua_lower or 'ipad' in ua_lower or 'ios' in ua_lower:
        os_family = 'iOS'
    elif 'android' in ua_lower:
        os_family = 'Android'
    elif 'mac os x' in ua_lower or 'macintosh' in ua_lower:
        os_family = 'macOS'
    elif 'linux' in ua_lower:
        os_family = 'Linux'

    # Browser Family
    browser_family = 'Unknown Browser'
    browser_version = ''

    if 'edg/' in ua_lower:
        browser_family = 'Microsoft Edge'
        m = re.search(r'edg/([0-9\.]+)', ua_lower)
        if m: browser_version = m.group(1)
    elif 'opr/' in ua_lower or 'opera' in ua_lower:
        browser_family = 'Opera'
    elif 'chrome/' in ua_lower and 'chromium' not in ua_lower:
        browser_family = 'Google Chrome'
        m = re.search(r'chrome/([0-9\.]+)', ua_lower)
        if m: browser_version = m.group(1)
    elif 'firefox/' in ua_lower:
        browser_family = 'Mozilla Firefox'
        m = re.search(r'firefox/([0-9\.]+)', ua_lower)
        if m: browser_version = m.group(1)
    elif 'safari/' in ua_lower and 'chrome' not in ua_lower:
        browser_family = 'Apple Safari'
        m = re.search(r'version/([0-9\.]+)', ua_lower)
        if m: browser_version = m.group(1)

    res = {
        'browser_family': browser_family,
        'browser_version': browser_version,
        'os_family': os_family,
        'device_category': device_category,
        'raw_user_agent': ua[:250]
    }
    if ip_address:
        res['ip_hash'] = anonymize_ip(ip_address)
    return res


def anonymize_ip(ip_address: str) -> str:
    """Create a pseudonymized SHA-256 hash of participant IP for GDPR/privacy compliance."""
    if not ip_address:
        return 'unknown'
    return hashlib.sha256(ip_address.encode('utf-8')).hexdigest()[:16]


def sanitize_referrer(referrer: str) -> str:
    """Sanitize HTTP Referrer, stripping query tokens and tracking parameters."""
    if not referrer:
        return ''
    cleaned = referrer.split('?')[0]
    return cleaned[:250]
