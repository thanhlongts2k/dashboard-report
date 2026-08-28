from django.db import models
from django.contrib.auth.models import User


class Department(models.Model):
    department_code = models.CharField(
        max_length=50, 
        primary_key=True, 
        verbose_name="Mã đơn vị / Phòng ban"
    )
    parent_department = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='parent_department_code',
        related_name='sub_departments', 
        verbose_name="Đơn vị cấp trên"
    )
    department_name = models.CharField(
        max_length=255, 
        verbose_name="Tên đơn vị / Phòng ban"
    )

    class Meta:
        db_table = 'departments'
        verbose_name = "Danh mục đơn vị"
        verbose_name_plural = "Danh mục đơn vị"

    def __str__(self):
        return f"{self.department_code} - {self.department_name}"


class JobTitle(models.Model):
    title_id = models.AutoField(
        primary_key=True, 
        verbose_name="ID Chức danh"
    )
    title_name = models.CharField(
        max_length=255, 
        verbose_name="Tên chức danh"
    )

    class Meta:
        db_table = 'job_titles'
        verbose_name = "Danh mục chức danh"
        verbose_name_plural = "Danh mục chức danh"

    def __str__(self):
        return self.title_name


class Employee(models.Model):
    GENDER_CHOICES = (
        ('MALE', 'Nam'),
        ('FEMALE', 'Nữ'),
    )

    employee_code = models.CharField(
        max_length=50,
        unique=True,
        default='',
        verbose_name="Mã nhân viên"
    )
    full_name = models.CharField(
        max_length=255,
        default='',
        verbose_name="Họ và tên"
    )
    gender = models.CharField(
        max_length=10, 
        choices=GENDER_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name="Giới tính"
    )
    date_of_birth = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Ngày sinh"
    )
    identity_number = models.CharField(
        max_length=50, 
        null=True, 
        blank=True, 
        verbose_name="Số CMND/CCCD"
    )
    phone_number = models.CharField(
        max_length=50, 
        null=True, 
        blank=True, 
        verbose_name="Số điện thoại"
    )
    email = models.CharField(
        max_length=150, 
        null=True, 
        blank=True, 
        verbose_name="Email"
    )
    google_sso_email = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Email Google cá nhân (Gmail) dùng để đăng nhập SSO (có thể nhập nhiều email cách nhau bởi dấu phẩy)",
        verbose_name="Email Google cá nhân liên kết"
    )
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee_profile',
        verbose_name="Tài khoản đăng nhập"
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name="Đang hoạt động"
    )

    class Meta:
        db_table = 'employees'
        verbose_name = "Danh sách nhân viên"
        verbose_name_plural = "Danh sách nhân viên"

    @property
    def code(self):
        return self.employee_code

    @property
    def name(self):
        return self.full_name

    def __str__(self):
        return f"{self.full_name} ({self.employee_code})"


class EmployeeAssignment(models.Model):
    assignment_id = models.AutoField(
        primary_key=True, 
        verbose_name="ID Quá trình công tác"
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name="Nhân viên"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='employee_assignments',
        verbose_name="Đơn vị / Phòng ban"
    )
    title = models.ForeignKey(
        JobTitle,
        on_delete=models.CASCADE,
        related_name='employee_assignments',
        verbose_name="Chức danh"
    )
    manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_assignments',
        verbose_name="Người quản lý trực tiếp"
    )
    start_date = models.DateField(
        verbose_name="Ngày bắt đầu"
    )
    end_date = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Ngày kết thúc"
    )

    class Meta:
        db_table = 'employee_assignments'
        verbose_name = "Quá trình công tác"
        verbose_name_plural = "Lịch sử quá trình công tác"

    def __str__(self):
        return f"{self.employee.full_name} - {self.department.department_name} ({self.title.title_name})"
