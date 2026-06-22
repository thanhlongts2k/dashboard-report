from django.test import TestCase
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
            due_total=1000
        )
        # cust_child: có nợ quá hạn (500)
        self.ageing_child = ReceivablesAgeing.objects.create(
            customer=self.cust_child,
            total_debt=2000,
            overdue_total=500,
            due_total=1500
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


