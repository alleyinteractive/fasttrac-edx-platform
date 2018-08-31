from django.core.management.base import BaseCommand

from affiliates.models import AffiliateEntity


class Command(BaseCommand):
    help = """
        Task for updating existing Affiliates location coordinates based on the saved address, city and zipcode.
    """

    def handle(self, *args, **options):  # pylint: disable=unused-argument
        affiliates = AffiliateEntity.objects.all()

        for affiliate in affiliates:
            try:
                latitude, longitude = affiliate.get_location_coordinates()
                affiliate.location_latitude = latitude
                affiliate.location_longitude = longitude
                affiliate.save()
                self.stdout.write('{} coordinates saved.'.format(affiliate.name))
            except:  # pylint: disable=bare-except
                self.stdout.write('Failed saving {} coordinates.'.format(affiliate.name))
