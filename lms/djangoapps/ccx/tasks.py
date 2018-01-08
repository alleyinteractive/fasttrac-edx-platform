"""
Asynchronous tasks for the CCX app.
"""

from datetime import datetime, timedelta, date, time
from django.dispatch import receiver
import logging
from opaque_keys import InvalidKeyError
from opaque_keys.edx.locator import CourseLocator
from ccx_keys.locator import CCXLocator
from xmodule.modulestore.django import SignalHandler
from lms import CELERY_APP
from courseware.models import StudentModule
import requests
from django.conf import settings
from lms.djangoapps.ccx.models import CustomCourseForEdX
from django.contrib.auth.models import User
from student.models import CourseEnrollment, CourseAccessRole
from opaque_keys.edx.keys import CourseKey


log = logging.getLogger("edx.ccx")


@receiver(SignalHandler.course_published)
def course_published_handler(sender, course_key, **kwargs):  # pylint: disable=unused-argument
    """
    Consume signals that indicate course published. If course already a CCX, do nothing.
    """
    if not isinstance(course_key, CCXLocator):
        send_ccx_course_published.delay(unicode(course_key))


@CELERY_APP.task
def send_ccx_course_published(course_key):
    """
    Find all CCX derived from this course, and send course published event for them.
    """
    course_key = CourseLocator.from_string(course_key)
    for ccx in CustomCourseForEdX.objects.filter(course_id=course_key):
        try:
            ccx_key = CCXLocator.from_course_locator(course_key, ccx.id)
        except InvalidKeyError:
            log.info('Attempt to publish course with deprecated id. Course: %s. CCX: %s', course_key, ccx.id)
            continue
        responses = SignalHandler.course_published.send(
            sender=ccx,
            course_key=ccx_key
        )
        for rec, response in responses:
            log.info('Signal fired when course is published. Receiver: %s. Response: %s', rec, response)


@CELERY_APP.task(name='ccx.print')
def send_emails():
    log.info('Sending Mandrill/Mailchimp post-course emails...')

    mandrill_url = 'https://mandrillapp.com/api/1.0/messages/send-template.json'
    mandrill_api_key = settings.MANDRILL_API_KEY

    if mandrill_api_key is None:
        return

    today = date.today()

    # One day after the "course completion date" for all learners enrolled in that course (not affiliates)
    yesterday = today - timedelta(days=1)

    ccx_min_date = datetime.combine(yesterday, time.min)
    ccx_max_date = datetime.combine(yesterday, time.max)

    ccxs = CustomCourseForEdX.objects.filter(end_date__range=(ccx_min_date, ccx_max_date))
    students = [student.user for ccx in ccxs for student in ccx.students]

    student_emails = [{'email': student.email, 'name': student.profile.name, 'type': 'to'} for student in students]

    # 45 days after a user's last activity in a course in which they are still enrolled
    n_days = 45
    n_days_ago = today - timedelta(days=n_days)

    users_min_date = datetime.combine(n_days_ago, time.min)
    users_max_date = datetime.combine(n_days_ago, time.max)

    users = User.objects.filter(last_login__range=(users_min_date, users_max_date))

    for user in users:
        course_key = CourseKey.from_string(settings.FASTTRAC_COURSE_KEY)
        is_enrolled_in_ccx = CourseEnrollment.objects.filter(user=user).exclude(course_id=course_key).exists()
        is_affiliate_staff = CourseAccessRole.objects.filter(user=user).exists()

        if not is_enrolled_in_ccx and not is_affiliate_staff:
            # send post-course email if student is not enrolled in a ccx
            student_emails.append({
                'email': user.email,
                'name': user.profile.name,
                'type': 'to'
            })

    data = {
        "key": mandrill_api_key,
        "template_name": "fasttrac-post-course-survey",
        "template_content": {},
        "message": {
            "to": student_emails,
            "from_email": "info@fasttrac.org",
            "from_name": "Fasttrac",
            "signing_domain": "fasttrac.org"
        }
    }

    request = requests.post(mandrill_url, json=data)
    if not request.status_code == 200:
        print('Mandrill API send error')
        print(request.content)
    else:
        print('Mandrill API send success')
