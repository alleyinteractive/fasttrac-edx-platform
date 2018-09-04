from django.core.management.base import BaseCommand

from affiliates.models import AffiliateEntity
from lms.djangoapps.ccx.models import CustomCourseForEdX


class Command(BaseCommand):
    help = "Command for updating CCX models with affiliate relationships."

    def handle(self, *args, **options):  # pylint: disable=unused-argument
        for affiliate in AffiliateEntity.objects.all():
            self.stdout.write('Updating affiliate {}'.format(affiliate.name))
            CustomCourseForEdX.objects.filter(
                coach=affiliate.program_director
            ).update(affiliate=affiliate)
