from django.contrib import admin

from django.contrib.auth.models import User

admin.site.unregister(User)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
	list_display = ('username', 'email', 'is_staff', 'is_active', 'last_login')
	list_filter = ('is_staff', 'is_active', 'is_superuser')
	search_fields = ('username', 'email', 'first_name', 'last_name')
