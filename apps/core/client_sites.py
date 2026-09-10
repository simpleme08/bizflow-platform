"""Client website content and visual identity profiles.

Each profile is keyed by the tenant organization slug. The first production
profile is High Speed Internet Support and can be replaced by organization
managed content when the website CMS is introduced.
"""

CLIENT_SITES = {
    "high-speed-internet-support": {
        "name": "High Speed Internet Support",
        "short_name": "HSIS",
        "eyebrow": "Hotel support • Virtual front desk • Technical support",
        "headline": "Smarter hotel support. Better guest experiences.",
        "description": "HSIS provides virtual front desk agents, kiosk-enabled guest support, and dedicated technical support agents for hotels across the United States. Our teams help hotel operations stay connected, responsive, and guest-focused 24/7.",
        "mission": "Our Mission is to deliver an outstanding customer experience beyond expectation while transforming the hospitality industry by providing the best in technological solutions.",
        "vision": "Technology and people working together to make hotel operations simpler, faster, and more guest-friendly.",
        "locations": [
            ("Parañaque", "35 Doña Soledad, Betterliving, Parañaque — Lido Cocina Tsina Building, 2nd Floor."),
            ("Davao", "Davao City, Philippines — operations and support center."),
        ],
        "services": [
            ("Virtual Front Desk Agents", "Professional agents support hotel guests with front-desk interactions, inquiries, reservations, check-in guidance, and service concerns."),
            ("Kiosk Technology", "Self-service hotel kiosks help accelerate check-in, check-out, room-key access, and guest transactions with or without human assistance."),
            ("Technical Support Agents", "Dedicated technical support agents troubleshoot connectivity, Wi-Fi, devices, networks, PMS and other hotel technology issues."),
            ("Internet & Network Support", "Connectivity-focused support for internet access, routers, Wi-Fi and network issues that can affect hotel guests and operations."),
            ("Hotel Systems Support", "Technology assistance for the systems and devices hotel teams rely on to deliver smooth day-to-day service."),
            ("Guest Experience Support", "People-first assistance designed to keep guests informed, supported, and connected throughout their hotel experience."),
        ],
        "advantages": [
            ("Hotel-focused teams", "Support designed around hospitality operations and guest experience."),
            ("Technology + people", "Kiosks accelerate routine processes while trained agents handle the moments that need human assistance."),
            ("Nationwide reach", "Dedicated support for hotels across the United States."),
            ("24/7 support", "Responsive virtual front desk and technical support for hotel operations."),
        ],
        "primary": "#0066d6",
        "primary_dark": "#062a63",
        "accent": "#18c9ef",
        "surface": "#eef7ff",
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
            "mission": "",
            "vision": "",
            "locations": [],
            "services": [],
            "advantages": [],
            "primary": "#2563eb",
            "primary_dark": "#0f172a",
            "accent": "#38bdf8",
            "surface": "#eff6ff",
            "facebook": "",
            "website": "",
        }
    return profile
