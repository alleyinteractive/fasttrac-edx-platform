import logging

from django.conf import settings
from django.contrib.auth import login, load_backend
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from rest_framework.permissions import BasePermission, IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response

from instructor_task.models import ReportStore

from affiliates.api.mixins import AffiliateViewMixin
from affiliates.models import AffiliateEntity, AffiliateMembership, AffiliateInvite
from affiliates.api.serializers import (
    AffiliateEntitySerializer,
    AffiliateMembershipSerializer,
    AffiliateInviteSerializer
)
from affiliates.tasks import (
    export_csv_user_report,
    export_csv_affiliate_course_report,
    export_csv_affiliate_report,
    export_csv_course_report,
    export_csv_interactives_completion_report
)


LOG = logging.getLogger(__name__)


class IsStaffOrProgramDirector(BasePermission):
    def has_permission(self, request, view):
        """Returns True for global staff and program director of an affiliate."""
        if request.user.is_anonymous():
            return False

        if request.user.is_staff:
            return True

        # If an individual affiliate page (eg. editing an affiliate) is opened,
        # only the PD of that affiliate can access it, along with the global staff user
        affiliate_slug = view.kwargs.get('affiliate_slug')
        if affiliate_slug:
            return AffiliateMembership.objects.filter(
                member=request.user, role=AffiliateMembership.STAFF, affiliate__slug=affiliate_slug
            ).exists()

        return AffiliateMembership.objects.filter(
            member=request.user, role=AffiliateMembership.STAFF
        ).exists()


class IsGlobalStaffOrAffiliateStaff(BasePermission):
    def has_permission(self, request, view):
        """Returns True for global staff and affiliate staff (PD or CM)."""
        if request.user.is_anonymous():
            return False

        if request.user.is_staff:
            return True

        # If an individual affiliate page (eg. editing an affiliate) is opened,
        # only the PD of that affiliate can access it, along with the global staff user
        affiliate_slug = view.kwargs.get('affiliate_slug')
        if affiliate_slug:
            return AffiliateMembership.objects.filter(
                member=request.user, role__in=AffiliateMembership.STAFF_ROLES, affiliate__slug=affiliate_slug
            ).exists()

        return AffiliateMembership.objects.filter(
            member=request.user, role__in=AffiliateMembership.STAFF_ROLES
        ).exists()


def _get_path_of_arbitrary_backend_for_user(user):
    """
    Return the path to the first found authentication backend that recognizes the given user.
    """
    for backend_path in settings.AUTHENTICATION_BACKENDS:
        backend = load_backend(backend_path)
        if backend.get_user(user.id):
            return backend_path
    return None


def rejection_response(text, status=400):
    """Returns a rejection response with the passed in text and status code."""
    return Response(data={'error': '{}'.format(text)}, status=status, content_type='application/json')


class ImpersonateView(APIView):
    """
    Login as a different user.
    """
    permission_classes = (IsAdminUser,)

    def get_user(self, email):
        """Returns the User instance or None."""
        try:
            user = User.objects.get(email=email)
            return user
        except User.DoesNotExist:
            return None

    def post(self, request):
        """
        Logs in the current user as the user whose email is passed.
        If `check_user` email is passed returns a response that the user exists.
        """
        email = request.POST.get('email')
        check_user = request.POST.get('check_user')

        user = self.get_user(email)
        if not user:
            # TODO: use `rejection_response()`
            return Response(
                data={'msg': 'User with email {} does not exist.'.format(email)},
                status=404,
                content_type='application/json'
            )
        if check_user:
            return Response(status=200)

        if not hasattr(request.user, 'backend'):
            user.backend = _get_path_of_arbitrary_backend_for_user(user)
        login(request, user)

        LOG.info('Impersonating %s', email)
        return Response(
            data={'msg': 'User logged in.'},
            status=200,
            content_type='application/json'
        )


class AffiliateEntityViewSet(AffiliateViewMixin, APIView):
    """Views for creating new affiliates."""
    permission_classes = (IsStaffOrProgramDirector,)

    # The get() method is missing because we haven't yet transitioned
    # to API-based affiliates list page.

    def post(self, request):
        """Creates a new AffiliateEntity instance."""
        affiliate = AffiliateEntity()
        affiliate = self.create_new_affiliate(request)
        response_data = AffiliateEntitySerializer(affiliate).data

        return Response(
            data=response_data,
            status=201,
            content_type='application/json'
        )


class AffiliateEntityDetailsViewSet(AffiliateViewMixin, APIView):
    """Views for displaying affiliate details, updating and deleting affiliates."""
    permission_classes = (IsStaffOrProgramDirector,)

    def get(self, request, affiliate_slug):  # pylint: disable=unused-argument
        """Returns the affiliate details."""
        affiliate = AffiliateEntity.objects.get(slug=affiliate_slug)
        response_data = AffiliateEntitySerializer(affiliate).data
        return Response(data=response_data)

    def patch(self, request, affiliate_slug):
        """Updates the affiliate."""
        affiliate = self.update_affiliate(affiliate_slug, request)
        response_data = AffiliateEntitySerializer(affiliate).data
        return Response(data=response_data)

    def delete(self, request, affiliate_slug):  # pylint: disable=unused-argument
        """Deletes the affiliate."""
        AffiliateEntity.objects.get(slug=affiliate_slug).remove()
        return Response(status=204)


class AffiliateMembershipViewSet(APIView):
    """Views for creating and removing affiliate memberships."""
    permission_classes = (IsGlobalStaffOrAffiliateStaff,)

    def success_response(self, status=201, invite_object=None, membership_object=None):
        """Returns a success response with serialized object and status code."""
        response = {}
        if invite_object:
            response['invite'] = AffiliateInviteSerializer(invite_object).data
        if membership_object:
            response['membership'] = AffiliateMembershipSerializer(membership_object).data

        return Response(data=response, status=status, content_type='application/json')

    def get(self, request, affiliate_slug):
        """
        Returns serialized data of all the memberships in the affiliate with the passed slug.
        If `role` param is passed, then returns only the data for the memberships of that role.
        """
        role = request.GET.get('role')
        params = {'affiliate__slug': affiliate_slug}

        if role:
            params['role'] = role

        memberships = AffiliateMembership.objects.filter(**params)
        response_data = AffiliateMembershipSerializer(memberships, many=True).data
        return Response(data=response_data)

    def post(self, request, affiliate_slug):
        """
        Creates a new affiliate membership.
        If the invited user is not yet registered on the platform it creates a new invite for that user.
        """
        email = request.POST.get('email')
        role = request.POST.get('role')

        if not email:
            return rejection_response('Email is empty.')

        if role not in AffiliateMembership.ROLES:
            return rejection_response('Role invalid.')
        # Only global staff users are allowed to create PD's for affiliates.
        if role == AffiliateMembership.STAFF and not request.user.is_staff:
            return rejection_response('You are not allowed to do that.')

        affiliate = AffiliateEntity.objects.get(slug=affiliate_slug)
        params = {
            'affiliate': affiliate,
            'role': role
        }

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            params['email'] = email
            params['invited_by'] = request.user
            params['active'] = True

            if AffiliateInvite.objects.filter(**params).exists():
                return rejection_response('Invite already exists.')

            invite = AffiliateInvite.objects.create(**params)
            return self.success_response(invite_object=invite)

        params['member'] = user
        if AffiliateMembership.objects.filter(**params).exists():
            return rejection_response('Membership already exists.')

        try:
            membership = AffiliateMembership.objects.create(**params)
        except IntegrityError:
            return rejection_response('An error happened.')
        return self.success_response(membership_object=membership)

    def delete(self, request, affiliate_slug):
        """Removes an existing affiliate membership."""
        member_id = request.POST.get('member_id')
        role = request.POST.get('role')

        # Only global staff users are allowed to remove PD's from affiliates.
        if role == AffiliateMembership.STAFF and not request.user.is_staff:
            return rejection_response('You are not allowed to do that.')

        try:
            membership = AffiliateMembership.objects.get(
                affiliate__slug=affiliate_slug,
                member_id=member_id,
                role=role
            )
        except AffiliateMembership.DoesNotExist:
            return rejection_response('Membership not found.', status=404)

        # An affiliate needs to have at least one Program Director,
        # so we don't allow removing the only PD in an affiliate.

        other_pd_membership = AffiliateMembership.objects.filter(
            affiliate=membership.affiliate, role=AffiliateMembership.STAFF
        ).exclude(id=membership.id).first()

        if role == AffiliateMembership.STAFF and not other_pd_membership:
            return rejection_response('Affiliate needs to have at least one program director.')

        membership.delete()
        return self.success_response(status=204)


class AffiliateMembershipDetailsViewSet(APIView):
    permission_classes = (IsGlobalStaffOrAffiliateStaff,)

    def delete(self, request, affiliate_slug, membership_id):  # pylint: disable=unused-argument
        """Removes the affiliate membership specified by the `membership_id`."""
        try:
            membership = AffiliateMembership.objects.get(id=membership_id)
        except AffiliateMembership.DoesNotExist:
            return rejection_response('Membership not found.', status=404)

        # Only global staff users are allowed to remove PD's from affiliates.
        if membership.role == AffiliateMembership.STAFF and not request.user.is_staff:
            return rejection_response('You are not allowed to do that.')

        # An affiliate needs to have at least one Program Director,
        # so we don't allow removing the only PD in an affiliate.

        other_pd_membership = AffiliateMembership.objects.filter(
            affiliate=membership.affiliate, role=AffiliateMembership.STAFF
        ).exclude(id=membership.id).first()

        if membership.role == AffiliateMembership.STAFF and not other_pd_membership:
            return rejection_response('Affiliate needs to have at least one program director.')

        try:
            AffiliateMembership.objects.get(id=membership_id).delete()
        except ValueError as err:
            return rejection_response(err.message)

        return Response(status=204)


class AffiliateInviteDetailsViewSet(APIView):
    permission_classes = (IsGlobalStaffOrAffiliateStaff,)

    def delete(self, request, affiliate_slug, invite_id):  # pylint: disable=unused-argument
        """Removes the affiliate invite specified by the `invite_id`."""
        try:
            invite = AffiliateInvite.objects.get(id=invite_id)
        except AffiliateInvite.DoesNotExist:
            return rejection_response('Invite not found.', status=404)

        invite.delete()
        return Response(status=204)


class DataExportView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):  # pylint: disable=unused-argument
        """Retrieve all the reports from S3."""
        report_store = ReportStore.from_config('GRADES_DOWNLOAD')
        return Response(
            data={'exports': report_store.links_for('affiliates')},
            status=200,
            content_type='application/json'
        )

    def post(self, request):
        """Start new report export task."""
        report_type = request.POST.get('report_type')

        if report_type == 'export_csv_affiliate_report':
            export_csv_affiliate_report.delay()
        elif report_type == 'export_csv_affiliate_course_report':
            export_csv_affiliate_course_report.delay()
        elif report_type == 'export_csv_user_report':
            export_csv_user_report.delay()
        elif report_type == 'export_csv_time_report':
            export_csv_course_report.delay(time_report=True)
        elif report_type == 'export_csv_completion_report':
            export_csv_course_report.delay(time_report=False)
        elif report_type == 'export_completion_report':
            export_csv_interactives_completion_report.delay()

        return Response(status=200)


class GetAffiliates(APIView):
    permission_classes = (IsGlobalStaffOrAffiliateStaff, )

    def has_facilitators(self, affiliate_id):
        return AffiliateMembership.objects.filter(
            role=AffiliateMembership.CCX_COACH, affiliate_id=affiliate_id
        ).exists()

    def get(self, request):
        """
        Returns all the affiliates of the user making the request
        where the user is a PD or CM.

        If 'has-facilitators' parameter is sent, then returns only those affiliates
        that have facilitators.
        """
        has_facilitators = request.GET.get('has-facilitators')
        affiliate_ids = AffiliateMembership.objects.filter(
            role__in=AffiliateMembership.STAFF_ROLES,
            member=request.user
        ).values_list('affiliate_id', flat=True)

        if has_facilitators:
            affiliate_ids = [aff_id for aff_id in affiliate_ids if self.has_facilitators(aff_id)]

        affiliates = AffiliateEntity.objects.filter(id__in=affiliate_ids)

        response_data = []
        for aff in affiliates:
            response_data.append({
                'affiliate': {
                    'name': aff.name,
                    'slug': aff.slug
                },
                'has_facilitators': self.has_facilitators(aff)
            })

        return Response(data=response_data)
