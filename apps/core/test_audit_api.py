from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.models import AuditEvent
from apps.organization.models import Organization, OrganizationMembership


class AuditApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='audit-admin', password='safe-password')
        self.org = Organization.objects.create(name='Audit Org', slug='audit-org')
        OrganizationMembership.objects.create(user=self.user, organization=self.org, role='HR', is_active=True)
        self.client.force_login(self.user)
        session = self.client.session
        session['active_organization_id'] = str(self.org.id)
        session.save()

    def test_audit_search_is_tenant_scoped(self):
        AuditEvent.objects.create(organization=self.org, actor=self.user, action='payroll.processed', entity_type='PayrollPeriod', entity_id='1', details={'period': 'September'})
        other = Organization.objects.create(name='Other Org', slug='other-org')
        AuditEvent.objects.create(organization=other, actor=self.user, action='secret.action', entity_type='PayrollPeriod', entity_id='2', details={})
        response = self.client.get('/api/audit/?action=payroll')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['results'][0]['action'], 'payroll.processed')

    def test_audit_csv_export(self):
        AuditEvent.objects.create(organization=self.org, actor=self.user, action='test.action', entity_type='Employee', entity_id='1', details={'ok': True})
        response = self.client.get('/api/audit/?format=csv')
        self.assertEqual(response.status_code, 200)
        self.assertIn('test.action', response.content.decode())
