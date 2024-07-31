from ArbDatabase import DataManager, DataModel, DataDict
from ArbUIUX import ArbEmbed, SuccessEmbed, ErrorEmbed


class Response:
    def __init__(self, success: bool = False, message: str = None, title: str = None):
        self.success = success
        self.message = message if message is not None else 'Нет описания'
        self.title = title if title is not None else 'Ответ'

    def get_embed(self) -> SuccessEmbed | ErrorEmbed:
        if self.success:
            return SuccessEmbed(title=self.title, desc=self.message)
        else:
            return ErrorEmbed(title=self.title, desc=self.message)

    def to_dict(self):
        return self.get_embed().to_dict()

    def __str__(self):
        return f'# {self.title}\n{self.message}'

    def __repr__(self):
        return f'Response(success={self.success}, message="{self.message}")'


class ResponsePool:
    def __init__(self, responses: list[Response] | Response):
        if isinstance(responses, list):
            self.responses = responses
        elif isinstance(responses, Response):
            self.responses = [responses]

    def get_embeds(self) -> list[ErrorEmbed | SuccessEmbed]:
        return [response.get_embed() for response in self.responses if response is not None]

    def __str__(self):
        return '\n'.join([str(response) for response in self.responses if response is not None])