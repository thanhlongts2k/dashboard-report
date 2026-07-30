from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import HttpResponse
from django.shortcuts import render
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
from accounting.services import (
    generate_activation_token, verify_activation_token,
    send_sso_registration_admin_notification, send_user_activation_success_email
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
                    'is_active': False
                }
            )

            if created:
                # Sinh link kích hoạt nhanh cho Admin
                act_token = generate_activation_token(user.id)
                scheme = request.scheme
                host = request.get_host()
                activation_url = f"{scheme}://{host}/api/auth/activate-user/?token={act_token}"
                
                # Gửi email thông báo cho Admin
                send_sso_registration_admin_notification(user, activation_url)

                return Response({'error': 'Tài khoản vừa được tạo mới, cần được kích hoạt Mức 2. Thông báo đã được gửi tới Admin để xác nhận. Vui lòng kiểm tra email sau khi được kích hoạt.'}, status=status.HTTP_400_BAD_REQUEST)

            if not user.is_active:
                return Response({'error': 'Tài khoản của bạn hiện đang bị khóa hoặc vô hiệu hóa. Vui lòng liên hệ Quản trị viên để được hỗ trợ.'}, status=status.HTTP_400_BAD_REQUEST)

            login(request, user)
            return super().post(request, format=None)

        except ValueError as e:
            return Response({'error': f'Google ID token không hợp lệ hoặc đã hết hạn: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Lỗi hệ thống khi xác thực Google: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ActivateUserAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        token = request.query_params.get('token')
        if not token:
            return render(request, 'auth/activation_error.html', {'error_message': 'Mã kích hoạt không hợp lệ hoặc thiếu tham số token.'}, status=400)

        user_id = verify_activation_token(token)
        if not user_id:
            return render(request, 'auth/activation_error.html', {'error_message': 'Link kích hoạt không hợp lệ hoặc đã hết hạn (sau 7 ngày).'}, status=400)

        try:
            user = User.objects.get(id=user_id)
            frontend_url = getattr(settings, 'FRONTEND_URL', None)
            if frontend_url:
                login_url = frontend_url
            else:
                scheme = request.scheme
                host = request.get_host()
                login_url = f"{scheme}://{host}/"

            if not user.is_active:
                user.is_active = True
                user.save()
                send_user_activation_success_email(user, login_url=login_url)

            return render(request, 'auth/activation_response.html', {'user': user, 'login_url': login_url})
        except User.DoesNotExist:
            return render(request, 'auth/activation_error.html', {'error_message': 'Không tìm thấy tài khoản người dùng tương ứng.'}, status=404)


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
