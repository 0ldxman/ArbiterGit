from ArbDatabase import DataManager


class Event:
    def __init__(self, source):
        self.source = source

    def get_source(self):
        return self.source


class EventHandler:
    def __init__(self, actors: list):
        self.actors = actors

    def handle(self, event: Event):
        raise NotImplementedError

    def __repr__(self):
        return f'{type(self)}({self.actors})'


class EventManager:
    def __init__(self):
        self.listeners = {}
        self.responses = []

    def listen(self, event_type:str, handler: EventHandler):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(handler)

    def unlisten(self, event_type:str, handler: EventHandler):
        if event_type in self.listeners and handler in self.listeners[event_type]:
            self.listeners[event_type].remove(handler)

    def trigger(self, event_type:str, event):
        for handler in self.listeners.get(event_type, []):
            responses = handler.handle(event)
            self.responses.extend(responses)