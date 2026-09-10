from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.employees.models import Employee
from apps.organization.billing import PLANS, active_employee_count, can_activate_employee, get_plan
from apps.organization.billing_service import activation_allowed, plan_summary
from apps.organization.models import Organization, OrganizationMembership


class SaaSBillingFoundationTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(username='owner', password='pass')
        self.organization = Organization.objects.create(name='Acme', slug='acme')
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMembership.Role.OWNER,
        )
        self.client.force_login(self.user)

    def _employee(self, number, active=True, status=None):
        user = self.User.objects.create_user(username=f'user-{number}')
        return Employee.objects.create(
            employee_number=number,
            user=user,
            organization=self.organization,
            first_name='Test',
            last_name=number,
            status=status or (Employee.Status.REGULAR if active else Employee.Status.SEPARATED),
            is_active=active,
        )

    def test_plan_catalog_has_expected_limits_and_prices(self):
        expected = {
            'FREE': (5, Decimal('0.00')),
            'STARTER': (10, Decimal('499.00')),
            'GROWTH': (30, Decimal('1499.00')),
            'BUSINESS': (75, Decimal('2999.00')),
        }
        self.assertEqual(set(PLANS), set(expected))
        for code, (limit, price) in expected.items():
            self.assertEqual(get_plan(code).employee_limit, limit)
            self.assertEqual(get_plan(code).monthly_price, price)

    def test_capacity_counts_active_employees_only(self):
        self.organization.plan_code = Organization.Plan.FREE
        self.organization.save(update_fields=['plan_code'])
        for index in range(5):
            self._employee(f'E{index}')
        self._employee('INACTIVE', active=False)
        self.assertEqual(active_employee_count(self.organization), 5)
        self.assertFalse(can_activate_employee(self.organization))
        self.assertTrue(can_activate_employee(self.organization, excluding_employee_id=Employee.objects.get(employee_number='E0').id))

    def test_activation_policy_blocks_at_plan_capacity(self):
        self.organization.plan_code = Organization.Plan.FREE
        self.organization.subscription_status = Organization.SubscriptionStatus.ACTIVE
        self.organization.save(update_fields=['plan_code', 'subscription_status'])
        for index in range(5):
            self._employee(f'E{index}')
        inactive = self._employee('REJOIN', active=False)
        response = self.client.post(
            reverse('employee-lifecycle-api', kwargs={'employee_id': inactive.id}),
            data={'status': Employee.Status.REGULAR, 'effective_date': '2026-09-10'},
        )
        self.assertEqual(response.status_code, 400)
        inactive.refresh_from_db()
        self.assertFalse(inactive.is_active)

    def test_subscription_endpoint_reports_usage(self):
        self.organization.plan_code = Organization.Plan.GROWTH
        self.organization.subscription_status = Organization.SubscriptionStatus.ACTIVE
        self.organization.save(update_fields=['plan_code', 'subscription_status'])
        self._employee('E1')
        response = self.client.get(reverse('subscription-api'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['plan']['code'], 'GROWTH')
        self.assertEqual(response.json()['plan']['employee_limit'], 30)
        self.assertEqual(response.json()['usage']['active_employees'], 1)
        self.assertEqual(response.json()['usage']['remaining_employee_slots'], 29)

    def test_activation_policy_rejects_canceled_subscription(self):
        self.organization.subscription_status = Organization.SubscriptionStatus.CANCELED
        self.organization.save(update_fields=['subscription_status'])
        self.assertFalse(activation_allowed(self.organization))

    def test_plan_summary_is_stable(self):
        self.organization.plan_code = Organization.Plan.STARTER
        self.organization.save(update_fields=['plan_code'])
        self.assertEqual(plan_summary(self.organization), {
            'code': 'STARTER',
            'name': 'Starter',
            'limit': 10,
            'monthly_price': '499.00',
        })
