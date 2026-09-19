"""Treatment: the same browser agent with a small language-model chooser."""

from jev_ultrafast.agent import Agent as BrowserAgent

from .model import choose


class Agent(BrowserAgent):
    def __init__(self, url, goals, **kwargs):
        super().__init__(url, goals, chooser=choose, **kwargs)
