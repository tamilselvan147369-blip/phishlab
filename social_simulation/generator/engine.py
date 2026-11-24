"""Unified Simulation Generator Engine.

Orchestrates AI scenario generation, platform-specific formatting, database persistence,
and direct campaign creation across all six social platforms.
"""

from typing import List, Dict, Any
from database import db
from ..models import (
    SocialSimulation, SimulatedConversation, SimulatedMessage,
    GeneratedScenario, GeneratedMessage, SOCIAL_PLATFORMS, utcnow_naive
)
from .ai_provider import get_ai_provider, SCENARIO_CATEGORIES
from .adapters import get_platform_adapter, PLATFORM_ADAPTERS


class UnifiedSimulationEngine:
    """Core generator engine unifying all six social platforms."""

    @staticmethod
    def generate_scenario(
        category: str,
        platform: str,
        sender_name: str = None,
        tone: str = 'Urgent',
        language: str = 'en',
        complexity: str = 'Intermediate',
        custom_instructions: str = '',
        provider_type: str = 'local'
    ) -> Dict[str, Any]:
        """Generate a complete educational scenario using the requested AI provider."""
        provider = get_ai_provider(provider_type)
        scenario = provider.generate_scenario(
            category=category,
            platform=platform,
            sender_name=sender_name,
            tone=tone,
            language=language,
            complexity=complexity,
            custom_instructions=custom_instructions
        )

        # Attach formatted previews for all platforms
        adapter = get_platform_adapter(platform)
        preview_data = adapter.format_preview(scenario)
        scenario['preview'] = preview_data
        return scenario

    @staticmethod
    def format_for_all_platforms(scenario: Dict[str, Any], platforms: List[str] = None) -> Dict[str, Any]:
        """Generate platform-specific rendering previews for every selected platform."""
        target_platforms = platforms or list(SOCIAL_PLATFORMS.keys())
        results = {}
        for p in target_platforms:
            adapter = get_platform_adapter(p)
            results[p] = adapter.format_preview(scenario)
        return results

    @staticmethod
    def save_scenario(data: Dict[str, Any], is_template: bool = False) -> GeneratedScenario:
        """Persist a generated or edited scenario to the database."""
        scenario = GeneratedScenario(
            title=data.get('title', 'Security Awareness Scenario'),
            category=data.get('category', 'account_security'),
            platform=data.get('platform', 'whatsapp'),
            fictional_sender=data.get('fictional_sender', 'Security Officer'),
            sender_handle=data.get('sender_handle', ''),
            sender_avatar=data.get('sender_avatar', '🛡️'),
            message_content=data.get('message_content', ''),
            language=data.get('language', 'en'),
            simulated_link=data.get('simulated_link', ''),
            simulated_attachment=data.get('simulated_attachment', ''),
            attachment_type=data.get('attachment_type', 'pdf'),
            warning_indicators=data.get('warning_indicators', ''),
            educational_objective=data.get('educational_objective', ''),
            expected_action=data.get('expected_action', ''),
            awareness_explanation=data.get('awareness_explanation', ''),
            risk_category=data.get('risk_category', 'High'),
            complexity_level=data.get('complexity_level', 'Intermediate'),
            tone=data.get('tone', 'Urgent'),
            is_saved_template=is_template,
            created_at=utcnow_naive()
        )
        db.session.add(scenario)
        db.session.commit()
        return scenario

    @staticmethod
    def create_campaign_from_scenario(
        scenario_id: int,
        campaign_name: str,
        platforms: List[str] = None
    ) -> SocialSimulation:
        """Turn a generated scenario directly into an active SocialSimulation campaign."""
        scenario = db.session.get(GeneratedScenario, scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found.")

        target_platforms = platforms or [scenario.platform]
        platform_str = ','.join(target_platforms)

        sim = SocialSimulation(
            name=campaign_name or f"Campaign: {scenario.title}",
            description=f"Generated from category '{scenario.category}' ({scenario.language.upper()})",
            platforms=platform_str,
            status='active',
            created_at=utcnow_naive()
        )
        db.session.add(sim)
        db.session.flush()

        # Build conversations for each platform
        for p in target_platforms:
            conv = SimulatedConversation(
                simulation_id=sim.id,
                platform=p,
                conversation_type='one_to_one',
                title=f"{scenario.fictional_sender}",
                sender_avatar=scenario.sender_avatar or '🛡️',
                subtitle='Verified Security Simulation',
                is_request=(p == 'instagram' and 'request' in scenario.title.lower()),
                created_at=utcnow_naive()
            )
            db.session.add(conv)
            db.session.flush()

            msg = SimulatedMessage(
                conversation_id=conv.id,
                sender_name=scenario.fictional_sender,
                sender_handle=scenario.sender_handle,
                sender_avatar=scenario.sender_avatar,
                is_from_user=False,
                content=scenario.message_content,
                simulated_link=scenario.simulated_link or f"https://{p}-training-verify.test/auth",
                attachment_name=scenario.simulated_attachment,
                attachment_type=scenario.attachment_type or 'pdf',
                read_status='read',
                is_suspicious=True,
                educational_notes=scenario.awareness_explanation,
                timestamp=utcnow_naive()
            )
            db.session.add(msg)

        db.session.commit()
        return sim
