from django.shortcuts import get_object_or_404, render

from apps.organization.models import Organization

from .client_sites import get_client_site


def client_site(request, slug):
    organization = get_object_or_404(Organization, slug=slug, is_active=True)
    profile = get_client_site(slug, organization)
    return render(request, 'client_site.html', {
        'organization': organization,
        'profile': profile,
        'login_url': f'/login/?org={organization.slug}',
        'clock_url': f'/clock/?org={organization.slug}',
    })
