import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('employees', '0003_employee_department_employee_employment_type_and_more'),
        ('organization', '0003_costcenter_department_employmenttype_position'),
    ]

    operations = [
        migrations.CreateModel(
            name='BenefitPlan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=140)), ('provider', models.CharField(blank=True, max_length=120)),
                ('description', models.TextField(blank=True)), ('employee_cost', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('employer_cost', models.DecimalField(decimal_places=2, default=0, max_digits=12)), ('is_active', models.BooleanField(default=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='benefit_plans', to='organization.organization')),
            ],
        ),
        migrations.CreateModel(
            name='Candidate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
                ('first_name', models.CharField(max_length=100)), ('last_name', models.CharField(max_length=100)), ('email', models.EmailField(max_length=254)), ('phone', models.CharField(blank=True, max_length=40)), ('source', models.CharField(blank=True, max_length=80)), ('resume_url', models.URLField(blank=True)), ('notes', models.TextField(blank=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='candidates', to='organization.organization')),
            ], options={'ordering': ('last_name', 'first_name')},
        ),
        migrations.CreateModel(
            name='JobOpening',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=150)), ('description', models.TextField(blank=True)), ('location', models.CharField(blank=True, max_length=120)), ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('OPEN', 'Open'), ('CLOSED', 'Closed')], default='DRAFT', max_length=12)), ('target_start_date', models.DateField(blank=True, null=True)),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='job_openings', to='organization.department')),
                ('employment_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='job_openings', to='organization.employmenttype')),
                ('hiring_manager', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='managed_job_openings', to=settings.AUTH_USER_MODEL)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='job_openings', to='organization.organization')),
            ], options={'ordering': ('-created_at',)},
        ),
        migrations.CreateModel(
            name='PerformanceCycle',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)), ('name', models.CharField(max_length=120)), ('start_date', models.DateField()), ('end_date', models.DateField()), ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('ACTIVE', 'Active'), ('CLOSED', 'Closed')], default='DRAFT', max_length=12)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='performance_cycles', to='organization.organization')),
            ], options={'ordering': ('-start_date',)},
        ),
        migrations.CreateModel(
            name='OffboardingRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)), ('last_working_day', models.DateField()), ('reason', models.CharField(blank=True, max_length=160)), ('status', models.CharField(choices=[('PLANNED', 'Planned'), ('IN_PROGRESS', 'In progress'), ('COMPLETED', 'Completed')], default='PLANNED', max_length=16)), ('notes', models.TextField(blank=True)),
                ('employee', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='offboarding_record', to='employees.employee')),
            ],
        ),
        migrations.CreateModel(
            name='JobApplication',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)), ('stage', models.CharField(choices=[('APPLIED', 'Applied'), ('SCREENING', 'Screening'), ('INTERVIEW', 'Interview'), ('OFFER', 'Offer'), ('HIRED', 'Hired'), ('REJECTED', 'Rejected')], default='APPLIED', max_length=16)), ('applied_at', models.DateTimeField(auto_now_add=True)), ('rating', models.PositiveSmallIntegerField(blank=True, null=True)), ('feedback', models.TextField(blank=True)),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='talent.candidate')), ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='talent.jobopening')),
            ],
        ),
        migrations.CreateModel(
            name='EmployeeGoal',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)), ('title', models.CharField(max_length=180)), ('description', models.TextField(blank=True)), ('due_date', models.DateField(blank=True, null=True)), ('progress', models.PositiveSmallIntegerField(default=0)), ('status', models.CharField(choices=[('NOT_STARTED', 'Not started'), ('ON_TRACK', 'On track'), ('AT_RISK', 'At risk'), ('COMPLETED', 'Completed')], default='NOT_STARTED', max_length=16)),
                ('cycle', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='goals', to='talent.performancecycle')), ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='goals', to='employees.employee')),
            ],
        ),
        migrations.CreateModel(
            name='PerformanceReview',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)), ('rating', models.PositiveSmallIntegerField(blank=True, null=True)), ('strengths', models.TextField(blank=True)), ('development_areas', models.TextField(blank=True)), ('comments', models.TextField(blank=True)), ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('SUBMITTED', 'Submitted'), ('ACKNOWLEDGED', 'Acknowledged')], default='DRAFT', max_length=16)),
                ('cycle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='talent.performancecycle')), ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='performance_reviews', to='employees.employee')), ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='submitted_reviews', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='BenefitEnrollment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)), ('effective_date', models.DateField()), ('end_date', models.DateField(blank=True, null=True)), ('status', models.CharField(choices=[('ENROLLED', 'Enrolled'), ('WAIVED', 'Waived'), ('ENDED', 'Ended')], default='ENROLLED', max_length=12)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='benefit_enrollments', to='employees.employee')), ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='enrollments', to='talent.benefitplan')),
            ],
        ),
        migrations.AddConstraint(model_name='candidate', constraint=models.UniqueConstraint(fields=('organization', 'email'), name='unique_candidate_email_per_org')),
        migrations.AddConstraint(model_name='jobapplication', constraint=models.UniqueConstraint(fields=('job', 'candidate'), name='unique_job_candidate_application')),
        migrations.AddConstraint(model_name='performancereview', constraint=models.UniqueConstraint(fields=('cycle', 'employee'), name='unique_cycle_employee_review')),
        migrations.AddConstraint(model_name='benefitenrollment', constraint=models.UniqueConstraint(fields=('employee', 'plan', 'effective_date'), name='unique_benefit_enrollment')),
    ]
