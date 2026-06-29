"""Model lifecycle events."""

from laraflask.events.event import Event


class ModelCreating(Event):
    def __init__(self, model=None): self.model = model

class ModelCreated(Event):
    def __init__(self, model=None): self.model = model

class ModelUpdating(Event):
    def __init__(self, model=None): self.model = model

class ModelUpdated(Event):
    def __init__(self, model=None): self.model = model

class ModelDeleting(Event):
    def __init__(self, model=None): self.model = model

class ModelDeleted(Event):
    def __init__(self, model=None): self.model = model

class ModelSaving(Event):
    def __init__(self, model=None): self.model = model

class ModelSaved(Event):
    def __init__(self, model=None): self.model = model
