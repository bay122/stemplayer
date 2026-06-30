from abc import ABC, abstractmethod


class AIProvider(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        ...

    @property
    @abstractmethod
    def supports_web_search(self) -> bool:
        ...

    @abstractmethod
    def chat_completion(
        self,
        prompt: str,
        model: str,
        api_key: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 2500,
        use_web_search: bool = False,
        timeout: tuple[int, int] = (20, 300),
    ) -> str:
        ...

    @abstractmethod
    def format_error(self, status_code: int, response_text: str) -> str:
        ...
