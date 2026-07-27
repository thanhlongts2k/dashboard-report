import asyncio
import logging
from celery import shared_task
from django.utils import timezone
from .models import ImportLog
from accounting.misa import (
    login_to_misa,
    handle_concurrent_login,
    find_locator_in_any_frame,
    close_misa_popups,
    select_accounts_for_so_chi_tiet,
    download_report_from_url,
    run_misa_automation
)

logger = logging.getLogger(__name__)


@shared_task(name="accounting.tasks.download_misa_reports")
def download_misa_reports_task(period_option=None):
    logger.info("Starting MISA report download task...")
    start_time = timezone.now()
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        result_msg = loop.run_until_complete(run_misa_automation(period_option=period_option))
        logger.info(f"MISA automation run finished: {result_msg}")
        
        ImportLog.objects.create(
            file_name="MISA_Playwright_Automation",
            status='SUCCESS' if "SUCCESS" in result_msg else 'ERROR',
            message=result_msg,
            start_time=start_time,
            end_time=timezone.now()
        )
        return result_msg
    except Exception as e:
        err_msg = f"MISA Playwright Automation Failed: {str(e)}"
        logger.error(err_msg)
        ImportLog.objects.create(
            file_name="MISA_Playwright_Automation",
            status='ERROR',
            message=err_msg,
            start_time=start_time,
            end_time=timezone.now()
        )
        raise e


@shared_task(name="accounting.tasks.misa_pipeline_master")
def misa_pipeline_master(period_option=None):
    logger.info("Starting MISA Pipeline Master Task...")
    
    download_result = download_misa_reports_task(period_option=period_option)
    logger.info(f"Download task finished with result: {download_result}")
    
    from .tasks import auto_import_excel_from_folder
    import_result = auto_import_excel_from_folder()
    logger.info(f"Import task finished with result: {import_result}")
    
    return f"MISA Pipeline completed. Download: {download_result}. Import: {import_result}"
