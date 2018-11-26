from lms.djangoapps.instructor.views.tools import get_student_from_identifier

from affiliates.models import AffiliateEntity, AffiliateMembership


class AffiliateViewMixin(object):
    UPDATEABLE_ATTRIBUTES = [
        'address', 'address_2', 'city', 'country', 'description', 'email', 'facebook', 'image', 'active',
        'linkedin', 'name', 'phone_number', 'phone_number_private', 'state', 'twitter', 'website', 'zipcode'
    ]

    def _clean_attribute(self, attr):
        """
        Cleans the attributes in the requests. E.g. a boolean from JS is received
        as 'true' or 'false', this will convert them to boolean objects.
        """
        if attr == 'true':
            return True
        if attr == 'false':
            return False
        return attr

    def get_affiliate_attributes_data(self, request_data):
        """
        Returns a dictionary of the updateable attributes in the request data.
        """
        attributes = {}

        for attr in self.UPDATEABLE_ATTRIBUTES:
            if attr in request_data:
                attributes[attr] = self._clean_attribute(request_data.get(attr))
        return attributes

    def create_new_affiliate(self, request):
        """
        Creates a new AffiliateEntity instance based on data in the request.
        """
        affiliate_request_data = self.get_affiliate_attributes_data(request.POST)
        affiliate = AffiliateEntity(**affiliate_request_data)

        # Only global staff users can set parent-child relationships
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

        # Affiliates app sends the PD ID (email).
        # If the attribute is sent (e.g. request comes from the affiliate app),
        # automatically create the PD membership for the passed in user.
        program_director_id = request.POST.get('member_identifier')
        if program_director_id:
            member = get_student_from_identifier(program_director_id)
            AffiliateMembership.objects.create(
                affiliate=affiliate,
                member=member,
                role=AffiliateMembership.STAFF
            )

        return affiliate

    def update_affiliate(self, affiliate_slug, request):
        """
        Updates an AffiliateEntity instance based on data in the request.
        """
        affiliate_update_attributes = self.get_affiliate_attributes_data(request.data)

        # We are using filter here to get a QS list on which .update() can be called,
        # even though only one affiliate matches one slug.
        matching_affiliates = AffiliateEntity.objects.filter(slug=affiliate_slug)
        matching_affiliates.update(**affiliate_update_attributes)
        return matching_affiliates.first()
