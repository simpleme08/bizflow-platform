from django.test import TestCase, Client as TestClient
from django.contrib.auth.models import User
from datetime import date

from apps.organization.models import Organization, OrganizationMembership
from apps.employees.models import Employee, EmployeeAssignment
from apps.workforce.models import ShiftTemplate, Client, ClientSite


class ShiftSchedulingTests(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.organization = Organization.objects.create(slug='test-org', name='Test Organization')
        self.user = User.objects.create_user(username='manager', password='TestPass123!')
        self.membership = OrganizationMembership.objects.create(user=self.user, organization=self.organization, role=OrganizationMembership.Role.MANAGER)
        self.client.login(username='manager', password='TestPass123!')
        self.shift_day = ShiftTemplate.objects.create(name='Day Shift', start_time='08:00', end_time='17:00')
        self.shift_night = ShiftTemplate.objects.create(name='Night Shift', start_time='22:00', end_time='07:00')
        self.client_obj = Client.objects.create(organization=self.organization, code='TEST', name='Test Client')
        self.site = ClientSite.objects.create(client=self.client_obj, name='Test Site')
        self.employee = Employee.objects.create(employee_number='EMP-001', user=User.objects.create_user(username='emp1', password='EmpPass123!'), organization=self.organization, first_name='John', last_name='Doe', is_active=True, status=Employee.Status.REGULAR)

    def test_scheduling_page_requires_login(self):
        self.client.logout()
        response = self.client.get('/scheduling/')
        self.assertEqual(response.status_code, 401)

    def test_get_shifts_returns_global_templates(self):
        response = self.client.get('/api/scheduling/shifts/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['shifts']), 2)
        self.assertEqual(data['shifts'][0]['name'], 'Day Shift')

    def test_get_shifts_does_not_expose_other_organization_templates(self):
        other_org = Organization.objects.create(slug='other-org', name='Other Organization')
        other_shift = ShiftTemplate.objects.create(organization=other_org, name='Other Tenant Shift', start_time='09:00', end_time='18:00')
        response = self.client.get('/api/scheduling/shifts/')
        self.assertEqual(response.status_code, 200)
        shift_ids = {item['id'] for item in response.json()['shifts']}
        self.assertNotIn(str(other_shift.id), shift_ids)


    def test_employee_cannot_list_client_sites_through_scheduling_api(self):
        employee_user = User.objects.create_user(username='client-list-employee', password='EmpPass123!')
        OrganizationMembership.objects.create(user=employee_user, organization=self.organization, role=OrganizationMembership.Role.EMPLOYEE)
        self.client.login(username='client-list-employee', password='EmpPass123!')
        response = self.client.get('/api/scheduling/clients/')
        self.assertEqual(response.status_code, 403)

    def test_get_employees_returns_active_only(self):
        Employee.objects.create(employee_number='EMP-002', user=User.objects.create_user(username='emp2', password='EmpPass123!'), organization=self.organization, first_name='Jane', last_name='Smith', is_active=False, status=Employee.Status.SEPARATED)
        response = self.client.get('/api/scheduling/employees/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['employees']), 1)
        self.assertEqual(data['employees'][0]['name'], 'John Doe')

    def test_assign_shift_creates_assignment(self):
        response = self.client.post('/api/scheduling/assign/', content_type='application/json', data={'employee_id': str(self.employee.id), 'shift_id': str(self.shift_day.id), 'client_id': str(self.client_obj.id), 'site_id': str(self.site.id), 'start_date': '2026-09-01', 'end_date': None, 'is_primary': True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'created')
        assignment = EmployeeAssignment.objects.filter(employee=self.employee).first()
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.shift_template, self.shift_day)
        self.assertEqual(assignment.client, self.client_obj)
        self.assertTrue(assignment.is_primary)

    def test_duplicate_overlapping_shift_assignment_is_rejected(self):
        EmployeeAssignment.objects.create(
            employee=self.employee,
            shift_template=self.shift_day,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
        )
        response = self.client.post(
            '/api/scheduling/assign/',
            content_type='application/json',
            data={
                'employee_id': str(self.employee.id),
                'shift_id': str(self.shift_day.id),
                'start_date': '2026-09-15',
                'end_date': '2026-10-15',
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(EmployeeAssignment.objects.filter(employee=self.employee).count(), 1)

    def test_assign_shift_rejects_string_for_primary_flag(self):
        response = self.client.post(
            '/api/scheduling/assign/',
            content_type='application/json',
            data={
                'employee_id': str(self.employee.id),
                'shift_id': str(self.shift_day.id),
                'start_date': '2026-10-01',
                'is_primary': 'false',
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EmployeeAssignment.objects.filter(employee=self.employee).exists())

    def test_cross_organization_shift_cannot_be_assigned(self):
        other_org = Organization.objects.create(slug='other-org', name='Other Organization')
        other_shift = ShiftTemplate.objects.create(organization=other_org, name='Other Tenant Shift', start_time='09:00', end_time='18:00')
        response = self.client.post('/api/scheduling/assign/', content_type='application/json', data={'employee_id': str(self.employee.id), 'shift_id': str(other_shift.id), 'start_date': '2026-09-01'})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(EmployeeAssignment.objects.filter(employee=self.employee).exists())

    def test_delete_assignment_removes_shift(self):
        assignment = EmployeeAssignment.objects.create(employee=self.employee, shift_template=self.shift_day, client=self.client_obj, start_date=date(2026, 9, 1))
        response = self.client.delete('/api/scheduling/delete/', content_type='application/json', data={'assignment_id': str(assignment.id)})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(EmployeeAssignment.objects.filter(id=assignment.id).exists())

    def test_scheduling_mutations_require_csrf(self):
        csrf_client = TestClient(enforce_csrf_checks=True)
        self.assertTrue(csrf_client.login(username='manager', password='TestPass123!'))
        response = csrf_client.post('/api/scheduling/assign/', content_type='application/json', data={'employee_id': str(self.employee.id), 'shift_id': str(self.shift_day.id), 'start_date': '2026-09-01'})
        self.assertEqual(response.status_code, 403)

    def test_non_manager_cannot_assign_shifts(self):
        employee_user = User.objects.create_user(username='emp3', password='EmpPass123!')
        OrganizationMembership.objects.create(user=employee_user, organization=self.organization, role=OrganizationMembership.Role.EMPLOYEE)
        self.client.login(username='emp3', password='EmpPass123!')
        response = self.client.post('/api/scheduling/assign/', content_type='application/json', data={'employee_id': str(self.employee.id), 'shift_id': str(self.shift_day.id), 'start_date': '2026-09-01'})
        self.assertEqual(response.status_code, 403)

    def test_ineligible_employee_is_not_assignable(self):
        self.employee.status = Employee.Status.SUSPENDED
        self.employee.is_active = False
        self.employee.save(update_fields=('status', 'is_active', 'updated_at'))
        response = self.client.get('/api/scheduling/employees/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['employees'], [])
        response = self.client.post('/api/scheduling/assign/', content_type='application/json', data={'employee_id': str(self.employee.id), 'shift_id': str(self.shift_day.id), 'start_date': '2026-09-01'})
        self.assertEqual(response.status_code, 409)

    def test_cross_organization_assignment_is_rejected(self):
        other_org = Organization.objects.create(slug='other-org', name='Other Organization')
        other_employee = Employee.objects.create(employee_number='OTHER-001', user=User.objects.create_user(username='other', password='EmpPass123!'), organization=other_org, first_name='Other', last_name='Employee', is_active=True, status=Employee.Status.REGULAR)
        response = self.client.post('/api/scheduling/assign/', content_type='application/json', data={'employee_id': str(other_employee.id), 'shift_id': str(self.shift_day.id), 'start_date': '2026-09-01'})
        self.assertEqual(response.status_code, 400)


class BulkShiftAssignmentImportTests(TestCase):
    def setUp(self):
        from io import BytesIO
        from openpyxl import Workbook
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.BytesIO = BytesIO
        self.Workbook = Workbook
        self.SimpleUploadedFile = SimpleUploadedFile
        self.organization = Organization.objects.create(slug='bulk-shifts', name='Bulk Shift Org')
        self.user = User.objects.create_user(username='hr-bulk', password='TestPass123!')
        OrganizationMembership.objects.create(user=self.user, organization=self.organization, role=OrganizationMembership.Role.HR)
        self.employee = Employee.objects.create(
            employee_number='EMP-BULK-01',
            user=User.objects.create_user(username='bulk-employee'),
            organization=self.organization,
            first_name='Alex',
            last_name='Worker',
            is_active=True,
            status=Employee.Status.REGULAR,
        )
        self.shift = ShiftTemplate.objects.create(name='Bulk Day Shift', start_time='08:00', end_time='17:00')

    def workbook_upload(self, rows, filename='assignments.xlsx'):
        workbook = self.Workbook()
        sheet = workbook.active
        sheet.append(['Employee Number', 'Shift Name', 'Start Date', 'End Date', 'Client Code', 'Site Name', 'Primary'])
        for row in rows:
            sheet.append(row)
        buffer = self.BytesIO()
        workbook.save(buffer)
        return self.SimpleUploadedFile(filename, buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_hr_can_download_template_and_import_shift_assignments(self):
        self.client.login(username='hr-bulk', password='TestPass123!')
        template_response = self.client.get('/api/scheduling/assignment-template/')
        self.assertEqual(template_response.status_code, 200)
        self.assertIn('spreadsheetml', template_response['Content-Type'])
        response = self.client.post('/api/scheduling/assignment-import/', {
            'file': self.workbook_upload([['EMP-BULK-01', 'Bulk Day Shift', date(2026, 10, 12), None, None, None, 'TRUE']])
        })
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['imported'], 1)
        assignment = EmployeeAssignment.objects.get(employee=self.employee)
        self.assertEqual(assignment.shift_template, self.shift)
        self.assertEqual(assignment.start_date, date(2026, 10, 12))
        self.assertTrue(assignment.is_primary)

    def test_sme_can_import_shift_assignments(self):
        sme = User.objects.create_user(username='sme-bulk', password='TestPass123!')
        OrganizationMembership.objects.create(user=sme, organization=self.organization, role=OrganizationMembership.Role.SME)
        self.client.login(username='sme-bulk', password='TestPass123!')
        response = self.client.post('/api/scheduling/assignment-import/', {
            'file': self.workbook_upload([['EMP-BULK-01', 'Bulk Day Shift', date(2026, 10, 13), None, None, None, 'FALSE']])
        })
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['imported'], 1)

    def test_invalid_row_prevents_all_assignments_from_being_saved(self):
        self.client.login(username='hr-bulk', password='TestPass123!')
        response = self.client.post('/api/scheduling/assignment-import/', {
            'file': self.workbook_upload([
                ['EMP-BULK-01', 'Bulk Day Shift', date(2026, 10, 14), None, None, None, 'TRUE'],
                ['UNKNOWN-EMP', 'Bulk Day Shift', date(2026, 10, 15), None, None, None, 'FALSE'],
            ])
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.json()['errors']), 1)
        self.assertFalse(EmployeeAssignment.objects.filter(employee=self.employee).exists())

    def test_import_rejects_workbooks_over_1000_rows(self):
        self.client.login(username='hr-bulk', password='TestPass123!')
        rows = [['EMP-BULK-01', 'Bulk Day Shift', date(2026, 10, 20), None, None, None, 'FALSE'] for _ in range(1001)]
        response = self.client.post('/api/scheduling/assignment-import/', {'file': self.workbook_upload(rows)})
        self.assertEqual(response.status_code, 400)
        self.assertIn('1,000 assignment rows', response.json()['detail'])
        self.assertFalse(EmployeeAssignment.objects.filter(employee=self.employee).exists())

    def test_employee_cannot_download_shift_assignment_template(self):
        employee_user = User.objects.create_user(username='template-employee', password='TestPass123!')
        OrganizationMembership.objects.create(user=employee_user, organization=self.organization, role=OrganizationMembership.Role.EMPLOYEE)
        self.client.login(username='template-employee', password='TestPass123!')
        response = self.client.get('/api/scheduling/assignment-template/')
        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_import_shift_assignments(self):
        employee_user = User.objects.create_user(username='employee-bulk', password='TestPass123!')
        OrganizationMembership.objects.create(user=employee_user, organization=self.organization, role=OrganizationMembership.Role.EMPLOYEE)
        self.client.login(username='employee-bulk', password='TestPass123!')
        response = self.client.post('/api/scheduling/assignment-import/', {
            'file': self.workbook_upload([['EMP-BULK-01', 'Bulk Day Shift', date(2026, 10, 16), None, None, None, 'FALSE']])
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(EmployeeAssignment.objects.filter(employee=self.employee).exists())
