
import logging
from mailjet_rest import Client
from app.core.config import settings

logger = logging.getLogger(__name__)

def send_email(subject: str, message: str):
    if not settings.mailjet_enabled:
        logger.warning("Mailjet is not enabled. Skipping email notification.")
        return

    if not all([
        settings.mailjet_api_key,
        settings.mailjet_api_secret,
        settings.mailjet_sender_email,
        settings.mailjet_sender_name,
        settings.mailjet_receiver_emails,
    ]):
        logger.warning("Mailjet credentials are not fully configured. Skipping email notification.")
        return

    mailjet = Client(auth=(settings.mailjet_api_key, settings.mailjet_api_secret), version='v3.1')
    data = {
        'Messages': [
            {
                "From": {
                    "Email": settings.mailjet_sender_email,
                    "Name": settings.mailjet_sender_name
                },
                "To": [
                    {"Email": email} for email in settings.mailjet_receiver_emails
                ],
                "Subject": subject,
                "TextPart": message,
            }
        ]
    }
    try:
        result = mailjet.send.create(data=data)
        if result.status_code == 200:
            logger.info("Email sent successfully.")
        else:
            logger.error(f"Failed to send email. Status code: {result.status_code}, response: {result.json()}")
    except Exception as e:
        logger.error(f"An error occurred while sending email: {e}")
