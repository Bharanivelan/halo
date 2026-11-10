"""Fixed vocabularies (DD-19). Single source for backend validation and GET /reference."""
from enum import StrEnum


class Role(StrEnum):
    admin = "admin"
    manager = "manager"
    rep = "rep"


class Offering(StrEnum):
    corporate_rate = "corporate_rate"
    mice = "mice"
    long_stay = "long_stay"
    fnb = "fnb"


OFFERING_LABELS = {
    "corporate_rate": "Corporate rate agreement",
    "mice": "Meetings & events (MICE)",
    "long_stay": "Long stay / project accommodation",
    "fnb": "F&B and catering",
}


class AccountStatus(StrEnum):
    discovered = "discovered"
    qualified = "qualified"
    contact_identified = "contact_identified"
    outreach_prepared = "outreach_prepared"
    outreach_sent = "outreach_sent"
    engaged = "engaged"
    dismissed = "dismissed"


ACCOUNT_STATUS_LABELS = {
    "discovered": "Discovered", "qualified": "Qualified", "contact_identified": "Contact identified",
    "outreach_prepared": "Outreach prepared", "outreach_sent": "Outreach sent", "engaged": "Engaged",
    "dismissed": "Dismissed",
}


class OpportunityStage(StrEnum):
    interested = "interested"
    meeting_scheduled = "meeting_scheduled"
    negotiation = "negotiation"
    won = "won"
    lost = "lost"


STAGE_LABELS = {
    "interested": "Interested", "meeting_scheduled": "Meeting scheduled",
    "negotiation": "Negotiation", "won": "Won", "lost": "Lost",
}

DISMISS_REASONS = {
    "not_relevant_industry": "Not a relevant industry", "too_small": "Too small", "too_far": "Too far",
    "already_customer": "Already a customer", "competitor_relationship": "Tied to a competitor hotel",
    "bad_data": "Bad or wrong data", "duplicate": "Duplicate", "other": "Other",
}

LOSS_REASONS = {
    "price": "Price", "location": "Location", "existing_hotel_contract": "Existing hotel contract",
    "no_current_need": "No current need", "chose_competitor": "Chose a competitor",
    "no_response": "No response", "other": "Other",
}

# code -> (label, default relevance per offering 0..1)
INDUSTRIES: dict[str, tuple[str, dict[str, float]]] = {
    "it_services": ("IT services", {"corporate_rate": 0.95, "mice": 0.7, "long_stay": 0.8, "fnb": 0.5}),
    "it_product_saas": ("IT product / SaaS", {"corporate_rate": 0.75, "mice": 0.6, "long_stay": 0.5, "fnb": 0.5}),
    "ites_bpo": ("ITES / BPO", {"corporate_rate": 0.7, "mice": 0.6, "long_stay": 0.8, "fnb": 0.5}),
    "engineering_rnd": ("Engineering & R&D", {"corporate_rate": 0.9, "mice": 0.6, "long_stay": 0.85, "fnb": 0.4}),
    "manufacturing_automotive": ("Manufacturing · automotive", {"corporate_rate": 0.85, "mice": 0.5, "long_stay": 0.8, "fnb": 0.4}),
    "manufacturing_electronics": ("Manufacturing · electronics", {"corporate_rate": 0.85, "mice": 0.5, "long_stay": 0.8, "fnb": 0.4}),
    "manufacturing_other": ("Manufacturing · other", {"corporate_rate": 0.75, "mice": 0.4, "long_stay": 0.7, "fnb": 0.4}),
    "consulting_professional": ("Consulting & professional services", {"corporate_rate": 0.95, "mice": 0.8, "long_stay": 0.5, "fnb": 0.6}),
    "bfsi_operations": ("Banking, finance & insurance", {"corporate_rate": 0.8, "mice": 0.8, "long_stay": 0.4, "fnb": 0.6}),
    "healthcare_hospital": ("Healthcare & hospitals", {"corporate_rate": 0.6, "mice": 0.6, "long_stay": 0.6, "fnb": 0.3}),
    "education": ("Education", {"corporate_rate": 0.4, "mice": 0.8, "long_stay": 0.5, "fnb": 0.5}),
    "logistics": ("Logistics", {"corporate_rate": 0.6, "mice": 0.4, "long_stay": 0.5, "fnb": 0.3}),
    "real_estate_coworking": ("Real estate & coworking", {"corporate_rate": 0.5, "mice": 0.6, "long_stay": 0.4, "fnb": 0.5}),
    "events_agency": ("Events agency", {"corporate_rate": 0.4, "mice": 1.0, "long_stay": 0.2, "fnb": 0.8}),
    "travel_management": ("Travel management", {"corporate_rate": 0.9, "mice": 0.7, "long_stay": 0.6, "fnb": 0.3}),
    "other": ("Other", {"corporate_rate": 0.3, "mice": 0.3, "long_stay": 0.3, "fnb": 0.3}),
}

EMPLOYEE_RANGES = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1001-5000", "5000+"]

# signal_type -> (label, implied offerings, default strength, half-life days)
SIGNAL_TYPES: dict[str, tuple[str, list[str], float, int]] = {
    "new_office_or_center": ("New office or centre", ["corporate_rate", "long_stay", "mice"], 1.0, 180),
    "facility_expansion": ("Facility expansion", ["corporate_rate", "long_stay"], 0.9, 180),
    "hiring_drive": ("Hiring drive", ["long_stay", "mice"], 0.7, 90),
    "event_or_conference": ("Event or conference", ["mice"], 0.9, 60),
    "new_project_or_client": ("New project or client", ["corporate_rate"], 0.6, 120),
    "leadership_or_hq_visit": ("Leadership or HQ visit", ["corporate_rate", "fnb"], 0.4, 60),
    "funding_or_growth": ("Funding or growth", ["corporate_rate", "mice"], 0.5, 120),
    "relocation": ("Staff relocation", ["long_stay"], 0.8, 120),
}

ROLE_CODES = {
    "founder_ceo": "Founder / CEO",
    "operations_head": "Operations Head",
    "admin_facilities": "Admin / Facilities Manager",
    "travel_desk": "Travel desk / Travel Manager",
    "procurement": "Procurement",
    "hr_manager": "HR Manager",
    "talent_acquisition": "HR / Talent Acquisition",
    "events_marketing": "Events / Marketing Manager",
    "plant_head": "Plant Head",
}

CLAIM_FIELDS = {
    "website": "Website",
    "description": "Description",
    "industry": "Industry",
    "employee_range": "Employees",
    "local_presence": "Local presence",
    "hq_location": "Headquarters",
    "other_locations": "Other locations",
    "client_facing_services": "Client-facing services",
    "has_training_or_onboarding": "Training / onboarding",
    "hosts_events": "Hosts events",
    "business_activities": "Business activities",
    "notable_clients_or_partners": "Clients & partners",
    "travel_indicators": "Travel indicators",
}
KEY_FIELDS = ["industry", "employee_range", "local_presence", "hq_location"]
