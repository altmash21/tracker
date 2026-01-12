"""
Middleware for debugging webhook requests
"""
import logging

logger = logging.getLogger(__name__)


class WebhookDebugMiddleware:
    """
    Middleware to log ALL incoming requests to webhook paths
    This helps diagnose if requests are reaching Django at all
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Log ALL requests to webhook paths BEFORE any other processing
        if 'whatsapp' in request.path.lower():
            logger.info(f"▶▶▶ MIDDLEWARE: Request to {request.path}")
            logger.info(f"▶▶▶ MIDDLEWARE: Method={request.method}")
            logger.info(f"▶▶▶ MIDDLEWARE: Content-Type={request.META.get('CONTENT_TYPE', 'N/A')}")
            logger.info(f"▶▶▶ MIDDLEWARE: User-Agent={request.META.get('HTTP_USER_AGENT', 'N/A')}")
            logger.info(f"▶▶▶ MIDDLEWARE: X-Hub-Signature-256={request.META.get('HTTP_X_HUB_SIGNATURE_256', 'N/A')}")
        
        response = self.get_response(request)
        
        # Log response for webhook paths
        if 'whatsapp' in request.path.lower():
            logger.info(f"◀◀◀ MIDDLEWARE: Response status={response.status_code}")
        
        return response
