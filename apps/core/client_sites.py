"""Client website content and visual identity profiles.

Each profile is keyed by the tenant organization slug. The first production
profile is High Speed Internet Support and can be replaced by organization
managed content when the website CMS is introduced.
"""

CLIENT_SITES = {
    "high-speed-internet-support": {
        "name": "High Speed Internet Support",
        "short_name": "HSIS",
        "eyebrow": "Internet support • customer service • Parañaque • Davao",
        "headline": "Keeping people connected. Keeping operations moving.",
        "description": "High Speed Internet Support provides customer-facing internet and technical support operations, with teams serving customers from its Parañaque and Davao locations.",
        "locations": [
            ("Parañaque", "35 Doña Soledad, Betterliving, Parañaque — Lido Cocina Tsina Building, 2nd Floor."),
            ("Davao", "Davao operations and support location."),
        ],
        "services": [
            ("Technical Support", "Troubleshooting support for internet connectivity, Wi-Fi, devices, gateways and routers."),
            ("Customer Support", "Clear, customer-focused assistance for service concerns, instructions and issue resolution."),
            ("Virtual Front Desk", "Professional front-desk and virtual support operations built around communication and customer satisfaction."),
        ],
        "primary": "#0ea5e9",
        "primary_dark": "#082f49",
        "accent": "#22d3ee",
        "surface": "#f0f9ff",
        "facebook": "https://web.facebook.com/profile.php?id=61552178101935",
        "website": "https://www.highspeedinternetsupportinc.com/",
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
            "website": "",
        }
    return profile
