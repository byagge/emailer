# core/apps/campaigns/serializers.py

from rest_framework import serializers

from apps.emails.models import SenderEmail
from apps.mailer.models import ContactList
from .models import Campaign, CampaignStats, EmailTracking

class EmailTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTracking
        fields = ['id', 'tracking_id', 'sent_at', 'opened_at', 'clicked_at', 'bounced_at', 'bounce_reason']

class CampaignStatsSerializer(serializers.ModelSerializer):
    emails_sent = serializers.SerializerMethodField()
    opens_count = serializers.SerializerMethodField()
    clicks_count = serializers.SerializerMethodField()
    bounces_count = serializers.SerializerMethodField()

    class Meta:
        model = CampaignStats
        fields = ['emails_sent', 'opens_count', 'clicks_count', 'bounces_count']

    def get_emails_sent(self, obj):
        return obj.emails_sent

    def get_opens_count(self, obj):
        return obj.opens_count

    def get_clicks_count(self, obj):
        return obj.clicks_count

    def get_bounces_count(self, obj):
        return obj.bounces_count

class CampaignSerializer(serializers.ModelSerializer):
    # Используем обычные поля для записи
    sender_email = serializers.PrimaryKeyRelatedField(queryset=SenderEmail.objects.all())
    contact_lists = serializers.PrimaryKeyRelatedField(many=True, queryset=ContactList.objects.all())

    # Эти поля оставляем как read-only для отображения доп. данных
    contact_lists_detail = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    emails_sent = serializers.SerializerMethodField()
    open_rate = serializers.SerializerMethodField()
    click_rate = serializers.SerializerMethodField()
    bounce_rate = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'template', 'sender_email', 'subject',
            'sender_name', 'reply_to', 'contact_lists', 'contact_lists_detail',
            'scheduled_at', 'status', 'created_at', 'sent_at',
            'stats', 'emails_sent', 'open_rate', 'click_rate', 'bounce_rate'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'sent_at']

    def validate(self, data):
        # Для черновиков можно пропустить валидацию
        if (self.instance and self.instance.status == Campaign.STATUS_DRAFT) or not self.instance:
            return data

        # Полная валидация перед отправкой
        required_fields = ['name', 'template', 'sender_email', 'subject', 'sender_name', 'contact_lists']
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError({field: f'Поле {field} обязательно'})

        return data

    # Остальные методы — без изменений
    def get_contact_lists_detail(self, obj):
        result = []
        for contact_list in obj.contact_lists.all():
            stats = CampaignStats.objects.filter(campaign=obj, contact_list=contact_list).first()
            contacts_count = contact_list.contacts.count()
            result.append({
                'id': contact_list.id,
                'name': contact_list.name,
                'contacts_count': contacts_count,
                'stats': CampaignStatsSerializer(stats).data if stats else {
                    'emails_sent': 0,
                    'opens_count': 0,
                    'clicks_count': 0,
                    'bounces_count': 0
                }
            })
        return result

    def get_stats(self, obj):
        stats = CampaignStats.objects.filter(campaign=obj)
        return CampaignStatsSerializer(stats, many=True).data

    def get_emails_sent(self, obj):
        return obj.emails_sent

    def get_open_rate(self, obj):
        return obj.open_rate

    def get_click_rate(self, obj):
        return obj.click_rate

    def get_bounce_rate(self, obj):
        return obj.bounce_rate
