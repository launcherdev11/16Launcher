import asyncio
import logging
import multiprocessing
from collections.abc import Callable, Coroutine
from multiprocessing.context import Process
from threading import Lock as TLock
from threading import Thread
from typing import Any


def dedicated(f: Callable[..., Any]) -> Thread:
    def wrapper(*args: tuple[Any, ...], **kwargs: dict[str, Any]) -> Thread:
        t = Thread(target=f, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()
        return t

    return wrapper


def dedicate(
    func: Callable[..., Any], *args: tuple[Any, ...], **kwargs: dict[str, Any],
) -> Thread:
    t = Thread(target=func, args=args, kwargs=kwargs)
    t.daemon = True
    t.start()
    return t


def adedicate(func: Coroutine[Any, Any, Any]) -> None:
    asyncio.run(func)


class Mutex:
    def __init__(self) -> None:
        self.tlock = TLock()

    def lock(self) -> None:
        self.tlock.acquire(True)

    def unlock(self) -> None:
        self.tlock.release()

    def sync(self) -> None:
        self.lock()
        self.unlock()


def pdedicate(func: Callable[..., Any]) -> multiprocessing.Process:
    def wrapper(*args: tuple[Any, ...], **kwargs: dict[str, Any]) -> Process:
        p = multiprocessing.Process(target=func, args=args, kwargs=kwargs)
        p.daemon = True
        p.start()
        return p

    return wrapper


__logged_level = 0


def logged(func: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args: tuple[Any, ...], **kwargs: dict[str, Any]) -> Any:
        global __logged_level
        logging.debug(" " * 4 * __logged_level + f"Running {func.__name__}")
        __logged_level += 1
        r = func(*args, **kwargs)
        __logged_level -= 1
        logging.debug(" " * 4 * __logged_level + f"Finished {func.__name__}")
        return r

    return wrapper
