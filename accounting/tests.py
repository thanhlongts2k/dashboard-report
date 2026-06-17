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

