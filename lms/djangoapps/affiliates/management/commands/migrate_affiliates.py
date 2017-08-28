import urllib2, io
from PIL import Image
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.utils import IntegrityError
from opaque_keys.edx.keys import CourseKey
from affiliates.models import AffiliateEntity, AffiliateMembership
from student.models import CourseAccessRole
from openedx.core.djangoapps.user_api.accounts.image_helpers import get_profile_image_urls_for_user


class Command(BaseCommand):
    help = """
        Task for migrating existing Program Directors into Affiliate Entities.
        This will create an Affiliate Entity and add Affiliate Membership connection
        between the Program Director and that entity.
        Program Director is ccx_coach on master course.
    """
    def handle(self, *args, **options):
        program_director_roles = CourseAccessRole.objects.filter(role='ccx_coach').exclude(course_id__startswith='ccx-')

        for program_director_role in program_director_roles:
            user = program_director_role.user
            self.stdout.write(str(user))

            image_url = get_profile_image_urls_for_user(user)['full']
            self.stdout.write(image_url)

            image_file = None

            try:
                if 's3' in image_url:
                    file_data = urllib2.urlopen(image_url).read()
                else:
                    image_path = '/edx/var/edxapp' + image_url.split('?')[0]
                    file_data = open(image_path).read()

                image_file = ContentFile(file_data)
            except IOError:
                self.stdout.write('Image not found')

            try:
                affiliate, _ = AffiliateEntity.objects.get_or_create(
                    email=user.profile.public_email or user.email,
                    name=user.profile.affiliate_organization_name or user.profile.name,
                    description=user.profile.description,
                    phone_number=user.profile.phone_number,
                    address=' '.join([user.profile.mailing_address or '', user.profile.secondary_address or '']),
                    city=user.profile.city,
                    zipcode=user.profile.zipcode,
                    facebook=user.profile.facebook_link,
                    twitter=user.profile.twitter_link,
                    linkedin=user.profile.linkedin_link,
                    state=user.profile.state,
                    country=user.profile.country,
                )

                if image_file:
                    image_filename = image_url.split('/')[-1].split('?')[0]
                    affiliate.image.save(image_filename, image_file, save=True)

                AffiliateMembership.objects.get_or_create(
                    affiliate=affiliate,
                    member=user,
                    role='staff'
                )
            except IntegrityError:
                self.stdout.write('Duplicate entry.')


        self.stdout.write('Successfully migrated affiliate users')
