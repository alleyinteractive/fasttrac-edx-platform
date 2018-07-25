from django.core.management.base import BaseCommand
from affiliates.models import AffiliateEntity


class Command(BaseCommand):
    help = "Command for updating CCX models with affiliate relationships."

    def handle(self, *args, **options):
        for affiliate in AffiliateEntity.objects.all():
            self.stdout.write('Updating affiliate {}'.format(affiliate.name))
            affiliate.courses.update(affiliate=affiliate)
