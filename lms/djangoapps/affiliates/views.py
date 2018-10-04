import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.contrib.auth.models import User
from django.core import serializers
from django.http import HttpResponseNotFound
from django.shortcuts import redirect
from django.db.models import Q
from django.views.generic import View
from django_countries import countries
from edxmako.shortcuts import render_to_response, render_to_string

from lms.djangoapps.ccx.models import CustomCourseForEdX
from lms.djangoapps.instructor.views.tools import get_student_from_identifier
from lms.envs.common import STATE_CHOICES
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment

from .decorators import only_program_director, only_staff
from .models import AffiliateEntity, AffiliateMembership, AffiliateInvite

LOG = logging.getLogger(__name__)


class IsStaffMixin(object):
    def has_permissions(self):
        return self.request.user.is_staff

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permissions():
            LOG.info('Unauthorized attempt to access site admin by %s', self.request.user.username)
            return redirect('root')
        return super(IsStaffMixin, self).dispatch(request, *args, **kwargs)


class SiteAdminView(IsStaffMixin, View):
    template_name = 'affiliates/admin.html'

    def user_statistics(self):
        """
        Returns a dictionary of the user statistics (count of):
            * users: unique users registered for the site
            * learners: unique learners
            * admins: FastTrac admins
            * affiliate_users: affiliate staff + affiliate enrolled users
            * affiliate_learners: unique learners in affiliate courses
            * affiliate_staff: PD's, Facilitators, Course Managers
            * fasttrac_learners: learners enrolled in the FT course but NOT in a CCX course
        """
        fasttrac_course_id = CourseKey.from_string(settings.FASTTRAC_COURSE_KEY)
        facilitator_course_id = CourseKey.from_string('course-v1:FastTrac+101+101')
        users = User.objects.filter(~Q(username=settings.ECOMMERCE_SERVICE_WORKER_USERNAME)).count()

        admins = User.objects.filter(
            Q(is_staff=True) | Q(is_superuser=True),
        ).count()
        learners = users - admins

        affiliate_course_enrollment_user_ids = set(CourseEnrollment.objects.filter(
            ~Q(course_id=fasttrac_course_id),
            ~Q(course_id=facilitator_course_id)
        ).values_list('user_id', flat=True))

        affiliate_staff_ids = set(AffiliateMembership.objects.all().values_list('member_id', flat=True))
        affiliate_staff = len(affiliate_staff_ids)
        affiliate_learners = len(affiliate_course_enrollment_user_ids - affiliate_staff_ids)
        affiliate_users = affiliate_staff + affiliate_learners

        fasttrac_learners = CourseEnrollment.objects.filter(
            ~Q(user_id__in=affiliate_course_enrollment_user_ids), course_id=fasttrac_course_id
        ).values_list('user_id', flat=True).distinct().count()

        return {
            'users': users,
            'learners': learners,
            'admins': admins,
            'affiliate_users': affiliate_users,
            'affiliate_learners': affiliate_learners,
            'affiliate_staff': affiliate_staff,
            'fasttrac_learners': fasttrac_learners
        }

    def get(self, request, *args, **kwargs):    # pylint: disable=unused-argument
        affiliates = AffiliateEntity.objects.all().order_by('name')
        ccxs = CustomCourseForEdX.objects.all()
        fasttrac_course_key = settings.FASTTRAC_COURSE_KEY

        context = {
            'affiliates': affiliates,
            'ccxs': ccxs,
            'partial_course_key': fasttrac_course_key.split(':')[1],
            'statistics': self.user_statistics()
        }
        return render_to_response(self.template_name, context)


class ImpersonateView(IsStaffMixin, View):
    template_name = 'affiliates/impersonate.html'

    def get(self, request):
        context = {
            'workspace_logout_url': '{}/users/logout?no_redirect=1'.format(settings.WORKSPACE_URL),
            'impersonated_email': request.GET.get('impersonated_email')
        }
        return render_to_response(self.template_name, context)


def index(request):
    affiliate_id = request.GET.get('affiliate_id', '')
    affiliate_city = request.GET.get('affiliate_city', '')
    affiliate_state = request.GET.get('affiliate_state', '')
    location_latitude = request.GET.get('latitude', '')
    location_longitude = request.GET.get('longitude', '')
    search_radius = request.GET.get('affiliate_search_radius', '')
    user_messages = []

    if not affiliate_id:
        filters = {'active': True}
        if location_latitude and location_longitude and search_radius:
            from courseware.views.views import get_coordinate_boundaries
            latitude_boundaries, longitude_boundaries = get_coordinate_boundaries(
                float(location_latitude), float(location_longitude), float(search_radius))

            filters['location_latitude__range'] = latitude_boundaries
            filters['location_longitude__range'] = longitude_boundaries
        else:
            if affiliate_city:
                filters['city__icontains'] = affiliate_city
            if affiliate_state:
                filters['state'] = affiliate_state

        affiliates = AffiliateEntity.objects.filter(**filters).order_by('name')
        if location_latitude and location_longitude:
            affiliates = affiliates.exclude(Q(location_longitude=None) | Q(location_latitude=None))
            affiliates = sorted(
                affiliates, key=lambda affiliate: affiliate.distance_from(
                    {'latitude': location_latitude, 'longitude': location_longitude}
                )
            )

            if affiliates:
                user_messages.append('Affiliates are sorted by the distance!')
    else:
        affiliates = AffiliateEntity.objects.filter(pk=affiliate_id, active=True)

    all_affiliates = AffiliateEntity.objects.filter(active=True).order_by('name')
    affiliates_as_json = serializers.serialize('json', all_affiliates, fields=('name', 'id'))

    return render_to_response('affiliates/index.html', {
        'affiliates': affiliates,
        'affiliates_as_json': affiliates_as_json,
        'affiliate_city': affiliate_city,
        'affiliate_state': affiliate_state,
        'state_choices': STATE_CHOICES,
        'user_messages': user_messages
    })


def show(request, slug):
    try:
        affiliate = AffiliateEntity.objects.get(slug=slug)
    except AffiliateEntity.DoesNotExist:
        return HttpResponseNotFound(render_to_string('static_templates/404.html', {}, request=request))
    return render_to_response('affiliates/show.html', {
        'affiliate': affiliate,
        'subaffiliates': affiliate.children.all(),
        'is_program_director': is_program_director(request.user, affiliate)
    })


@only_program_director
def new(request):    # pylint: disable=unused-argument
    all_affiliates = AffiliateEntity.objects.all()

    return render_to_response('affiliates/form.html', {
        'affiliate': AffiliateEntity(),
        'affiliates': all_affiliates,
        'available_subs': all_affiliates,
        'state_choices': STATE_CHOICES,
        'countries': countries,
        'role_choices': AffiliateMembership.role_choices
    })


@only_program_director
def create(request):
    affiliate = AffiliateEntity()
    post_data = request.POST.copy().dict()

    program_director_identifier = post_data.pop('member_identifier', None)

    # delete image from POST since we pull it from FILES
    post_data.pop('image', None)

    if request.FILES and request.FILES['image']:
        setattr(affiliate, 'image', request.FILES['image'])

    for key in post_data:
        if key == 'year_of_birth':
            setattr(affiliate, key, int(post_data[key]))
        elif key == 'parent':
            if not int(post_data[key]):
                continue
            parent = AffiliateEntity.objects.get(id=post_data[key])
            setattr(affiliate, key, parent)
        else:
            setattr(affiliate, key, post_data[key])

    affiliate.save()
    if request.user.is_staff and post_data.get('affiliate-type') == 'parent':
        subs = dict(request.POST)['sub-affiliates']
        AffiliateEntity.objects.filter(id__in=subs).update(parent=affiliate)

    # SurveyGizmo functionality to automatically add Program Director upon creation
    if program_director_identifier:
        member = get_student_from_identifier(program_director_identifier)
        AffiliateMembership.objects.create(affiliate=affiliate, member=member, role='staff')

    return redirect('affiliates:show', slug=affiliate.slug)


@only_staff
def edit(request, slug):
    affiliates = AffiliateEntity.objects.all()
    affiliate = affiliates.get(slug=slug)

    if request.method == 'POST':
        # delete image from POST since we pull it from FILES
        request.POST.pop('image', None)

        if request.FILES and request.FILES['image']:
            setattr(affiliate, 'image', request.FILES['image'])

        # If a parent affiliate is changed to be a standalone or a sub-affiliate
        # we remove all of that parent's children references.
        if request.user.is_staff:
            affiliate_type = request.POST['affiliate-type']
            if affiliate.is_parent and affiliate_type in ['standalone', 'sub-affiliate']:
                affiliate.children.all().update(parent=None)

            if affiliate_type in ['parent', 'standalone']:
                affiliate.parent = None

            if affiliate_type == 'parent':
                subs = dict(request.POST)['sub-affiliates'] if 'sub-affiliates' in request.POST else []
                affiliate.children.exclude(id__in=subs).update(parent=None)
                affiliates.filter(id__in=subs).update(parent=affiliate)

        for key in request.POST:
            if key == 'year_of_birth':
                setattr(affiliate, key, int(request.POST[key]))
            elif request.user.is_staff and key == 'parent':
                if affiliate_type == 'sub-affiliate' and int(request.POST[key]):
                    parent = AffiliateEntity.objects.get(id=request.POST[key])
                else:
                    parent = None
                setattr(affiliate, key, parent)
            else:
                setattr(affiliate, key, request.POST[key])

        affiliate.save()

        return redirect('affiliates:show', slug=affiliate.slug)

    role_choices = AffiliateMembership.role_choices

    if not request.user.is_staff:
        role_choices = (
            ('ccx_coach', 'Facilitator'),
            ('instructor', 'Course Manager'),
        )

    return render_to_response('affiliates/form.html', {
        'affiliate': affiliate,
        'affiliates': affiliates,
        'available_subs': affiliates.exclude(
            id__in=affiliate.children.all().values_list('id', flat=True)
        ),
        'state_choices': STATE_CHOICES,
        'countries': countries,
        'role_choices': role_choices,
        'is_program_director': is_program_director(request.user, affiliate)
    })


@only_program_director
def delete(request, slug):    # pylint: disable=unused-argument
    AffiliateEntity.objects.get(slug=slug).delete()

    return redirect('affiliates:index')


def payment(request):    # pylint: disable=unused-argument
    return render_to_response('affiliates/payment.html', {
        'preview': settings.PAYMENT_PREVIEW
    })


@only_staff
def add_member(request, slug):
    member_identifier = request.POST.get('member_identifier')
    role = request.POST.get('role')
    affiliate = AffiliateEntity.objects.get(slug=slug)

    if role == 'staff' and not request.user.is_staff:
        messages.add_message(request, messages.INFO, 'You are not allowed to do that.')
        return redirect('affiliates:edit', slug=slug)

    try:
        member = get_student_from_identifier(member_identifier)
    except ObjectDoesNotExist:
        # create a user invite if the user does not exist
        invite_new_user(affiliate, member_identifier, role, request.user)

        messages.add_message(
            request,
            messages.INFO,
            'User "{}" does not exist. They will be invited.'.format(member_identifier)
        )
        return redirect('affiliates:edit', slug=slug)

    params = {
        'affiliate': affiliate,
        'member': member,
        'role': role,
    }

    AffiliateMembership.objects.create(**params)
    return redirect('affiliates:edit', slug=slug)


@only_staff
def remove_member(request, slug, member_id):
    role = request.GET.get('role')

    if role == 'staff' and not request.user.is_staff:
        messages.add_message(request, messages.INFO, 'You are not allowed to do that.')
        return redirect('affiliates:edit', slug=slug)

    params = {
        'affiliate': AffiliateEntity.objects.get(slug=slug),
        'member_id': member_id,
        'role': role
    }

    try:
        AffiliateMembership.objects.filter(**params).delete()
    except ValueError as e:
        messages.add_message(request, messages.INFO, e)

    return redirect('affiliates:edit', slug=slug)


@only_staff
def remove_invite(request, slug, invite_id):
    try:
        AffiliateInvite.objects.get(id=invite_id).delete()
    except ValueError as e:
        messages.add_message(request, messages.INFO, e)

    return redirect('affiliates:edit', slug=slug)


@only_staff
def toggle_active_status(request, slug):    # pylint: disable=unused-argument
    affiliate = AffiliateEntity.objects.select_for_update().get(slug=slug)
    affiliate.active = not affiliate.active
    affiliate.save()

    return redirect('affiliates:edit', slug=slug)


def is_program_director(user, affiliate):
    if user.is_anonymous():
        return False
    else:
        return user.is_staff or AffiliateMembership.objects.filter(
            member=user, affiliate=affiliate, role='staff'
        ).exists()


def invite_new_user(affiliate, user_email, role, current_user):
    AffiliateInvite.objects.create(affiliate=affiliate, email=user_email, role=role, invited_by=current_user)
