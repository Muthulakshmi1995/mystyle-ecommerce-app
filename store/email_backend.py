import json
import urllib.request
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class AppsScriptEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent_count = 0

        for message in email_messages:
            try:
                html_body = ""
                for content, mimetype in getattr(message, "alternatives", []):
                    if mimetype == "text/html":
                        html_body = content
                        break

                payload = {
                    "secret": settings.MYSTYLE_API_SECRET,
                    "to": ",".join(message.to),
                    "subject": message.subject,
                    "text": message.body or "",
                    "html": html_body,
                }

                request = urllib.request.Request(
                    settings.MYSTYLE_EMAIL_API_URL,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )

                with urllib.request.urlopen(request, timeout=30) as response:
                    result = json.loads(response.read().decode("utf-8"))

                if not result.get("success"):
                    raise RuntimeError(result.get("error", "Email sending failed"))

                sent_count += 1

            except Exception:
                if not self.fail_silently:
                    raise

        return sent_count