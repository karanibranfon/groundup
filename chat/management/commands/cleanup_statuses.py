from django.core.management.base import BaseCommand
from django.utils import timezone
from chat.models import Status


class Command(BaseCommand):
    help = 'Delete expired statuses (older than 24 hours)'

    def handle(self, *args, **options):
        expired = Status.objects.filter(expires_at__lt=timezone.now())
        count = expired.count()
        expired.delete()
        self.stdout.write(f'Deleted {count} expired statuses')
