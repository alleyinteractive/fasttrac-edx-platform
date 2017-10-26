from datetime import datetime
import json
from lms import CELERY_APP
from instructor_task.tasks_helper import upload_csv_to_report_store
from django.conf import settings
from lms.djangoapps.ccx.models import CustomCourseForEdX
from student.models import UserProfile
from .models import AffiliateEntity
from lms.djangoapps.ccx.views import get_ccx_schedule
from courseware.models import StudentModule, StudentTimeTracker
from opaque_keys.edx.keys import UsageKey


@CELERY_APP.task
def export_csv_affiliate_course_report():
    """
    Celery task for saving affiliate reports as CSV and uploading to S3
    """
    partial_course_key = settings.FASTTRAC_COURSE_KEY.split(':')[1]
    ccxs = CustomCourseForEdX.objects.all()
    ccxs = sorted(ccxs, key=lambda ccx: ccx.affiliate.name)

    rows = [['Course Name', 'Course ID', 'Affiliate Name', 'Start Date', 'End Date', 'Participant Count',
         'Delivery Mode', 'Enrollment Type', 'Course Type', 'Fee', 'Facilitator Name']]

    for ccx in ccxs:
        rows.append([
            ccx.display_name, ccx.ccx_course_id,
            ccx.affiliate.name, ccx.time.strftime("%B %d, %Y"),
            (ccx.end_date.strftime("%B %d, %Y") if ccx.end_date else '--'),
            ccx.students.count(), ccx.get_delivery_mode_display(),
            ccx.get_enrollment_type_display(),
            ('FastTrac' if partial_course_key in unicode(ccx.ccx_course_id) else 'Facilitator Guide'),
            ('Yes' if ccx.fee else 'No'),
            ccx.facilitator_names
        ])

    params = {
        'csv_name': 'course_report',
        'course_id': 'affiliates',
        'timestamp': datetime.now(),
        'rows': rows
    }

    upload_csv_to_report_store(**params)



@CELERY_APP.task
def export_csv_affiliate_report():
    """
    Celery task for saving affiliate reports as CSV and uploading to S3
    """
    affiliates = AffiliateEntity.objects.all().order_by('name')

    rows = [[
        'Name', 'Members count', 'Courses count', 'Enrollments count', 'Last Course Taught',
        'Last Course Date', 'Last Affiliate User Login (name, date)', 'Last Affiliate Learner Login'
    ]]

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
        'csv_name': 'affiliate_report',
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

    rows = [['Username', 'Email', 'Registration Date', 'Country', 'First Name', 'Last Name',
             'Mailing Address', 'City', 'State', 'Postal Code', 'Phone Number', 'Company', 'Title',
             'Would you like to receive marketing communication from the Ewing Marion Kauffman Foundation and Kauffman FastTrac?',
             'Your motivation', 'Age', 'Gender', 'Race/Ethnicity', 'Were you born a citizen of the United States?',
             'Have you ever served in any branch of the U.S. Armed Forces, including the Coast Guard, the National Guard, or Reserve component of any service branch?',
             'What was the highest degree or level of school you have completed?']]

    profiles = UserProfile.objects.all()
    for profile in profiles:
        rows.append([profile.user.username, profile.user.email, profile.user.date_joined,
                     profile.get_country_display(), profile.user.first_name, profile.user.last_name,
                     profile.mailing_address, profile.city, profile.get_state_display(), profile.zipcode,
                     profile.phone_number, profile.company, profile.title, profile.get_newsletter_display(),
                     profile.get_bio_display(), profile.get_age_category_display(), profile.get_gender_display(),
                     profile.get_ethnicity_display(), profile.get_immigrant_status_display(),
                     profile.get_veteran_status_display(), profile.get_education_display()])

    params.update({'rows': rows})

    upload_csv_to_report_store(**params)


@CELERY_APP.task
def export_csv_course_report(time_report=True):
    fasttrac_course_key = settings.FASTTRAC_COURSE_KEY.split(':')[1]
    ccxs = CustomCourseForEdX.objects.filter(course_id__icontains=fasttrac_course_key)

    fasttrac_course = ccxs[0].course
    original_course_id = unicode(fasttrac_course.id).split(':')[1]

    # build headers
    header_columns = ['Username', 'Email', 'Course ID', 'Course Name']
    header_index_padding = len(header_columns)

    for section in fasttrac_course.get_children():
        for subsection in section.get_children():
            for unit in subsection.get_children():
                header_columns.append("{} - {} - {}".format(section.display_name, subsection.display_name, unit.display_name))

    fasttrac_course_units_length = len(header_columns) - header_index_padding

    rows = [header_columns]

    for ccx in ccxs:
        # we need these values for converting unit and xblock location keys
        ccx_course_id = unicode(ccx.ccx_course_id).split(':')[1]

        students = [student.user for student in ccx.students]
        student_time_tracker = StudentTimeTracker.objects.filter(course_id=ccx.ccx_course_id)
        student_modules = StudentModule.objects.filter(course_id=ccx.ccx_course_id)

        student_data = {}

        # for each student create empty CSV row
        for student in students:
            student_id = unicode(student.id)
            student_data[student_id] = ['/'] * fasttrac_course_units_length

        for section in get_ccx_schedule(ccx.course, ccx, True):
            for subsection in section['children']:
                for unit in subsection['children']:
                    # get ccx location key
                    # get_ccx_schedule returns original course location keys
                    ccx_id = 'ccx-' + unit['location']
                    ccx_unit_location = ccx_id.replace(original_course_id, ccx_course_id)
                    location = UsageKey.from_string(ccx_unit_location)

                    for student in students:
                        student_id = unicode(student.id)

                        try:
                            column_name = "{} - {} - {}".format(section['display_name'], subsection['display_name'], unit['display_name'])
                            unit_index = header_columns.index(column_name) - header_index_padding
                        except IndexError:
                            continue

                        unit_data = '-'

                        # if we are generating a time spent on unit report
                        if time_report:
                            # get time tracker object
                            tracker = student_time_tracker.filter(unit_location=location, student=student).first()

                            if tracker:
                                unit_data = tracker.time_duration/1000

                        # if we are generating a course completion report
                        else:
                            for xblock_id in unit['children']:
                                xblock_ccx_id = 'ccx-' + unicode(xblock_id)
                                ccx_xblock_location = xblock_ccx_id.replace(original_course_id, ccx_course_id)
                                xblock_location = UsageKey.from_string(ccx_xblock_location)

                                module = student_modules.filter(module_state_key=xblock_location, student=student).first()
                                if module and ('done' in module.state or 'helpful' in module.state):
                                    module_state = json.loads(module.state)

                                    if module_state.get('done'):
                                        unit_data = 'done'
                                    elif module_state.get('helpful') != None:
                                        if module_state.get('helpful'):
                                            unit_data = 'helpful'
                                        else:
                                            unit_data = 'not helpful'

                        student_data[student_id][unit_index] = unit_data


        for student_id in student_data:
            if student_data.get(student_id):
                student = filter(lambda s: unicode(s.id) == student_id, students)[0]

                student_data[student_id].insert(0, ccx.display_name)
                student_data[student_id].insert(0, ccx.ccx_course_id)
                student_data[student_id].insert(0, student.email)
                student_data[student_id].insert(0, student.username)

                rows.append(student_data[student_id])

    csv_name = 'time_report' if time_report else 'completion_report'

    params = {
        'csv_name': csv_name,
        'course_id': 'affiliates',
        'timestamp': datetime.now(),
        'rows': rows
    }

    upload_csv_to_report_store(**params)
