from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from apps.attendance.views import attendance_page, clock_action, clock_login, clock_page, dashboard, dashboard_page, import_timekeeping, record_attendance, timekeeping_template
from apps.employees.views import employee_directory, employee_directory_page, employee_lifecycle_api, employee_profile_api
from apps.organization.views import current_user
from apps.organization.subscription_views import subscription_api
from apps.leave.views import leave_api, leave_decision, leave_page, my_leave_api
from apps.payroll.views import apply_payroll_adjustments, approve_payroll, create_payroll_adjustment, mark_payroll_paid, my_payroll_api, payroll_api, payroll_page, payroll_preflight, process_payroll
from apps.payroll.payslip_views import payslip
from apps.payroll.loan_views import loans_api, payroll_loan_preview
from apps.payroll.final_pay_views import final_pay_api
from apps.payroll.remittance_views import payroll_remittance_export
from apps.payroll.summary import payroll_summary_api
from apps.reports.views import reports_api, reports_page
from apps.ess.views import ess_api, ess_page
from apps.accounts.views import employee_login, login_page
from apps.core.views import website
from apps.scheduling.views import scheduling_page, get_shifts, get_clients, get_assignable_employees, get_employee_schedule, assign_shift, delete_assignment
from apps.onboarding.views import onboarding_page, onboarding_api, onboarding_task_update
from apps.talent.views import benefits_api, offboarding_api, performance_api, recruiting_api, talent_page
from apps.operations.views import approval_decision, employee_hub_api, employee_hub_page, operations_api, operations_page, profile_request_decision, timesheet_decision

urlpatterns = [
    path('admin/', admin.site.urls), path('', website, name='website'), path('workspace/', dashboard_page, name='workspace'),
    path('employees/', employee_directory_page, name='employees-page'), path('attendance/', attendance_page, name='attendance-page'), path('clock/', clock_page, name='clock-page'),
    path('clock/login/', clock_login, name='clock-login'), path('clock/action/', clock_action, name='clock-action'), path('login/', login_page, name='login'), path('employee-login/', employee_login, name='employee-login'), path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('scheduling/', scheduling_page, name='scheduling-page'), path('api/dashboard/', dashboard, name='dashboard'), path('api/employees/', employee_directory, name='employee-directory'), path('api/employees/<uuid:employee_id>/', employee_profile_api, name='employee-profile-api'), path('api/employees/<uuid:employee_id>/lifecycle/', employee_lifecycle_api, name='employee-lifecycle-api'), path('api/attendance/', record_attendance, name='record-attendance'),
    path('api/attendance/import/', import_timekeeping, name='import-timekeeping'), path('api/attendance/template/', timekeeping_template, name='timekeeping-template'), path('api/me/', current_user, name='current-user'), path('api/subscription/', subscription_api, name='subscription-api'),
    path('leave/', leave_page, name='leave-page'), path('api/leave/', leave_api, name='leave-api'), path('api/leave/me/', my_leave_api, name='my-leave-api'), path('api/leave/<uuid:application_id>/decision/', leave_decision, name='leave-decision'),
    path('payroll/', payroll_page, name='payroll-page'), path('api/payroll/', payroll_api, name='payroll-api'), path('api/payroll/me/', my_payroll_api, name='my-payroll-api'), path('api/payroll/summary/', payroll_summary_api, name='payroll-summary-api'), path('api/payroll/preflight/', payroll_preflight, name='payroll-preflight'),
    path('api/payroll/process/', process_payroll, name='process-payroll'), path('api/payroll/<uuid:record_id>/adjustments/', create_payroll_adjustment, name='create-payroll-adjustment'), path('api/payroll/<uuid:record_id>/adjustments/apply/', apply_payroll_adjustments, name='apply-payroll-adjustments'), path('api/payroll/<uuid:record_id>/loan-preview/', payroll_loan_preview, name='payroll-loan-preview'), path('api/payroll/<uuid:record_id>/approve/', approve_payroll, name='approve-payroll'), path('api/payroll/<uuid:record_id>/pay/', mark_payroll_paid, name='mark-payroll-paid'), path('api/payroll/<uuid:record_id>/payslip/', payslip, name='payslip'),
    path('api/payroll/loans/', loans_api, name='payroll-loans'), path('api/payroll/final-pay/', final_pay_api, name='payroll-final-pay'), path('api/payroll/remittance/<uuid:period_id>/<str:export_type>/', payroll_remittance_export, name='payroll-remittance-export'),
    path('reports/', reports_page, name='reports-page'), path('api/reports/', reports_api, name='reports-api'), path('ess/', ess_page, name='ess-page'), path('api/ess/', ess_api, name='ess-api'),
    path('api/scheduling/shifts/', get_shifts, name='scheduling-shifts'), path('api/scheduling/clients/', get_clients, name='scheduling-clients'), path('api/scheduling/employees/', get_assignable_employees, name='scheduling-employees'), path('api/scheduling/employee-schedule/', get_employee_schedule, name='scheduling-employee-schedule'), path('api/scheduling/assign/', assign_shift, name='scheduling-assign'), path('api/scheduling/delete/', delete_assignment, name='scheduling-delete'),
    path('onboarding/', onboarding_page, name='onboarding-page'), path('api/onboarding/', onboarding_api, name='onboarding-api'), path('api/onboarding/<uuid:onboarding_id>/tasks/<uuid:task_id>/', onboarding_task_update, name='onboarding-task-update'),
    path('talent/', talent_page, name='talent-page'), path('api/recruiting/', recruiting_api, name='recruiting-api'), path('api/performance/', performance_api, name='performance-api'), path('api/benefits/', benefits_api, name='benefits-api'), path('api/offboarding/', offboarding_api, name='offboarding-api'),
    path('operations/', operations_page, name='operations-page'), path('employee-hub/', employee_hub_page, name='employee-hub-page'), path('api/operations/', operations_api, name='operations-api'), path('api/operations/employee/', employee_hub_api, name='employee-hub-api'), path('api/operations/approvals/<uuid:approval_id>/decision/', approval_decision, name='approval-decision'), path('api/operations/profile-requests/<uuid:request_id>/decision/', profile_request_decision, name='profile-request-decision'), path('api/operations/timesheets/<uuid:entry_id>/decision/', timesheet_decision, name='timesheet-decision'),
]
