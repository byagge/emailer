# core/apps/campaigns/models.py

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

class Campaign(models.Model):
    """
    Рассылка (кампания).
    """
    STATUS_DRAFT     = 'draft'
    STATUS_SENDING   = 'sending'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (STATUS_DRAFT,     'Черновик'),
        (STATUS_SENDING,   'Отправляется'),
        (STATUS_COMPLETED, 'Завершена'),
    ]

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='campaigns')
    name           = models.CharField(max_length=255, blank=True, default='')
    template       = models.ForeignKey('mail_templates.EmailTemplate', on_delete=models.PROTECT, null=True, blank=True)
    sender_email   = models.ForeignKey('emails.SenderEmail', on_delete=models.PROTECT, null=True, blank=True)
    subject        = models.CharField(max_length=255, blank=True, default='')
    sender_name    = models.CharField(max_length=100, blank=True, default='')
    reply_to       = models.EmailField(blank=True, default='')
    contact_lists  = models.ManyToManyField('mailer.ContactList', related_name='campaigns', blank=True)
    scheduled_at   = models.DateTimeField(null=True, blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_at     = models.DateTimeField(auto_now_add=True)
    sent_at        = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    @property
    def emails_sent(self):
        """Общее количество отправленных писем"""
        return EmailTracking.objects.filter(campaign=self).count()

    @property
    def open_rate(self):
        """Процент открытий"""
        total_sent = self.emails_sent
        if total_sent == 0:
            return 0
        total_opens = EmailTracking.objects.filter(campaign=self, opened_at__isnull=False).count()
        return (total_opens / total_sent * 100)

    @property
    def click_rate(self):
        """Процент кликов"""
        total_sent = self.emails_sent
        if total_sent == 0:
            return 0
        total_clicks = EmailTracking.objects.filter(campaign=self, clicked_at__isnull=False).count()
        return (total_clicks / total_sent * 100)

    @property
    def bounce_rate(self):
        """Процент отказов"""
        total_sent = self.emails_sent
        if total_sent == 0:
            return 0
        total_bounces = EmailTracking.objects.filter(campaign=self, bounced_at__isnull=False).count()
        return (total_bounces / total_sent * 100)


class EmailTracking(models.Model):
    """
    Отслеживание статистики по каждому письму.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='email_tracking')
    contact = models.ForeignKey('mailer.Contact', on_delete=models.CASCADE, related_name='email_tracking')
    tracking_id = models.CharField(max_length=100, unique=True)  # Уникальный ID для трекинга
    sent_at = models.DateTimeField(auto_now_add=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    bounced_at = models.DateTimeField(null=True, blank=True)
    bounce_reason = models.TextField(blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"Tracking for {self.contact.email} in {self.campaign.name}"

    def mark_as_opened(self, ip_address=None, user_agent=None):
        """Отметить письмо как открытое"""
        if not self.opened_at:
            self.opened_at = timezone.now()
            self.ip_address = ip_address
            self.user_agent = user_agent
            self.save()

    def mark_as_clicked(self, ip_address=None, user_agent=None):
        """Отметить письмо как открытое по клику"""
        if not self.clicked_at:
            self.clicked_at = timezone.now()
            if not self.opened_at:
                self.opened_at = self.clicked_at
            self.ip_address = ip_address
            self.user_agent = user_agent
            self.save()

    def mark_as_bounced(self, reason=''):
        """Отметить письмо как отказ"""
        if not self.bounced_at:
            self.bounced_at = timezone.now()
            self.bounce_reason = reason
            self.save()


class CampaignStats(models.Model):
    """
    Статистика кампании по списку контактов.
    """
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='stats')
    contact_list = models.ForeignKey('mailer.ContactList', on_delete=models.CASCADE, related_name='campaign_stats')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('campaign', 'contact_list')
        ordering = ['-updated_at']

    def __str__(self):
        return f"Stats for {self.campaign.name} - {self.contact_list.name}"

    @property
    def emails_sent(self):
        """Количество отправленных писем"""
        return EmailTracking.objects.filter(
            campaign=self.campaign,
            contact__in=self.contact_list.contacts.all()
        ).count()

    @property
    def opens_count(self):
        """Количество открытий"""
        return EmailTracking.objects.filter(
            campaign=self.campaign,
            contact__in=self.contact_list.contacts.all(),
            opened_at__isnull=False
        ).count()

    @property
    def clicks_count(self):
        """Количество кликов"""
        return EmailTracking.objects.filter(
            campaign=self.campaign,
            contact__in=self.contact_list.contacts.all(),
            clicked_at__isnull=False
        ).count()

    @property
    def bounces_count(self):
        """Количество отказов"""
        return EmailTracking.objects.filter(
            campaign=self.campaign,
            contact__in=self.contact_list.contacts.all(),
            bounced_at__isnull=False
        ).count()
