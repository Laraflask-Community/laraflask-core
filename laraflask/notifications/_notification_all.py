"""
Laraflask Notification System
Multi-channel notifications: Email, SMS, WhatsApp, Telegram, Push.
"""

from __future__ import annotations
import os
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger('laraflask.notifications')


# ─── Message Types ────────────────────────────────────────────────────────────

class MailMessage:
    """Fluent mail message builder."""

    def __init__(self):
        self._subject: str = ''
        self._from: Optional[tuple] = None
        self._to: List[str] = []
        self._cc: List[str] = []
        self._bcc: List[str] = []
        self._reply_to: Optional[str] = None
        self._lines: List[str] = []
        self._action_text: Optional[str] = None
        self._action_url: Optional[str] = None
        self._greeting: str = 'Hello!'
        self._salutation: str = 'Regards,\nThe Team'
        self._attachments: List[Dict] = []
        self._level: str = 'info'  # info, success, warning, error
        self._view: Optional[str] = None
        self._view_data: Dict = {}
        self._markdown: Optional[str] = None
        self._html: Optional[str] = None
        self._priority: int = 3

    def subject(self, subject: str) -> 'MailMessage':
        self._subject = subject
        return self

    def from_(self, address: str, name: str = '') -> 'MailMessage':
        self._from = (address, name)
        return self

    def to(self, address: str) -> 'MailMessage':
        self._to.append(address)
        return self

    def cc(self, address: str) -> 'MailMessage':
        self._cc.append(address)
        return self

    def bcc(self, address: str) -> 'MailMessage':
        self._bcc.append(address)
        return self

    def reply_to(self, address: str) -> 'MailMessage':
        self._reply_to = address
        return self

    def greeting(self, text: str) -> 'MailMessage':
        self._greeting = text
        return self

    def salutation(self, text: str) -> 'MailMessage':
        self._salutation = text
        return self

    def line(self, text: str) -> 'MailMessage':
        self._lines.append(text)
        return self

    def action(self, text: str, url: str) -> 'MailMessage':
        self._action_text = text
        self._action_url = url
        return self

    def attach(self, path: str, options: Dict = None) -> 'MailMessage':
        self._attachments.append({'path': path, **(options or {})})
        return self

    def attach_data(self, data: bytes, name: str, options: Dict = None) -> 'MailMessage':
        self._attachments.append({'data': data, 'name': name, **(options or {})})
        return self

    def view(self, template: str, data: Dict = None) -> 'MailMessage':
        self._view = template
        self._view_data = data or {}
        return self

    def html(self, content: str) -> 'MailMessage':
        self._html = content
        return self

    def markdown(self, template: str, data: Dict = None) -> 'MailMessage':
        self._markdown = template
        self._view_data = data or {}
        return self

    def level(self, level: str) -> 'MailMessage':
        self._level = level
        return self

    def success(self) -> 'MailMessage':
        return self.level('success')

    def error(self) -> 'MailMessage':
        return self.level('error')

    def warning(self) -> 'MailMessage':
        return self.level('warning')

    def priority(self, level: int) -> 'MailMessage':
        self._priority = level
        return self

    def render(self) -> str:
        """Render the message as HTML."""
        if self._html:
            return self._html

        color_map = {
            'info':    '#3b82f6',
            'success': '#10b981',
            'warning': '#f59e0b',
            'error':   '#ef4444',
        }
        color = color_map.get(self._level, '#3b82f6')

        lines_html = ''.join(
            f'<p style="margin:0 0 16px;color:#374151;font-size:16px;line-height:1.6">'
            f'{line}</p>'
            for line in self._lines
        )

        action_html = ''
        if self._action_text and self._action_url:
            action_html = f'''
            <div style="text-align:center;margin:32px 0">
              <a href="{self._action_url}"
                 style="background:{color};color:#fff;padding:12px 28px;
                        border-radius:6px;text-decoration:none;font-weight:600;
                        font-size:16px;display:inline-block">
                {self._action_text}
              </a>
            </div>
            '''

        return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{self._subject}</title></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
             background:#f3f4f6;margin:0;padding:40px 20px">
  <div style="max-width:600px;margin:0 auto">
    <div style="background:{color};height:4px;border-radius:4px 4px 0 0"></div>
    <div style="background:#fff;padding:40px;border-radius:0 0 8px 8px;
                box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <p style="font-size:20px;font-weight:600;color:#111827;margin:0 0 24px">{self._greeting}</p>
      {lines_html}
      {action_html}
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
      <p style="color:#6b7280;font-size:14px;margin:0">{self._salutation}</p>
    </div>
    <p style="text-align:center;color:#9ca3af;font-size:12px;margin-top:16px">
      Sent by Laraflask Notifications
    </p>
  </div>
</body></html>"""


class SmsMessage:
    """SMS message builder."""

    def __init__(self, content: str = ''):
        self._content = content
        self._from: Optional[str] = None
        self._unicode: bool = False

    def content(self, text: str) -> 'SmsMessage':
        self._content = text
        return self

    def from_(self, number: str) -> 'SmsMessage':
        self._from = number
        return self

    def unicode(self) -> 'SmsMessage':
        self._unicode = True
        return self


class TelegramMessage:
    """Telegram message builder."""

    def __init__(self, content: str = ''):
        self._content = content
        self._parse_mode: str = 'HTML'
        self._buttons: List[List[Dict]] = []
        self._chat_id: Optional[str] = None
        self._disable_preview: bool = False
        self._photo: Optional[str] = None

    def content(self, text: str) -> 'TelegramMessage':
        self._content = text
        return self

    def chat_id(self, cid: str) -> 'TelegramMessage':
        self._chat_id = cid
        return self

    def markdown(self) -> 'TelegramMessage':
        self._parse_mode = 'Markdown'
        return self

    def html(self) -> 'TelegramMessage':
        self._parse_mode = 'HTML'
        return self

    def button(self, text: str, url: str) -> 'TelegramMessage':
        self._buttons.append([{'text': text, 'url': url}])
        return self

    def photo(self, url: str) -> 'TelegramMessage':
        self._photo = url
        return self

    def disable_preview(self) -> 'TelegramMessage':
        self._disable_preview = True
        return self

    def line(self, text: str) -> 'TelegramMessage':
        self._content += ('\n' if self._content else '') + text
        return self


class WhatsAppMessage:
    """WhatsApp message builder."""

    def __init__(self, content: str = ''):
        self._content = content
        self._template: Optional[str] = None
        self._template_params: List[str] = []
        self._media_url: Optional[str] = None
        self._to: Optional[str] = None

    def content(self, text: str) -> 'WhatsAppMessage':
        self._content = text
        return self

    def to(self, number: str) -> 'WhatsAppMessage':
        self._to = number
        return self

    def template(self, name: str, *params: str) -> 'WhatsAppMessage':
        self._template = name
        self._template_params = list(params)
        return self

    def media(self, url: str) -> 'WhatsAppMessage':
        self._media_url = url
        return self

    def line(self, text: str) -> 'WhatsAppMessage':
        self._content += ('\n' if self._content else '') + text
        return self


class PushMessage:
    """Push notification message builder."""

    def __init__(self):
        self._title: str = ''
        self._body: str = ''
        self._data: Dict = {}
        self._icon: Optional[str] = None
        self._badge: Optional[int] = None
        self._sound: str = 'default'
        self._click_action: Optional[str] = None

    def title(self, text: str) -> 'PushMessage':
        self._title = text
        return self

    def body(self, text: str) -> 'PushMessage':
        self._body = text
        return self

    def data(self, **kwargs) -> 'PushMessage':
        self._data.update(kwargs)
        return self

    def icon(self, url: str) -> 'PushMessage':
        self._icon = url
        return self

    def badge(self, count: int) -> 'PushMessage':
        self._badge = count
        return self

    def sound(self, sound: str) -> 'PushMessage':
        self._sound = sound
        return self

    def click_action(self, action: str) -> 'PushMessage':
        self._click_action = action
        return self


# ─── Channels ─────────────────────────────────────────────────────────────────

class Channel(ABC):
    """Base notification channel."""

    @abstractmethod
    def send(self, notifiable: Any, notification: 'Notification') -> bool:
        pass


class MailChannel(Channel):
    """Email notification channel using SMTP."""

    def send(self, notifiable: Any, notification: 'Notification') -> bool:
        if not hasattr(notification, 'to_mail'):
            return False

        message: MailMessage = notification.to_mail(notifiable)
        to_address = getattr(notifiable, 'email', None)

        if not to_address:
            logger.warning(f"No email address for notifiable [{type(notifiable).__name__}]")
            return False

        return self._send_smtp(to_address, message)

    def _send_smtp(self, to: str, message: MailMessage) -> bool:
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            host = os.getenv('MAIL_HOST', 'smtp.mailtrap.io')
            port = int(os.getenv('MAIL_PORT', 2525))
            username = os.getenv('MAIL_USERNAME', '')
            password = os.getenv('MAIL_PASSWORD', '')
            from_addr = os.getenv('MAIL_FROM_ADDRESS', 'hello@laraflask.dev')
            from_name = os.getenv('MAIL_FROM_NAME', 'Laraflask')

            msg = MIMEMultipart('alternative')
            msg['Subject'] = message._subject
            msg['From'] = f"{from_name} <{from_addr}>"
            msg['To'] = to

            if message._cc:
                msg['Cc'] = ', '.join(message._cc)

            html_content = message.render()
            msg.attach(MIMEText(html_content, 'html'))

            # Handle attachments
            for attachment in message._attachments:
                if 'path' in attachment:
                    from email.mime.base import MIMEBase
                    from email import encoders
                    with open(attachment['path'], 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        filename = os.path.basename(attachment['path'])
                        part.add_header('Content-Disposition', f'attachment; filename={filename}')
                        msg.attach(part)

            with smtplib.SMTP(host, port) as server:
                if port in (587, 2525):
                    server.starttls()
                if username:
                    server.login(username, password)

                recipients = [to] + message._cc + message._bcc
                server.sendmail(from_addr, recipients, msg.as_string())

            logger.info(f"Mail sent to [{to}]: {message._subject}")
            return True

        except Exception as e:
            logger.error(f"Mail send failed: {e}")
            return False


class SmsChannel(Channel):
    """SMS notification channel using Twilio."""

    def send(self, notifiable: Any, notification: 'Notification') -> bool:
        if not hasattr(notification, 'to_sms'):
            return False

        message: SmsMessage = notification.to_sms(notifiable)
        to_number = getattr(notifiable, 'phone', None)

        if not to_number:
            logger.warning("No phone number for SMS notification")
            return False

        return self._send_twilio(to_number, message)

    def _send_twilio(self, to: str, message: SmsMessage) -> bool:
        try:
            from twilio.rest import Client
            client = Client(
                os.getenv('TWILIO_SID'),
                os.getenv('TWILIO_TOKEN'),
            )
            client.messages.create(
                to=to,
                from_=message._from or os.getenv('TWILIO_FROM'),
                body=message._content,
            )
            logger.info(f"SMS sent to [{to}]")
            return True
        except ImportError:
            logger.error("Twilio not installed. Run: pip install twilio")
            return False
        except Exception as e:
            logger.error(f"SMS send failed: {e}")
            return False


class TelegramChannel(Channel):
    """Telegram notification channel."""

    def send(self, notifiable: Any, notification: 'Notification') -> bool:
        if not hasattr(notification, 'to_telegram'):
            return False

        message: TelegramMessage = notification.to_telegram(notifiable)
        chat_id = (message._chat_id
                   or getattr(notifiable, 'telegram_chat_id', None)
                   or getattr(notifiable, 'telegram_id', None))

        if not chat_id:
            logger.warning("No Telegram chat ID for notification")
            return False

        return self._send(chat_id, message)

    def _send(self, chat_id: str, message: TelegramMessage) -> bool:
        try:
            import urllib.request
            import json

            token = os.getenv('TELEGRAM_BOT_TOKEN')
            if not token:
                logger.error("TELEGRAM_BOT_TOKEN not set")
                return False

            base_url = f"https://api.telegram.org/bot{token}"

            if message._photo:
                endpoint = f"{base_url}/sendPhoto"
                payload = {
                    'chat_id': chat_id,
                    'photo': message._photo,
                    'caption': message._content,
                    'parse_mode': message._parse_mode,
                }
            else:
                endpoint = f"{base_url}/sendMessage"
                payload = {
                    'chat_id': chat_id,
                    'text': message._content,
                    'parse_mode': message._parse_mode,
                    'disable_web_page_preview': message._disable_preview,
                }

            if message._buttons:
                payload['reply_markup'] = json.dumps({
                    'inline_keyboard': message._buttons
                })

            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                endpoint,
                data=data,
                headers={'Content-Type': 'application/json'},
            )
            urllib.request.urlopen(req, timeout=10)
            logger.info(f"Telegram message sent to [{chat_id}]")
            return True
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False


class WhatsAppChannel(Channel):
    """WhatsApp notification channel via Twilio."""

    def send(self, notifiable: Any, notification: 'Notification') -> bool:
        if not hasattr(notification, 'to_whatsapp'):
            return False

        message: WhatsAppMessage = notification.to_whatsapp(notifiable)
        to_number = message._to or getattr(notifiable, 'whatsapp', None) or getattr(notifiable, 'phone', None)

        if not to_number:
            logger.warning("No phone number for WhatsApp notification")
            return False

        return self._send(to_number, message)

    def _send(self, to: str, message: WhatsAppMessage) -> bool:
        try:
            from twilio.rest import Client
            client = Client(
                os.getenv('TWILIO_SID'),
                os.getenv('TWILIO_TOKEN'),
            )
            from_number = f"whatsapp:{os.getenv('TWILIO_WHATSAPP_FROM')}"
            to_number = f"whatsapp:{to}"

            client.messages.create(
                from_=from_number,
                to=to_number,
                body=message._content,
                media_url=[message._media_url] if message._media_url else None,
            )
            logger.info(f"WhatsApp sent to [{to}]")
            return True
        except ImportError:
            logger.error("Twilio not installed. Run: pip install twilio")
            return False
        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}")
            return False


class DatabaseChannel(Channel):
    """Store notifications in database."""

    TABLE = 'notifications'

    def send(self, notifiable: Any, notification: 'Notification') -> bool:
        try:
            import uuid
            import json
            from laraflask.orm.db import DB

            data = {}
            if hasattr(notification, 'to_array'):
                data = notification.to_array(notifiable)
            elif hasattr(notification, 'to_database'):
                data = notification.to_database(notifiable)

            notifiable_id = getattr(notifiable, 'id', None)
            notifiable_type = type(notifiable).__name__

            DB.insert(
                f"INSERT INTO {self.TABLE} "
                f"(id, type, notifiable_type, notifiable_id, data, read_at, created_at, updated_at) "
                f"VALUES (:id, :type, :notifiable_type, :notifiable_id, :data, NULL, :now, :now)",
                {
                    'id': str(uuid.uuid4()),
                    'type': type(notification).__name__,
                    'notifiable_type': notifiable_type,
                    'notifiable_id': notifiable_id,
                    'data': json.dumps(data),
                    'now': __import__('datetime').datetime.utcnow().isoformat(),
                }
            )
            return True
        except Exception as e:
            logger.error(f"Database notification failed: {e}")
            return False


class PushChannel(Channel):
    """Push notification channel via Firebase FCM."""

    def send(self, notifiable: Any, notification: 'Notification') -> bool:
        if not hasattr(notification, 'to_push'):
            return False

        message: PushMessage = notification.to_push(notifiable)
        token = getattr(notifiable, 'fcm_token', None) or getattr(notifiable, 'push_token', None)

        if not token:
            logger.warning("No FCM token for push notification")
            return False

        return self._send_fcm(token, message)

    def _send_fcm(self, token: str, message: PushMessage) -> bool:
        try:
            import urllib.request
            import json

            server_key = os.getenv('FCM_SERVER_KEY')
            if not server_key:
                logger.error("FCM_SERVER_KEY not set")
                return False

            payload = {
                'to': token,
                'notification': {
                    'title': message._title,
                    'body': message._body,
                    'icon': message._icon,
                    'badge': message._badge,
                    'sound': message._sound,
                    'click_action': message._click_action,
                },
                'data': message._data,
            }

            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                'https://fcm.googleapis.com/fcm/send',
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'key={server_key}',
                },
            )
            urllib.request.urlopen(req, timeout=10)
            logger.info(f"Push notification sent")
            return True
        except Exception as e:
            logger.error(f"Push notification failed: {e}")
            return False


# ─── Notification Base ────────────────────────────────────────────────────────

class Notification:
    """
    Base class for all Laraflask notifications.

    Usage:
        class WelcomeNotification(Notification):
            def via(self, notifiable):
                return ['mail', 'telegram']

            def to_mail(self, notifiable):
                return (MailMessage()
                        .subject('Welcome!')
                        .line(f'Welcome, {notifiable.name}!')
                        .action('Get Started', 'https://example.com'))

            def to_telegram(self, notifiable):
                return TelegramMessage(f'Welcome, {notifiable.name}!')
    """

    def via(self, notifiable: Any) -> List[str]:
        """Define which channels to use."""
        return ['mail']

    def should_send(self, notifiable: Any, channel: str) -> bool:
        """Determine if notification should be sent."""
        return True

    def to_array(self, notifiable: Any) -> Dict:
        """Convert to array (for database channel)."""
        return {}

    def failed(self, exception: Exception) -> None:
        """Handle a failed notification."""
        logger.error(f"Notification [{type(self).__name__}] failed: {exception}")


class NotificationSender:
    """Sends notifications through the appropriate channels."""

    CHANNEL_MAP = {
        'mail':      MailChannel,
        'sms':       SmsChannel,
        'telegram':  TelegramChannel,
        'whatsapp':  WhatsAppChannel,
        'database':  DatabaseChannel,
        'push':      PushChannel,
    }

    def __init__(self):
        self._channels: Dict[str, Channel] = {}

    def send(self, notifiables: Any, notification: Notification) -> None:
        """Send notification to one or multiple notifiables."""
        if not isinstance(notifiables, (list, tuple)):
            notifiables = [notifiables]

        for notifiable in notifiables:
            self._send_to(notifiable, notification)

    def _send_to(self, notifiable: Any, notification: Notification) -> None:
        channels = notification.via(notifiable)
        for channel_name in channels:
            if not notification.should_send(notifiable, channel_name):
                continue
            channel = self._resolve_channel(channel_name)
            if channel:
                try:
                    channel.send(notifiable, notification)
                except Exception as e:
                    notification.failed(e)

    def _resolve_channel(self, name: str) -> Optional[Channel]:
        if name in self._channels:
            return self._channels[name]

        channel_class = self.CHANNEL_MAP.get(name)
        if channel_class:
            self._channels[name] = channel_class()
            return self._channels[name]

        logger.warning(f"Unknown notification channel [{name}]")
        return None

    def register_channel(self, name: str, channel: Channel) -> None:
        self._channels[name] = channel


# ─── Notifiable Mixin ─────────────────────────────────────────────────────────

class Notifiable:
    """
    Mixin for models that can receive notifications.
    Add to your User model: class User(Model, Notifiable)
    """

    def notify(self, notification: Notification) -> None:
        """Send a notification to this notifiable."""
        sender = NotificationSender()
        sender.send(self, notification)

    def notify_now(self, notification: Notification) -> None:
        """Send notification immediately, bypassing queue."""
        self.notify(notification)

    def unread_notifications(self) -> List[Dict]:
        """Get unread notifications from database."""
        try:
            from laraflask.orm.db import DB
            return DB.select(
                "SELECT * FROM notifications WHERE notifiable_id = :id "
                "AND notifiable_type = :type AND read_at IS NULL ORDER BY created_at DESC",
                {'id': getattr(self, 'id'), 'type': type(self).__name__}
            )
        except Exception:
            return []

    def read_notifications(self) -> List[Dict]:
        """Get read notifications."""
        try:
            from laraflask.orm.db import DB
            return DB.select(
                "SELECT * FROM notifications WHERE notifiable_id = :id "
                "AND notifiable_type = :type AND read_at IS NOT NULL ORDER BY created_at DESC",
                {'id': getattr(self, 'id'), 'type': type(self).__name__}
            )
        except Exception:
            return []

    def mark_all_as_read(self) -> None:
        """Mark all notifications as read."""
        try:
            from laraflask.orm.db import DB
            import datetime
            DB.update(
                "UPDATE notifications SET read_at = :now "
                "WHERE notifiable_id = :id AND notifiable_type = :type AND read_at IS NULL",
                {
                    'now': datetime.datetime.utcnow().isoformat(),
                    'id': getattr(self, 'id'),
                    'type': type(self).__name__,
                }
            )
        except Exception as e:
            logger.error(f"mark_all_as_read failed: {e}")


# ─── Global Facade ────────────────────────────────────────────────────────────

class Notification_:
    """Facade for sending notifications."""

    _sender = NotificationSender()

    @classmethod
    def send(cls, notifiables: Any, notification: Notification) -> None:
        cls._sender.send(notifiables, notification)

    @classmethod
    def send_now(cls, notifiables: Any, notification: Notification) -> None:
        cls._sender.send(notifiables, notification)

    @classmethod
    def route(cls, channel: str, destination: Any) -> 'AnonymousNotifiable':
        return AnonymousNotifiable(channel, destination)


class AnonymousNotifiable:
    """Anonymous notifiable for routing notifications to arbitrary destinations."""

    def __init__(self, channel: str, destination: Any):
        self._routes: Dict[str, Any] = {channel: destination}

    def route(self, channel: str, destination: Any) -> 'AnonymousNotifiable':
        self._routes[channel] = destination
        return self

    def notify(self, notification: Notification) -> None:
        for channel, destination in self._routes.items():
            setattr(self, channel, destination)
        Notification_.send(self, notification)

    @property
    def email(self) -> Optional[str]:
        return self._routes.get('mail')

    @property
    def phone(self) -> Optional[str]:
        return self._routes.get('sms') or self._routes.get('whatsapp')

    @property
    def telegram_chat_id(self) -> Optional[str]:
        return self._routes.get('telegram')
