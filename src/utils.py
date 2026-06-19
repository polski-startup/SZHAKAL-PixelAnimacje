import time
from functools import wraps
from typing import Callable, TypeVar

T = TypeVar("T")


def retry(max_attempts: int = 3, base_delay: float = 5.0) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args, **kwargs) -> T:
            last_exc: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < max_attempts - 1:
                        wait = base_delay * (2 ** attempt)
                        print(f"  [retry {attempt + 1}/{max_attempts}] {type(exc).__name__}: {exc} — czekam {wait:.0f}s")
                        time.sleep(wait)
            assert last_exc is not None
            raise last_exc
        return wrapper
    return decorator
