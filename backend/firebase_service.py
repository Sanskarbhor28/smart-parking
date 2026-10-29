
import os
import firebase_admin
from firebase_admin import credentials, messaging


def initialize_firebase():
    if firebase_admin._apps:
        return

    raw_credentials = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not raw_credentials:
        return

    import json
    credential_data = json.loads(raw_credentials)
    credential = credentials.Certificate(credential_data)
    firebase_admin.initialize_app(credential)


def send_parking_notification(token, title, body):
    initialize_firebase()

    if not firebase_admin._apps:
        raise RuntimeError("Firebase credentials are not configured")

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
    )

    return messaging.send(message)
