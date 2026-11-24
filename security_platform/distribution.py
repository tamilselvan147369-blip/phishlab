"""Controlled message distribution and formatting across 6 messaging platforms."""

import urllib.parse
from typing import Dict, Any


DEFAULT_SCENARIO_TEMPLATES = {
    'whatsapp': {
        'title': 'Mandatory MFA Synchronization Check',
        'sender': 'Global Information Security',
        'handle': '+1 (555) 019-8234',
        'body': (
            'SECURITY ADVISORY: Your organizational multi-factor authentication (MFA) profile requires periodic verification. '
            'Please complete the authorized verification assessment within 24 hours: {testing_url}\n\n'
            'Authorized PhishLab Security Assessment. No real passwords will be requested.'
        ),
        'red_flags': '1. Unsolicited WhatsApp message from unknown mobile number\n2. Urgency pressure (24-hour limit)\n3. Moving corporate authentication onto social messaging',
        'explanation': 'Corporate IT operations use established internal helpdesk tickets and enterprise email, never unverified mobile WhatsApp messages.'
    },
    'telegram': {
        'title': 'Security Directory Account Review',
        'sender': 'Verification Officer',
        'handle': '@security_directory_bot',
        'body': (
            'NOTICE: Unrecognized sign-in detected on corporate VPN gateway. '
            'Confirm your current authorized device here: {testing_url}\n\n'
            'Internal Awareness Exercise. Do not share credentials or SMS codes.'
        ),
        'red_flags': '1. Foreign VPN login pretext\n2. Unsolicited Telegram bot outreach\n3. Demanding verification outside corporate intranet',
        'explanation': 'Telegram bots cannot authenticate internal VPN sessions. Always contact the SOC via documented internal channels.'
    },
    'linkedin': {
        'title': 'Executive Security Strategy Opportunity',
        'sender': 'Dr. Marcus Vance',
        'handle': 'Senior Talent Partner • Cyber Practice',
        'body': (
            'Dear Colleague, I reviewed your background in infrastructure security and would like to invite you '
            'to review the briefing specification for our VP Security opening: {testing_url}\n\n'
            'Please review the job parameters in the secure assessment portal.'
        ),
        'red_flags': '1. Flattering unsolicited executive outreach\n2. Unusually high compensation lure\n3. External link for confidential job description',
        'explanation': 'Attackers use executive headhunting pretexts to compromise senior technical personnel through external portals.'
    },
    'instagram': {
        'title': 'Copyright & Trademark Compliance Notice',
        'sender': 'Compliance Verification Hub',
        'handle': '@meta_compliance_review_test',
        'body': (
            'ALERT: Media used in your recent post has received a copyright claim. '
            'Review the claim and submit an appeal if this was an error: {testing_url}\n\n'
            'Authorized Security Training Simulation.'
        ),
        'red_flags': '1. Direct message copyright claim\n2. Pressure to appeal immediately\n3. External link instead of native app settings',
        'explanation': 'Social platforms handle legal and copyright notices strictly through native Account Settings, never through casual direct messages.'
    },
    'facebook_messenger': {
        'title': 'Business Page Administrative Review',
        'sender': 'Page Governance System',
        'handle': 'Administrative Support',
        'body': (
            'IMPORTANT: Your business page has been flagged for administrative review. '
            'Verify ownership to prevent publishing restrictions: {testing_url}\n\n'
            'Training exercise. Verify only through approved security procedures.'
        ),
        'red_flags': '1. Fear of publishing restrictions\n2. Demands clicking external verification link\n3. Unverified sender identity',
        'explanation': 'Page management notices must be confirmed through Meta Business Suite, not via incoming Messenger chats.'
    },
    'x': {
        'title': 'Premium Organization Checkmark Verification',
        'sender': 'X Verification Support',
        'handle': '@X_OrgSupport_Test',
        'body': (
            'Your organization verification status requires billing profile confirmation. '
            'Review your security checkpoint here: {testing_url}\n\n'
            'Security awareness drill. No billing details will be collected.'
        ),
        'red_flags': '1. Threat of losing verified status badge\n2. Spoofed support handle\n3. Direct message billing alert',
        'explanation': 'Billing notifications occur inside official billing portals, never through direct messages.'
    }
}


def build_distribution_payload(platform: str, participant_alias: str, testing_url: str, custom_body: str = None) -> Dict[str, Any]:
    """Generate platform-specific message body, direct dispatch action URL, and copyable text."""
    template = DEFAULT_SCENARIO_TEMPLATES.get(platform, DEFAULT_SCENARIO_TEMPLATES['whatsapp'])
    body_text = custom_body or template['body']
    formatted_body = body_text.replace('{testing_url}', testing_url)

    dispatch_link = ''
    encoded_text = urllib.parse.quote(formatted_body)

    if platform == 'whatsapp':
        dispatch_link = f"https://wa.me/?text={encoded_text}"
    elif platform == 'telegram':
        dispatch_link = f"https://t.me/share/url?url={urllib.parse.quote(testing_url)}&text={urllib.parse.quote(formatted_body)}"
    elif platform == 'x':
        dispatch_link = f"https://twitter.com/intent/tweet?text={encoded_text}"
    else:
        # Manual copy workflow for LinkedIn, Instagram, and Messenger where direct prefilled URL APIs are restricted
        dispatch_link = ''

    return {
        'platform': platform,
        'participant_alias': participant_alias,
        'testing_url': testing_url,
        'sender_name': template['sender'],
        'sender_handle': template['handle'],
        'scenario_title': template['title'],
        'formatted_body': formatted_body,
        'dispatch_link': dispatch_link,
        'red_flags': template['red_flags'],
        'explanation': template['explanation'],
    }
