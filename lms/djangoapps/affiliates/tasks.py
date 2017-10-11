from datetime import datetime
from lms import CELERY_APP
from instructor_task.tasks_helper import upload_csv_to_report_store

@CELERY_APP.task
def export_csv_report():
    """
    Celery task for saving affiliate reports as CSV and uploading to S3
    """
    params = {
        'csv_name': 'report',
        'course_id': 'affiliates',
        'timestamp': datetime.now(),
        'rows': [
            ['header'],
            ['content']
        ]
    }

    upload_csv_to_report_store(**params)
