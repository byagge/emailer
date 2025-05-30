from django.contrib import admin
from .models import Campaign

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'status', 'created_at', 'sent_at')
    list_filter = ('status', 'created_at', 'sent_at')
    search_fields = ('name', 'owner__email', 'subject')
    readonly_fields = ('id', 'created_at', 'sent_at')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'owner', 'status')
        }),
        ('Настройки отправки', {
            'fields': ('template', 'sender_email', 'subject', 'sender_name', 'reply_to', 'contact_lists')
        }),
        ('Расписание', {
            'fields': ('scheduled_at',)
        }),
        ('Системная информация', {
            'fields': ('id', 'created_at', 'sent_at'),
            'classes': ('collapse',)
        }),
    )
    filter_horizontal = ('contact_lists',)
