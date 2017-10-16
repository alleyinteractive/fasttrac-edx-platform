from datetime import datetime
from lms import CELERY_APP
from instructor_task.tasks_helper import upload_csv_to_report_store
from django.conf import settings
from lms.djangoapps.ccx.models import CustomCourseForEdX
from student.models import UserProfile
from .models import AffiliateEntity


@CELERY_APP.task
def export_csv_affiliate_report():
    """
    Celery task for saving affiliate reports as CSV and uploading to S3
    """
    partial_course_key = settings.FASTTRAC_COURSE_KEY.split(':')[1]
    ccxs = CustomCourseForEdX.objects.all()
    ccxs = sorted(ccxs, key=lambda ccx: ccx.affiliate.name)
    affiliates = AffiliateEntity.objects.all().order_by('name')


    rows = [['Course Name', 'Affiliate Name', 'Start Date', 'End Date', 'Participant Count',
        'Delivery Mode', 'Enrollment Type', 'Course Type', 'Fee', 'Facilitator Name']]

    for ccx in ccxs:
        rows.append([
            ccx.display_name, ccx.affiliate.name, ccx.time.strftime("%B %d, %Y"),
            (ccx.end_date.strftime("%B %d, %Y") if ccx.end_date else '--'),
            ccx.students.count(), ccx.get_delivery_mode_display(),
            ccx.get_enrollment_type_display(),
            ('FastTrac' if partial_course_key in unicode(ccx.ccx_course_id) else 'Facilitator Guide'),
            ('Yes' if ccx.fee else 'No'),
            ccx.facilitator_names
        ])

    rows.append([])

    rows.append([
        'Name', 'Members count', 'Courses count', 'Enrollments count', 'Last Course Taught',
        'Last Course Date', 'Last Affiliate User Login (name, date)', 'Last Affiliate Learner Login'
    ])

    for affiliate in affiliates:
        rows.append([
            affiliate.name, affiliate.members.count(), affiliate.courses.count(), affiliate.enrollments.count(),
            (affiliate.last_course_taught.display_name if affiliate.last_course_taught else '--'),
            (affiliate.last_course_taught.end_date.strftime(
                "%B %d, %Y") if affiliate.last_course_taught else '--'),
            ("{}, {}".format(affiliate.last_affiliate_user.profile.name, affiliate.last_affiliate_user.last_login.strftime(
                "%B %d, %Y")) if affiliate.last_affiliate_user else '--'),
            ("{}, {}".format(affiliate.last_affiliate_learner.profile.name, affiliate.last_affiliate_learner.last_login.strftime(
                "%B %d, %Y")) if affiliate.last_affiliate_learner else '--')
        ])

    params = {
        'csv_name': 'report',
        'course_id': 'affiliates',
        'timestamp': datetime.now(),
        'rows': rows
    }

    upload_csv_to_report_store(**params)


@CELERY_APP.task
def export_csv_user_report():
    """
    Celery task for saving user reports as CSV and uploading to S3
    """
    params = {'csv_name': 'user_report', 'course_id': 'affiliates',
              'timestamp': datetime.now()}

    rows = [['username', 'email', 'country', 'first_name', 'last_name', 'mailing_address', 'city', 'state', 'postal_code', 'phone_number', 'company', 'title', 'Would you like to receive marketing communication from the Ewing Marion Kauffman Foundation and Kauffman FastTrac?', 'Your motivation', 'Age', 'Gender', 'Race/Ethnicity', 'Were you born a citizen of the United States?', 'Have you ever served in any branch of the U.S. Armed Forces, including the Coast Guard, the National Guard, or Reserve component of any service branch?', 'What was the highest degree or level of school you have completed?']]

    profiles = UserProfile.objects.all()
    for profile in profiles:
        rows.append([profile.user.username, profile.user.email, profile.get_country_display(), profile.user.first_name, profile.user.last_name, profile.mailing_address, profile.city, profile.get_state_display(), profile.zipcode, profile.phone_number, profile.company, profile.title, profile.get_newsletter_display(), profile.get_bio_display(), profile.get_age_category_display(), profile.get_gender_display(), profile.get_ethnicity_display(), profile.get_immigrant_status_display(), profile.get_veteran_status_display(), profile.get_education_display()])

    params.update({'rows': rows})
    upload_csv_to_report_store(**params)
