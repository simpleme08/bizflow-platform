from django.contrib.auth import authenticate, login
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from apps.organization.context import ACTIVE_ORGANIZATION_SESSION_KEY, current_membership

LOGIN_FAILURE_LIMIT = 5
LOGIN_FAILURE_WINDOW = 15 * 60


def _client_ip(request):
    return request.META.get('REMOTE_ADDR', 'unknown')


def _login_throttle_key(request, username):
    normalized = (username or '').strip().lower()[:150]
    return f'bizflow:login-failures:{_client_ip(request)}:{normalized}'


def _safe_next(request):
    next_url = request.GET.get('next') or request.POST.get('next') or request.session.get('post_login_next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return next_url
    return None


def login_page(request):
    if request.user.is_authenticated:
        if current_membership(request) is None:
            return redirect('organization-select')
        return redirect_for_user(request)

    next_url = request.GET.get('next') or request.POST.get('next')
    if request.method == 'POST':
        username = request.POST.get('username', '')
        throttle_key = _login_throttle_key(request, username)
        if cache.get(throttle_key, 0) >= LOGIN_FAILURE_LIMIT:
            return render(
                request,
                'registration/login.html',
                {'error': 'Too many failed login attempts. Try again later.', 'next': next_url},
                status=429,
            )

        user = authenticate(request, username=username, password=request.POST.get('password', ''))
        if user is not None and user.is_active:
            memberships = user.organization_memberships.filter(is_active=True, organization__is_active=True).select_related('organization').order_by('organization__name')
            if not memberships.exists():
                return render(request, 'registration/login.html', {'error': 'No active organization membership found.', 'next': next_url}, status=401)
            cache.delete(throttle_key)
            login(request, user)
            request.session.pop(ACTIVE_ORGANIZATION_SESSION_KEY, None)
            if memberships.count() > 1:
                if next_url:
                    request.session['post_login_next'] = next_url
                return redirect('organization-select')
            membership = memberships.first()
            request.session[ACTIVE_ORGANIZATION_SESSION_KEY] = str(membership.organization_id)
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)
            return redirect_for_user(request)

        failures = cache.get(throttle_key, 0) + 1
        cache.set(throttle_key, failures, LOGIN_FAILURE_WINDOW)
        return render(request, 'registration/login.html', {'error': 'Invalid username or password.', 'next': next_url}, status=401)
    return render(request, 'registration/login.html', {'next': next_url})


@require_http_methods(['GET', 'POST'])
def organization_select(request):
    if not request.user.is_authenticated:
        return redirect('login')
    memberships = request.user.organization_memberships.filter(is_active=True, organization__is_active=True).select_related('organization').order_by('organization__name')
    if not memberships.exists():
        return redirect('logout')
    if memberships.count() == 1:
        request.session[ACTIVE_ORGANIZATION_SESSION_KEY] = str(memberships.first().organization_id)
        return redirect(_safe_next(request) or workspace_url_for_user(request))
    if request.method == 'POST':
        organization_id = request.POST.get('organization_id', '').strip()
        membership = memberships.filter(organization_id=organization_id).first()
        if membership is None:
            return render(request, 'registration/organization_select.html', {'organizations': memberships, 'error': 'Select a valid organization.'}, status=400)
        request.session[ACTIVE_ORGANIZATION_SESSION_KEY] = str(membership.organization_id)
        next_url = _safe_next(request)
        request.session.pop('post_login_next', None)
        return redirect(next_url or workspace_url_for_user(request))
    return render(request, 'registration/organization_select.html', {'organizations': memberships})


def _user_from_request_or_user(request_or_user):
    return request_or_user.user if hasattr(request_or_user, 'user') else request_or_user


def workspace_url_for_user(request_or_user):
    """Return a workspace URL without ever guessing a tenant for multi-org users."""
    user = _user_from_request_or_user(request_or_user)
    if user.is_anonymous:
        return '/login/'
    if user.is_superuser:
        return '/workspace/'
    if hasattr(request_or_user, 'user'):
        membership = current_membership(request_or_user)
    else:
        memberships = user.organization_memberships.filter(is_active=True, organization__is_active=True)
        membership = memberships.first() if memberships.count() == 1 else None
    if membership is None:
        return '/login/'
    if membership.role == membership.Role.EMPLOYEE:
        return '/ess/'
    return '/workspace/'


def redirect_for_user(request):
    return redirect(workspace_url_for_user(request))


def employee_login(request):
    return redirect('login')
