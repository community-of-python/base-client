from typing import TypeVar

import httpx
import pydantic


T = TypeVar("T")


def response_to_model(*, model_type: type[T], response: httpx.Response) -> T:
    return pydantic.TypeAdapter(model_type).validate_python(response.json() if response else None)
