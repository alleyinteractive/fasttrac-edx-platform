import json
from collections import OrderedDict, defaultdict
from datetime import datetime

import requests
from django.conf import settings
from ccx_keys.locator import CCXBlockUsageLocator
from opaque_keys.edx.keys import CourseKey, UsageKey

from instructor_task.tasks_helper import upload_csv_to_report_store
from lms import CELERY_APP
from lms.djangoapps.ccx.models import CustomCourseForEdX
from lms.djangoapps.ccx.utils import get_ccx_from_ccx_locator
from lms.djangoapps.ccx.views import get_ccx_schedule
from student.models import UserProfile, CourseEnrollment, CourseAccessRole
from courseware.models import StudentModule, StudentTimeTracker
from openedx.core.djangoapps.content.course_structures.models import CourseStructure
from .models import AffiliateEntity, AffiliateMembership
from xmodule.modulestore.django import modulestore


@CELERY_APP.task
def export_csv_affiliate_course_report():
    """
    Celery task for saving affiliate reports as CSV and uploading to S3
    """
    partial_course_key = settings.FASTTRAC_COURSE_KEY.split(':')[1]
    ccxs = CustomCourseForEdX.objects.all()
    ccxs = sorted(ccxs, key=lambda ccx: ccx.affiliate.name)

    rows = [['Course Name', 'Course ID', 'Affiliate Name', 'Affiliate Active', 'Start Date', 'End Date', 'Participant Count',
         'Delivery Mode', 'Enrollment Type', 'Course Type', 'Fee', 'Facilitator Name']]

    for ccx in ccxs:
        rows.append([
            ccx.display_name, ccx.ccx_course_id,
            ccx.affiliate.name, ('Yes' if ccx.affiliate.active else 'No'),
            ccx.time.strftime("%B %d, %Y"),
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
        'Name', 'Active', 'Members count', 'Courses count', 'Enrollments count', 'Last Course Taught',
        'Last Course Date', 'Last Affiliate User Login (name, date)', 'Last Affiliate Learner Login'
    ]]

    for affiliate in affiliates:
        rows.append([
            affiliate.name, ('Yes' if affiliate.active else 'No'),
            affiliate.members.count(), affiliate.courses.count(), affiliate.enrollments.count(),
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

    def list_to_csv(values):
        """Convert list to string of CSV's."""
        return '{}'.format(', '.join(values))

    params = {'csv_name': 'user_report', 'course_id': 'affiliates',
              'timestamp': datetime.now()}

    rows = [['Username', 'Email', 'Registration Date', 'Country', 'First Name', 'Last Name',
             'Mailing Address', 'City', 'State', 'Postal Code', 'Phone Number', 'Company', 'Title',
             'Would you like to receive marketing communication from the Ewing Marion Kauffman Foundation and Kauffman FastTrac?',
             'Your motivation', 'Age', 'Gender', 'Race/Ethnicity',
             'Have you ever served in any branch of the U.S. Armed Forces, including the Coast Guard, the National Guard, or Reserve component of any service branch?',
             'What was the highest degree or level of school you have completed?', 'Affiliate Organization', 'Affiliate Role', 'Course ID']]

    profiles = UserProfile.objects.all()

    for profile in profiles:
        user = profile.user

        course_id_list = [
            str(course_id) for course_id in user.courseenrollment_set.all().values_list('course_id', flat=True)
        ]
        course_ids = list_to_csv(course_id_list)

        affiliate_org_list = []
        affiliate_role_list = []
        for affiliate_membership in user.affiliatemembership_set.all():
            affiliate_org_list.append(affiliate_membership.affiliate.name)
            affiliate_role_list.append(AffiliateMembership.ROLES[affiliate_membership.role])

        affiliate_orgs = list_to_csv(affiliate_org_list)
        affiliate_roles = list_to_csv(affiliate_role_list)

        rows.append([
            user.username, user.email, user.date_joined,
            profile.get_country_display(), user.first_name, user.last_name,
            profile.mailing_address, profile.city, profile.get_state_display(), profile.zipcode,
            profile.phone_number, profile.company, profile.title, profile.get_newsletter_display(),
            profile.get_bio_display(), profile.get_age_category_display(), profile.get_gender_display(),
            profile.get_ethnicity_display(), profile.get_veteran_status_display(), profile.get_education_display(),
            affiliate_orgs, affiliate_roles, course_ids
        ])

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

    # here goes FT master course
    non_student_user_ids = CourseAccessRole.objects.filter(
        course_id=fasttrac_course.id).values_list('user_id', flat=True)
    student_enrollments = CourseEnrollment.objects.filter(
        course_id=fasttrac_course.id, is_active=True).exclude(user_id__in=non_student_user_ids)
    students = [enrollment.user for enrollment in student_enrollments]

    student_time_tracker = StudentTimeTracker.objects.filter(
        course_id=fasttrac_course.id)
    student_modules = StudentModule.objects.filter(course_id=fasttrac_course.id)



    # for each student create empty CSV row
    student_data = {}

    for student in students:
        student_id = unicode(student.id)
        student_data[student_id] = ['/'] * fasttrac_course_units_length

    for section in fasttrac_course.get_children():
        for subsection in section.get_children():
            for unit in subsection.get_children():
                location = unit.location

                for student in students:
                        student_id = unicode(student.id)

                        try:
                            column_name = "{} - {} - {}".format(
                                section.display_name, subsection.display_name, unit.display_name)
                            unit_index = header_columns.index(
                                column_name) - header_index_padding
                        except IndexError:
                            continue

                        unit_data = '-'

                        # if we are generating a time spent on unit report
                        if time_report:
                            # get time tracker object
                            tracker = student_time_tracker.filter(
                                unit_location=location, student=student).first()

                            if tracker:
                                unit_data = tracker.time_duration / 1000

                        # if we are generating a course completion report
                        else:
                            for xblock in unit.get_children():
                                module = student_modules.filter(
                                    module_state_key=xblock.location, student=student).first()
                                if module and ('done' in module.state or 'helpful' in module.state):
                                    module_state = json.loads(module.state)

                                    if module_state.get('done'):
                                        unit_data = 'done'
                                    elif module_state.get('helpful') != None:
                                        if module_state.get('helpful') == 'true':
                                            unit_data = 'helpful'
                                        else:
                                            unit_data = 'not helpful'

                        student_data[student_id][unit_index] = unit_data

    for student_id in student_data:
        if student_data.get(student_id):
            student = filter(lambda s: unicode(
                s.id) == student_id, students)[0]

            student_data[student_id].insert(0, fasttrac_course.display_name)
            student_data[student_id].insert(0, fasttrac_course.id)
            student_data[student_id].insert(0, student.email)
            student_data[student_id].insert(0, student.username)

            rows.append(student_data[student_id])
    # end master course

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
                                        if module_state.get('helpful') == 'true':
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


FASTTRAC_COURSE_KEY = CourseKey.from_string(settings.FASTTRAC_COURSE_KEY)
INTERACTIVES_TYPES = {
    'survey': 'Reality Check (survey)',
    'ftinputxblock': 'Reality Check (text)',
    'lti_consumer': 'Workspace Tool',
}


def course_interactives_csv_data():
    """
    Information about the interactives in the FastTrac course for the CSV.
    Returns:
    * a list of columns (strings) indicating the location of each interactive in format:
        <chapter_name> - <section_name> - <subsection_name> - <interactive_type>
    * list of unit IDs and types
    """
    structure = CourseStructure.objects.get(course_id=FASTTRAC_COURSE_KEY).ordered_blocks
    units = []
    columns = []

    for chapter in structure.items()[0][1]['children']:
        for section in structure[chapter]['children']:
            for subsection in structure[section]['children']:
                for unit in structure[subsection]['children']:
                    value = structure[unit]
                    unit_type = value['block_type']
                    if unit_type in INTERACTIVES_TYPES:
                        units.append({
                            'id': unit,
                            'type': unit_type
                        })
                        columns.append(
                            '{} - {} - {} - {}'.format(
                                structure[chapter]['display_name'],
                                structure[section]['display_name'],
                                structure[subsection]['display_name'],
                                INTERACTIVES_TYPES.get(unit_type, unit_type),
                            )
                        )
    return columns, units


def create_ccx_usage_key(course_id, unit_id):
    """Create a CCXBlockUsageLocator instance from a course block usage location."""
    unit_usage_key = UsageKey.from_string(unit_id)
    return CCXBlockUsageLocator(course_id, unit_usage_key.block_type, unit_usage_key.block_id)


def is_lti_done(completion_list, unit_id):
    """Determine if the workspace form contains data (is done)."""
    usage_key = UsageKey.from_string(unit_id)
    item = modulestore().get_item(usage_key)
    name = item.launch_url.split('/')[-1]  # last part of the LTI URL is the name of the form
    for el in completion_list:
        if name in el:
            return el[name]
    return False


def get_lti_completion():
    """
    Retrieve the full workspace forms / LTI completion list from the workspace app.
    Returns a dictionary of format:
        user_email:
            lti_name: completed_bool
    """
    response = requests.get(
        settings.WORKSPACE_URL + '/api/completion',
        headers={'Authorization': settings.WORKSPACE_API_KEY}
    )
    data = defaultdict(list)
    for item in response.json():
        data[item['email']].append({item['name']: item['completed']})
    return data


@CELERY_APP.task
def export_csv_interactives_completion_report():
    """
    Export a CSV containing information about the completion of interactives (reality checks and workspace forms)
    for each student in all CCX courses.
    """
    header_row = ['Username', 'Email', 'Course ID', 'Course Name']
    interactive_columns, units = course_interactives_csv_data()
    header_row.extend(interactive_columns)

    # CCX staff/coach/instructor etc.
    non_student_user_ids = CourseAccessRole.objects.filter(
        course_id=FASTTRAC_COURSE_KEY
    ).values_list('user_id', flat=True)

    lti_completion = get_lti_completion()

    student_rows = []
    fasttrac_ccxs = CustomCourseForEdX.objects.filter(course_id=FASTTRAC_COURSE_KEY)
    ccxs_ids = [ccx.ccx_course_id for ccx in fasttrac_ccxs]

    enrollments = CourseEnrollment.objects.filter(
        course_id__in=ccxs_ids,
        is_active=True
    ).exclude(
        user_id__in=non_student_user_ids
    ).order_by('course_id', 'user')

    for enrollment in enrollments:
        student = enrollment.user
        course = enrollment.course
        row = [
            student.username,
            student.email,
            course.id,
            course.display_name
        ]
        student_lti_completion = lti_completion[student.email]

        modules = StudentModule.objects.filter(course_id=course.id, student_id=student.id)
        for unit in units:
            if unit['type'] == 'lti_consumer':
                row.append('Done' if is_lti_done(student_lti_completion, unit['id']) else '')
            else:
                usage_key = create_ccx_usage_key(course.id, unit['id'])
                module = modules.filter(module_state_key=usage_key)
                row.append('Done' if module else '')
        student_rows.append(row)

    rows = [header_row]
    rows.extend(student_rows)

    params = {
        'csv_name': 'interactives_completion_report',
        'course_id': 'affiliates',
        'timestamp': datetime.now(),
        'rows': rows
    }

    upload_csv_to_report_store(**params)
