import time
from collections import defaultdict
from django.http import JsonResponse
from django.conf import settings


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.requests = defaultdict(list)
        self.enabled = getattr(settings, 'RATE_LIMIT_ENABLED', True)
        self.per_minute = getattr(settings, 'RATE_LIMIT_PER_MINUTE', 60)
        self.per_hour = getattr(settings, 'RATE_LIMIT_PER_HOUR', 1000)
    
    def __call__(self, request):
        if not self.enabled:
            return self.get_response(request)
        
        if request.path.startswith('/api/'):
            client_ip = self._get_client_ip(request)
            user_id = str(request.user.id) if request.user.is_authenticated else client_ip
            
            current_time = time.time()
            minute_key = f"{user_id}_minute"
            hour_key = f"{user_id}_hour"
            
            self.requests[minute_key] = [t for t in self.requests[minute_key] if current_time - t < 60]
            self.requests[hour_key] = [t for t in self.requests[hour_key] if current_time - t < 3600]
            
            if len(self.requests[minute_key]) >= self.per_minute:
                return JsonResponse({
                    'error': 'Rate limit exceeded. Please wait before making more requests.',
                    'retry_after': 60
                }, status=429)
            
            if len(self.requests[hour_key]) >= self.per_hour:
                return JsonResponse({
                    'error': 'Hourly rate limit exceeded. Please try again later.',
                    'retry_after': 3600
                }, status=429)
            
            self.requests[minute_key].append(current_time)
            self.requests[hour_key].append(current_time)
        
        return self.get_response(request)
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.path == '/health/':
            return JsonResponse({
                'status': 'healthy',
                'service': 'telemedvision'
            })
        return self.get_response(request)
