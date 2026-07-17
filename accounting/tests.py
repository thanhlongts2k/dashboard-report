from django.test import TestCase, override_settings
from django.db.models.deletion import ProtectedError
from django.contrib.admin.sites import site
from accounting.models import Customer, CustomerGroup

class CustomerGroupProtectionTests(TestCase):
    def setUp(self):
        self.group = CustomerGroup.objects.create(code="CG01", name="Group 01")
        self.customer = Customer.objects.create(
            code="C01",
            name="Customer 01",
            group=self.group,
            address="Hanoi, Vietnam"
        )

    def test_delete_group_with_customers_raises_protected_error(self):
        # Deleting a group referenced by a customer should raise ProtectedError
        with self.assertRaises(ProtectedError):
            self.group.delete()

    def test_delete_group_without_customers_succeeds(self):
        # If the customer is deleted or has its group removed, we can delete the group
        self.customer.delete()
        self.group.delete()
        self.assertFalse(CustomerGroup.objects.filter(id=self.group.id).exists())

    def test_customer_admin_fields(self):
        # Verify CustomerAdmin registration and fields
        model_admin = site._registry[Customer]
        self.assertIn('group_name', model_admin.list_display)
        self.assertIn('group__name', model_admin.search_fields)
        
        # Test group_name display method
        self.assertEqual(model_admin.group_name(self.customer), "Group 01")
        
        # Test group_name when group is None
        customer_no_group = Customer.objects.create(
            code="C02",
            name="Customer 02",
            group=None,
            address="Hanoi, Vietnam"
        )
        self.assertEqual(model_admin.group_name(customer_no_group), "-")


class ScheduleDescriptionTests(TestCase):
    def test_settings_has_schedule_desc(self):
        from django.conf import settings
        desc = getattr(settings, 'IMPORT_SCHEDULE_DESC', None)
        self.assertIsNotNone(desc)
        self.assertTrue(isinstance(desc, str))
        self.assertTrue(len(desc) > 0)

    def test_parse_days_of_week_desc(self):
        from report2026.schedule_utils import parse_days_of_week_desc
        self.assertEqual(parse_days_of_week_desc('1'), 'Thứ Hai')
        self.assertEqual(parse_days_of_week_desc('1,3,5'), 'Thứ Hai, Thứ Tư, Thứ Sáu')
        self.assertEqual(parse_days_of_week_desc('1-5'), 'từ Thứ Hai đến Thứ Sáu')
        self.assertEqual(parse_days_of_week_desc('*'), 'tất cả các ngày')

    def test_parse_days_of_month_desc(self):
        from report2026.schedule_utils import parse_days_of_month_desc
        self.assertEqual(parse_days_of_month_desc('1'), 'ngày 01')
        self.assertEqual(parse_days_of_month_desc('1,15'), 'ngày 01, 15')
        self.assertEqual(parse_days_of_month_desc('1-10'), 'từ ngày 01 đến ngày 10')
        self.assertEqual(parse_days_of_month_desc('*'), 'mọi ngày')

    def test_parse_cron_desc(self):
        from report2026.schedule_utils import parse_cron_desc
        self.assertEqual(parse_cron_desc('57 8 * * 1,3,5'), 'Tùy chỉnh (Lúc 08:57 vào các ngày Thứ Hai, Thứ Tư, Thứ Sáu)')
        self.assertEqual(parse_cron_desc('0 7 1,15 * *'), 'Tùy chỉnh (Lúc 07:00 vào ngày 01, 15 hàng tháng)')
        self.assertEqual(parse_cron_desc('30 22 1-5 12 *'), 'Tùy chỉnh (Lúc 22:30 vào từ ngày 01 đến ngày 05 của tháng 12)')


class MisaAutomationTests(TestCase):
    def test_misa_settings_load(self):
        from django.conf import settings
        self.assertIsNotNone(settings.MISA_AMIS_LOGIN_URL)
        self.assertIsNotNone(settings.MISA_REPORTS)
        self.assertIn('BAN_HANG', settings.MISA_REPORTS)
        self.assertIn('MUA_HANG', settings.MISA_REPORTS)
        self.assertIn('TON_KHO', settings.MISA_REPORTS)

    def test_download_misa_reports_fails_without_credentials(self):
        from django.conf import settings
        from django.test import override_settings
        from accounting.tasks import download_misa_reports_task
        from accounting.models import ImportLog

        with override_settings(MISA_EMAIL='', MISA_PASSWORD=''):
            # This should create an ERROR log in ImportLog because credentials are empty
            result = download_misa_reports_task()
            self.assertIn("ERROR", result)
                
            # Verify ImportLog was created with status 'ERROR'
            misa_logs = ImportLog.objects.filter(file_name="MISA_Playwright_Automation")
            self.assertTrue(misa_logs.exists())
            self.assertEqual(misa_logs.first().status, 'ERROR')


from accounting.models import BusinessUnit, Customer, ReceivablesAgeing, AccountDetail, BUPerformance
from accounting.tasks import update_single_bu_performance

class BUHierarchyAndCollectionTests(TestCase):
    def setUp(self):
        # Tạo BU cha và BU con
        self.bu_parent = BusinessUnit.objects.create(code="BUP", name="Parent BU", is_main=True)
        self.bu_child = BusinessUnit.objects.create(code="BUC", name="Child BU", parent=self.bu_parent)

        # Tạo các khách hàng
        self.cust_parent = Customer.objects.create(code="CP", name="Cust Parent", business_unit=self.bu_parent, has_revenue=True)
        self.cust_child = Customer.objects.create(code="CC", name="Cust Child", business_unit=self.bu_child, has_revenue=True)

        # Tạo tuổi nợ cho khách hàng
        # cust_parent: không có nợ quá hạn
        self.ageing_parent = ReceivablesAgeing.objects.create(
            customer=self.cust_parent,
            total_debt=1000,
            overdue_total=0,
            due_total=1000,
            reporting_period="2026-06"
        )
        # cust_child: có nợ quá hạn (500)
        self.ageing_child = ReceivablesAgeing.objects.create(
            customer=self.cust_child,
            total_debt=2000,
            overdue_total=500,
            due_total=1500,
            reporting_period="2026-06"
        )

        # Tạo bút toán thực thu trong AccountDetail
        # Thu từ cust_parent: 400 (vào ngày 2026-06-15)
        self.acc_parent = AccountDetail.objects.create(
            posting_date="2026-06-15",
            doc_id="D1",
            account_number="1111",
            account_name="Cash",
            offset_account="1311",
            debit_amount=400,
            credit_amount=0,
            business_unit=self.bu_parent,
            customer=self.cust_parent
        )
        # Thu từ cust_child: 600 (vào ngày 2026-06-15)
        self.acc_child = AccountDetail.objects.create(
            posting_date="2026-06-15",
            doc_id="D2",
            account_number="1121",
            account_name="Bank",
            offset_account="1312",
            debit_amount=600,
            credit_amount=0,
            business_unit=self.bu_child,
            customer=self.cust_child
        )

    def test_get_all_descendant_ids(self):
        parent_descendants = self.bu_parent.get_all_descendant_ids()
        self.assertIn(self.bu_parent.id, parent_descendants)
        self.assertIn(self.bu_child.id, parent_descendants)
        self.assertEqual(len(parent_descendants), 2)

        child_descendants = self.bu_child.get_all_descendant_ids()
        self.assertEqual(child_descendants, [self.bu_child.id])

    def test_update_single_bu_performance_hierarchy(self):
        # Chạy tính toán hiệu suất BU cha
        update_single_bu_performance(self.bu_parent.id, month=6, year=2026, target_date_str="2026-06-30")

        # Lấy bản ghi hiệu suất BU cha vừa tạo/cập nhật
        perf = BUPerformance.objects.get(business_unit=self.bu_parent, month=6, year=2026)

        # Tổng dư nợ: 1000 (cust_parent) + 2000 (cust_child) = 3000
        self.assertEqual(perf.receivable_total, 3000)

        # Tổng nợ quá hạn: 0 (cust_parent) + 500 (cust_child) = 500
        self.assertEqual(perf.receivable_overdue, 500)

        # Tổng thực thu lũy kế: 400 (cust_parent) + 600 (cust_child) = 1000
        self.assertEqual(perf.mtd_collection_actual, 1000)

        # Đã thu (đến hạn): chỉ có cust_child có nợ quá hạn, số tiền thu là 600
        self.assertEqual(perf.collection_due_actual, 600)

        # Thu trong hạn + COD: 1000 (tổng thực thu) - 600 (đã thu đến hạn) = 400
        self.assertEqual(perf.collection_in_term_cod, 400)


from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from knox.models import AuthToken

class BUReportAPIFilterTests(APITestCase):
    def setUp(self):
        # Tạo user và đăng nhập qua Knox Token
        self.user = User.objects.create_user(username='testuser', password='password')
        _, token = AuthToken.objects.create(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        # Tạo Business Units
        self.bu_parent = BusinessUnit.objects.create(code="BUP", name="Parent BU", is_main=True)
        self.bu_child = BusinessUnit.objects.create(code="BUC", name="Child BU", parent=self.bu_parent)

        # Tạo BUPerformance cho các tháng khác nhau
        self.perf_may = BUPerformance.objects.create(
            business_unit=self.bu_parent, month=5, year=2026,
            mtd_revenue_plan=100, mtd_revenue_actual=90
        )
        self.perf_june = BUPerformance.objects.create(
            business_unit=self.bu_parent, month=6, year=2026,
            mtd_revenue_plan=200, mtd_revenue_actual=180
        )
        self.perf_july_child = BUPerformance.objects.create(
            business_unit=self.bu_child, month=7, year=2026,
            mtd_revenue_plan=150, mtd_revenue_actual=140
        )

        self.api_url = reverse('bu_performance_api')

    def test_get_all_without_params(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)

    def test_filter_by_month_and_year(self):
        response = self.client.get(self.api_url, {'month': 6, 'year': 2026})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['month'], 6)

    def test_filter_by_start_date_only(self):
        # start_date = 2026-06-15, sẽ lấy tháng 6 và tháng 7
        response = self.client.get(self.api_url, {'start_date': '2026-06-15'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        months = [item['month'] for item in response.data]
        self.assertIn(6, months)
        self.assertIn(7, months)

    def test_filter_by_end_date_only(self):
        # end_date = 2026-06-15, sẽ lấy tháng 5 và tháng 6
        response = self.client.get(self.api_url, {'end_date': '2026-06-15'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        months = [item['month'] for item in response.data]
        self.assertIn(5, months)
        self.assertIn(6, months)

    def test_filter_by_date_range(self):
        # start_date = 2026-05-15, end_date = 2026-06-15 -> Lấy tháng 5 và tháng 6
        response = self.client.get(self.api_url, {'start_date': '2026-05-15', 'end_date': '2026-06-15'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        months = [item['month'] for item in response.data]
        self.assertIn(5, months)
        self.assertIn(6, months)

    def test_filter_by_bu_id(self):
        # bu_id = null -> Lấy Tổng công ty (bu_parent vì business_unit__isnull=True là null)
        # Wait, bu_parent và bu_child trong setup đều có business_unit_id khác null.
        # Chúng ta hãy tạo một BUPerformance không có business_unit (Tổng công ty)
        perf_total = BUPerformance.objects.create(
            business_unit=None, month=6, year=2026,
            mtd_revenue_plan=1000, mtd_revenue_actual=900
        )
        # Query bu_id=null -> Trả về perf_total
        response = self.client.get(self.api_url, {'bu_id': 'null'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertIsNone(response.data[0]['business_unit'])

        # Query bu_id = bu_parent -> Trả về perf_may và perf_june
        response = self.client.get(self.api_url, {'bu_id': self.bu_parent.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_filter_only_roots(self):
        # only_roots=true -> Chỉ lấy perf_may và perf_june (vì bu_parent không có parent)
        # và perf_total (vì business_unit=None không có parent)
        perf_total = BUPerformance.objects.create(
            business_unit=None, month=6, year=2026,
            mtd_revenue_plan=1000, mtd_revenue_actual=900
        )
        response = self.client.get(self.api_url, {'only_roots': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3) # perf_may, perf_june, perf_total
        bu_ids = [item['business_unit'] for item in response.data]
        self.assertNotIn(self.bu_child.id, bu_ids)

    def test_no_matching_records_returns_404(self):
        response = self.client.get(self.api_url, {'year': 2027})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['message'], "Không tìm thấy dữ liệu phù hợp với bộ lọc.")


class ImportPeriodDetectionTests(TestCase):
    def test_detect_period_from_filename_range(self):
        from accounting.tasks import detect_period_from_filename
        start, end, period, is_range = detect_period_from_filename("BAN_HANG_202601-202605.xlsx", None)
        self.assertEqual(start.year, 2026)
        self.assertEqual(start.month, 1)
        self.assertEqual(start.day, 1)
        self.assertEqual(end.year, 2026)
        self.assertEqual(end.month, 5)
        self.assertEqual(end.day, 31)
        self.assertEqual(period, "2026-05")
        self.assertTrue(is_range)

    def test_detect_period_from_filename_single(self):
        from accounting.tasks import detect_period_from_filename
        start, end, period, is_range = detect_period_from_filename("BAN_HANG_20260710_072009.xlsx", None)
        self.assertEqual(start.year, 2026)
        self.assertEqual(start.month, 7)
        self.assertEqual(start.day, 1)
        self.assertEqual(end.year, 2026)
        self.assertEqual(end.month, 7)
        self.assertEqual(end.day, 31)
        self.assertEqual(period, "2026-07")
        self.assertFalse(is_range)

    def test_detect_period_from_filename_month(self):
        from accounting.tasks import detect_period_from_filename
        start, end, period, is_range = detect_period_from_filename("BAN_HANG_202606.xlsx", None)
        self.assertEqual(start.year, 2026)
        self.assertEqual(start.month, 6)
        self.assertEqual(start.day, 1)
        self.assertEqual(end.year, 2026)
        self.assertEqual(end.month, 6)
        self.assertEqual(end.day, 30)
        self.assertEqual(period, "2026-06")
        self.assertFalse(is_range)

    def test_bu_performance_ytd_propagation(self):
        from accounting.models import BusinessUnit, BUPerformance
        from accounting.tasks import update_single_bu_performance
        
        bu = BusinessUnit.objects.create(code="TEST_YTD", name="Test YTD BU")
        
        # Tạo sẵn bản ghi BUPerformance cho tháng 5 và 6
        perf_may = BUPerformance.objects.create(
            business_unit=bu, month=5, year=2026,
            mtd_revenue_actual=1000, mtd_collection_actual=800,
            ytd_revenue_actual=1000, ytd_collection_actual=800
        )
        perf_june = BUPerformance.objects.create(
            business_unit=bu, month=6, year=2026,
            mtd_revenue_actual=1500, mtd_collection_actual=1200,
            ytd_revenue_actual=2500, ytd_collection_actual=2000
        )
        
        # Chạy update cho tháng 5
        update_single_bu_performance(bu.id, month=5, year=2026)
        
        # Lấy lại bản ghi tháng 6 để kiểm tra lũy kế YTD có tự động cập nhật
        perf_june.refresh_from_db()
        perf_may.refresh_from_db()
        self.assertEqual(perf_june.ytd_revenue_actual, perf_may.ytd_revenue_actual + perf_june.mtd_revenue_actual)
        self.assertEqual(perf_june.ytd_collection_actual, perf_may.ytd_collection_actual + perf_june.mtd_collection_actual)


class OPEXTestCase(TestCase):
    def setUp(self):
        self.bu = BusinessUnit.objects.create(code="TEST_BU", name="Test Business Unit")

    def test_opex_calculation_and_sync(self):
        from datetime import datetime
        from accounting.models import BUPerformanceDaily
        
        # 1. Tạo BUPerformance tháng 6/2026 với opex_plan = 3.0 tỷ
        perf = BUPerformance.objects.create(
            business_unit=self.bu,
            month=6,
            year=2026,
            opex_plan=3000000000
        )
        
        # 2. Tạo bút toán thực tế cho ngày 01/06 và 02/06
        # Tài khoản 641 (Nợ 50 triệu)
        AccountDetail.objects.create(
            posting_date=datetime(2026, 6, 1).date(),
            doc_id="PC001",
            account_number="6411",
            debit_amount=50000000,
            credit_amount=0,
            business_unit=self.bu
        )
        # Tài khoản 642 (Nợ 30 triệu)
        AccountDetail.objects.create(
            posting_date=datetime(2026, 6, 2).date(),
            doc_id="PC002",
            account_number="6422",
            debit_amount=30000000,
            credit_amount=0,
            business_unit=self.bu
        )
        
        # 3. Chạy tính toán hiệu suất BU cho ngày 15/06/2026
        update_single_bu_performance(self.bu.id, month=6, year=2026, target_date_str="2026-06-15")
        
        # 4. Kiểm chứng kết quả
        perf.refresh_from_db()
        
        # Kiểm tra chi phí vận hành tháng thực tế opex_actual = Kế hoạch 15 ngày (1.5 tỷ) + Thực tế giao dịch (80 triệu) = 1.58 tỷ
        self.assertEqual(perf.opex_actual, 1580000000)
        
        # Kiểm tra các ngày con:
        # Số ngày tháng 6 = 30 ngày. Kế hoạch mỗi ngày = 3 tỷ / 30 = 100 triệu
        day1 = BUPerformanceDaily.objects.get(performance_month=perf, date=datetime(2026, 6, 1).date())
        self.assertEqual(day1.daily_opex_plan, 100000000)
        self.assertEqual(day1.daily_opex_actual, 50000000)
        
        day2 = BUPerformanceDaily.objects.get(performance_month=perf, date=datetime(2026, 6, 2).date())
        self.assertEqual(day2.daily_opex_plan, 100000000)
        self.assertEqual(day2.daily_opex_actual, 30000000)
        
        # Một ngày tương lai (ví dụ 20/06) - opex_plan vẫn có nhưng opex_actual = 0 vì vượt quá target_date
        day20 = BUPerformanceDaily.objects.get(performance_month=perf, date=datetime(2026, 6, 20).date())
        self.assertEqual(day20.daily_opex_plan, 100000000)
        self.assertEqual(day20.daily_opex_actual, 0)


class BankBalanceTestCase(TestCase):
    def setUp(self):
        from accounting.models import BusinessUnit, Customer
        self.bu = BusinessUnit.objects.create(code="TEST_BU_BAL", name="BU Test Balance")
        self.cust = Customer.objects.create(code="TEST_CUST_BAL", name="Cust Test Balance", has_revenue=True)

    def test_cash_balance_actual_with_excluded_bank_account(self):
        from datetime import datetime
        from accounting.models import AccountDetail, BankBalance, BUPerformance
        from accounting.tasks import update_single_bu_performance
        
        # 1. Tạo các bút toán Sổ chi tiết
        # TK 111 có số dư 100 triệu
        AccountDetail.objects.create(
            posting_date=datetime(2026, 7, 10).date(),
            doc_id="PC001",
            account_number="111",
            debit_amount=100000000,
            credit_amount=0,
            balance_debit=100000000,
            business_unit=self.bu,
            customer=self.cust
        )
        
        # TK 112 có số dư 500 triệu
        AccountDetail.objects.create(
            posting_date=datetime(2026, 7, 11).date(),
            doc_id="UNC001",
            account_number="112",
            debit_amount=500000000,
            credit_amount=0,
            balance_debit=500000000,
            business_unit=self.bu,
            customer=self.cust
        )
        
        # 2. Tạo số dư ngân hàng trong BankBalance
        # Có tài khoản loại trừ '113611393939' có số dư 120 triệu
        BankBalance.objects.create(
            bank_account_number="113611393939",
            bank_name="Vietcombank",
            balance=120000000,
            reporting_month="2026-07"
        )
        
        # Có tài khoản bình thường khác có số dư 380 triệu
        BankBalance.objects.create(
            bank_account_number="9999999999",
            bank_name="Techcombank",
            balance=380000000,
            reporting_month="2026-07"
        )

        # 3. Chạy tính toán hiệu suất BU cho tháng 7/2026
        # opex_plan = 0
        perf = BUPerformance.objects.create(
            business_unit=self.bu,
            month=7,
            year=2026,
            opex_plan=0
        )
        
        update_single_bu_performance(self.bu.id, month=7, year=2026, target_date_str="2026-07-15")
        
        # 4. Kiểm chứng kết quả
        perf.refresh_from_db()
        
        # Tổng Ledger: 111 (100tr) + 112 (500tr) = 600tr
        # Trừ đi tài khoản loại trừ (120tr) = 480tr
        self.assertEqual(perf.cash_balance_actual, 480000000)


class SalesTransactionImportTests(TestCase):
    def test_customer_group_auto_creation_during_import(self):
        from accounting.resources import SalesTransactionResource
        from accounting.models import Customer, CustomerGroup
        
        resource = SalesTransactionResource()
        row = {
            'Ngày hạch toán': '2026-07-15',
            'Số chứng từ': 'HD001',
            'Mã khách hàng': 'CUST_TEST_001',
            'Tên khách hàng': 'Khách hàng Test',
            'Mã hàng': 'PROD_TEST_001',
            'Tên hàng': 'Hàng hóa Test',
            'Mã nhóm khách hàng': 'GRP_TEST_001',
            'Tên nhóm khách hàng': 'Nhóm KH Test',
            'Mã nhóm VTHH': 'VTHH_TEST',
            'Tên nhóm VTHH': 'Nhóm VTHH Test',
            'Mã kho': 'KHO_TEST',
            'Tên kho': 'Kho Test',
            'Chi nhánh': 'Chi nhánh Test',
            'Mã nhân viên bán hàng': 'NV_TEST',
            'Tên nhân viên bán hàng': 'Nhân viên Test',
            'Mã thống kê': 'BU_TEST',
            'Tên thống kê': 'BU Test',
            'Tổng số lượng bán': 10,
            'Đơn giá': 1000,
            'Doanh số bán': 10000,
            'TK Nợ': '131',
            'TK Có': '511',
            'Doanh số thực tế': 10000
        }
        
        # Chạy before_import_row
        resource.before_import_row(row)
        
        # Kiểm tra xem CustomerGroup đã được tự động tạo chưa
        group = CustomerGroup.objects.filter(code='GRP_TEST_001').first()
        self.assertIsNotNone(group)
        self.assertEqual(group.name, 'Nhóm KH Test')
        
        # Kiểm tra xem Customer đã được tạo và liên kết với CustomerGroup chưa
        customer = Customer.objects.filter(code='CUST_TEST_001').first()
        self.assertIsNotNone(customer)
        self.assertEqual(customer.name, 'Khách hàng Test')
        self.assertEqual(customer.group, group)


class BUOverseaFilterTests(TestCase):
    def setUp(self):
        from accounting.models import BusinessUnit, Customer, CustomerGroup, Product, MaterialGroup
        
        # 1. Tạo BU
        self.hpc = BusinessUnit.objects.create(code='HPC', name='Hạo Phương', is_main=False)
        self.bu_elevator = BusinessUnit.objects.create(code='BU_ELEVATOR', name='Thang máy', is_main=True, parent=self.hpc)
        self.bu_oversea = BusinessUnit.objects.create(code='Oversea', name='Oversea', is_main=True, parent=self.hpc)
        
        # 2. Tạo Nhóm khách hàng
        self.grp_dom = CustomerGroup.objects.create(code='DOM', name='Trong nước')
        self.grp_ovs = CustomerGroup.objects.create(code='Oversea', name='Oversea')
        
        # 3. Tạo Khách hàng và liên kết với BU để thỏa mãn bộ lọc công nợ/doanh thu
        self.cust_dom = Customer.objects.create(code='C_DOM', name='Khách Trong nước', group=self.grp_dom, business_unit=self.bu_elevator)
        self.cust_ovs = Customer.objects.create(code='C_OVS', name='Khách Oversea', group=self.grp_ovs, business_unit=self.bu_oversea)
        
        # 4. Tạo sản phẩm để tránh lỗi FK
        self.mat_grp = MaterialGroup.objects.create(code='VTHH_TEST', name='Nhóm VTHH')
        self.prod = Product.objects.create(code='PROD_TEST', name='Sản phẩm test', group=self.mat_grp)

    def test_oversea_customer_filtering_in_bu_performance(self):
        from datetime import date
        from accounting.models import SalesTransaction, BUPerformance, ReceivablesAgeing, AccountDetail
        from accounting.tasks import update_single_bu_performance
        
        # 5. Tạo các giao dịch bán hàng (Tháng 7/2026)
        # Tx1: Giao dịch của Khách trong nước thuộc BU ELEVATOR
        SalesTransaction.objects.create(
            posting_date=date(2026, 7, 15),
            doc_id='HD001',
            customer=self.cust_dom,
            product=self.prod,
            business_unit=self.bu_elevator,
            actual_sales=1000000
        )
        # Tx2: Giao dịch của Khách Oversea thuộc BU ELEVATOR (Phải bị LOẠI TRỪ khỏi ELEVATOR)
        SalesTransaction.objects.create(
            posting_date=date(2026, 7, 15),
            doc_id='HD002',
            customer=self.cust_ovs,
            product=self.prod,
            business_unit=self.bu_elevator,
            actual_sales=2000000
        )
        # Tx3: Giao dịch của Khách Oversea thuộc BU Oversea (Phải được tính cho BU Oversea)
        SalesTransaction.objects.create(
            posting_date=date(2026, 7, 15),
            doc_id='HD003',
            customer=self.cust_ovs,
            product=self.prod,
            business_unit=self.bu_oversea,
            actual_sales=3000000
        )
        # Tx4: Giao dịch của Khách trong nước thuộc BU Oversea (Phải bị LOẠI TRỪ khỏi BU Oversea)
        SalesTransaction.objects.create(
            posting_date=date(2026, 7, 15),
            doc_id='HD004',
            customer=self.cust_dom,
            product=self.prod,
            business_unit=self.bu_oversea,
            actual_sales=4000000
        )

        # 6. Tạo tuổi nợ để kiểm thử lọc ageing
        ReceivablesAgeing.objects.create(
            customer=self.cust_dom,
            reporting_period='2026-07',
            total_debt=100000,
            overdue_total=10000
        )
        ReceivablesAgeing.objects.create(
            customer=self.cust_ovs,
            reporting_period='2026-07',
            total_debt=200000,
            overdue_total=20000
        )

        # 7. Tạo bút toán sổ chi tiết để kiểm thử lọc thực thu (collection)
        # Coll1: Khách trong nước thuộc BU Elevator (Phải được tính cho Elevator)
        AccountDetail.objects.create(
            posting_date=date(2026, 7, 10),
            doc_id='PT001',
            account_number='1121',
            offset_account='1311',
            debit_amount=150000,
            credit_amount=0,
            business_unit=self.bu_elevator,
            customer=self.cust_dom
        )
        # Coll2: Khách Oversea thuộc BU Elevator (Phải bị loại trừ khỏi Elevator, tính cho Oversea)
        AccountDetail.objects.create(
            posting_date=date(2026, 7, 11),
            doc_id='PT002',
            account_number='1121',
            offset_account='1311',
            debit_amount=250000,
            credit_amount=0,
            business_unit=self.bu_elevator,
            customer=self.cust_ovs
        )
        # Coll3: Khách Oversea thuộc BU Oversea (Phải được tính cho Oversea)
        AccountDetail.objects.create(
            posting_date=date(2026, 7, 12),
            doc_id='PT003',
            account_number='1121',
            offset_account='1311',
            debit_amount=350000,
            credit_amount=0,
            business_unit=self.bu_oversea,
            customer=self.cust_ovs
        )
        # Coll4: Khách trong nước thuộc BU Oversea (Phải bị loại trừ khỏi Oversea)
        AccountDetail.objects.create(
            posting_date=date(2026, 7, 13),
            doc_id='PT004',
            account_number='1121',
            offset_account='1311',
            debit_amount=450000,
            credit_amount=0,
            business_unit=self.bu_oversea,
            customer=self.cust_dom
        )

        # Chạy tính toán cho BU_ELEVATOR
        update_single_bu_performance(self.bu_elevator.id, month=7, year=2026, target_date_str='2026-07-15')
        perf_elevator = BUPerformance.objects.get(business_unit=self.bu_elevator, month=7, year=2026)
        
        # BU_ELEVATOR: Chỉ tính giao dịch của khách hàng TRONG NƯỚC được ghi nhận vào BU Elevator
        # Tx1 (1M, khách DOM, BU Elevator) → Tính
        # Tx2 (2M, khách OVS, BU Elevator) → Loại trừ (khách Oversea, không phải BU Oversea)
        self.assertEqual(perf_elevator.mtd_revenue_actual, 1000000)
        # Công nợ: chỉ khách hàng trong nước (DOM) → 100k
        self.assertEqual(perf_elevator.receivable_total, 100000)
        self.assertEqual(perf_elevator.receivable_overdue, 10000)
        # Thực thu: chỉ tính Coll1 (150k), loại trừ Coll2 (250k, khách Oversea)
        self.assertEqual(perf_elevator.mtd_collection_actual, 150000)
        self.assertEqual(perf_elevator.mtd_collection_oversea_actual, 0)
        self.assertEqual(perf_elevator.mtd_collection_exclude_oversea_actual, 150000)

        # Chạy tính toán cho BU Oversea
        update_single_bu_performance(self.bu_oversea.id, month=7, year=2026, target_date_str='2026-07-15')
        perf_oversea = BUPerformance.objects.get(business_unit=self.bu_oversea, month=7, year=2026)
        
        # BU Oversea (Cách B): Tính TẤT CẢ giao dịch của khách hàng thuộc nhóm Oversea,
        # BẤT KỂ giao dịch đó được ghi nhận ở BU nào trong MISA.
        # Tx2 (2M, khách OVS, BU Elevator) → Tính (khách Oversea)
        # Tx3 (3M, khách OVS, BU Oversea)  → Tính (khách Oversea)
        # Tx4 (4M, khách DOM, BU Oversea)  → Loại trừ (khách trong nước)
        self.assertEqual(perf_oversea.mtd_revenue_actual, 5000000)  # 2M + 3M
        # Công nợ: chỉ khách Oversea (OVS) → 200k
        self.assertEqual(perf_oversea.receivable_total, 200000)
        self.assertEqual(perf_oversea.receivable_overdue, 20000)
        # Thực thu: tính Coll2 (250k) và Coll3 (350k) = 600k, loại trừ Coll4 (450k, khách DOM)
        self.assertEqual(perf_oversea.mtd_collection_actual, 600000)
        self.assertEqual(perf_oversea.mtd_collection_oversea_actual, 600000)
        self.assertEqual(perf_oversea.mtd_collection_exclude_oversea_actual, 0)

        # Chạy tính toán cho Global (Tổng công ty)
        update_single_bu_performance(None, month=7, year=2026, target_date_str='2026-07-15')
        perf_global = BUPerformance.objects.get(business_unit__isnull=True, month=7, year=2026)
        
        # Tổng công ty: Tính tất cả = 1M + 2M + 3M + 4M = 10M
        self.assertEqual(perf_global.mtd_revenue_actual, 10000000)
        # Tổng công ty: Công nợ = 100k (DOM) + 200k (OVS) = 300k
        self.assertEqual(perf_global.receivable_total, 300000)
        self.assertEqual(perf_global.receivable_overdue, 30000)
        # Tổng công ty: Thực thu = 150k + 250k + 350k + 450k = 1.2M
        self.assertEqual(perf_global.mtd_collection_actual, 1200000)
        self.assertEqual(perf_global.mtd_collection_oversea_actual, 600000)  # Coll2 + Coll3
        self.assertEqual(perf_global.mtd_collection_exclude_oversea_actual, 600000)  # Coll1 + Coll4


from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from knox.models import AuthToken
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile

class SendEmailAPITests(APITestCase):
    def setUp(self):
        # Create a user and get Knox token
        self.user = User.objects.create_user(username='testuser', password='password123')
        _, self.token = AuthToken.objects.create(self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token)
        
        # URL
        self.url = '/api/reports/send-email/'

    def test_send_email_unauthorized_fails(self):
        # Clear credentials
        self.client.credentials()
        response = self.client.post(self.url, {
            'to_emails': 'recipient@example.com',
            'subject': 'Test Subject',
            'message': 'Test Message'
        })
        self.assertEqual(response.status_code, 401)

    def test_send_email_missing_required_fields_fails(self):
        # Missing to_emails
        response = self.client.post(self.url, {
            'subject': 'Test Subject',
            'message': 'Test Message'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('to_emails', response.data)

        # Missing subject
        response = self.client.post(self.url, {
            'to_emails': 'recipient@example.com',
            'message': 'Test Message'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('subject', response.data)

    def test_send_email_invalid_to_emails_fails(self):
        response = self.client.post(self.url, {
            'to_emails': 'invalid-email',
            'subject': 'Test Subject',
            'message': 'Test Message'
        })
        self.assertEqual(response.status_code, 400)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_email_success_without_attachment(self):
        mail.outbox = []
        response = self.client.post(self.url, {
            'to_emails': 'recipient1@example.com, recipient2@example.com',
            'subject': 'Test Subject',
            'message': 'Test Message',
            'from_email': 'sender@example.com'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'success')
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, 'Test Subject')
        self.assertEqual(sent_email.body, 'Test Message')
        self.assertIn('sender@example.com', sent_email.from_email)
        self.assertEqual(sent_email.to, ['recipient1@example.com', 'recipient2@example.com'])
        self.assertEqual(len(sent_email.attachments), 0)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_email_success_with_attachment(self):
        mail.outbox = []
        # Create a simple file
        test_file = SimpleUploadedFile("report.xlsx", b"excel_content", content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        response = self.client.post(self.url, {
            'to_emails': 'recipient@example.com',
            'subject': 'Test Attachment Subject',
            'message': 'Test Message with file',
            'file': test_file,
            'file_name': 'custom_report_name.xlsx'
        }, format='multipart')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'success')
        
        # Verify email was sent with attachment
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, 'Test Attachment Subject')
        self.assertEqual(sent_email.to, ['recipient@example.com'])
        self.assertEqual(len(sent_email.attachments), 1)
        
        attachment = sent_email.attachments[0]
        # attachment is a tuple: (filename, content, mimetype)
        self.assertEqual(attachment[0], 'custom_report_name.xlsx')
        self.assertEqual(attachment[1], b'excel_content')
        self.assertEqual(attachment[2], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_email_json_success(self):
        mail.outbox = []
        response = self.client.post(self.url, {
            'to_emails': 'json_recipient@example.com',
            'subject': 'Test JSON Subject',
            'message': 'Test JSON Message'
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'success')
        
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, 'Test JSON Subject')
        self.assertEqual(sent_email.body, 'Test JSON Message')
        self.assertEqual(sent_email.to, ['json_recipient@example.com'])

    def test_send_email_oversized_file_fails(self):
        # Create a file larger than 20MB (21MB)
        large_file = SimpleUploadedFile("huge_report.xlsx", b"0" * (21 * 1024 * 1024))
        
        response = self.client.post(self.url, {
            'to_emails': 'recipient@example.com',
            'subject': 'Oversized Subject',
            'message': 'Test Message',
            'file': large_file
        }, format='multipart')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('file', response.data)
        self.assertEqual(response.data['file'][0], "Kích thước file đính kèm không được vượt quá 20MB.")







