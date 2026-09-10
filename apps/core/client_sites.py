"""Client website content and visual identity profiles.

Keep customer-facing copy here until a full website CMS is introduced. Each
profile is keyed by the tenant organization slug, so new clients can receive
a branded landing page without changing the page template.
"""

CLIENT_SITES = {
    "high-speed-internet-support": {
        "name": "High Speed Internet Support",
        "short_name": "HSIS",
        "eyebrow": "Connectivity support • Parañaque • Davao",
        "headline": "Keeping people connected. Keeping operations moving.",
        "description": "High Speed Internet Support delivers dependable internet support and field operations for customers and teams across its Parañaque and Davao locations.",
        "locations": ["Parañaque", "Davao"],
        "services": [
            ("Internet Support", "Responsive support for connectivity and service concerns."),
            ("Field Operations", "Local teams supporting customers and day-to-day service delivery."),
            ("Customer Care", "People-focused support built around fast, clear communication."),
        ],
        "primary": "#0ea5e9",
        "primary_dark": "#082f49",
        "accent": "#22d3ee",
        "surface": "#f0f9ff",
        "facebook": "https://web.facebook.com/profile.php?id=61552178101935",
    },
}


def get_client_site(slug, organization=None):
    profile = CLIENT_SITES.get(slug, {}).copy()
    if not profile and organization:
        profile = {
            "name": organization.name,
            "short_name": organization.name,
            "eyebrow": "People • Operations • Service",
            "headline": f"Welcome to {organization.name}",
            "description": "A connected client experience powered by BizFlow HRIS.",
            "locations": [],
            "services": [],
            "primary": "#2563eb",
            "primary_dark": "#0f172a",
            "accent": "#38bdf8",
            "surface": "#eff6ff",
            "facebook": "",
        }
    return profile
