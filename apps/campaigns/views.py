# apps/campaigns/views.py

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_GET
from django.http import Http404

from .models import Campaign, CampaignStats, EmailTracking
from .serializers import CampaignSerializer, EmailTrackingSerializer


class CampaignViewSet(viewsets.ModelViewSet):
    """
    REST API: CRUD кампаний + экшен send.
    """
    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Campaign.objects.filter(owner=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], url_path='send')
    def send(self, request, pk=None):
        campaign = self.get_object()

        if campaign.status != Campaign.STATUS_DRAFT:
            return Response({'detail': 'Можно отправить только черновик.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Проверяем обязательные поля
        missing = []
        
        # Проверяем простые поля
        for field in ('name', 'template', 'sender_email', 'subject', 'sender_name'):
            value = getattr(campaign, field)
            if not value:
                missing.append(field)
        
        # Проверяем списки контактов
        if not campaign.contact_lists.exists():
            missing.append('contact_lists')
            
        # Проверяем шаблон
        if not campaign.template:
            missing.append('template')
            
        # Проверяем email отправителя
        if not campaign.sender_email:
            missing.append('sender_email')

        if missing:
            return Response(
                {'detail': f'Не заполнены: {", ".join(missing)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем наличие контента в шаблоне
        if not campaign.template.html_content:
            return Response(
                {'detail': 'Шаблон не содержит HTML-контента'},
                status=status.HTTP_400_BAD_REQUEST
            )

        campaign.status = Campaign.STATUS_SENDING
        campaign.save(update_fields=['status'])
        self._send_sync(campaign)
        return Response({'detail': 'Кампания запущена.'})

    def _send_sync(self, campaign: Campaign):
        recipients = {
            c.email
            for cl in campaign.contact_lists.all()
            for c in cl.contacts.all()
        }

        subject    = campaign.subject
        from_email = f"{campaign.sender_name} <{campaign.sender_email.email}>"
        html_body  = campaign.template.html_content
        text_body  = campaign.template.plain_text_content or ''

        for to in recipients:
            msg = EmailMultiAlternatives(
                subject, text_body, from_email, [to],
                reply_to=[campaign.reply_to] if campaign.reply_to else None
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send(fail_silently=True)

        campaign.status  = Campaign.STATUS_COMPLETED
        campaign.sent_at = timezone.now()
        campaign.save(update_fields=['status','sent_at'])

    @action(detail=True, methods=['post'])
    def track_open(self, request, pk=None):
        """Отслеживание открытия письма"""
        tracking_id = request.GET.get('tracking_id')
        if not tracking_id:
            return Response({'error': 'Tracking ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tracking = EmailTracking.objects.get(
                campaign_id=pk,
                tracking_id=tracking_id
            )
            tracking.mark_as_opened(
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            return Response({'status': 'success'})
        except EmailTracking.DoesNotExist:
            return Response({'error': 'Invalid tracking ID'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def track_click(self, request, pk=None):
        """Отслеживание клика по ссылке"""
        tracking_id = request.GET.get('tracking_id')
        if not tracking_id:
            return Response({'error': 'Tracking ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tracking = EmailTracking.objects.get(
                campaign_id=pk,
                tracking_id=tracking_id
            )
            tracking.mark_as_clicked(
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            return Response({'status': 'success'})
        except EmailTracking.DoesNotExist:
            return Response({'error': 'Invalid tracking ID'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def track_bounce(self, request, pk=None):
        """Отслеживание отказа письма"""
        tracking_id = request.GET.get('tracking_id')
        reason = request.data.get('reason', '')
        
        if not tracking_id:
            return Response({'error': 'Tracking ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tracking = EmailTracking.objects.get(
                campaign_id=pk,
                tracking_id=tracking_id
            )
            tracking.mark_as_bounced(reason=reason)
            return Response({'status': 'success'})
        except EmailTracking.DoesNotExist:
            return Response({'error': 'Invalid tracking ID'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Получение статистики по кампаниям"""
        # Получаем все кампании пользователя
        campaigns = self.get_queryset()
        
        # Считаем общую статистику
        total_sent = sum(c.emails_sent for c in campaigns)
        total_opened = sum(c.emails_sent * (c.open_rate / 100) for c in campaigns)
        total_clicked = sum(c.emails_sent * (c.click_rate / 100) for c in campaigns)
        
        # Считаем статистику за последние 7 дней для тренда
        week_ago = timezone.now() - timezone.timedelta(days=7)
        week_campaigns = campaigns.filter(created_at__gte=week_ago)
        
        week_sent = sum(c.emails_sent for c in week_campaigns)
        week_opened = sum(c.emails_sent * (c.open_rate / 100) for c in week_campaigns)
        week_clicked = sum(c.emails_sent * (c.click_rate / 100) for c in week_campaigns)
        
        # Считаем тренды (процент изменения)
        prev_week = week_ago - timezone.timedelta(days=7)
        prev_week_campaigns = campaigns.filter(
            created_at__gte=prev_week,
            created_at__lt=week_ago
        )
        
        prev_week_sent = sum(c.emails_sent for c in prev_week_campaigns)
        prev_week_opened = sum(c.emails_sent * (c.open_rate / 100) for c in prev_week_campaigns)
        prev_week_clicked = sum(c.emails_sent * (c.click_rate / 100) for c in prev_week_campaigns)
        
        # Вычисляем процент изменения
        def calculate_trend(current, previous):
            if previous == 0:
                return 0
            return round(((current - previous) / previous) * 100, 1)
        
        return Response({
            'sent': total_sent,
            'opened': total_opened,
            'clicked': total_clicked,
            'sentTrend': calculate_trend(week_sent, prev_week_sent),
            'openedTrend': calculate_trend(week_opened, prev_week_opened),
            'clickedTrend': calculate_trend(week_clicked, prev_week_clicked),
            'newSubscribers': 0,  # Пока не реализовано
            'subscribersTrend': 0  # Пока не реализовано
        })


class CampaignListView(LoginRequiredMixin, TemplateView):
    """
    Рендерит страницу «Список кампаний».
    SPA на Alpine.js сама подгрузит их через API.
    """
    template_name = 'campaigns_list.html'


class CampaignFormView(LoginRequiredMixin, TemplateView):
    """
    Рендерит страницу «Создать/редактировать кампанию».
    """
    template_name = 'campaigns_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = kwargs.get('pk')
        
        if pk:
            try:
                campaign = Campaign.objects.get(pk=pk, owner=self.request.user)
                # Преобразуем данные кампании в формат для фронтенда
                context['campaign'] = {
                    'id': str(campaign.id),
                    'name': campaign.name,
                    'subject': campaign.subject,
                    'sender_name': campaign.sender_name,
                    'reply_to': campaign.reply_to,
                    'status': campaign.status,
                    'scheduled_at': campaign.scheduled_at.isoformat() if campaign.scheduled_at else None,
                    'template': {
                        'id': str(campaign.template.id),
                        'title': campaign.template.title
                    } if campaign.template else None,
                    'sender_email': {
                        'id': str(campaign.sender_email.id),
                        'email': campaign.sender_email.email
                    } if campaign.sender_email else None,
                    'contact_lists': [
                        {
                            'id': str(cl.id),
                            'name': cl.name
                        } for cl in campaign.contact_lists.all()
                    ]
                }
            except Campaign.DoesNotExist:
                raise Http404("Кампания не найдена")
        
        return context


@require_GET
def track_email_open(request, tracking_id):
    """Обработчик открытия письма"""
    try:
        tracking = EmailTracking.objects.get(tracking_id=tracking_id)
        tracking.mark_as_opened(
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    except EmailTracking.DoesNotExist:
        pass
    
    # Возвращаем прозрачный 1x1 пиксель
    return HttpResponse(
        bytes.fromhex('47494638396101000100800000dbdbdb00000021f90401000000002c00000000010001000002024401003b'),
        content_type='image/gif'
    )

@require_GET
def track_email_click(request, tracking_id):
    """Обработчик клика по ссылке"""
    try:
        tracking = EmailTracking.objects.get(tracking_id=tracking_id)
        tracking.mark_as_clicked(
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        # Перенаправляем на оригинальный URL
        return HttpResponseRedirect(request.GET.get('url', '/'))
    except EmailTracking.DoesNotExist:
        return HttpResponseRedirect('/')
