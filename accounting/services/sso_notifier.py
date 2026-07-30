import logging
from datetime import datetime
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

SIGNER_SALT = 'google-sso-activate'

def generate_activation_token(user_id):
    """
    Tạo token ký số kèm thời gian (TimestampSigner) an toàn cho User ID
    """
    signer = TimestampSigner(salt=SIGNER_SALT)
    return signer.sign(str(user_id))

def verify_activation_token(token, max_age=86400*7):
    """
    Xác thực token ký số (Mặc định hết hạn sau 7 ngày)
    Trả về user_id (int) nếu hợp lệ, ngược lại trả về None
    """
    signer = TimestampSigner(salt=SIGNER_SALT)
    try:
        user_id_str = signer.unsign(token, max_age=max_age)
        return int(user_id_str)
    except (BadSignature, SignatureExpired, ValueError) as e:
        logger.warning(f"Lỗi xác thực Activation Token: {e}")
        return None

def get_formatted_from_email(override_display_name=None):
    """
    Format người gửi kèm Tên hiển thị Alias (Ví dụ: "Hao Phuong Reporting System" <noreply@haophuong.com>)
    Hỗ trợ truyền override_display_name khi API muốn dùng tên khác.
    """
    default_display_name = getattr(settings, 'EMAIL_DISPLAY_NAME', 'Hao Phuong Reporting System')
    display_name = override_display_name.strip() if (override_display_name and isinstance(override_display_name, str) and override_display_name.strip()) else default_display_name
    
    smtp_user = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', None) or 'noreply@haophuong.com'
    if display_name and smtp_user:
        return f'"{display_name}" <{smtp_user}>'
    return smtp_user or 'noreply@haophuong.com'

def send_sso_registration_admin_notification(user, activation_url):
    """
    Gửi email thông báo người dùng mới đăng ký qua SSO cho Admin kèm Link kích hoạt Mức 2 (sử dụng Django Template)
    """
    admin_emails = []
    
    # Priority 1: Lấy từ cấu hình ADMIN_NOTIFICATION_EMAILS trong settings/env
    configured_emails = getattr(settings, 'ADMIN_NOTIFICATION_EMAILS', None)
    if configured_emails:
        if isinstance(configured_emails, str):
            admin_emails = [e.strip() for e in configured_emails.split(',') if e.strip()]
        elif isinstance(configured_emails, (list, tuple)):
            admin_emails = [str(e).strip() for e in configured_emails if str(e).strip()]

    # Priority 2: Nếu chưa có ở Priority 1 -> Lấy từ danh sách Superusers trong CSDL
    if not admin_emails:
        admin_emails = list(User.objects.filter(is_superuser=True, is_active=True).exclude(email='').values_list('email', flat=True))

    # Priority 3: Fallback nếu 1 & 2 đều chưa có email nào
    if not admin_emails:
        default_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', None) or 'admin@haophuong.com'
        admin_emails = [default_email]

    # Loại bỏ các email trùng lặp (chuẩn hoá chữ thường + loại bỏ khoảng trắng dư thừa)
    cleaned_emails = []
    seen = set()
    for e in admin_emails:
        if isinstance(e, str) and e.strip():
            normalized = e.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                cleaned_emails.append(normalized)
    admin_emails = cleaned_emails

    registration_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    subject = f"[Report2026] 🔔 Thông báo: Người dùng mới đăng ký qua Google SSO ({user.email})"
    
    text_content = f"""
    Gửi Quản trị viên,

    Hệ thống vừa ghi nhận một người dùng mới đăng ký tài khoản qua Google SSO:
    - Họ và tên: {user.get_full_name() or user.username}
    - Email: {user.email}
    - Ngày giờ đăng ký: {registration_time}
    - Trạng thái hiện tại: Chờ kích hoạt Mức 2 (is_active = False)

    Vui lòng bấm vào đường dẫn bên dưới để kích hoạt tài khoản Mức 2 cho người dùng này:
    {activation_url}

    Trân trọng,
    Hệ thống tự động Report2026.
    """

    context = {
        'user': user,
        'activation_url': activation_url,
        'registration_time': registration_time,
    }
    
    html_content = render_to_string('emails/admin_sso_notification.html', context)
    from_email = get_formatted_from_email()
    
    msg = EmailMultiAlternatives(subject, text_content, from_email, admin_emails)
    msg.attach_alternative(html_content, "text/html")
    
    try:
        msg.send(fail_silently=False)
        logger.info(f"✅ Đã gửi email thông báo đăng ký SSO cho Admin ({admin_emails}) từ [{from_email}] về user: {user.email}")
        return True
    except Exception as e:
        logger.error(f"❌ Thất bại khi gửi email thông báo SSO cho Admin: {e}")
        return False

def send_user_activation_success_email(user, login_url=None):
    """
    Gửi email thông báo cho User khi tài khoản của họ được Admin kích hoạt Mức 2 thành công (sử dụng Django Template)
    """
    if not user.email:
        return False

    if not login_url:
        frontend_url = getattr(settings, 'FRONTEND_URL', None)
        if frontend_url:
            login_url = frontend_url
        else:
            login_url = 'http://localhost:8000/'

    subject = f"[Report2026] 🎉 Tài khoản của bạn đã được kích hoạt thành công!"
    
    text_content = f"""
    Xin chào {user.get_full_name() or user.username},

    Tài khoản Google SSO ({user.email}) của bạn đã được Quản trị viên kích hoạt thành công Mức 2.
    Bây giờ bạn đã có thể đăng nhập và truy cập đầy đủ các chức năng trên hệ thống Report2026.

    Bấm vào đường dẫn bên dưới để đăng nhập ngay:
    {login_url}

    Trân trọng,
    Ban Quản Trị Hệ Thống Report2026.
    """

    context = {
        'user': user,
        'login_url': login_url,
    }

    html_content = render_to_string('emails/user_activation_success.html', context)
    from_email = get_formatted_from_email()
    
    msg = EmailMultiAlternatives(subject, text_content, from_email, [user.email])
    msg.attach_alternative(html_content, "text/html")
    
    try:
        msg.send(fail_silently=False)
        logger.info(f"✅ Đã gửi email thông báo kích hoạt thành công từ [{from_email}] cho User: {user.email}")
        return True
    except Exception as e:
        logger.error(f"❌ Thất bại khi gửi email kích hoạt cho User: {e}")
        return False
