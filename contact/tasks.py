from .models import ContactMessage
from bird import APIError, Bird

def send_contact_message_notification(message):
    msg = ContactMessage.objects.get(pk=message.id)
    with Bird() as client:
        try:
            message = client.email.send(
                from_={"email": "info@twinpeaksinvestment.com", "name": "TwinPeaks Investments"},
                to=["andileblessinghlophe@gmail.com"],
                subject=f"New Contact Message from {msg.name}",
                html=f"<p>{msg.message}</p>",
            )
            print(message.id, message.status)
        except APIError as err:
            print("send failed:", err)


