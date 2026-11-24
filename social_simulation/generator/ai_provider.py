"""AI Provider Architecture for the Unified Social Media Simulation Generator.

Provides a provider-independent interface supporting Local Templates (default,
multilingual in English and Tamil with zero external dependencies), Google Gemini,
OpenAI, and Anthropic.
"""

import os
import json
import random
from abc import ABC, abstractmethod

# The 11 Educational Scenario Categories
SCENARIO_CATEGORIES = {
    'account_security': 'Account security awareness',
    'suspicious_login': 'Suspicious login notification',
    'fake_recruitment': 'Fake recruitment awareness',
    'job_opportunity': 'Job opportunity awareness',
    'payment_notification': 'Payment notification awareness',
    'delivery_notification': 'Delivery notification awareness',
    'prize_notification': 'Prize notification awareness',
    'suspicious_attachment': 'Suspicious attachment awareness',
    'social_engineering': 'Social engineering awareness',
    'urgency_pressure': 'Urgency and pressure tactics',
    'impersonation_warning': 'Impersonation warning awareness',
}

class BaseAIProvider(ABC):
    """Abstract base class for all scenario and message generator providers."""

    @abstractmethod
    def generate_scenario(
        self,
        category: str,
        platform: str,
        sender_name: str = None,
        tone: str = 'Urgent',
        language: str = 'en',
        complexity: str = 'Intermediate',
        custom_instructions: str = ''
    ) -> dict:
        """Generate a simulated social engineering scenario."""
        pass


class LocalTemplateProvider(BaseAIProvider):
    """High-reliability deterministic local template generator supporting English & Tamil.
    
    Provides rich, safe, educational training scenarios for all 11 categories across all 6
    platforms without requiring external network connectivity or paid API keys.
    """

    TEMPLATES = {
        'en': {
            'account_security': {
                'title': 'Account Security Audit Notification',
                'sender': 'Global IT Security Desk',
                'handle': '@security_verify_team',
                'avatar': '🔐',
                'content': 'URGENT SECURITY NOTICE: Your corporate directory credentials require immediate verification. Multi-Factor Authentication token synchronization was detected as out of date. Update your authentication profile within 15 minutes to prevent account freeze: https://corporate-auth-sync.test/mfa-portal',
                'link': 'https://corporate-auth-sync.test/mfa-portal',
                'attachment': '',
                'warning_indicators': '1. Artificial time limit (15 minutes)\n2. Unsolicited request to re-authenticate credentials\n3. External unverified .test link rather than internal SSO portal\n4. Threat of account freeze without prior manager communication',
                'educational_objective': 'Train employees to identify urgency tactics and unauthorized third-party authentication links.',
                'expected_action': 'Report message immediately to the internal security operations center (SOC).',
                'awareness_explanation': 'Legitimate IT security teams never demand credential re-entry through messaging platforms with short deadlines. Always verify authentication requests via standard corporate support channels.',
                'risk_category': 'Critical',
            },
            'suspicious_login': {
                'title': 'Unusual Location Login Alert',
                'sender': 'Account Security Bot',
                'handle': '@login_guard_alert',
                'avatar': '⚠️',
                'content': 'SECURITY ALERT: We observed an unrecognized sign-in to your profile from Frankfurt, Germany (IP: 185.220.101.4). If this was not you, terminate the remote session and reset your credentials immediately: https://profile-guardian-reset.test/session-kill',
                'link': 'https://profile-guardian-reset.test/session-kill',
                'attachment': '',
                'warning_indicators': '1. Foreign location fear tactic\n2. Urging immediate password reset on external link\n3. Lack of device fingerprint details\n4. Delivery via social messaging rather than native security settings',
                'educational_objective': 'Teach participants to inspect the origin of security alerts and avoid clicking panic-induced links.',
                'expected_action': 'Do not click the link; check active sessions directly in official security settings.',
                'awareness_explanation': 'Attackers routinely spoof login security alerts to cause panic and harvest user credentials. Real notifications should be reviewed inside native application settings.',
                'risk_category': 'High',
            },
            'fake_recruitment': {
                'title': 'Senior Executive Opportunity Lure',
                'sender': 'Marcus Vance (Executive Search)',
                'handle': '@vance_global_talent',
                'avatar': '💼',
                'content': 'Dear Colleague, your professional portfolio was shortlisted for a confidential VP of Engineering role ($320k base + performance shares). Please review the job brief and complete the candidate background authorization: https://global-executive-talent.test/job-spec',
                'link': 'https://global-executive-talent.test/job-spec',
                'attachment': 'Job_Specification_NDA.pdf',
                'warning_indicators': '1. Unsolicited executive outreach with disproportionately high salary\n2. Premature background check form\n3. External link requesting document signatures\n4. Vague company details without verified corporate domain',
                'educational_objective': 'Recognize recruitment-themed social engineering targeting senior staff.',
                'expected_action': 'Verify the recruiter on professional networks and request verified corporate email correspondence.',
                'awareness_explanation': 'Cyber adversaries pose as headhunters to target executives and engineers for intellectual property theft and credential harvesting.',
                'risk_category': 'High',
            },
            'job_opportunity': {
                'title': 'Remote Freelance Project Proposal',
                'sender': 'Sarah Lin (Creative Projects)',
                'handle': '@remote_freelance_scout',
                'avatar': '👩‍💻',
                'content': 'Hi! We have an immediate requirement for freelance security analysis work ($85/hour, fully remote, 10 hrs/week). Download the project scope and client confidentiality form to confirm your interest.',
                'link': '',
                'attachment': 'Project_Requirements_Scope.pdf',
                'warning_indicators': '1. Unsolicited high-paying freelance proposal\n2. Prompts downloading an unverified attachment\n3. Generic project description without corporate verification\n4. Pressure to confirm immediately before quota closes',
                'educational_objective': 'Train participants to exercise extreme caution before downloading attachments from unknown contacts.',
                'expected_action': 'Do not open attachments from unknown senders; request details in plain text.',
                'awareness_explanation': 'Malicious PDFs and weaponized documents are among the most common intrusion vectors in professional social networks.',
                'risk_category': 'Medium',
            },
            'payment_notification': {
                'title': 'Outstanding Invoice Settlement Notice',
                'sender': 'Corporate Accounts Payable',
                'handle': '@billing_settlements_dept',
                'avatar': '💳',
                'content': 'FINAL NOTICE: Your departmental vendor subscription invoice #INV-98243 remains unpaid ($1,850.00). Avoid service termination and late penalty charges by settling through our secure payment gateway: https://settlement-billing-desk.test/pay',
                'link': 'https://settlement-billing-desk.test/pay',
                'attachment': 'Invoice_98243_Summary.pdf',
                'warning_indicators': '1. Fear of service termination\n2. Final notice urgency pressure\n3. Routing payments through unknown external portal\n4. Unsolicited billing claims on social channels',
                'educational_objective': 'Reinforce corporate payment validation procedures and defense against Business Email Compromise (BEC).',
                'expected_action': 'Verify invoice validity directly with internal procurement or accounting teams.',
                'awareness_explanation': 'Financial lures use urgent payment demands to bypass standard internal audit and approval controls.',
                'risk_category': 'Critical',
            },
            'delivery_notification': {
                'title': 'Express Parcel Delivery Hold Notice',
                'sender': 'National Courier Logistics',
                'handle': '@express_delivery_hub',
                'avatar': '📦',
                'content': 'Your international package #PKG-449102 could not be dispatched due to missing customs clearance paperwork. Pay the $3.50 redelivery fee and update your shipping address to schedule delivery: https://courier-customs-track.test/release',
                'link': 'https://courier-customs-track.test/release',
                'attachment': '',
                'warning_indicators': '1. Small nominal fee lure ($3.50) designed to extract credit card details\n2. Urgency to avoid package return\n3. Unsolicited delivery claim for unremembered purchase\n4. Non-official courier URL',
                'educational_objective': 'Educate participants on package delivery scams used for mass financial harvesting.',
                'expected_action': 'Do not click the link; check official tracking numbers on legitimate courier portals.',
                'awareness_explanation': 'Smishing and social delivery scams exploit curiosity and small fee lures to steal payment card data.',
                'risk_category': 'Medium',
            },
            'prize_notification': {
                'title': 'Annual Technology Community Award',
                'sender': 'VIP Rewards Community',
                'handle': '@tech_community_rewards',
                'avatar': '🎁',
                'content': 'Congratulations! Your profile was randomly selected as a 1st tier recipient of the Annual Tech Community Appreciation Bonus ($1,000 Apple Gift Voucher). Claim your digital voucher before 23:59 tonight: https://tech-rewards-exclusive.test/claim-voucher',
                'link': 'https://tech-rewards-exclusive.test/claim-voucher',
                'attachment': '',
                'warning_indicators': '1. Unsolicited prize or giveaway win\n2. Tight expiration deadline (tonight at 23:59)\n3. Requires submitting personal information to claim voucher\n4. Too-good-to-be-true promise',
                'educational_objective': 'Train employees to resist greed and lottery-themed social engineering.',
                'expected_action': 'Ignore and report the message; legitimate lotteries do not award unsolicited prizes on social messaging.',
                'awareness_explanation': 'Free gift and prize scams seek personal identifiable information (PII) and corporate email registrations.',
                'risk_category': 'Medium',
            },
            'suspicious_attachment': {
                'title': 'Confidential Salary Benchmarking Review',
                'sender': 'HR Benefits Advisory',
                'handle': '@hr_payroll_benchmarks',
                'avatar': '📑',
                'content': 'Please review the updated 2026 confidential departmental compensation bands and executive equity benchmarks in the attached file before the all-hands briefing.',
                'link': '',
                'attachment': 'Executive_Compensation_2026.pdf',
                'warning_indicators': '1. Curiosity lure involving sensitive payroll data\n2. Distributed via unofficial social media message\n3. Prompts recipient to open an unverified document\n4. Lack of digital signature',
                'educational_objective': 'Demonstrate how curiosity about payroll or executive data is weaponized to deliver malware.',
                'expected_action': 'Do not open the attachment; verify with HR through official corporate directory channels.',
                'awareness_explanation': 'Compensation and organizational restructuring documents are prime vectors for spear phishing.',
                'risk_category': 'High',
            },
            'social_engineering': {
                'title': 'Executive Assistant Travel Assistance Request',
                'sender': 'Jordan Reed (Executive Operations)',
                'handle': '@jreed_exec_office',
                'avatar': '✈️',
                'content': 'Hey, I am traveling with the CIO and our hotel WiFi is blocking access to the internal ticketing portal. Can you quickly generate a temporary 2FA bypass code for his login and message it here? We need it for a customer emergency.',
                'link': '',
                'attachment': '',
                'warning_indicators': '1. Executive impersonation / authority pressure\n2. Traveling emergency pretext\n3. Requesting bypass of two-factor authentication (2FA)\n4. Moving off official helpdesk channels into social messaging',
                'educational_objective': 'Instill zero-trust discipline regarding access credentials and 2FA codes.',
                'expected_action': 'Refuse to share bypass codes; enforce documented identity verification procedures.',
                'awareness_explanation': 'Social engineers exploit helpfulness and executive urgency to persuade employees to bypass core security safeguards.',
                'risk_category': 'Critical',
            },
            'urgency_pressure': {
                'title': 'Mandatory Compliance Policy Acknowledgment',
                'sender': 'Compliance Oversight Directorate',
                'handle': '@policy_compliance_review',
                'avatar': '⚖️',
                'content': 'FINAL ESCALATION: Failure to sign the updated corporate code of ethics by 5:00 PM today will result in disciplinary suspension and system access revocation. Sign now: https://ethics-compliance-portal.test/sign',
                'link': 'https://ethics-compliance-portal.test/sign',
                'attachment': '',
                'warning_indicators': '1. Threat of disciplinary suspension\n2. Intense deadline pressure (5:00 PM today)\n3. External link disguised as internal portal\n4. Aggressive, intimidating tone',
                'educational_objective': 'Recognize intimidation and punitive pressure as hallmarks of social engineering attacks.',
                'expected_action': 'Pause and cross-reference compliance deadlines via the official internal intranet.',
                'awareness_explanation': 'Adversaries weaponize fear of disciplinary consequences to rush victims into careless security decisions.',
                'risk_category': 'High',
            },
            'impersonation_warning': {
                'title': 'Helpdesk Password Reset Request',
                'sender': 'Tech Support Tier 1',
                'handle': '@it_support_desk_help',
                'avatar': '🛠️',
                'content': 'Hello, we received a ticket indicating your mailbox is over storage capacity. To migrate your archive to cloud storage, reply with your current password and username.',
                'link': '',
                'attachment': '',
                'warning_indicators': '1. Direct request for plaintext password\n2. Generic storage quota pretext\n3. IT support contacting staff via informal social messaging\n4. Lack of official ticket reference',
                'educational_objective': 'Reiterate the foundational cybersecurity principle: legitimate IT staff never ask for passwords.',
                'expected_action': 'Immediately report the sender; never share passwords with anyone under any circumstances.',
                'awareness_explanation': 'Direct credential requests via chat are unequivocal indicators of social engineering.',
                'risk_category': 'Critical',
            }
        },
        'ta': {
            'account_security': {
                'title': 'கணக்கு பாதுகாப்பு எச்சரிக்கை (Account Security Alert)',
                'sender': 'நிறுவன IT பாதுகாப்பு பிரிவு (Corporate IT)',
                'handle': '@corporate_it_security',
                'avatar': '🔐',
                'content': 'அவசர பாதுகாப்பு அறிவிப்பு: உங்கள் நிறுவன கணக்கின் இரு-காரணி அங்கீகரிப்பு (2FA) காலாவதியாகிவிட்டது. உங்கள் கணக்கு முடக்கப்படுவதைத் தவிர்க்க அடுத்த 15 நிமிடங்களுக்குள் இந்த இணைப்பை கிளிக் செய்து அங்கீகரிக்கவும்: https://corporate-auth-sync.test/mfa-portal',
                'link': 'https://corporate-auth-sync.test/mfa-portal',
                'attachment': '',
                'warning_indicators': '1. 15 நிமிட அவசர காலக்கெடு\n2. கடவுச்சொல் மற்றும் 2FA சரிபார்ப்பு கோரிக்கை\n3. சரிபார்க்கப்படாத வெளிப்புற இணைப்பு (.test)\n4. சமூக வலைத்தள செய்தி மூலமான தொடர்பு',
                'educational_objective': 'அவசர அச்சுறுத்தல்களையும் போலி அங்கீகார இணைப்புகளையும் கண்டறிய பழகுதல்.',
                'expected_action': 'இணைப்பை கிளிக் செய்யாமல் பாதுகாப்பு குழுவிற்கு புகார் அளிக்கவும்.',
                'awareness_explanation': 'உண்மையான IT குழுக்கள் ஒருபோதும் குறுகிய நேர அவகாசத்துடன் சமூக ஊடகங்களில் கடவுச்சொல் சரிபார்ப்பைக் கோர மாட்டார்கள்.',
                'risk_category': 'Critical',
            },
            'suspicious_login': {
                'title': 'சந்தேகத்திற்கிடமான உள்நுழைவு எச்சரிக்கை (Suspicious Login Alert)',
                'sender': 'கணக்கு பாதுகாப்பு போட் (Security Bot)',
                'handle': '@account_guard_ta',
                'avatar': '⚠️',
                'content': 'பாதுகாப்பு எச்சரிக்கை: உங்கள் கணக்கில் புதிய சாதனத்திலிருந்து (ஜெர்மனி) உள்நுழைவு கண்டறியப்பட்டது. இது நீங்கள் இல்லையெனில் உடனே உங்கள் கணக்கை மீட்டெடுக்க இந்த இணைப்பை பயன்படுத்தவும்: https://profile-guardian-reset.test/session-kill',
                'link': 'https://profile-guardian-reset.test/session-kill',
                'attachment': '',
                'warning_indicators': '1. வெளிநாட்டு உள்நுழைவு பயம்\n2. உடனடியாக கடவுச்சொல்லை மாற்ற அழுத்தம்\n3. வெளிப்புற இணைப்பு',
                'educational_objective': 'போலி உள்நுழைவு எச்சரிக்கைகளை உண்மையான செயலி அமைப்புகளில் மட்டும் சரிபார்க்க பழகுதல்.',
                'expected_action': 'இணைப்பை தவிர்க்கவும்; அதிகாரப்பூர்வ அமைப்புகளில் உள்நுழைவு வரலாற்றை பார்க்கவும்.',
                'awareness_explanation': 'தாக்குபவர்கள் பீதியை ஏற்படுத்தி கடவுச்சொற்களை திருட போலி உள்நுழைவு எச்சரிக்கைகளை அனுப்புகின்றனர்.',
                'risk_category': 'High',
            },
            'fake_recruitment': {
                'title': 'போலி வேலைவாய்ப்பு அறிவிப்பு (Fake Job Offer)',
                'sender': 'குளோபல் டேலண்ட் பார்ட்னர்ஸ் (Global Talent)',
                'handle': '@talent_partners_ta',
                'avatar': '💼',
                'content': 'வணக்கம், உங்கள் சுயவிவரம் எங்கள் நிறுவனத்தின் உயர் பதவிக்கு தேர்ந்தெடுக்கப்பட்டுள்ளது (ஆண்டு ஊதியம் ₹25,00,000). வேலை விவரங்களைப் பார்த்து உறுதி செய்ய இணைப்பை கிளிக் செய்யவும்: https://global-executive-talent.test/job-spec',
                'link': 'https://global-executive-talent.test/job-spec',
                'attachment': 'Job_Description.pdf',
                'warning_indicators': '1. எதிர்பாராத அதிக சம்பள வேலை வாய்ப்பு\n2. ஆவண கையொப்ப கோரிக்கை\n3. சரிபார்க்கப்படாத வெளிப்புற இணைப்பு',
                'educational_objective': 'சமூக ஊடகங்கள் வழி வரும் போலி வேலை வாய்ப்புகளை அடையாளம் காணுதல்.',
                'expected_action': 'அழைப்பை நிராகரிக்கவும்; அதிகாரப்பூர்வ மின்னஞ்சல் முகவரியை சரிபார்க்கவும்.',
                'awareness_explanation': 'அதிக ஊதிய ஆசை காட்டி தனிநபர் விவரங்களை திருடுவது வழக்கமான சமூக பொறியியல் தந்திரமாகும்.',
                'risk_category': 'High',
            },
            'payment_notification': {
                'title': 'கட்டண நிலுவை எச்சரிக்கை (Payment Due Notice)',
                'sender': 'கணக்கு பிரிவு (Finance Dept)',
                'handle': '@finance_billing_ta',
                'avatar': '💳',
                'content': 'இறுதி அறிவிப்பு: உங்கள் சந்தா கட்டணம் ₹12,500 நிலுவையில் உள்ளது. சேவை துண்டிக்கப்படுவதை தவிர்க்க உடனே கட்டணம் செலுத்தவும்: https://settlement-billing-desk.test/pay',
                'link': 'https://settlement-billing-desk.test/pay',
                'attachment': 'Bill_Summary.pdf',
                'warning_indicators': '1. சேவை துண்டிப்பு அச்சுறுத்தல்\n2. அவசர கட்டண கோரிக்கை\n3. அதிகாரப்பூர்வமற்ற கட்டண தளம்',
                'educational_objective': 'அவசர பண பரிவர்த்தனை கோரிக்கைகளை நேரடியாக சரிபார்க்க பழகுதல்.',
                'expected_action': 'கணக்கு பிரிவை அதிகாரப்பூர்வமாக தொடர்புகொண்டு சரிபார்க்கவும்.',
                'awareness_explanation': 'பண மோசடி தாக்குதல்கள் அவசரத்தை பயன்படுத்தி போலி கட்டண தளங்களுக்கு வழிநடத்துகின்றன.',
                'risk_category': 'Critical',
            },
            'prize_notification': {
                'title': 'பரிசு வென்றதற்கான அறிவிப்பு (Prize Notification)',
                'sender': 'சமூக வெகுமதி பிரிவு (Rewards Hub)',
                'handle': '@rewards_official_ta',
                'avatar': '🎁',
                'content': 'வாழ்த்துக்கள்! சமூக ஊடக கணக்கு பயனர்களில் நீங்கள் ₹50,000 மதிப்புள்ள பரிசு வவுச்சரை வென்றுள்ளீர்கள். உங்கள் பரிசை பெற இன்றிரவு 12 மணிக்குள் பதிவு செய்யவும்: https://tech-rewards-exclusive.test/claim-voucher',
                'link': 'https://tech-rewards-exclusive.test/claim-voucher',
                'attachment': '',
                'warning_indicators': '1. எதிர்பாராத பரிசு அறிவிப்பு\n2. குறுகிய காலக்கெடு\n3. தனிநபர் விவரங்களை கோரும் இணைப்பு',
                'educational_objective': 'இலவச பரிசு வலைகளை புறக்கணிக்க கற்றுக்கொடுத்தல்.',
                'expected_action': 'செய்தியை புறக்கணித்து புகார் அளிக்கவும்.',
                'awareness_explanation': 'எந்தவொரு நியாயமான நிறுவனமும் சமூக வலைதள குறுஞ்செய்திகளில் பணப் பரிசுகளை வழங்காது.',
                'risk_category': 'Medium',
            }
        }
    }

    def generate_scenario(
        self,
        category: str,
        platform: str,
        sender_name: str = None,
        tone: str = 'Urgent',
        language: str = 'en',
        complexity: str = 'Intermediate',
        custom_instructions: str = ''
    ) -> dict:
        """Generate scenario using validated educational template dictionary."""
        lang_dict = self.TEMPLATES.get(language, self.TEMPLATES['en'])
        template = lang_dict.get(category, self.TEMPLATES['en'].get(category, self.TEMPLATES['en']['account_security']))

        sender = sender_name.strip() if sender_name and sender_name.strip() else template['sender']
        
        # Adapt link to platform if necessary
        simulated_link = template.get('link', '')
        if simulated_link and platform:
            simulated_link = f"https://{platform}-security-checkpoint.test/verify-auth"

        return {
            'title': f"{template['title']} ({platform.title()})",
            'category': category,
            'category_display': SCENARIO_CATEGORIES.get(category, category),
            'platform': platform,
            'fictional_sender': sender,
            'sender_handle': template.get('handle', f"@{sender.lower().replace(' ', '_')}"),
            'sender_avatar': template.get('avatar', '🛡️'),
            'message_content': template['content'],
            'language': language,
            'simulated_link': simulated_link,
            'simulated_attachment': template.get('attachment', ''),
            'attachment_type': 'pdf' if template.get('attachment') else '',
            'warning_indicators': template['warning_indicators'],
            'educational_objective': template['educational_objective'],
            'expected_action': template['expected_action'],
            'awareness_explanation': template['awareness_explanation'],
            'risk_category': template.get('risk_category', 'High'),
            'complexity_level': complexity,
            'tone': tone,
            'provider': 'LocalTemplateProvider (Safe Fallback)'
        }


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI integration with automatic local template fallback."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY') or os.getenv('PHISHLAB_AI_API_KEY')
        self.fallback = LocalTemplateProvider()

    def generate_scenario(
        self,
        category: str,
        platform: str,
        sender_name: str = None,
        tone: str = 'Urgent',
        language: str = 'en',
        complexity: str = 'Intermediate',
        custom_instructions: str = ''
    ) -> dict:
        if not self.api_key:
            return self.fallback.generate_scenario(category, platform, sender_name, tone, language, complexity, custom_instructions)

        try:
            import urllib.request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            
            prompt = (
                f"You are a cybersecurity awareness training expert. Generate a simulated, educational phishing scenario "
                f"for security awareness training (NON-DEPLOYABLE, SAFE SIMULATION).\n"
                f"Platform: {platform}\n"
                f"Category: {SCENARIO_CATEGORIES.get(category, category)}\n"
                f"Language: {language}\n"
                f"Tone: {tone}\n"
                f"Complexity: {complexity}\n"
                f"Fictional Sender: {sender_name or 'Default'}\n"
                f"Instructions: {custom_instructions}\n\n"
                f"Return ONLY valid JSON matching this schema:\n"
                f"{{\n"
                f"  \"title\": \"Scenario Title\",\n"
                f"  \"fictional_sender\": \"Name\",\n"
                f"  \"sender_handle\": \"@handle\",\n"
                f"  \"message_content\": \"Simulated message text\",\n"
                f"  \"simulated_link\": \"https://safe-training-portal.test/link\",\n"
                f"  \"simulated_attachment\": \"Document.pdf or empty\",\n"
                f"  \"warning_indicators\": \"List of red flags\",\n"
                f"  \"educational_objective\": \"Goal\",\n"
                f"  \"expected_action\": \"Recommended action\",\n"
                f"  \"awareness_explanation\": \"Why this is suspicious\",\n"
                f"  \"risk_category\": \"High\"\n"
                f"}}"
            )

            req_data = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}]
            }).encode('utf-8')

            req = urllib.request.Request(url, data=req_data, headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=8) as response:
                result = json.loads(response.read().decode('utf-8'))
                raw_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                if raw_text.startswith('```json'):
                    raw_text = raw_text[7:]
                if raw_text.startswith('```'):
                    raw_text = raw_text[3:]
                if raw_text.endswith('```'):
                    raw_text = raw_text[:-3]
                parsed = json.loads(raw_text.strip())
                parsed.update({
                    'category': category,
                    'category_display': SCENARIO_CATEGORIES.get(category, category),
                    'platform': platform,
                    'language': language,
                    'tone': tone,
                    'complexity_level': complexity,
                    'sender_avatar': '🛡️',
                    'provider': 'Google Gemini API'
                })
                return parsed
        except Exception:
            # Safe degradation to local verified templates
            res = self.fallback.generate_scenario(category, platform, sender_name, tone, language, complexity, custom_instructions)
            res['provider'] = 'LocalTemplateProvider (Gemini fallback)'
            return res


class OpenAIProvider(BaseAIProvider):
    """OpenAI API integration with automatic local fallback."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY') or os.getenv('PHISHLAB_AI_API_KEY')
        self.fallback = LocalTemplateProvider()

    def generate_scenario(
        self,
        category: str,
        platform: str,
        sender_name: str = None,
        tone: str = 'Urgent',
        language: str = 'en',
        complexity: str = 'Intermediate',
        custom_instructions: str = ''
    ) -> dict:
        if not self.api_key:
            return self.fallback.generate_scenario(category, platform, sender_name, tone, language, complexity, custom_instructions)

        try:
            import urllib.request
            url = "https://api.openai.com/v1/chat/completions"
            
            prompt = (
                f"Generate a simulated security training scenario for {platform}. Category: {category}. "
                f"Language: {language}. Output strictly valid JSON."
            )

            req_data = json.dumps({
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }).encode('utf-8')

            req = urllib.request.Request(
                url, data=req_data,
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {self.api_key}'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                result = json.loads(response.read().decode('utf-8'))
                raw_text = result['choices'][0]['message']['content'].strip()
                parsed = json.loads(raw_text)
                parsed.update({'category': category, 'platform': platform, 'provider': 'OpenAI API'})
                return parsed
        except Exception:
            res = self.fallback.generate_scenario(category, platform, sender_name, tone, language, complexity, custom_instructions)
            res['provider'] = 'LocalTemplateProvider (OpenAI fallback)'
            return res


def get_ai_provider(provider_type: str = None) -> BaseAIProvider:
    """Factory to retrieve configured AI scenario generator provider."""
    ptype = (provider_type or os.getenv('AI_PROVIDER', 'local')).lower()
    if ptype == 'gemini':
        return GeminiProvider()
    elif ptype == 'openai':
        return OpenAIProvider()
    return LocalTemplateProvider()
