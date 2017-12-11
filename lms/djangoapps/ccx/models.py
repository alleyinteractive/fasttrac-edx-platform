"""
Models for the custom course feature
"""
import json
import logging
import decimal
from datetime import datetime

from django.contrib.auth.models import User
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from pytz import utc
import requests

from lazy import lazy
from openedx.core.lib.time_zone_utils import get_time_zone_abbr
from xmodule_django.models import CourseKeyField, LocationKeyField
from xmodule.error_module import ErrorDescriptor
from xmodule.modulestore.django import modulestore
from student.models import CourseAccessRole, CourseEnrollment
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from ccx_keys.locator import CCXLocator
from instructor.access import allow_access
from lms.djangoapps.courseware.gis_helpers import coordinates_distance



log = logging.getLogger("edx.ccx")


class CustomCourseForEdX(models.Model):
    """
    A Custom Course.
    """
    IN_PERSON = 'IN_PERSON'
    ONLINE_ONLY = 'ONLINE_ONLY'
    BLENDED = 'BLENDED'
    DELIVERY_MODE_CHOICES = (
        (IN_PERSON, 'In-Person'),
        (ONLINE_ONLY, 'Online'),
        (BLENDED, 'Blended'),
    )

    PRIVATE = 'PRIVATE'
    PUBLIC = 'PUBLIC'
    ENROLLMENT_TYPE_CHOICES = (
        (PRIVATE, 'Private'),
        (PUBLIC, 'Public')
    )


    course_id = CourseKeyField(max_length=255, db_index=True)
    display_name = models.CharField(max_length=255)
    coach = models.ForeignKey(User, db_index=True)
    # if not empty, this field contains a json serialized list of
    # the master course modules
    structure_json = models.TextField(verbose_name='Structure JSON', blank=True, null=True)
    delivery_mode = models.CharField(
        default=IN_PERSON,
        max_length=255,
        choices=DELIVERY_MODE_CHOICES,
    )
    location_city = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    location_state = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    location_postal_code = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    enrollment_type = models.CharField(
        default=PUBLIC,
        max_length=255,
        choices=ENROLLMENT_TYPE_CHOICES
    )
    time = models.DateTimeField(default=datetime.now)
    fee = models.BooleanField(default=False)
    course_description = models.TextField(default='Course description...')
    location_latitude = models.FloatField(null=True, blank=True)
    location_longitude = models.FloatField(null=True, blank=True)

    enrollment_end_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    _full_address = None

    class Meta(object):
        app_label = 'ccx'

    def __init__(self, *args, **kwargs):
        super(CustomCourseForEdX, self).__init__(*args, **kwargs)
        self._full_address = self.build_full_address()


    def save(self, *args, **kwargs):
        new_full_address = self.build_full_address()

        if self._full_address != new_full_address:
            latitude, longitude = self.get_location_coordinates()
            setattr(self, 'location_latitude', latitude)
            setattr(self, 'location_longitude', longitude)

        # All ccxs not originating from Fasttrac master course should be private
        partial_course_key = settings.FASTTRAC_COURSE_KEY.split(':')[1]
        if not partial_course_key in unicode(self.course_id):
            self.enrollment_type = self.PRIVATE

        super(CustomCourseForEdX, self).save(*args, **kwargs)
        self._full_address = new_full_address

    def delete(self):
        with transaction.atomic():
            CourseAccessRole.objects.filter(course_id=self.ccx_course_id).delete()
            CourseOverview.objects.filter(id=self.ccx_course_id).delete()
            CourseEnrollment.objects.filter(course_id=self.ccx_course_id).delete()

            super(CustomCourseForEdX, self).delete()

    @property
    def affiliate(self):
        return self.coach.profile.affiliate

    @property
    def students(self):
        non_student_user_ids = CourseAccessRole.objects.filter(course_id=self.ccx_course_id).values_list('user_id', flat=True)
        return CourseEnrollment.objects.filter(course_id=self.ccx_course_id, is_active=True).exclude(user_id__in=non_student_user_ids)

    @property
    def facilitator_names(self):
        facilitator_roles = CourseAccessRole.objects.filter(course_id=self.ccx_course_id, role='ccx_coach')
        return ', '.join([f.user.profile.name for f in facilitator_roles])

    @property
    def ccx_course_id(self):
        return CCXLocator.from_course_locator(self.course_id, self.id)

    @property
    def image_url(self):
        if self.coach.profile.affiliate.image:
            return self.coach.profile.affiliate.image.url
        else:
            return 'https://s3-us-west-2.amazonaws.com/fasttrac-edx-prod/default_full.png'

    @lazy
    def course(self):
        """Return the CourseDescriptor of the course related to this CCX"""
        store = modulestore()
        with store.bulk_operations(self.course_id):
            course = store.get_course(self.course_id)
            if not course or isinstance(course, ErrorDescriptor):
                log.error("CCX {0} from {2} course {1}".format(  # pylint: disable=logging-format-interpolation
                    self.display_name, self.course_id, "broken" if course else "non-existent"
                ))
            return course

    @lazy
    def start(self):
        """Get the value of the override of the 'start' datetime for this CCX
        """
        # avoid circular import problems
        from .overrides import get_override_for_ccx
        return get_override_for_ccx(self, self.course, 'start')

    @lazy
    def due(self):
        """Get the value of the override of the 'due' datetime for this CCX
        """
        # avoid circular import problems
        from .overrides import get_override_for_ccx
        return get_override_for_ccx(self, self.course, 'due')

    @lazy
    def max_student_enrollments_allowed(self):
        """
        Get the value of the override of the 'max_student_enrollments_allowed'
        datetime for this CCX
        """
        # avoid circular import problems
        from .overrides import get_override_for_ccx
        return get_override_for_ccx(self, self.course, 'max_student_enrollments_allowed')

    def has_started(self):
        """Return True if the CCX start date is in the past"""
        return datetime.now(utc) > self.start

    def has_ended(self):
        """Return True if the CCX due date is set and is in the past"""
        return self.end_date and self.end_date < datetime.now(utc)

    def enrollment_closed(self):
        """Return True if the CCX due date is set and is in the past"""
        return self.enrollment_end_date and self.enrollment_end_date < datetime.now(utc)

    def start_datetime_text(self, format_string="SHORT_DATE", time_zone=utc):
        """Returns the desired text representation of the CCX start datetime

        The returned value is in specified time zone, defaulted to UTC.
        """
        i18n = self.course.runtime.service(self.course, "i18n")
        strftime = i18n.strftime
        value = strftime(self.start.astimezone(time_zone), format_string)
        if format_string == 'DATE_TIME':
            value += ' ' + get_time_zone_abbr(time_zone, self.start)
        return value

    def end_datetime_text(self, format_string="SHORT_DATE", time_zone=utc):
        """Returns the desired text representation of the CCX due datetime

        If the due date for the CCX is not set, the value returned is the empty
        string.

        The returned value is in specified time zone, defaulted to UTC.
        """
        if self.due is None:
            return ''

        i18n = self.course.runtime.service(self.course, "i18n")
        strftime = i18n.strftime
        value = strftime(self.due.astimezone(time_zone), format_string)
        if format_string == 'DATE_TIME':
            value += ' ' + get_time_zone_abbr(time_zone, self.due)
        return value

    @property
    def structure(self):
        """
        Deserializes a course structure JSON object
        """
        if self.structure_json:
            return json.loads(self.structure_json)
        return None

    def is_instructor(self, user):
        if unicode(self.course_id).startswith('ccx'):
            ccx_locator = self.course_id
        else:
            ccx_locator = CCXLocator.from_course_locator(self.course_id, unicode(self.id))

        return CourseAccessRole.objects.filter(course_id=ccx_locator, user=user, role='instructor').exists()

    def is_staff(self, user):
        if unicode(self.course_id).startswith('ccx'):
            ccx_locator = self.course_id
        else:
            ccx_locator = CCXLocator.from_course_locator(self.course_id, unicode(self.id))

        return CourseAccessRole.objects.filter(course_id=ccx_locator, user=user, role='staff').exists()

    def build_full_address(self):
        return '{}, {}, {}'.format(self.location_city, self.location_postal_code, self.location_state)

    def get_location_coordinates(self):
        geocoding_api_key = settings.GEOCODING_API_KEY
        params = self.build_full_address()

        url = 'https://maps.googleapis.com/maps/api/geocode/json?address=' + params + ',&key=' + geocoding_api_key
        json_response = requests.get(url).json()

        if len(json_response['results']) == 0:
            return None, None

        location = json_response['results'][0]['geometry']['location']

        return location['lat'], location['lng']

    def distance_from(self, coordinate):
        return coordinates_distance({'latitude': self.location_latitude, 'longitude': self.location_longitude}, coordinate)


class CcxFieldOverride(models.Model):
    """
    Field overrides for custom courses.
    """
    ccx = models.ForeignKey(CustomCourseForEdX, db_index=True, on_delete=models.CASCADE)
    location = LocationKeyField(max_length=255, db_index=True)
    field = models.CharField(max_length=255)

    class Meta(object):
        app_label = 'ccx'
        unique_together = (('ccx', 'location', 'field'),)

    value = models.TextField(default='null')

class CourseUpdates(models.Model):
    date = models.DateField(blank=False, null=False)
    content = models.TextField(blank=False, null=False)
    author = models.ForeignKey(User)
    ccx = models.ForeignKey(CustomCourseForEdX, on_delete=models.CASCADE)

    def __getitem__(self, item):
        return getattr(self, item)


@receiver(post_save, sender=CustomCourseForEdX, dispatch_uid="add_affiliate_course_enrollments")
def add_affiliate_course_enrollments(sender, instance, created, **kwargs):
    'Allow all affiliate staff and instructors access to this course.'
    # do this only for new CCX courses
    if not created:
        return

    from courseware.courses import get_course_by_id

    course = get_course_by_id(instance.ccx_course_id)
    for membership in instance.affiliate.memberships.exclude(role='ccx_coach'):
        allow_access(course, membership.member, membership.role, False)
