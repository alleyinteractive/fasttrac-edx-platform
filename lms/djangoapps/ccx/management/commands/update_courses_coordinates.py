from django.core.management.base import BaseCommand, CommandError
from lms.djangoapps.ccx.models import CustomCourseForEdX

class Command(BaseCommand):
  help = """
      Task for updating existing Affiliates location coordinates based on the saved address, city and zipcode.
  """
  def handle(self, *args, **options):
    ccxs = CustomCourseForEdX.objects.all()

    for ccx in ccxs:
      try:
        latitude, longitude = ccx.get_location_coordinates()
        setattr(ccx, 'location_latitude', latitude)
        setattr(ccx, 'location_longitude', longitude)
        ccx.save()
        self.stdout.write('{} coordinates saved.'.format(ccx.display_name))
      except:
        self.stdout.write('Failed saving {} coordinates.'.format(ccx.display_name))
