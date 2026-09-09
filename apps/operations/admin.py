from django.contrib import admin
from .models import ApprovalRequest, Announcement, CompensationChange, DocumentAcknowledgement, EmployeeDocument, ExternalConnector, OffboardingTask, ProfileChangeRequest, Project, TimesheetEntry

admin.site.register([ApprovalRequest, Announcement, CompensationChange, DocumentAcknowledgement, EmployeeDocument, ExternalConnector, OffboardingTask, ProfileChangeRequest, Project, TimesheetEntry])
