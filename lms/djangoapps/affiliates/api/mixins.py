from lms.djangoapps.instructor.views.tools import get_student_from_identifier

from affiliates.models import AffiliateEntity, AffiliateMembership


class AffiliateViewMixin(object):
    def get_affiliate_attributes_data(self, request):
        return {
            'address': request.POST.get('address'),
            'address_2': request.POST.get('address_2'),
            'city': request.POST.get('city'),
            'country': request.POST.get('country'),
            'description': request.POST.get('description'),
            'email': request.POST.get('email'),
            'facebook': request.POST.get('facebook'),
            'image': request.FILES.get('image') if request.FILES else None,
            'linkedin': request.POST.get('linkedin'),
            'name': request.POST.get('name'),
            'phone_number': request.POST.get('phone_number'),
            'phone_number_private': request.POST.get('phone_number_private'),
            'state': request.POST.get('state'),
            'twitter': request.POST.get('twitter'),
            'website': request.POST.get('website'),
            'zipcode': request.POST.get('zipcode')
        }

    def create_new_affiliate(self, request):
        affiliate_request_data = self.get_affiliate_attributes_data(request)
        affiliate = AffiliateEntity(**affiliate_request_data)

        if request.user.is_staff:
            parent_id = int(request.POST.get('parent', 0))
            if parent_id:
                affiliate.parent = AffiliateEntity.objects.get(id=parent_id)
            else:
                affiliate.parent = None

        affiliate.save()

        affiliate_type = request.POST.get('affiliate-type')
        if request.user.is_staff and affiliate_type == 'parent':
            subs = dict(request.POST)['sub-affiliates']
            AffiliateEntity.objects.filter(id__in=subs).update(parent=affiliate)

        # Affiliates app sends the PD ID (email)
        program_director_id = request.POST.get('member_identifier')
        if program_director_id:
            member = get_student_from_identifier(program_director_id)
            AffiliateMembership.objects.create(
                affiliate=affiliate,
                member=member,
                role=AffiliateMembership.STAFF
            )

        return affiliate

    def update_affiliate(self, affiliate, request):
        affiliate_request_data = self.get_affiliate_attributes_data(request)
        values = dict((k, v) for k, v in affiliate_request_data.iteritems() if v)
        affiliate.update(**values)
        return affiliate
