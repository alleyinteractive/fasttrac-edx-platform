from django.core.management.base import BaseCommand, CommandError
from affiliates.models import AffiliateEntity

class Command(BaseCommand):
  help = """
      Task for updating existing Affiliates location coordinates based on the saved address, city and zipcode.
  """
  def handle(self, *args, **options):
    affiliates = AffiliateEntity.objects.all()

    for affiliate in affiliates:
      try:
        latitude, longitude = affiliate.get_location_coordinates()
        setattr(affiliate, 'location_latitude', latitude)
        setattr(affiliate, 'location_longitude', longitude)
        affiliate.save()
        self.stdout.write('{} coordinates saved.'.format(affiliate.name))
      except:
        self.stdout.write('Failed saving {} coordinates.'.format(affiliate.name))
