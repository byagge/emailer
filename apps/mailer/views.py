# mailer/views.py

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser

from .models import ContactList, Contact
from .serializers import ContactListSerializer, ContactSerializer
from .utils import parse_emails, classify_email


class ContactListViewSet(viewsets.ModelViewSet):
    """
    CRUD для ContactList и вложенные операции с Contact через @action.
    """
    serializer_class    = ContactListSerializer
    permission_classes  = [IsAuthenticated]
    parser_classes      = [MultiPartParser] + viewsets.ModelViewSet.parser_classes

    def get_queryset(self):
        return ContactList.objects.filter(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Переопределяем метод создания, чтобы при дублировании имени вернуть 400 с ошибкой,
        вместо падения 500.
        """
        # Подготовим сериализатор (owner запишем в perform_create)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)
        except IntegrityError:
            return Response(
                {'name': ['Список с таким именем уже существует']},
                status=status.HTTP_400_BAD_REQUEST
            )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


    @action(detail=True, methods=['get', 'post'], url_path='contacts')
    def contacts(self, request, pk=None):
        """
        GET  /contactlists/{pk}/contacts/  — список контактов
        POST /contactlists/{pk}/contacts/  — добавить контакт { email, status }
        """
        contact_list = self.get_object()

        if request.method == 'GET':
            qs = contact_list.contacts.all()
            ser = ContactSerializer(qs, many=True)
            return Response(ser.data)

        ser = ContactSerializer(data=request.data)
        if ser.is_valid():
            ser.save(contact_list=contact_list)
            return Response(ser.data, status=status.HTTP_201_CREATED)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=['delete'], url_path='contacts/(?P<cid>[^/.]+)')
    def delete_contact(self, request, pk=None, cid=None):
        """
        DELETE /contactlists/{pk}/contacts/{cid}/
        """
        contact_list = self.get_object()
        contact = get_object_or_404(Contact, pk=cid, contact_list=contact_list)
        contact.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


    @action(detail=True, methods=['post'], url_path='import')
    def import_contacts(self, request, pk=None):
        """
        POST /contactlists/{pk}/import/ — импорт контактов из файла
        """
        contact_list = self.get_object()
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'detail': 'No file uploaded.'},
                            status=status.HTTP_400_BAD_REQUEST)

        emails = parse_emails(file_obj, file_obj.name)
        added = 0
        for email in emails:
            status_code = classify_email(email)
            obj, created = Contact.objects.get_or_create(
                contact_list=contact_list,
                email=email,
                defaults={'status': status_code}
            )
            if not created and obj.status != status_code:
                obj.status = status_code
                obj.save(update_fields=['status'])
            if created:
                added += 1

        return Response({'imported': added}, status=status.HTTP_201_CREATED)


class ListSpaView(LoginRequiredMixin, TemplateView):
    template_name = 'list.html'

