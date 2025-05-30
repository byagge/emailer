from django.contrib import admin
from .models import Plan, PurchasedPlan, User

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'subscribers', 'discount', 'max_emails_per_day', 'price')
    search_fields = ('title',)
    list_filter = ('price', 'max_emails_per_day')

@admin.register(PurchasedPlan)
class PurchasedPlanAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'plan', 'start_date', 'end_date')
    search_fields = ('user__email', 'user__full_name')
    date_hierarchy = 'start_date'

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'is_email_verified', 'is_verified', 'current_plan', 'plan_expiry', 'date_joined')
    list_filter = ('is_email_verified', 'is_verified', 'is_active', 'is_staff', 'current_plan')
    search_fields = ('email', 'full_name')
    date_hierarchy = 'date_joined'
    fieldsets = (
        (None, {'fields': ('email', 'full_name', 'password')}),
        ('Status', {'fields': ('is_email_verified', 'is_verified', 'is_active', 'is_staff')}),
        ('Plan Information', {'fields': ('current_plan', 'plan_expiry', 'emails_sent_today')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
    )
