from __future__ import annotations

from aqt import gui_hooks, reviewer, clayout, mw, utils

from dataclasses import dataclass
from typing import Callable
import re, os, json

class Hook:
    def __init__(self, *, args: list[str] | None = None, doc: str | None = None):
        self._handlers: list[function] = []
        self._args = args
        self.__doc__ = doc

    def append(self, fn: Callable):
        self._handlers.append(fn)

    def remove(self, fn: Callable):
        if fn in self._handlers: self._handlers.remove(fn)

    def count(self):
        return len(self._handlers)
    
    def __call__(self, *args):
        if self._args is None or len(self._args) == 0:
            for fn in list(self._handlers):
                fn(*args)
        else:
            if len(args) != len(self._args): raise ValueError(f"Hook requires {len(self._args)} argument(s)")

            for fn in list(self._handlers):
                args = fn(*args)
                if len(args) != len(self._args): raise ValueError(f"Hook requires {len(self._args)} argument(s)")

            return args


#Actual hooks
@dataclass
class MMTF_hooks:
    will_compare_answer_list = Hook(
        args=["answer_list", "card_kind"],
        doc = """
        Fires after answers have been collected before looping through them.

        Args:
            answer_list: [{
                field: str = name of field
                value: str = typed value
                kind: str = input kind (of MMTFF_dev_tools.input_kinds)
                compare_mode: str = comparison method of the input kind
            }]
            card_kind: str
        """
    )
    will_compare_answer = Hook(
        args=["answer", "card_kind"],
        doc = """
        Fires before answer is graded.

        Args:
            answer: {
                field: str = name of field
                value: str = typed value
                kind: str = input kind (of MMTFF_dev_tools.input_kinds)
                compare_mode: str = comparison method of the input kind
            }
            card_kind: str
        """
    )