from django.contrib.auth import authenticate, login, get_user_model
import logging

from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
from django.core import signing
from django.db import transaction
from django.http import JsonResponse
from django.utils.text import slugify
from django.core.mail import send_mail
from apps.organization.models import Organization, OrganizationMembership

from apps.organization.context import ACTIVE_ORGANIZATION_SESSION_KEY, current_membership

LOGIN_FAILURE_LIMIT = 5
LOGIN_FAILURE_WINDOW = 15 * 60
logger = logging.getLogger(__name__)


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
        try:
            failure_count = cache.get(throttle_key, 0)
        except Exception:
            # Authentication must not become a 500 just because the shared
            # throttling cache is temporarily unavailable. Readiness still
            # reports cache health so the infrastructure can replace/recover
            # an unhealthy instance.
            logger.exception('Login throttling cache unavailable during sign-in')
            failure_count = 0
        if failure_count >= LOGIN_FAILURE_LIMIT:
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
            try:
                cache.delete(throttle_key)
            except Exception:
                logger.exception('Login throttling cache unavailable while clearing failures')
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

        try:
            failures = cache.get(throttle_key, 0) + 1
            cache.set(throttle_key, failures, LOGIN_FAILURE_WINDOW)
        except Exception:
            logger.exception('Login throttling cache unavailable while recording failed sign-in')
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



@require_http_methods(['GET', 'POST'])
def signup(request):
    if request.user.is_authenticated:
        return redirect('workspace')
    if request.method == 'GET':
        return render(request, 'registration/signup.html')
    username = request.POST.get('email', '').strip().lower()
    password = request.POST.get('password', '')
    organization_name = request.POST.get('organization_name', '').strip()
    full_name = request.POST.get('name', '').strip()
    if not username or '@' not in username or len(password) < 12 or not organization_name or not full_name:
        return render(request, 'registration/signup.html', {'error': 'Provide a valid email, organization name, name, and a password of at least 12 characters.'}, status=400)
    if get_user_model().objects.filter(email__iexact=username).exists():
        return render(request, 'registration/signup.html', {'error': 'An account already exists for that email.'}, status=409)
    slug = slugify(organization_name)[:70] or 'organization'
    if Organization.objects.filter(slug=slug).exists():
        slug = f'{slug}-{signing.b62_encode(abs(hash(username)) % 10**8)}'[:80]
    with transaction.atomic():
        User = get_user_model()
        user = User.objects.create_user(username=username, email=username, password=password, first_name=full_name.split(' ', 1)[0], last_name=full_name.split(' ', 1)[1] if ' ' in full_name else '')
        user.is_active = False
        user.save(update_fields=('is_active',))
        organization = Organization.objects.create(name=organization_name, slug=slug)
        OrganizationMembership.objects.create(user=user, organization=organization, role=OrganizationMembership.Role.OWNER)
        token = signing.dumps({'user_id': user.pk, 'organization_id': organization.pk}, salt='bizflow-email-verification')
        verification_url = request.build_absolute_uri(f'/verify-email/{token}/')
        send_mail('Verify your BizFlow account', f'Verify your account: {verification_url}', None, [username], fail_silently=False)
    return render(request, 'registration/signup_done.html')
 
 
def verify_email(request, token):
    try:
        data = signing.loads(token, salt='bizflow-email-verification', max_age=60 * 60 * 24)
        user = get_user_model().objects.get(pk=data['user_id'], email__isnull=False)
        membership = OrganizationMembership.objects.get(user=user, organization_id=data['organization_id'], role=OrganizationMembership.Role.OWNER)
    except (signing.BadSignature, signing.SignatureExpired, get_user_model().DoesNotExist, OrganizationMembership.DoesNotExist):
        return render(request, 'registration/signup_done.html', {'error': 'This verification link is invalid or expired.'}, status=400)
    user.is_active = True
    user.save(update_fields=('is_active',))
    return redirect('login')
