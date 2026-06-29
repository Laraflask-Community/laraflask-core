"""Framework events - Request, User, Job, Message events."""

from laraflask.events.event import Event


class RequestReceived(Event):
    def __init__(self, request=None): self.request = request

class ResponseSent(Event):
    def __init__(self, request=None, response=None):
        self.request = request
        self.response = response

class UserRegistered(Event):
    def __init__(self, user=None): self.user = user

class UserLoggedIn(Event):
    def __init__(self, user=None): self.user = user

class UserLoggedOut(Event):
    def __init__(self, user=None): self.user = user

class JobProcessing(Event):
    def __init__(self, job=None): self.job = job

class JobProcessed(Event):
    def __init__(self, job=None): self.job = job

class JobFailed(Event):
    def __init__(self, job=None, exception=None):
        self.job = job
        self.exception = exception

class MessageSending(Event):
    def __init__(self, message=None): self.message = message

class MessageSent(Event):
    def __init__(self, message=None): self.message = message
