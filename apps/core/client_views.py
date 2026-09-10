from django.http import Http404
from django.shortcuts import render

from apps.organization.models import Organization

from .client_sites import get_client_site


def client_site(request, slug):
    organization = Organization.objects.filter(slug=slug, is_active=True).first()
    profile = get_client_site(slug, organization)
    if not profile:
        raise Http404('Client website not found.')
    return render(request, 'client_site.html', {
        'organization': organization,
        'profile': profile,
        'login_url': f'/login/?org={slug}',
        'clock_url': f'/clock/?org={slug}',
    })
