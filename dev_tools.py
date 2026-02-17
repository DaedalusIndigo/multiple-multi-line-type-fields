from __future__ import annotations

from aqt import gui_hooks, mw
from .hooks import MMTF_hooks

from enum import Enum
import dataclasses
from dataclasses import dataclass
from typing import Callable, Any

@dataclass
class card_format:
    _element: str | Callable
    style: str | None = None
    
    def element(self, context, q_args, a_args, body=None) -> str:
        return self._element(context, q_args, a_args) if callable(self._element) else self._element.format(context, q_args, a_args, comparison=body)

@dataclass
class example:
    value: str
    set_value: str = "(typeAns, i, value) => {{ typeAns.value = value; }}" # Must be a string expressed as a JavaScript function
    make_read_only: str = "(typeAns) => {{ typeAns.readOnly = true; }}"

class example_list:
    def __init__(self, expected: example | str, provided: example | str):
        self.expected = expected if isinstance(expected, example) else example(expected)
        self.provided = provided if isinstance(provided, example) else example(provided)

class input_kind:
    def __init__(self, *, name: str, qfmt: card_format, afmt: card_format, compare_modes: dict[str, Callable], q_params: dict[str, Callable] = {}, a_params: dict[str, Callable] = {}, examples: list[str] | example_list, get_answer: str | None = "(typeAns) => typeAns.value"):
        self.name: str = name
        self.qfmt: card_format = qfmt
        self.afmt: card_format = afmt
        self.compare_modes: dict[str, Callable] = compare_modes
        self.q_params: dict[str, Callable] = q_params
        self.a_params: dict[str, Callable] = a_params
        self.examples: example_list = examples if examples is example_list else example_list(*examples)
        self.get_answer: str = get_answer # Must be a string expressed as a JavaScript function with a single HTMLElement parameter

@dataclass
class input_instance:
    kind: input_kind | None = None
    field: str | None = None
    expected: str | None = None
    provided: str | None = None
    q_args: list[str] = dataclasses.field(default_factory=list)
    a_args: list[str] = dataclasses.field(default_factory=list)

class pseudo_reviewer:
    pass

linebreak = "__@MMTF#__" # needs to be unlikely value

def compare_single(thisInfo: input_instance, *, combining: bool = True):
    return mw.col.compare_answer(thisInfo.expected, thisInfo.provided, combining)

def compare_multi_delimited(thisInfo: input_instance, *, combining: bool = True):
    provided = thisInfo.provided.replace("\n", linebreak)
    expected = thisInfo.expected.replace("\n", linebreak).replace("<br>", linebreak)
    return mw.col.compare_answer(expected, provided, combining).replace(linebreak, "<br>")

def compare_multi_byline(thisInfo: input_instance, *, combining: bool = True):
    comparison = []
    provided = thisInfo.provided.splitlines()
    expected = thisInfo.expected.replace("<br>", "\n").splitlines()
    for i in range(max(len(expected), len(provided))):
        e_line = expected[i] if i < len(expected) else ""
        p_line = provided[i] if i < len(provided) else ""
        comparison.append(mw.col.compare_answer(e_line, p_line, combining))

    return "<code id=typeans>" + "<br>".join(comparison).replace('<br><span id=typearrow>&darr;</span><br>', '<span id=typearrow> → </span>').replace("<code id=typeans>", "").replace("</code>", "") + "</code>"

def parameter_single_linear(output: str, style: str, thisInfo: input_instance, comparison: Callable):
    return output.replace("<br><span id=typearrow>&darr;</span><br>", "<span id=typearrow> → </span>"), style

@dataclass
class input_kinds:
    single = input_kind(
        name = "single",
        qfmt = card_format(
            '<input class="typeans typeans-single" id="typeans" type="text" onkeydown="_typeAnsPress(event);">',
            '.typeans-single {font-family: "Arial"; font-size: 20px; margin: auto;}'
        ),
        afmt = card_format("<div class='typeans-comparison typeans-comparison-single'>{comparison}</div>"),
        compare_modes = {
            "_": compare_single
        },
        a_params = {
            "linear": parameter_single_linear
        },
        examples = ["sample", "example"]
    )
    multi = input_kind(
        name = "multi",
        qfmt = card_format(
            '<textarea class="typeans typeans-multi" id="typeans" onkeydown="typeboxAnsPress(event);"></textarea>',
            '.typeans-multi {font-family: "Arial"; font-size: 20px; margin: auto; height: 300px; resize: none;}'
        ),
        afmt = card_format("<div class='typeans-comparison typeans-comparison-multi'>{comparison}</div>"),
        compare_modes = {
            "_": compare_multi_byline,
            "delimited": compare_multi_delimited
        },
        examples = ["that\nis\na\nsample", "this\nis\nan\nexample"]
    )