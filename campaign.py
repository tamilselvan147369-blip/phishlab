"""Campaign related helper functions for PhishLab.

This module abstracts common campaign queries used by the Flask
application, keeping the view code tidy.
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from database import Campaign, Event, db

def get_campaign_stats():
    """Return a list of dictionaries with aggregated statistics for each
    campaign. The keys correspond to the values used by the dashboard
    template.
    """
    rows = db.session.query(
        Campaign.id,
        Campaign.name,
        func.count(Event.id).filter(Event.event_type == 'email_sent').label('emails_sent'),
        func.count(Event.id).filter(Event.event_type == 'email_opened').label('opens'),
        func.count(Event.id).filter(Event.event_type == 'demo_link_clicked').label('clicks'),
        func.count(Event.id).filter(Event.event_type == 'demo_form_submitted').label('submits')
    ).outerjoin(Event).group_by(Campaign.id).all()

    return [
        {
            'id': r.id,
            'name': r.name,
            'emails_sent': r.emails_sent,
            'opens': r.opens,
            'clicks': r.clicks,
            'submits': r.submits,
        }
        for r in rows
    ]
