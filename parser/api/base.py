from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseAPI(ABC):
    @abstractmethod
    def request(
        self,
        method: str,
        params: Optional[dict] = None,
    ) -> dict[str, Any]:
        pass

