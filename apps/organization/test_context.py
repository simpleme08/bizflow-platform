from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from .context import ACTIVE_ORGANIZATION_SESSION_KEY, current_membership
from .models import Organization, OrganizationMembership


class CurrentMembershipTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='multi-org', password='password')
        self.org_a = Organization.objects.create(name='Org A', slug='org-a')
        self.org_b = Organization.objects.create(name='Org B', slug='org-b')
        self.membership_a = OrganizationMembership.objects.create(
            organization=self.org_a, user=self.user, role=OrganizationMembership.Role.HR,
        )
        OrganizationMembership.objects.create(
            organization=self.org_b, user=self.user, role=OrganizationMembership.Role.HR,
        )
        self.factory = RequestFactory()

    def _request(self, selected=None, header=None):
        request = self.factory.get('/')
        request.user = self.user
        from django.contrib.sessions.backends.db import SessionStore
        request.session = SessionStore()
        if selected:
            request.session[ACTIVE_ORGANIZATION_SESSION_KEY] = str(selected)
            request.session.save()
        if header:
            request.META['HTTP_X_ORGANIZATION_ID'] = str(header)
        return request

    def test_multiple_memberships_without_selection_fail_closed(self):
        self.assertIsNone(current_membership(self._request()))

    def test_selected_session_membership_is_returned(self):
        membership = current_membership(self._request(selected=self.org_a.id))
        self.assertEqual(membership.id, self.membership_a.id)
        self.assertEqual(membership.organization_id, self.org_a.id)

    def test_selected_header_membership_is_returned(self):
        membership = current_membership(self._request(header=self.org_b.id))
        self.assertEqual(membership.organization_id, self.org_b.id)

    def test_invalid_selection_does_not_fall_back_to_another_tenant(self):
        self.assertIsNone(current_membership(self._request(selected='00000000-0000-0000-0000-000000000000')))
