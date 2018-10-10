# pylint: disable=unused-argument,C0411,C0412
"""
Views related to the Custom Courses feature.
"""
import csv
import datetime
import functools
import json
import logging
import pytz
import ast
from copy import deepcopy
from cStringIO import StringIO

from django.db.models import Q
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseForbidden,
)
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.models import User

from student.models import CourseAccessRole, CourseEnrollmentAllowed
from courseware.access import has_access, has_ccx_coach_role
from courseware.courses import get_course_by_id

from courseware.field_overrides import disable_overrides
from courseware.grades import iterate_grades_for
from edxmako.shortcuts import render_to_response
from opaque_keys.edx.keys import CourseKey
from ccx_keys.locator import CCXLocator
from student.models import CourseEnrollment

from instructor.access import allow_access, revoke_access
from instructor.views.api import _split_input_list
from instructor.views.gradebook_api import get_grade_book_page
from instructor.enrollment import (
    enroll_email,
    get_email_params,
)
from instructor_task.models import ReportStore

from lms.envs.common import STATE_CHOICES
from lms.djangoapps.ccx.models import CustomCourseForEdX, CourseUpdates
from lms.djangoapps.ccx.overrides import (
    get_override_for_ccx,
    override_field_for_ccx,
    clear_ccx_field_info_from_ccx_map,
    bulk_delete_ccx_override_fields,
)
from lms.djangoapps.ccx.utils import (
    ccx_course,
    ccx_students_enrolling_center,
    get_ccx_creation_dict,
    get_date,
    parse_date,
    prep_course_for_grading,
    is_ccx_coach_on_master_course
)

from affiliates.models import AffiliateEntity, AffiliateMembership


log = logging.getLogger(__name__)
TODAY = datetime.datetime.today  # for patching in tests


def coach_dashboard(view):
    """
    View decorator which enforces that the user have the CCX coach role on the
    given course and goes ahead and translates the course_id from the Django
    route into a course object.
    """
    @functools.wraps(view)
    def wrapper(request, course_id, **kwargs):
        """
        Wraps the view function, performing access check, loading the course,
        and modifying the view's call signature.
        """
        course_key = CourseKey.from_string(course_id)
        ccx = None

        if isinstance(course_key, CCXLocator):
            ccx_id = course_key.ccx
            try:
                ccx = CustomCourseForEdX.objects.get(pk=ccx_id)
            except CustomCourseForEdX.DoesNotExist:
                raise Http404

        if ccx:
            # get permissions for ccx course
            course = get_course_by_id(course_key, depth=None)
            is_staff = has_access(request.user, 'staff', course)
            is_instructor = has_access(request.user, 'instructor', course)

            # and then set course key to CCX master course
            course_key = ccx.course_id

        course = get_course_by_id(course_key, depth=None)

        if not course.enable_ccx:
            raise Http404
        elif ccx and (is_staff or is_instructor):
            return view(request, course, ccx, **kwargs)
        else:
            if ccx is not None:
                if not has_ccx_coach_role(request.user, ccx.ccx_course_id):
                    return HttpResponseForbidden(
                        _('You must be the coach for this ccx to access this view')
                    )
        return view(request, course, ccx, **kwargs)
    return wrapper


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@coach_dashboard
def edit_course_view(request, course, ccx, **kwargs):
    context = {
        'course': course,
        'ccx': ccx,
        'delivery_mode_choices': CustomCourseForEdX.DELIVERY_MODE_CHOICES,
        'enrollment_choices': CustomCourseForEdX.ENROLLMENT_TYPE_CHOICES,
    }

    context.update(get_ccx_creation_dict(course))
    context.update(edit_ccx_context(course, ccx, request.user))
    context['edit_current'] = True
    return render_to_response('ccx/coach_dashboard.html', context)


def edit_ccx_context(course, ccx, user, **kwargs):
    ccx_locator = CCXLocator.from_course_locator(course.id, unicode(ccx.pk))

    schedule = get_ccx_schedule(course, ccx)
    grading_policy = get_override_for_ccx(
        ccx, course, 'grading_policy', course.grading_policy)

    context = {}
    context['ccx_locator'] = ccx_locator
    context['modify_access_url'] = reverse('modify_access', kwargs={'course_id': ccx_locator})
    context['schedule'] = json.dumps(schedule, indent=4)
    context['save_url'] = reverse(
        'save_ccx', kwargs={'course_id': ccx_locator})

    non_student_user_ids = CourseAccessRole.objects.filter(course_id=ccx_locator).values_list('user_id', flat=True)
    ccx_student_enrollments = CourseEnrollment.objects.filter(
        course_id=ccx_locator, is_active=True
    ).exclude(user_id__in=non_student_user_ids)

    context['ccx_student_enrollments'] = ccx_student_enrollments
    context['gradebook_url'] = reverse('ccx_gradebook', kwargs={'course_id': ccx_locator})
    context['grades_csv_url'] = reverse('ccx_grades_csv', kwargs={'course_id': ccx_locator})
    context['grading_policy'] = json.dumps(grading_policy, indent=4)
    context['grading_policy_url'] = reverse('ccx_set_grading_policy', kwargs={'course_id': ccx_locator})
    context['STATE_CHOICES'] = STATE_CHOICES

    all_facilitators = get_facilitators(ccx.affiliate)
    added_facilitator_user_ids = CourseAccessRole.objects.filter(
        course_id=ccx_locator, role=AffiliateMembership.CCX_COACH
    ).values_list('user_id', flat=True)
    context['added_facilitators'] = all_facilitators.filter(id__in=added_facilitator_user_ids)
    context['not_added_facilitators'] = all_facilitators.exclude(id__in=added_facilitator_user_ids)

    with ccx_course(ccx_locator) as course:
        context['course'] = course

    context['edit_ccx_url'] = reverse('edit_ccx', kwargs={'course_id': ccx_locator})
    context['edit_ccx_dasboard_url'] = reverse('ccx_edit_course_view', kwargs={'course_id': ccx_locator})

    return context


def get_facilitators(affiliate):
    """Retrieve all affiliate staff for the passed-in affiliate entity."""
    member_ids = AffiliateMembership.objects.filter(
        affiliate=affiliate, role=AffiliateMembership.CCX_COACH
    ).values_list('member_id', flat=True).distinct()

    return User.objects.filter(id__in=member_ids)


def get_serialized_affiliate_facilitators(affiliates):
    """
    Returns a list of dictionaries consisting of the affiliate object
    and a list of its facilitators. Affiliates without facilitators are
    skipped.
    """
    affiliate_facilitators = []
    for aff in affiliates:
        facilitators = get_facilitators(aff)
        if facilitators:
            affiliate_facilitators.append({
                'affiliate': aff,
                'facilitators': facilitators
            })
    return affiliate_facilitators


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@coach_dashboard
def dashboard(request, course, ccx=None, **kwargs):
    """
    Display the CCX Coach Dashboard
    """
    partial_course_key = settings.FASTTRAC_COURSE_KEY.split(':')[1]
    affiliate_ids = AffiliateMembership.objects.filter(
        Q(role=AffiliateMembership.STAFF) | Q(role=AffiliateMembership.INSTRUCTOR),
        member=request.user
    ).values_list('affiliate_id', flat=True)
    affiliate_facilitators = get_serialized_affiliate_facilitators(
        AffiliateEntity.objects.filter(id__in=affiliate_ids)
    )

    context = {
        'course': course,
        'ccx': ccx,
        'STATE_CHOICES': STATE_CHOICES,
        'delivery_mode_choices': CustomCourseForEdX.DELIVERY_MODE_CHOICES,
        'enrollment_choices': CustomCourseForEdX.ENROLLMENT_TYPE_CHOICES,
        'is_instructor': False,
        'is_ccx_coach': False,
        'is_staff': False,
        'is_from_fasttrac_course': partial_course_key in unicode(course.id),
        'affiliate_facilitators': affiliate_facilitators
    }

    context.update(get_ccx_creation_dict(course))

    if ccx:
        context.update(edit_ccx_context(course, ccx, request.user))
        ccx_locator = ccx.ccx_course_id

        context['affiliate_entity'] = ccx.affiliate
        context['is_ccx_coach'] = ccx.coach == request.user
        context['is_instructor'] = ccx.is_instructor(request.user)
        context['is_staff'] = ccx.is_staff(request.user)

        context['ccx_coach_permissions'] = CourseAccessRole.objects.filter(course_id=ccx_locator, role='ccx_coach')

        context['edit_current'] = False

        non_student_user_ids = CourseAccessRole.objects.filter(
            course_id=ccx_locator
        ).values_list('user_id', flat=True)
        ccx_student_enrollments = CourseEnrollment.objects.filter(
            course_id=ccx_locator
        ).exclude(user_id__in=non_student_user_ids)

        # show students on Student Admin tab
        context['ccx_student_enrollments'] = ccx_student_enrollments

        # show enrolled not existing students on Enrollments tab
        context['ccx_student_invitations'] = CourseEnrollmentAllowed.objects.filter(course_id=ccx_locator)

        # facilitator dropdown choices
        facilitator_ids = [ccx_coach_permissions.user.id for ccx_coach_permissions in context['ccx_coach_permissions']]
        context['facilitator_dropdown_choices'] = ccx.affiliate.members.exclude(id__in=facilitator_ids)
    else:
        context['create_ccx_url'] = reverse(
            'create_ccx', kwargs={'course_id': course.id})

    return render_to_response('ccx/coach_dashboard.html', context)


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@coach_dashboard
def edit_ccx(request, course, ccx=None, **kwargs):
    if not ccx:
        raise Http404

    name = request.POST.get('name')
    delivery_mode = request.POST.get('delivery_mode')
    location_city = request.POST.get('city')
    location_state = request.POST.get('state')
    location_postal_code = request.POST.get('postal_code')
    time = '{} {}Z'.format(request.POST.get('date'), request.POST.get('time'))
    enrollment_end_date = '{} {}Z'.format(
        request.POST.get('enrollment_end_date'),
        request.POST.get('enrollment_end_time')
    )
    end_date = '{} {}Z'.format(request.POST.get('end_date'), request.POST.get('end_time'))
    fee = request.POST.get('fee')
    course_description = request.POST.get('course_description')
    enrollment_type = request.POST.get('enrollment_type')
    facilitators = dict(request.POST).get('facilitators')

    ccx.display_name = name
    ccx.delivery_mode = delivery_mode
    ccx.location_city = location_city
    ccx.location_state = location_state
    ccx.location_postal_code = location_postal_code
    ccx.enrollment_type = enrollment_type
    ccx.time = time
    ccx.enrollment_end_date = enrollment_end_date
    ccx.end_date = end_date
    ccx.fee = ast.literal_eval(fee)
    ccx.course_description = course_description
    ccx.save()

    current_facilitator_ids = CourseAccessRole.objects.filter(
        course_id=ccx.ccx_course_id, role=AffiliateMembership.CCX_COACH
    ).values_list('user_id', flat=True)
    removed_facilitator_ids = set(current_facilitator_ids).difference(set(facilitators))
    added_facilitator_ids = set(facilitators).difference(set(current_facilitator_ids))

    ccx_id = CCXLocator.from_course_locator(course.id, ccx.pk)
    course_obj = get_course_by_id(ccx.ccx_course_id, depth=None)

    for facilitator_id in removed_facilitator_ids:
        user = User.objects.get(id=facilitator_id)
        revoke_access(course_obj, user, AffiliateMembership.CCX_COACH, False)

    email_params = get_email_params(course, auto_enroll=True, course_key=ccx_id, display_name=ccx.display_name)

    for facilitator_id in added_facilitator_ids:
        user = User.objects.get(id=facilitator_id)
        enroll_email(
            course_id=ccx_id,
            student_email=user.email,
            auto_enroll=True,
            email_students=True,
            email_params=email_params
        )
        allow_access(course_obj, user, AffiliateMembership.CCX_COACH, False)

    url = reverse('ccx_coach_dashboard', kwargs={'course_id': ccx_id})
    return redirect(url)


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@coach_dashboard
def create_ccx(request, course, ccx=None, **kwargs):
    """
    Create a new CCX
    """
    if not is_ccx_coach_on_master_course(request.user, course) or not request.user.profile.affiliate:
        return HttpResponseForbidden()

    affiliate_id = request.POST.get('affiliate')
    name = request.POST.get('name')
    delivery_mode = request.POST.get('delivery_mode')
    location_city = request.POST.get('city')
    location_state = request.POST.get('state')
    location_postal_code = request.POST.get('postal_code')
    time = '{} {}Z'.format(request.POST.get('date'), request.POST.get('time'))
    enrollment_end_date = '{} {}Z'.format(
        request.POST.get('enrollment_end_date'),
        request.POST.get('enrollment_end_time')
    )
    end_date = '{} {}Z'.format(request.POST.get('end_date'), request.POST.get('end_time'))
    fee = request.POST.get('fee')
    course_description = request.POST.get('course_description')
    enrollment_type = request.POST.get('enrollment_type')
    facilitators = dict(request.POST).get('facilitators')

    context = get_ccx_creation_dict(course)
    if not affiliate_id:
        messages.error(request, 'Affiliate not selected.')
        return render_to_response('ccx/coach_dashboard.html', context)

    if not facilitators:
        messages.error(request, 'No facilitators added.')
        return render_to_response('ccx/coach_dashboard.html', context)

    if hasattr(course, 'ccx_connector') and course.ccx_connector:
        # if ccx connector url is set in course settings then inform user that he can
        # only create ccx by using ccx connector url.
        messages.error(request, context['use_ccx_con_error_message'])
        return render_to_response('ccx/coach_dashboard.html', context)

    # prevent CCX objects from being created for deprecated course ids.
    if course.id.deprecated:
        messages.error(request, _(
            "You cannot create a CCX from a course using a deprecated id. "
            "Please create a rerun of this course in the studio to allow "
            "this action."))
        url = reverse('ccx_coach_dashboard', kwargs={'course_id': course.id})
        return redirect(url)

    affiliate = AffiliateEntity.objects.get(id=affiliate_id)

    ccx = CustomCourseForEdX(
        affiliate=affiliate,
        course_id=course.id,
        coach=request.user,
        display_name=name,
        delivery_mode=delivery_mode,
        location_city=location_city,
        location_state=location_state,
        location_postal_code=location_postal_code,
        time=time,
        enrollment_end_date=enrollment_end_date,
        end_date=end_date,
        fee=ast.literal_eval(fee),
        enrollment_type=enrollment_type,
        course_description=course_description)
    ccx.save()

    # we need this for authorization
    ccx.save()

    # Make sure start/due are overridden for entire course
    start = TODAY().replace(tzinfo=pytz.UTC)
    override_field_for_ccx(ccx, course, 'start', start)
    override_field_for_ccx(ccx, course, 'due', None)

    # Enforce a static limit for the maximum amount of students that can be enrolled
    override_field_for_ccx(ccx, course, 'max_student_enrollments_allowed', settings.CCX_MAX_STUDENTS_ALLOWED)

    # Hide anything that can show up in the schedule
    hidden = 'visible_to_staff_only'
    for chapter in course.get_children():
        override_field_for_ccx(ccx, chapter, hidden, True)
        for sequential in chapter.get_children():
            override_field_for_ccx(ccx, sequential, hidden, True)
            for vertical in sequential.get_children():
                override_field_for_ccx(ccx, vertical, hidden, True)

    ccx_id = CCXLocator.from_course_locator(course.id, ccx.pk)

    url = reverse('ccx_coach_dashboard', kwargs={'course_id': ccx_id})

    # Enroll the coach in the course
    email_params = get_email_params(course, auto_enroll=True, course_key=ccx_id, display_name=ccx.display_name)
    enroll_email(
        course_id=ccx_id,
        student_email=request.user.email,
        auto_enroll=True,
        email_students=True,
        email_params=email_params,
    )

    course_obj = get_course_by_id(ccx.ccx_course_id, depth=None)
    facilitator_ids = [int(i) for i in facilitators]

    for user_id in facilitator_ids:
        user = User.objects.get(id=user_id)
        enroll_email(
            course_id=ccx_id,
            student_email=user.email,
            auto_enroll=True,
            email_students=True,
            email_params=email_params
        )
        allow_access(course_obj, user, AffiliateMembership.CCX_COACH, False)

    return redirect(url)


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@coach_dashboard
def save_ccx(request, course, ccx=None, **kwargs):
    """
    Save changes to CCX.
    """
    if not ccx:
        raise Http404

    def override_fields(parent, data, graded, earliest=None, ccx_ids_to_delete=None):
        """
        Recursively apply CCX schedule data to CCX by overriding the
        `visible_to_staff_only`, `start` and `due` fields for units in the
        course.
        """
        if ccx_ids_to_delete is None:
            ccx_ids_to_delete = []
        blocks = {
            str(child.location): child
            for child in parent.get_children()}

        for unit in data:
            block = blocks[unit['location']]
            override_field_for_ccx(
                ccx, block, 'visible_to_staff_only', unit['hidden'])

            start = parse_date(unit['start'])
            if start:
                if not earliest or start < earliest:
                    earliest = start
                override_field_for_ccx(ccx, block, 'start', start)
            else:
                ccx_ids_to_delete.append(get_override_for_ccx(ccx, block, 'start_id'))
                clear_ccx_field_info_from_ccx_map(ccx, block, 'start')

            # Only subsection (aka sequential) and unit (aka vertical) have due dates.
            if 'due' in unit:  # checking that the key (due) exist in dict (unit).
                due = parse_date(unit['due'])
                if due:
                    override_field_for_ccx(ccx, block, 'due', due)
                else:
                    ccx_ids_to_delete.append(get_override_for_ccx(ccx, block, 'due_id'))
                    clear_ccx_field_info_from_ccx_map(ccx, block, 'due')
            else:
                # In case of section aka chapter we do not have due date.
                ccx_ids_to_delete.append(get_override_for_ccx(ccx, block, 'due_id'))
                clear_ccx_field_info_from_ccx_map(ccx, block, 'due')

            if not unit['hidden'] and block.graded:
                graded[block.format] = graded.get(block.format, 0) + 1

            children = unit.get('children', None)
            # For a vertical, override start and due dates of all its problems.
            if unit.get('category', None) == u'vertical':
                for component in block.get_children():
                    # override start and due date of problem (Copy dates of vertical into problems)
                    if start:
                        override_field_for_ccx(ccx, component, 'start', start)

                    if due:
                        override_field_for_ccx(ccx, component, 'due', due)

            if children:
                override_fields(block, children, graded, earliest, ccx_ids_to_delete)
        return earliest, ccx_ids_to_delete

    graded = {}
    earliest, ccx_ids_to_delete = override_fields(course, json.loads(request.body), graded, [])
    bulk_delete_ccx_override_fields(ccx, ccx_ids_to_delete)
    if earliest:
        override_field_for_ccx(ccx, course, 'start', earliest)

    # Attempt to automatically adjust grading policy
    changed = False
    policy = get_override_for_ccx(
        ccx, course, 'grading_policy', course.grading_policy
    )
    policy = deepcopy(policy)
    grader = policy['GRADER']
    for section in grader:
        count = graded.get(section.get('type'), 0)
        if count < section.get('min_count', 0):
            changed = True
            section['min_count'] = count
    if changed:
        override_field_for_ccx(ccx, course, 'grading_policy', policy)

    return HttpResponse(
        json.dumps({
            'schedule': get_ccx_schedule(course, ccx),
            'grading_policy': json.dumps(policy, indent=4)}),
        content_type='application/json',
    )


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@coach_dashboard
def set_grading_policy(request, course, ccx=None, **kwargs):
    """
    Set grading policy for the CCX.
    """
    if not ccx:
        raise Http404

    override_field_for_ccx(
        ccx, course, 'grading_policy', json.loads(request.POST['policy']))

    url = reverse(
        'ccx_coach_dashboard',
        kwargs={'course_id': CCXLocator.from_course_locator(course.id, ccx.pk)}
    )
    return redirect(url)


def get_ccx_schedule(course, ccx, return_xblocks=False):
    """
    Generate a JSON serializable CCX schedule.
    """
    def visit(node, depth=1):
        """
        Recursive generator function which yields CCX schedule nodes.
        We convert dates to string to get them ready for use by the js date
        widgets, which use text inputs.
        Visits students visible nodes only; nodes children of hidden ones
        are skipped as well.

        Dates:
        Only start date is applicable to a section. If ccx coach did not override start date then
        getting it from the master course.
        Both start and due dates are applicable to a subsection (aka sequential). If ccx coach did not override
        these dates then getting these dates from corresponding subsection in master course.
        Unit inherits start date and due date from its subsection. If ccx coach did not override these dates
        then getting them from corresponding subsection in master course.
        """
        for child in node.get_children():
            # in case the children are visible to staff only, skip them
            if child.visible_to_staff_only:
                continue

            hidden = get_override_for_ccx(
                ccx, child, 'visible_to_staff_only',
                child.visible_to_staff_only)

            start = get_date(ccx, child, 'start')
            if depth > 1:
                # Subsection has both start and due dates and unit inherit dates from their subsections
                if depth == 2:
                    due = get_date(ccx, child, 'due')
                elif depth == 3:
                    # Get start and due date of subsection in case unit has not override dates.
                    due = get_date(ccx, child, 'due', node)
                    start = get_date(ccx, child, 'start', node)

                visited = {
                    'location': str(child.location),
                    'display_name': child.display_name,
                    'category': child.category,
                    'start': start,
                    'due': due,
                    'hidden': hidden,
                }
            else:
                visited = {
                    'location': str(child.location),
                    'display_name': child.display_name,
                    'category': child.category,
                    'start': start,
                    'hidden': hidden,
                }
            if depth < 3:
                children = tuple(visit(child, depth + 1))
                if children:
                    visited['children'] = children
                    yield visited
            elif return_xblocks and depth == 3:
                visited['children'] = child.children
                yield visited
            else:
                yield visited

    with disable_overrides():
        return tuple(visit(course))


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@coach_dashboard
def ccx_schedule(request, course, ccx=None, **kwargs):  # pylint: disable=unused-argument
    """
    get json representation of ccx schedule
    """
    if not ccx:
        raise Http404

    schedule = get_ccx_schedule(course, ccx)
    json_schedule = json.dumps(schedule, indent=4)
    return HttpResponse(json_schedule, content_type='application/json')


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@coach_dashboard
def ccx_invite(request, course, ccx=None, **kwargs):
    """
    Invite users to new ccx
    """
    if not ccx:
        raise Http404

    action = request.POST.get('enrollment-button')
    identifiers_raw = request.POST.get('student-ids')
    identifiers = _split_input_list(identifiers_raw)
    email_students = 'email-students' in request.POST
    course_key = CCXLocator.from_course_locator(course.id, ccx.pk)
    email_params = get_email_params(course, auto_enroll=True, course_key=course_key, display_name=ccx.display_name)

    ccx_students_enrolling_center(action, identifiers, email_students, course_key, email_params, ccx.coach)

    url = reverse('ccx_coach_dashboard', kwargs={'course_id': course_key})
    return redirect(url)


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@coach_dashboard
def ccx_student_management(request, course, ccx=None, **kwargs):
    """
    Manage the enrollment of individual students in a CCX
    """
    if not ccx:
        raise Http404

    action = request.POST.get('student-action', None)
    student_id = request.POST.get('student-id', '')
    email_students = 'email-students' in request.POST
    identifiers = [student_id]
    course_key = CCXLocator.from_course_locator(course.id, ccx.pk)
    email_params = get_email_params(course, auto_enroll=True, course_key=course_key, display_name=ccx.display_name)

    errors = ccx_students_enrolling_center(action, identifiers, email_students, course_key, email_params, ccx.coach)

    for error_message in errors:
        messages.error(request, error_message)

    url = reverse('ccx_coach_dashboard', kwargs={'course_id': course_key})
    return redirect(url)


# Grades can potentially be written - if so, let grading manage the transaction.
@transaction.non_atomic_requests
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@coach_dashboard
def ccx_gradebook(request, course, ccx=None, **kwargs):
    """
    Show the gradebook for this CCX.
    """
    if not ccx:
        raise Http404

    ccx_key = CCXLocator.from_course_locator(course.id, unicode(ccx.pk))
    with ccx_course(ccx_key) as course:
        prep_course_for_grading(course, request)
        student_info, page = get_grade_book_page(request, course, course_key=ccx_key)

        return render_to_response('courseware/gradebook.html', {
            'page': page,
            'page_url': reverse('ccx_gradebook', kwargs={'course_id': ccx_key}),
            'students': student_info,
            'course': course,
            'course_id': course.id,
            'staff_access': request.user.is_staff,
            'ordered_grades': sorted(
                course.grade_cutoffs.items(), key=lambda i: i[1], reverse=True),
        })


# Grades can potentially be written - if so, let grading manage the transaction.
@transaction.non_atomic_requests
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@coach_dashboard
def ccx_grades_csv(request, course, ccx=None, **kwargs):
    """
    Download grades as CSV.
    """
    if not ccx:
        raise Http404

    ccx_key = CCXLocator.from_course_locator(course.id, ccx.pk)
    with ccx_course(ccx_key) as course:
        prep_course_for_grading(course, request)

        enrolled_students = User.objects.filter(
            courseenrollment__course_id=ccx_key,
            courseenrollment__is_active=1
        ).order_by('username').select_related("profile")
        grades = iterate_grades_for(course, enrolled_students)

        header = None
        rows = []
        for student, gradeset, __ in grades:
            if gradeset:
                # We were able to successfully grade this student for this
                # course.
                if not header:
                    # Encode the header row in utf-8 encoding in case there are
                    # unicode characters
                    header = [section['label'].encode('utf-8')
                              for section in gradeset[u'section_breakdown']]
                    rows.append(["id", "email", "username", "grade"] + header)

                percents = {
                    section['label']: section.get('percent', 0.0)
                    for section in gradeset[u'section_breakdown']
                    if 'label' in section
                }

                row_percents = [percents.get(label, 0.0) for label in header]
                rows.append([student.id, student.email, student.username,
                             gradeset['percent']] + row_percents)

        buf = StringIO()
        writer = csv.writer(buf)
        for row in rows:
            writer.writerow(row)

        response = HttpResponse(buf.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment'

        return response


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@coach_dashboard
def delete_ccx(request, course, ccx=None):
    if ccx:
        ccx.delete()

    return redirect('/dashboard')


@transaction.non_atomic_requests
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@coach_dashboard
def ccx_messages(request, course, ccx=None, **kwargs):
    if not ccx:
        raise Http404

    msgs = CourseUpdates.objects.filter(ccx=ccx)
    ccx_id = unicode(CCXLocator.from_course_locator(course.id, unicode(ccx.id)))

    context = {
        'create_message_url': reverse('ccx_messages_create', kwargs={'course_id': ccx_id}),
        'delete_message_url': 'ccx_messages/delete/',
        'messages': msgs,
        'course': get_course_by_id(ccx.ccx_course_id, depth=2)
    }

    return render_to_response('ccx/ccx_messages_dashboard.html', context)


@transaction.non_atomic_requests
@coach_dashboard
def ccx_messages_create(request, course, ccx=None, **kwargs):
    if not ccx:
        raise Http404

    post_data = request.POST.copy().dict()

    ccx_message = CourseUpdates(
        date=post_data['date'],
        content=post_data['content'],
        author=request.user,
        ccx=ccx
    )
    ccx_message.save()

    ccx_id = unicode(CCXLocator.from_course_locator(course.id, unicode(ccx.id)))

    return redirect(reverse('ccx_messages', kwargs={'course_id': ccx_id}))


@transaction.non_atomic_requests
@coach_dashboard
def ccx_messages_delete(request, course, ccx=None, **kwargs):
    message_id = kwargs.get('message_id')

    if not ccx or not message_id:
        raise Http404

    CourseUpdates.objects.get(pk=message_id).delete()

    ccx_id = unicode(CCXLocator.from_course_locator(course.id, unicode(ccx.id)))

    return redirect(reverse('ccx_messages', kwargs={'course_id': ccx_id}))


@coach_dashboard
def export_report(request, course, ccx, **kwargs):
    # Importing here to avoid circular dependecies
    # TODO: Fix the circular deps.
    from affiliates.tasks import export_ccx_interactives_completion_report

    report = request.POST['report_type']

    if report == 'export_interactives_completion_report':
        export_ccx_interactives_completion_report.delay(ccx_id=ccx.id)
        return HttpResponse(
            json.dumps({'status': 'export_started'}),
            content_type='application/json',
        )


@coach_dashboard
def report_list(request, course, ccx, **kwargs):
    report_store = ReportStore.from_config('GRADES_DOWNLOAD')
    reports = report_store.links_for(str(ccx.ccx_course_id))
    data = []
    for report in reports:
        data.append({
            'filename': report[0],
            'url': report[1],
        })
    return HttpResponse(json.dumps(data), content_type='application/json')
