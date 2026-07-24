from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from knox.views import LoginView as KnoxLoginView
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from accounting.models import Branch, Customer, Employee, BusinessUnit, SalesTransaction, AccountDetail
from accounting.serializers import (
    BranchSerializer, CustomerSerializer, EmployeeSerializer,
    BusinessUnitSerializer, SalesTransactionSerializer, AccountDetailSerializer,
    GoogleLoginSerializer
)

class LoginAPI(KnoxLoginView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, format=None):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)
        if not user:
            return Response({'error': 'Sai tài khoản hoặc mật khẩu'}, status=400)

        login(request, user)
        return super().post(request, format=None)

class GoogleLoginAPI(KnoxLoginView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, format=None):
        serializer = GoogleLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token = serializer.validated_data['id_token']
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)

        try:
            id_info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                audience=client_id if client_id else None
            )

            email = id_info.get('email')
            name = id_info.get('name', '')
            given_name = id_info.get('given_name', '')
            family_name = id_info.get('family_name', '')

            if not email:
                return Response({'error': 'Google ID token không chứa email hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

            user, created = User.objects.get_or_create(
                username=email,
                defaults={
                    'email': email,
                    'first_name': given_name or name,
                    'last_name': family_name,
                    'is_active': True
                }
            )

            if not user.is_active:
                return Response({'error': 'Tài khoản người dùng đã bị khóa.'}, status=status.HTTP_400_BAD_REQUEST)

            login(request, user)
            return super().post(request, format=None)

        except ValueError as e:
            return Response({'error': f'Google ID token không hợp lệ hoặc đã hết hạn: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Lỗi hệ thống khi xác thực Google: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

class BusinessUnitViewSet(viewsets.ModelViewSet):
    queryset = BusinessUnit.objects.all()
    serializer_class = BusinessUnitSerializer

    def get_queryset(self):
        queryset = BusinessUnit.objects.all()
        is_main = self.request.query_params.get("is_main")

        if is_main in ["true", "false"]:
            queryset = queryset.filter(is_main=(is_main == "true"))

        return queryset

class SalesTransactionViewSet(viewsets.ModelViewSet):
    queryset = SalesTransaction.objects.all()
    serializer_class = SalesTransactionSerializer

class AccountDetailViewSet(viewsets.ModelViewSet):
    queryset = AccountDetail.objects.all().order_by('-id')
    serializer_class = AccountDetailSerializer
    filterset_fields = ['business_unit__code']
