"""Platform-Specific Rendering Adapters for the Unified Social Media Simulation Generator.

Transforms ONE common generated scenario into high-fidelity, platform-appropriate
visual formats for WhatsApp, Instagram, Facebook Messenger, Telegram, X, and LinkedIn.
"""

from abc import ABC, abstractmethod


class BasePlatformAdapter(ABC):
    """Abstract base adapter for platform visual styling and message formatting."""

    @abstractmethod
    def format_preview(self, scenario: dict, format_variant: str = 'default') -> dict:
        """Return platform-specific visual metadata, badge, and HTML preview snippet."""
        pass


class WhatsAppAdapter(BasePlatformAdapter):
    """WhatsApp styling adapter (Individual chat, Group message, Account security)."""

    def format_preview(self, scenario: dict, format_variant: str = 'individual') -> dict:
        sender = scenario.get('fictional_sender', 'IT Support Desk')
        content = scenario.get('message_content', '')
        link = scenario.get('simulated_link', '')
        att = scenario.get('simulated_attachment', '')

        # Variants: individual, group, account_security
        is_group = (format_variant == 'group')
        header_title = "Internal Staff Group (5)" if is_group else sender
        header_subtitle = "Tap here for group info" if is_group else "online"

        link_html = f'<div class="wa-link-preview"><a href="#">{link}</a></div>' if link else ''
        att_html = f'<div class="wa-att-preview">📄 <strong>{att}</strong> (Safe Document)</div>' if att else ''

        snippet = f"""
        <div class="wa-preview-box">
            <div class="wa-top-bar">
                <span class="wa-avatar">📱</span>
                <div class="wa-info">
                    <strong>{header_title}</strong>
                    <small>{header_subtitle}</small>
                </div>
            </div>
            <div class="wa-bubble-container">
                <div class="wa-bubble-msg">
                    {f'<div class="wa-group-sender">{sender}</div>' if is_group else ''}
                    <div class="wa-text">{content}</div>
                    {link_html}
                    {att_html}
                    <div class="wa-meta">12:45 PM <span class="wa-ticks">✓✓</span></div>
                </div>
            </div>
        </div>
        """
        return {
            'platform': 'whatsapp',
            'display_name': 'WhatsApp',
            'format_variant': format_variant,
            'accent_color': '#25D366',
            'icon': '📱',
            'snippet_html': snippet,
            'supported_variants': ['individual', 'group', 'account_security']
        }


class InstagramAdapter(BasePlatformAdapter):
    """Instagram styling adapter (Direct Message, Message Request, Story Notification)."""

    def format_preview(self, scenario: dict, format_variant: str = 'direct') -> dict:
        sender = scenario.get('fictional_sender', 'Security Review')
        handle = scenario.get('sender_handle', '@meta_security_test')
        content = scenario.get('message_content', '')
        link = scenario.get('simulated_link', '')
        att = scenario.get('simulated_attachment', '')

        is_request = (format_variant == 'request')
        is_story = (format_variant == 'story')

        banner_html = ''
        if is_request:
            banner_html = '<div class="ig-request-notice">⚠️ <strong>Message Request:</strong> This account does not follow you.</div>'
        elif is_story:
            banner_html = '<div class="ig-story-notice">📸 <em>Mentioned you in their story: "Review security credentials"</em></div>'

        link_html = f'<div class="ig-link-preview"><a href="#">{link}</a></div>' if link else ''
        att_html = f'<div class="ig-att-preview">📄 <strong>{att}</strong></div>' if att else ''

        snippet = f"""
        <div class="ig-preview-box">
            <div class="ig-top-bar">
                <div class="ig-gradient-avatar"><div class="ig-avatar-core">📸</div></div>
                <div class="ig-info">
                    <strong>{sender}</strong>
                    <small>{handle}</small>
                </div>
            </div>
            {banner_html}
            <div class="ig-bubble-container">
                <div class="ig-bubble-msg">
                    <div class="ig-text">{content}</div>
                    {link_html}
                    {att_html}
                </div>
            </div>
        </div>
        """
        return {
            'platform': 'instagram',
            'display_name': 'Instagram',
            'format_variant': format_variant,
            'accent_color': '#E1306C',
            'icon': '📸',
            'snippet_html': snippet,
            'supported_variants': ['direct', 'request', 'story']
        }


class MessengerAdapter(BasePlatformAdapter):
    """Facebook Messenger styling adapter (Individual, Group, Notification)."""

    def format_preview(self, scenario: dict, format_variant: str = 'individual') -> dict:
        sender = scenario.get('fictional_sender', 'Support Desk')
        content = scenario.get('message_content', '')
        link = scenario.get('simulated_link', '')
        att = scenario.get('simulated_attachment', '')

        is_group = (format_variant == 'group')
        is_notif = (format_variant == 'notification')

        banner_html = '<div class="fb-notif-notice">🔔 <strong>Page Security Alert:</strong> Administrative review required.</div>' if is_notif else ''
        link_html = f'<div class="fb-link-preview"><a href="#">{link}</a></div>' if link else ''
        att_html = f'<div class="fb-att-preview">📎 {att}</div>' if att else ''

        snippet = f"""
        <div class="fb-preview-box">
            <div class="fb-top-bar">
                <span class="fb-avatar">💬</span>
                <div class="fb-info">
                    <strong>{sender}</strong>
                    <small>Active Now</small>
                </div>
            </div>
            {banner_html}
            <div class="fb-bubble-container">
                <div class="fb-bubble-msg">
                    <div class="fb-text">{content}</div>
                    {link_html}
                    {att_html}
                </div>
            </div>
        </div>
        """
        return {
            'platform': 'facebook_messenger',
            'display_name': 'Facebook Messenger',
            'format_variant': format_variant,
            'accent_color': '#0084FF',
            'icon': '💬',
            'snippet_html': snippet,
            'supported_variants': ['individual', 'group', 'notification']
        }


class TelegramAdapter(BasePlatformAdapter):
    """Telegram styling adapter (Private message, Group, Channel notification)."""

    def format_preview(self, scenario: dict, format_variant: str = 'private') -> dict:
        sender = scenario.get('fictional_sender', 'Verification Bot')
        handle = scenario.get('sender_handle', '@verify_bot')
        content = scenario.get('message_content', '')
        link = scenario.get('simulated_link', '')
        att = scenario.get('simulated_attachment', '')

        is_channel = (format_variant == 'channel')
        is_bot = (format_variant == 'bot')

        banner_html = ''
        if is_channel:
            banner_html = '<div class="tg-banner">📢 <strong>Broadcast Channel</strong> • 12,480 subscribers</div>'
        elif is_bot:
            banner_html = '<div class="tg-banner" style="color: #ffb74d;">🤖 <strong>Automated Bot</strong> (Never share Telegram SMS login codes)</div>'

        link_html = f'<div class="tg-link-preview"><a href="#">{link}</a></div>' if link else ''
        att_html = f'<div class="tg-att-preview">📁 {att}</div>' if att else ''

        snippet = f"""
        <div class="tg-preview-box">
            <div class="tg-top-bar">
                <span class="tg-avatar">✈️</span>
                <div class="tg-info">
                    <strong>{sender}</strong>
                    <small>{handle}</small>
                </div>
            </div>
            {banner_html}
            <div class="tg-bubble-container">
                <div class="tg-bubble-msg">
                    <div class="tg-text">{content}</div>
                    {link_html}
                    {att_html}
                    <div class="tg-meta">12:35 PM ✓✓</div>
                </div>
            </div>
        </div>
        """
        return {
            'platform': 'telegram',
            'display_name': 'Telegram',
            'format_variant': format_variant,
            'accent_color': '#2481CC',
            'icon': '✈️',
            'snippet_html': snippet,
            'supported_variants': ['private', 'group', 'channel', 'bot']
        }


class XAdapter(BasePlatformAdapter):
    """X (Twitter) styling adapter (Direct Message, Account Notification, Security Alert)."""

    def format_preview(self, scenario: dict, format_variant: str = 'direct') -> dict:
        sender = scenario.get('fictional_sender', 'X Support Notice')
        handle = scenario.get('sender_handle', '@X_Support_Alert')
        content = scenario.get('message_content', '')
        link = scenario.get('simulated_link', '')

        is_notif = (format_variant == 'notification')
        banner_html = '<div class="x-notif-banner">⚠️ <strong>Account Alert:</strong> Security update recommended.</div>' if is_notif else ''
        link_html = f'<div class="x-card-preview"><div style="font-size: 0.7rem; color: #71767b;">LINK CARD</div><a href="#">{link}</a></div>' if link else ''

        snippet = f"""
        <div class="x-preview-box">
            <div class="x-top-bar">
                <span class="x-avatar">✖️</span>
                <div class="x-info">
                    <strong>{sender} <span class="x-badge">✓</span></strong>
                    <small>{handle}</small>
                </div>
            </div>
            {banner_html}
            <div class="x-bubble-container">
                <div class="x-bubble-msg">
                    <div class="x-text">{content}</div>
                    {link_html}
                </div>
            </div>
        </div>
        """
        return {
            'platform': 'x',
            'display_name': 'X (Twitter)',
            'format_variant': format_variant,
            'accent_color': '#1D9BF0',
            'icon': '✖️',
            'snippet_html': snippet,
            'supported_variants': ['direct', 'notification', 'security_alert']
        }


class LinkedInAdapter(BasePlatformAdapter):
    """LinkedIn styling adapter (Recruitment InMail, Connection Request, Professional Notice)."""

    def format_preview(self, scenario: dict, format_variant: str = 'recruitment') -> dict:
        sender = scenario.get('fictional_sender', 'Dr. Marcus Vance')
        handle = scenario.get('sender_handle', 'Executive Search Director')
        content = scenario.get('message_content', '')
        link = scenario.get('simulated_link', '')
        att = scenario.get('simulated_attachment', '')

        is_recruit = (format_variant == 'recruitment')
        is_connect = (format_variant == 'connection')

        badge_text = "InMail" if is_recruit else "Invitation"
        card_html = ''
        if is_recruit:
            card_html = '<div class="li-inmail-card">💼 <strong>Executive Opportunity</strong> • Verified Recruiter Network</div>'
        elif is_connect:
            card_html = '<div class="li-inmail-card">🤝 <strong>Connection Request</strong> • 500+ mutual connections</div>'

        link_html = f'<div class="li-link-preview"><a href="#">{link}</a></div>' if link else ''
        att_html = f'<div class="li-doc-preview">📑 <strong>{att}</strong> (Safe Document Inspection)</div>' if att else ''

        snippet = f"""
        <div class="li-preview-box">
            <div class="li-top-bar">
                <span class="li-avatar">💼</span>
                <div class="li-info">
                    <strong>{sender} <span class="li-inmail-tag">{badge_text}</span></strong>
                    <small>{handle}</small>
                </div>
            </div>
            {card_html}
            <div class="li-bubble-container">
                <div class="li-bubble-msg">
                    <div class="li-text">{content}</div>
                    {link_html}
                    {att_html}
                </div>
            </div>
        </div>
        """
        return {
            'platform': 'linkedin',
            'display_name': 'LinkedIn',
            'format_variant': format_variant,
            'accent_color': '#0A66C2',
            'icon': '💼',
            'snippet_html': snippet,
            'supported_variants': ['recruitment', 'connection', 'professional']
        }


# Adapter Registry
PLATFORM_ADAPTERS = {
    'whatsapp': WhatsAppAdapter(),
    'instagram': InstagramAdapter(),
    'facebook_messenger': MessengerAdapter(),
    'telegram': TelegramAdapter(),
    'x': XAdapter(),
    'linkedin': LinkedInAdapter(),
}

def get_platform_adapter(platform: str) -> BasePlatformAdapter:
    """Return platform adapter instance or default to WhatsAppAdapter."""
    return PLATFORM_ADAPTERS.get(platform, PLATFORM_ADAPTERS['whatsapp'])
