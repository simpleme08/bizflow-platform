from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('organization', '0001_initial'),
	]

	operations = [
		migrations.AlterField(
			model_name='organizationmembership',
			name='role',
			field=models.CharField(
				choices=[
					('OWNER', 'Owner'),
					('ADMIN', 'Administrator'),
					('CEO', 'Chief Executive Officer'),
					('HR', 'Human Resources'),
					('SME', 'Subject Matter Expert'),
					('TEAM_LEADER', 'Team Leader'),
					('MANAGER', 'Manager'),
					('EMPLOYEE', 'Employee'),
					('SUPER_USER', 'Super User'),
				],
				default='EMPLOYEE',
				max_length=20,
			),
		),
	]