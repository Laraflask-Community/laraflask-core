"""
Laraflask Framework v1.0.0
Elegant · Expressive · Modern · Fast · Scalable · Developer Friendly
"""

__version__ = '1.0.0'

def _lazy(module_path, attr):
    """Lazy import helper — avoids loading optional deps at package level."""
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, attr)

# Expose convenience symbols without triggering all optional deps
def __getattr__(name):
    _map = {
        'Application':          ('laraflask.core.application',        'Application'),
        'Model':                ('laraflask.orm.model',                'Model'),
        'DB':                   ('laraflask.orm.db',                   'DB'),
        'Cache':                ('laraflask.cache.cache',              'Cache'),
        'Auth':                 ('laraflask.auth.auth',                'Auth'),
        'Gate':                 ('laraflask.auth.auth',                'Gate'),
        'Hash':                 ('laraflask.auth.auth',                'Hash'),
        'Policy':               ('laraflask.auth.auth',                'Policy'),
        'Validator':            ('laraflask.validation.validator',     'Validator'),
        'FormRequest':          ('laraflask.validation.validator',     'FormRequest'),
        'ValidationException':  ('laraflask.validation.validator',     'ValidationException'),
        'Queue':                ('laraflask.queue.queue',              'Queue'),
        'Job':                  ('laraflask.queue.queue',              'Job'),
        'dispatch':             ('laraflask.queue.queue',              'dispatch'),
        'dispatch_now':         ('laraflask.queue.queue',              'dispatch_now'),
        'Events':               ('laraflask.events.dispatcher',        'Events'),
        'Event':                ('laraflask.events.dispatcher',        'Event'),
        'Listener':             ('laraflask.events.dispatcher',        'Listener'),
        'Schedule':             ('laraflask.scheduler.schedule',       'Schedule'),
        'Storage':              ('laraflask.storage.storage',          'Storage'),
        'Notification':         ('laraflask.notifications.notification','Notification'),
        'Notifiable':           ('laraflask.notifications.notification','Notifiable'),
        'MailMessage':          ('laraflask.notifications.notification','MailMessage'),
        'SmsMessage':           ('laraflask.notifications.notification','SmsMessage'),
        'TelegramMessage':      ('laraflask.notifications.notification','TelegramMessage'),
        'WhatsAppMessage':      ('laraflask.notifications.notification','WhatsAppMessage'),
        'PushMessage':          ('laraflask.notifications.notification','PushMessage'),
        'Middleware':           ('laraflask.middleware.middleware',     'Middleware'),
        'ApiResponse':          ('laraflask.api.api',                  'ApiResponse'),
        'ApiResource':          ('laraflask.api.api',                  'ApiResource'),
        'ApiController':        ('laraflask.api.api',                  'ApiController'),
        'ServiceProvider':      ('laraflask.core.providers',           'ServiceProvider'),
        'TestCase':             ('laraflask.testing.test_case',        'TestCase'),
        'FeatureTestCase':      ('laraflask.testing.test_case',        'FeatureTestCase'),
        'UnitTestCase':         ('laraflask.testing.test_case',        'UnitTestCase'),
    }
    if name in _map:
        return _lazy(*_map[name])
    raise AttributeError(f"module 'laraflask' has no attribute '{name}'")
