"""Pre-configured educational scenarios, fictional profiles, and awareness questions
for the Multi-Platform Social Media Simulation Engine.
"""

from .models import (
    SocialSimulation, SocialMessageTemplate, SimulatedConversation,
    SimulatedMessage, utcnow_naive
)

DEFAULT_SCENARIOS = {
    'whatsapp': [
        {
            'title': 'IT Support Team (Urgent)',
            'type': 'one_to_one',
            'avatar': '📱',
            'subtitle': 'online',
            'messages': [
                {
                    'sender': 'Alex (IT Support Desk)',
                    'is_user': False,
                    'content': 'Hello, this is IT Support Desk. We detected unauthorized login attempts from a foreign IP address on your internal account. Please re-authenticate your 2FA profile immediately to avoid account lockout.',
                    'link': 'https://sso-portal-auth.test/verify-session',
                    'attachment': 'MFA_Emergency_Guide.pdf',
                    'att_type': 'pdf',
                    'status': 'read',
                    'is_suspicious': True,
                    'notes': 'Urgency tactic, unusual channel for IT support (WhatsApp rather than official company email/helpdesk ticket), external unverified link.'
                },
                {
                    'sender': 'Alex (IT Support Desk)',
                    'is_user': False,
                    'content': 'Please confirm once you have submitted your credentials.',
                    'status': 'read',
                    'is_suspicious': False,
                    'notes': ''
                }
            ]
        },
        {
            'title': 'Internal Team Social Club (Group)',
            'type': 'group',
            'avatar': '👥',
            'subtitle': '5 participants',
            'messages': [
                {
                    'sender': 'Jordan (Marketing)',
                    'is_user': False,
                    'content': 'Hey everyone! Don\'t forget lunch meetup at 1 PM today!',
                    'status': 'read',
                    'is_suspicious': False,
                    'notes': 'Normal baseline internal communication.'
                },
                {
                    'sender': 'Unknown Member (+1-555-0199)',
                    'is_user': False,
                    'content': 'Special exclusive staff holiday vouchers available here: https://corporate-rewards-gift.test/claim (Valid for next 15 mins only!)',
                    'link': 'https://corporate-rewards-gift.test/claim',
                    'status': 'read',
                    'is_suspicious': True,
                    'notes': 'Unknown phone number in group, time-limited artificial urgency, unverified free voucher link.'
                }
            ]
        }
    ],
    'instagram': [
        {
            'title': '@meta_security_alerts_test',
            'type': 'request',
            'avatar': '📸',
            'subtitle': 'Message Request • 2.4k followers',
            'is_request': True,
            'messages': [
                {
                    'sender': 'Instagram Security Review',
                    'handle': '@meta_security_alerts_test',
                    'is_user': False,
                    'content': 'Copyright Infringement Notice: Your account has been reported for using copyrighted media in your recent post. If you believe this is an error, appeal within 24 hours or your profile will be permanently deactivated.',
                    'link': 'https://instagram-appeal-center.test/submit-form',
                    'status': 'read',
                    'is_suspicious': True,
                    'notes': 'Official Instagram/Meta security notices appear inside the native App Settings -> Security, never through random Direct Message requests.'
                }
            ]
        },
        {
            'title': 'Luxe Brand Collaboration',
            'type': 'one_to_one',
            'avatar': '💎',
            'subtitle': 'Active 10m ago',
            'is_request': False,
            'messages': [
                {
                    'sender': 'Elena Vance (Talent Scout)',
                    'handle': '@luxe_ambassadors_test',
                    'is_user': False,
                    'content': 'Hi! We love your profile content and want to offer you a $2,500 ambassador contract. Click below to view contract terms and enter your bank details for direct payout.',
                    'link': 'https://influencer-sponsorship-portal.test/onboarding',
                    'attachment': 'Brand_Contract_Terms.pdf',
                    'att_type': 'pdf',
                    'status': 'read',
                    'is_suspicious': True,
                    'notes': 'Too-good-to-be-true offer, demands banking details upfront without prior interview or verified business contract.'
                }
            ]
        }
    ],
    'facebook_messenger': [
        {
            'title': 'IT Operations Security Notice',
            'type': 'one_to_one',
            'avatar': '💬',
            'subtitle': 'Typically replies instantly',
            'messages': [
                {
                    'sender': 'Messenger Security System',
                    'is_user': False,
                    'content': 'CRITICAL ALERT: Your Facebook page violates community guidelines. Verify your administrative identity immediately to avoid page deletion.',
                    'link': 'https://business-page-verification-center.test/review',
                    'status': 'read',
                    'is_suspicious': True,
                    'notes': 'Phishing attempt designed to hijack company social media pages through fear-based messaging.'
                }
            ]
        },
        {
            'title': 'Q4 Project Alpha Team',
            'type': 'group',
            'avatar': '🏢',
            'subtitle': '8 members',
            'messages': [
                {
                    'sender': 'Taylor Chen',
                    'is_user': False,
                    'content': 'Draft slides for tomorrow are attached. Please check slide 4.',
                    'attachment': 'Slides_Draft.pdf',
                    'att_type': 'pdf',
                    'status': 'read',
                    'is_suspicious': False,
                    'notes': 'Normal collaborative file sharing.'
                },
                {
                    'sender': 'Guest Participant',
                    'is_user': False,
                    'content': 'Here is the confidential employee compensation update sheet for everyone: https://hr-payroll-overview.test/view',
                    'link': 'https://hr-payroll-overview.test/view',
                    'status': 'read',
                    'is_suspicious': True,
                    'notes': 'Unsolicited sharing of sensitive internal payroll claims in a general work chat group.'
                }
            ]
        }
    ],
    'telegram': [
        {
            'title': 'Crypto VIP Signals Channel',
            'type': 'channel',
            'avatar': '✈️',
            'subtitle': '12,480 subscribers',
            'messages': [
                {
                    'sender': 'Channel Admin',
                    'is_user': False,
                    'content': '🔥 EMERGENCY AIRDROP: 500 USDT giveaway for active channel members! Connect your Web3 wallet now before quota runs out: https://claim-crypto-airdrop.test/wallet-connect',
                    'link': 'https://claim-crypto-airdrop.test/wallet-connect',
                    'status': 'read',
                    'is_suspicious': True,
                    'notes': 'High-risk crypto airdrop lure requiring seed phrase or wallet connection.'
                }
            ]
        },
        {
            'title': '@OfficialVerificationBot',
            'type': 'bot',
            'avatar': '🤖',
            'subtitle': 'bot',
            'messages': [
                {
                    'sender': 'Verification Bot',
                    'handle': '@OfficialVerificationBot',
                    'is_user': False,
                    'content': 'Telegram Security Bot: Unusual login attempt in Singapore. Please enter your Telegram SMS login code into this chat to confirm your identity.',
                    'status': 'read',
                    'is_suspicious': True,
                    'notes': 'Telegram explicitly warns users never to share login SMS codes with any chat or bot.'
                }
            ]
        }
    ],
    'x': [
        {
            'title': 'X Premium Verification Support',
            'type': 'one_to_one',
            'avatar': '✖️',
            'subtitle': '@X_Support_Notice_Test',
            'messages': [
                {
                    'sender': 'X Premium Support',
                    'handle': '@X_Support_Notice_Test',
                    'is_user': False,
                    'content': 'Important notice regarding your verified organization status. Your billing profile has expired. Update credit card details within 12 hours to maintain checkmark.',
                    'link': 'https://x-billing-portal-test.net/renew',
                    'status': 'read',
                    'is_suspicious': True,
                    'notes': 'Spoofed support handle, fear of losing status symbol, directs to unverified external billing domain.'
                }
            ]
        },
        {
            'title': 'Notification Simulation',
            'type': 'one_to_one',
            'avatar': '🔔',
            'subtitle': 'Direct Message',
            'messages': [
                {
                    'sender': 'Conference Organizer',
                    'handle': '@infosec_conf_2026',
                    'is_user': False,
                    'content': 'Thank you for attending the keynote today! Slide decks are published on GitHub.',
                    'status': 'read',
                    'is_suspicious': False,
                    'notes': 'Legitimate informational outreach.'
                }
            ]
        }
    ],
    'linkedin': [
        {
            'title': 'Dr. Marcus Vance (Global Talent Partners)',
            'type': 'recruitment',
            'avatar': '💼',
            'subtitle': 'Executive Talent Partner • 500+ connections',
            'messages': [
                {
                    'sender': 'Dr. Marcus Vance',
                    'is_user': False,
                    'content': 'Dear Colleague, I reviewed your professional background and believe you are an ideal candidate for our VP of Cyber Strategy position ($280k - $340k base + equity). Please review the job specification document attached and sign the non-disclosure agreement to proceed.',
                    'link': 'https://global-executive-talent.test/job-spec',
                    'attachment': 'Executive_Job_Description_NDA.pdf',
                    'att_type': 'pdf',
                    'status': 'read',
                    'is_suspicious': True,
                    'notes': 'High-profile lure, unsolicited executive recruitment, requests opening an external document or visiting unverified portal.'
                }
            ]
        },
        {
            'title': 'Sarah Jenkins (Cyber Security Guild)',
            'type': 'one_to_one',
            'avatar': '👩‍💼',
            'subtitle': 'Senior Security Consultant',
            'messages': [
                {
                    'sender': 'Sarah Jenkins',
                    'is_user': False,
                    'content': 'Hi! I saw your post on threat modeling methodologies. Would love to exchange insights if you are free for a virtual coffee next week.',
                    'status': 'read',
                    'is_suspicious': False,
                    'notes': 'Typical legitimate professional networking conversation.'
                }
            ]
        }
    ]
}

AWARENESS_QUIZZES = {
    'whatsapp': {
        'question': 'How should you verify an IT Support message received on WhatsApp asking you to authenticate credentials?',
        'options': [
            'Click the provided link immediately so you don\'t get locked out.',
            'Reply on WhatsApp with your username and password.',
            'Ignore the WhatsApp message and contact your company\'s verified internal IT Helpdesk via known corporate channels.',
            'Forward the message to all colleagues in your group chat.'
        ],
        'correct': 'Ignore the WhatsApp message and contact your company\'s verified internal IT Helpdesk via known corporate channels.',
        'explanation': 'Official corporate IT teams never use unverified social messaging apps like WhatsApp to request employee credentials or 2FA resets. Always verify through documented internal channels.'
    },
    'instagram': {
        'question': 'What is the primary indicator of a copyright or security infringement scam on Instagram?',
        'options': [
            'It comes from an unknown profile via Direct Message, while official notices only appear inside native App Settings.',
            'The message contains polite language.',
            'The profile has a profile picture.',
            'It asks you to like a post.'
        ],
        'correct': 'It comes from an unknown profile via Direct Message, while official notices only appear inside native App Settings.',
        'explanation': 'Meta and Instagram never send copyright strikes or account deactivation warnings via standard Direct Messages. Official notifications are delivered through Settings > Security > Emails from Instagram.'
    },
    'facebook_messenger': {
        'question': 'What should you do if an unfamiliar participant shares a "Confidential Employee Compensation" link in a workgroup chat?',
        'options': [
            'Click it immediately to see your salary.',
            'Do not click the link; report the message to the group administrator and security team.',
            'Share the link on social media.',
            'Download the attachment and open it on your personal laptop.'
        ],
        'correct': 'Do not click the link; report the message to the group administrator and security team.',
        'explanation': 'Curiosity and financial lures are common social engineering vectors. Malicious links shared in group chats should never be clicked.'
    },
    'telegram': {
        'question': 'When is it safe to share your Telegram login verification SMS code with a Telegram bot?',
        'options': [
            'Whenever the bot has "@Official" in its username.',
            'Only if the message mentions an unauthorized login from another country.',
            'Never; Telegram login codes must never be entered into any chat or shared with bots.',
            'If the bot sends you a free cryptocurrency token.'
        ],
        'correct': 'Never; Telegram login codes must never be entered into any chat or shared with bots.',
        'explanation': 'Authentication SMS and 2FA codes are private and strictly for the official Telegram login prompt. No bot or support agent ever legitimately requests them.'
    },
    'x': {
        'question': 'What is the best way to handle a DM claiming your account verification badge will be revoked unless you update credit card details via a link?',
        'options': [
            'Immediately enter your credit card on the linked webpage.',
            'Check your account status directly in your official X Settings/Billing dashboard without clicking the link.',
            'Tweet your password to customer support.',
            'Pay the fee with gift cards.'
        ],
        'correct': 'Check your account status directly in your official X Settings/Billing dashboard without clicking the link.',
        'explanation': 'Phishing attackers spoof platform branding to induce panic over account badges. Always navigate directly to the platform settings independently.'
    },
    'linkedin': {
        'question': 'What red flag suggests an executive job offer message on LinkedIn may be a social engineering attack?',
        'options': [
            'An extraordinarily high compensation offer for an unapplied position demanding you click an external link to sign an NDA.',
            'The recruiter has a professional title.',
            'The message is written in English.',
            'The job description specifies required skills.'
        ],
        'correct': 'An extraordinarily high compensation offer for an unapplied position demanding you click an external link to sign an NDA.',
        'explanation': 'Attackers frequently pose as recruiters with high-salary lures to deliver malicious attachments disguised as job descriptions or NDAs.'
    }
}

def seed_default_simulation(db_session):
    """Seed or return the master social media simulation campaign."""
    sim = SocialSimulation.query.filter_by(name='Master Multi-Platform Security Exercise').first()
    if sim:
        return sim

    sim = SocialSimulation(
        name='Master Multi-Platform Security Exercise',
        description='Comprehensive educational awareness simulation across WhatsApp, Instagram, Facebook Messenger, Telegram, X, and LinkedIn.',
        platforms='whatsapp,instagram,facebook_messenger,telegram,x,linkedin',
        status='active',
        created_at=utcnow_naive(),
    )
    db_session.add(sim)
    db_session.flush()

    for platform, conv_list in DEFAULT_SCENARIOS.items():
        for conv_data in conv_list:
            conv = SimulatedConversation(
                simulation_id=sim.id,
                platform=platform,
                conversation_type=conv_data.get('type', 'one_to_one'),
                title=conv_data['title'],
                sender_avatar=conv_data.get('avatar', '💬'),
                subtitle=conv_data.get('subtitle', ''),
                is_request=conv_data.get('is_request', False),
                created_at=utcnow_naive(),
            )
            db_session.add(conv)
            db_session.flush()

            for msg_data in conv_data.get('messages', []):
                msg = SimulatedMessage(
                    conversation_id=conv.id,
                    sender_name=msg_data['sender'],
                    sender_handle=msg_data.get('handle', ''),
                    sender_avatar=conv_data.get('avatar', '💬'),
                    is_from_user=msg_data.get('is_user', False),
                    content=msg_data['content'],
                    simulated_link=msg_data.get('link', ''),
                    attachment_name=msg_data.get('attachment', ''),
                    attachment_type=msg_data.get('att_type', ''),
                    read_status=msg_data.get('status', 'read'),
                    is_suspicious=msg_data.get('is_suspicious', False),
                    educational_notes=msg_data.get('notes', ''),
                    timestamp=utcnow_naive(),
                )
                db_session.add(msg)

    db_session.commit()
    return sim
