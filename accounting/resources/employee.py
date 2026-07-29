from datetime import datetime
from import_export import fields
from import_export.resources import ModelResource
from accounting.models import Department, JobTitle, Employee, EmployeeAssignment


class EmployeeResource(ModelResource):
    employee_code = fields.Field(attribute='employee_code', column_name='Mã nhân viên')
    full_name = fields.Field(attribute='full_name', column_name='Tên nhân viên')
    gender = fields.Field(attribute='gender', column_name='Giới tính')
    date_of_birth = fields.Field(attribute='date_of_birth', column_name='Ngày sinh')
    identity_number = fields.Field(attribute='identity_number', column_name='Số CMND')
    phone_number = fields.Field(attribute='phone_number', column_name='Số điện thoại')
    email = fields.Field(attribute='email', column_name='Email')
    is_active = fields.Field(attribute='is_active', column_name='Trạng thái người dùng')

    class Meta:
        model = Employee
        import_id_fields = ('employee_code',)
        fields = ('employee_code', 'full_name', 'gender', 'date_of_birth', 'identity_number', 'phone_number', 'email', 'is_active')

    def before_import_row(self, row, **kwargs):
        """
        Chuẩn hóa dữ liệu và tự động tạo Department & JobTitle trước khi import Employee.
        EmployeeAssignment được tạo trong after_save_instance.
        """
        # 1. Chuẩn hóa gender
        raw_gender = str(row.get('Giới tính') or '').strip().lower()
        if raw_gender in ['nam', 'male', '1']:
            row['Giới tính'] = 'MALE'
        elif raw_gender in ['nữ', 'nu', 'female', '0']:
            row['Giới tính'] = 'FEMALE'
        else:
            row['Giới tính'] = None

        # 2. Chuẩn hóa is_active thành boolean string "1"/"0" cho Field
        raw_status = str(row.get('Trạng thái người dùng') or '').strip().lower()
        row['Trạng thái người dùng'] = (
            'hoạt động' in raw_status or 'active' in raw_status or raw_status == '1'
        )

        # 3. Chuẩn hóa date_of_birth — Excel có thể trả về datetime object
        raw_dob = row.get('Ngày sinh')
        if raw_dob:
            if hasattr(raw_dob, 'date'):
                row['Ngày sinh'] = raw_dob.date()
            elif isinstance(raw_dob, str) and raw_dob.strip():
                for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
                    try:
                        row['Ngày sinh'] = datetime.strptime(raw_dob.strip(), fmt).date()
                        break
                    except ValueError:
                        pass
        else:
            row['Ngày sinh'] = None

        # 4. Tự động get_or_create Department
        dept_code = str(row.get('Mã đơn vị') or '').strip()
        dept_name = str(row.get('Tên đơn vị') or '').strip()
        if dept_code:
            dept, _ = Department.objects.get_or_create(
                department_code=dept_code,
                defaults={'department_name': dept_name or dept_code}
            )
            if dept_name and dept.department_name != dept_name:
                dept.department_name = dept_name
                dept.save()

        # 5. Tự động get_or_create JobTitle
        title_name = str(row.get('Chức danh') or '').strip()
        if title_name:
            JobTitle.objects.get_or_create(title_name=title_name)

        # 6. Lấy mã người quản lý trực tiếp
        manager_code = str(row.get('Mã người quản lý') or row.get('Mã quản lý') or '').strip()

        # Lưu dept_code, title_name và manager_code vào row để after_save_instance dùng
        row['_dept_code'] = dept_code
        row['_title_name'] = title_name
        row['_manager_code'] = manager_code

    def after_save_instance(self, instance, row, **kwargs):
        """Tạo/cập nhật EmployeeAssignment sau khi Employee đã được lưu."""
        dept_code = row.get('_dept_code', '')
        title_name = row.get('_title_name', '')
        manager_code = row.get('_manager_code', '')

        if dept_code and title_name:
            dept = Department.objects.filter(department_code=dept_code).first()
            title = JobTitle.objects.filter(title_name=title_name).first()
            manager_emp = Employee.objects.filter(employee_code=manager_code).first() if manager_code else None

            if dept and title:
                assignment, created = EmployeeAssignment.objects.get_or_create(
                    employee=instance,
                    department=dept,
                    title=title,
                    defaults={
                        'start_date': datetime.now().date(),
                        'manager': manager_emp
                    }
                )
                if not created and manager_emp and assignment.manager != manager_emp:
                    assignment.manager = manager_emp
                    assignment.save()

    def import_field(self, field, obj, data, is_m2m=False, **kwargs):
        """Override để xử lý date_of_birth và is_active đúng kiểu."""
        attr = field.attribute
        if attr == 'date_of_birth':
            val = data.get(field.column_name)
            if val and hasattr(val, 'date'):
                obj.date_of_birth = val.date()
            elif val and not hasattr(val, 'date'):
                obj.date_of_birth = val  # đã được chuẩn hóa trong before_import_row
            else:
                obj.date_of_birth = None
        elif attr == 'is_active':
            obj.is_active = bool(data.get(field.column_name))
        else:
            super().import_field(field, obj, data, is_m2m=is_m2m, **kwargs)
