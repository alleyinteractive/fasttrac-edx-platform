import datetime
import hashlib
import logging

import requests
from ccx_keys.locator import CCXLocator
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models, IntegrityError, transaction
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.template.defaultfilters import slugify
from django.utils.crypto import get_random_string
from django_countries.fields import CountryField

from courseware.courses import get_course_by_id
from instructor.access import allow_access, revoke_access
from lms.djangoapps.ccx.models import CustomCourseForEdX
from lms.djangoapps.courseware.gis_helpers import coordinates_distance
from lms.djangoapps.instructor.enrollment import enroll_email
from lms.envs.common import STATE_CHOICES
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.models import CourseEnrollment

LOG = logging.getLogger(__name__)


def user_directory_path(instance, filename):
    return 'user_{0}/{1}'.format(instance.id, filename)


class AffiliateEntity(models.Model):
    slug = models.SlugField(max_length=255, unique=True, default='')
    parent = models.ForeignKey('self', related_name='children', blank=True, null=True, on_delete=models.SET_NULL)

    email = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True, default='')
    phone_number = models.CharField(null=True, blank=True, max_length=255, default='')
    phone_number_private = models.CharField(null=True, blank=True, max_length=255, default='')
    address = models.CharField(null=True, blank=True, max_length=255, default='')
    address_2 = models.CharField(null=True, blank=True, max_length=255, default='')
    city = models.CharField(null=True, blank=True, max_length=255, default='')
    zipcode = models.CharField(null=True, blank=True, max_length=255, default='')
    website = models.CharField(null=True, blank=True, max_length=255, default='')
    facebook = models.CharField(null=True, blank=True, max_length=255, default='')
    twitter = models.CharField(null=True, blank=True, max_length=255, default='')
    linkedin = models.CharField(null=True, blank=True, max_length=255, default='')
    state = models.CharField(null=True, blank=True, default='na', choices=STATE_CHOICES, max_length=255)
    country = CountryField(blank=True, null=True)

    location_latitude = models.FloatField(null=True, blank=True)
    location_longitude = models.FloatField(null=True, blank=True)
    image = models.ImageField(upload_to=user_directory_path, null=True, blank=True)
    active = models.BooleanField(blank=True, default=True)

    members = models.ManyToManyField(User, through='AffiliateMembership')

    _full_address = None

    class Meta:  # pylint: disable=no-init,old-style-class
        unique_together = ('email', 'name')

    def __init__(self, *args, **kwargs):
        super(AffiliateEntity, self).__init__(*args, **kwargs)
        self._full_address = self.build_full_address()

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        slug = slugify(self.name)

        slug_exists = AffiliateEntity.objects.filter(slug=slug).exclude(pk=self.pk).exists()

        if slug_exists:
            self.slug = '-'.join([slug, get_random_string(4)])
        else:
            self.slug = slug

        new_full_address = self.build_full_address()

        if self._full_address != new_full_address:
            latitude, longitude = self.get_location_coordinates()
            self.location_latitude = latitude
            self.location_longitude = longitude

        super(AffiliateEntity, self).save(*args, **kwargs)
        self._full_address = new_full_address

    def delete(self):
        with transaction.atomic():
            self.courses.delete()
            super(AffiliateEntity, self).delete()

    def build_full_address(self):
        return '{}, {}, {}'.format(self.address, self.zipcode, self.city)

    def get_location_coordinates(self):
        geocoding_api_key = settings.GEOCODING_API_KEY
        params = self.build_full_address()
        if self.state != 'NA':
            params = params + ',' + self.state

        url = 'https://maps.googleapis.com/maps/api/geocode/json?address=' + params + ',&key=' + geocoding_api_key
        json_response = requests.get(url).json()

        if not json_response['results']:
            return None, None

        location = json_response['results'][0]['geometry']['location']
        return location['lat'], location['lng']

    def distance_from(self, coordinate):
        return coordinates_distance({
            'latitude': self.location_latitude,
            'longitude': self.location_longitude
        }, coordinate)

    @property
    def is_parent(self):
        return self.parent is None and self.children.exists()

    @property
    def is_child(self):
        return self.parent is not None

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return 'https://s3-us-west-2.amazonaws.com/fasttrac-edx-prod/default_full.png'

    @property
    def website_url(self):
        if self.website.startswith('http'):
            return self.website
        return 'http://{}'.format(self.website)

    @property
    def memberships(self):
        return AffiliateMembership.objects.filter(affiliate=self)

    @property
    def invites(self):
        return AffiliateInvite.objects.filter(affiliate=self)

    @property
    def active_invites(self):
        return AffiliateInvite.objects.filter(affiliate=self, active=True)

    @property
    def courses(self):
        return self.ccx.all()

    @property
    def enrollments(self):
        course_ids = [c.ccx_course_id for c in self.courses]
        return CourseEnrollment.objects.filter(course_id__in=course_ids)

    @property
    def last_course_taught(self):
        today = datetime.datetime.today()
        return self.courses.filter(end_date__gte=today).order_by('end_date').first()

    @property
    def last_affiliate_user(self):
        return self.members.order_by('-last_login').first()

    @property
    def last_affiliate_learner(self):
        member_ids = self.members.values_list('id', flat=True)
        learner_enrollments = self.enrollments.exclude(user_id__in=member_ids)
        learner_ids = [e.user_id for e in learner_enrollments]
        return User.objects.filter(id__in=learner_ids).order_by('-last_login').first()

    @property
    def program_director(self):
        pd_membership = self.affiliatemembership_set.filter(role=AffiliateMembership.STAFF)
        return pd_membership.first().member if pd_membership else None


class AffiliateMembership(models.Model):
    CCX_COACH = 'ccx_coach'
    INSTRUCTOR = 'instructor'
    STAFF = 'staff'

    ROLES = {
        CCX_COACH: 'Facilitator',
        INSTRUCTOR: 'Course Manager',
        STAFF: 'Program Director',
    }

    STAFF_ROLES = [
        STAFF,
        INSTRUCTOR
    ]

    role_choices = (
        (CCX_COACH, 'Facilitator'),
        (INSTRUCTOR, 'Course Manager'),
        (STAFF, 'Program Director'),
    )

    non_pd_role_choices = (
        (CCX_COACH, 'Facilitator'),
        (INSTRUCTOR, 'Course Manager'),
    )

    mailchimp_interests = {
        CCX_COACH: '1b920c7fe2',
        INSTRUCTOR: '738d5d6873',
        STAFF: 'c6f38d6306'
    }

    class Meta:
        unique_together = ('member', 'affiliate', 'role')

    member = models.ForeignKey(User)
    affiliate = models.ForeignKey(AffiliateEntity, on_delete=models.CASCADE)
    role = models.CharField(choices=role_choices, max_length=255)


class AffiliateInvite(models.Model):
    email = models.CharField(max_length=255)
    role = models.CharField(choices=AffiliateMembership.role_choices, max_length=255)
    affiliate = models.ForeignKey(AffiliateEntity, on_delete=models.CASCADE)

    invited_by = models.ForeignKey(User)
    invited_at = models.DateTimeField(auto_now=True)

    active = models.BooleanField(default=True)


def update_mailchimp_interest(affiliate_membership, value):
    mailchimp_api_key = settings.MAILCHIMP_API_KEY
    mailing_list_id = settings.MAILCHIMP_LIST_ID

    # skip if mailchimp not configured
    if mailchimp_api_key and mailing_list_id:
        email_hash = hashlib.md5(affiliate_membership.member.email.lower()).hexdigest()
        mailchimp_url = 'https://us15.api.mailchimp.com/3.0/lists/{}/members/{}'.format(mailing_list_id, email_hash)

        interest_id = affiliate_membership.mailchimp_interests[affiliate_membership.role]
        affiliate = affiliate_membership.member.profile.affiliate
        is_affiliate_user = affiliate_membership.member.profile.is_affiliate_user

        data = {
            'email_address': affiliate_membership.member.email,
            'status': 'subscribed',
            'merge_fields': {
                'AFFILIATE': (affiliate and affiliate.name) or '',
            },
            'interests': {
                interest_id: value,
                settings.ENTREPRENEUR_MAILCHIMP_INTEREST_ID: not is_affiliate_user,  # Entrepreneur User
                settings.AFFILIATE_MAILCHIMP_INTEREST_ID: is_affiliate_user  # Affiliate User
            }
        }

        # TODO: notify admin if this fails (send email)
        r = requests.put(mailchimp_url, auth=('fasttrac', mailchimp_api_key), json=data)
        if not r.status_code == 200:
            LOG.error('Affiliate membership update error: %s', r.content)


@receiver(post_save, sender=AffiliateInvite, dispatch_uid="send_invite_email")
def send_invite_email(sender, instance, created, **kwargs):  # pylint: disable=unused-argument
    if created:
        from django.core.mail import send_mail
        from django.template import loader

        context = {
            'site_name': settings.SITE_NAME,
            'role': instance.get_role_display(),
            'affiliate_name': instance.affiliate.name
        }

        from_address = settings.DEFAULT_FROM_EMAIL
        subject = 'FastTrac Affiliate Invite'
        message = loader.render_to_string('emails/affiliate_invitation.txt', context)

        send_mail(subject, message, from_address, [instance.email], fail_silently=False)


@receiver(post_save, sender=AffiliateMembership, dispatch_uid="add_mailchimp_interests")
def add_mailchimp_interests(sender, instance, **kwargs):  # pylint: disable=unused-argument
    update_mailchimp_interest(instance, True)


@receiver(post_delete, sender=AffiliateMembership, dispatch_uid="remove_mailchimp_interests")
def remove_mailchimp_interests(sender, instance, **kwargs):  # pylint: disable=unused-argument
    update_mailchimp_interest(instance, False)


@receiver(post_save, sender=AffiliateMembership, dispatch_uid="add_affiliate_course_enrollments")
def add_affiliate_course_enrollments(sender, instance, **kwargs):  # pylint: disable=unused-argument
    """
    Allow staff or instructor access to affiliate member into
    all affiliate courses if they are staff or instructor member.
    """
    if not instance.role == AffiliateMembership.CCX_COACH:
        for ccx in instance.affiliate.courses:
            ccx_locator = CCXLocator.from_course_locator(ccx.course_id, ccx.id)
            course = get_course_by_id(ccx_locator)

            try:
                with transaction.atomic():
                    allow_access(course, instance.member, instance.role, False)
            except IntegrityError:
                LOG.error('IntegrityError: Allow access failed.')

    # Program Director and Course Manager needs to be CCX coach on FastTrac course
    course_overviews = CourseOverview.objects.exclude(id__startswith='ccx-')

    if instance.role in AffiliateMembership.STAFF_ROLES:
        for course_overview in course_overviews:
            course_id = course_overview.id
            course = get_course_by_id(course_id)

            try:
                with transaction.atomic():
                    allow_access(course, instance.member, AffiliateMembership.CCX_COACH, False)
            except IntegrityError:
                LOG.error('IntegrityError: CCX coach failed.')

    elif instance.role == AffiliateMembership.CCX_COACH:
        for course_overview in course_overviews:
            course_id = course_overview.id

            enroll_email(course_id, instance.member.email, auto_enroll=True)


@receiver(post_save, sender=AffiliateMembership, dispatch_uid="deactivate_invite")
def deactivate_invite(sender, instance, created, **kwargs):  # pylint: disable=unused-argument
    """An invite needs to be deactivated once a user creates an account."""
    if created:
        try:
            invite = AffiliateInvite.objects.get(
                email=instance.member.email,
                affiliate=instance.affiliate,
                active=True
            )
            invite.active = False
            invite.save()
        except AffiliateInvite.DoesNotExist:
            pass


@receiver(post_delete, sender=AffiliateMembership, dispatch_uid="remove_affiliate_course_enrollments")
def remove_affiliate_course_enrollments(sender, instance, **kwargs):  # pylint: disable=unused-argument
    'Remove all privileges over all affiliate courses.'
    for ccx in instance.affiliate.courses:
        ccx_locator = CCXLocator.from_course_locator(ccx.course_id, ccx.id)
        course = get_course_by_id(ccx_locator)

        revoke_access(course, instance.member, instance.role, False)

    # Remove CCX coach on FastTrac course
    if instance.role in AffiliateMembership.STAFF_ROLES:
        course_overviews = CourseOverview.objects.exclude(id__startswith='ccx-')
        for course_overview in course_overviews:
            course_id = course_overview.id
            course = get_course_by_id(course_id)

            revoke_access(course, instance.member, AffiliateMembership.CCX_COACH, False)


@receiver(pre_delete, sender=AffiliateMembership, dispatch_uid="validate_course_dependency")
def validate_course_dependency(sender, instance, **kwargs):  # pylint: disable=unused-argument
    """
    An affiliate needs to have at least one Program Director, so we don't allow removing the
    only PD in an affiliate. Also if the removed member is a coach in any CCX we change the coach
    to be the first program director.
    """
    other_pd_membership = AffiliateMembership.objects.filter(
        affiliate=instance.affiliate, role=AffiliateMembership.STAFF
    ).exclude(id=instance.id).first()

    if instance.role == AffiliateMembership.STAFF and not other_pd_membership:
        raise ValueError('Affiliate needs to have at least one program director.')

    ccxs = CustomCourseForEdX.objects.filter(coach=instance.member, affiliate=instance.affiliate)
    for ccx in ccxs:
        ccx.coach = other_pd_membership.member
        ccx.save()
