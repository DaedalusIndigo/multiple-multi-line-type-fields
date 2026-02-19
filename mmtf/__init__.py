from __future__ import annotations

import re, os, json
from pathlib import Path

from aqt import gui_hooks, reviewer, clayout, mw, utils
from .hooks import MMTF_hooks
from .dev_tools import *
from pprint import pprint

addon_path = mw.addonManager.addon_from_module(__name__)
resources_path = Path(mw.addonManager.addonsFolder()) / addon_path / "resources"

# Handle different card contexts (reviewer, card layout editor, card preview)
def on_card_will_show(html, card, card_kind):
   if card_kind == "reviewQuestion":
      html += """
      <script>
      function typeboxAnsPress(e) {
         if (!e.shiftKey && e.key === "Enter") {
            e.preventDefault();
            _typeAnsPress();
         }
      }
      </script>
      """

   return html
   
gui_hooks.card_will_show.append(on_card_will_show)

def to_dict(obj: Any):
   return obj.__dict__

def MMTF_getTypedAnswer(self: reviewer.Reviewer):
   self.web.evalWithCallback("""(() => {{
      var typeAnsInfo = {};
      var answers = [];
      document.querySelectorAll(".typeans").forEach((typeAns, i) => {{
         if (typeAnsInfo[i] != null) {{
            answers.push((new Function(`return ${{ typeAnsInfo[i].kind.get_answer }};`))()(typeAns, i));
         }}
      }})
      return JSON.stringify(answers);
   }})()
   """.format(json.dumps(self.typeAnsInfo, default=to_dict)),
   self._onTypedAnswer)

def MMTF_onTypedAnswer(self: reviewer.Reviewer, answers):
   print("RETRIEVED", answers)
   self.typedAnswer = [] if answers is None else (json.loads(answers) or [])
   self._showAnswer()

def is_in(l: list, element: Any):
   was = element in l
   if was: l.remove(element)
   return was

def MMTF_typeAnsQuestionFilter(self: reviewer.Reviewer, buf: str, is_example: bool = False) -> str:

   # compatibility
   buf = re.sub(r"\[\[typebox:(?P<field>[^\]]+)\]\]", (lambda match: f"[[type:{match.group('field')}]][multi]"), buf)

   self.typeAnsInfo = []
   default_styles: str = ""
   for match in self.typeAnsPat.finditer(buf):
      def replace_pattern(replacement: str) -> None:
         nonlocal buf
         buf = re.sub(self.typeAnsPat, replacement, buf, count=1)

      thisInfo = input_instance()
      self.typeAnsInfo.append(thisInfo)

      self._combining = True
      clozeIdx = None

      field = thisInfo.field = match.group("field")

      thisInfo.q_args = match.group("args") or ""
      thisInfo.q_args = re.split(r'[,\s]+', thisInfo.q_args)
      for arg in thisInfo.q_args[1:]:
         if arg[0:1] == "c" and arg[1:2] != "0" and arg[2:].isdigit():
            clozeIdx = arg[1:]
            thisInfo.q_args.remove(arg)
            break

      kind_name = thisInfo.q_args.pop(0)
      if kind_name is None or kind_name.strip() == "" or kind_name == "_":
         kind_name = "hybrid"

      strict = strict = is_in(thisInfo.q_args, "!s")

      try:
         thisInfo.kind = input_kinds._get(kind_name)
      except Exception:
         replace_pattern(f"(MMTF) Could not find input kind '{kind_name}'") # [TRANSLATION REMINDER]
         continue

      # if it's a cloze, extract data
      if field.startswith("cloze:"):
         # get field and cloze position [HOOK REMINDER]
         if clozeIdx is None:
            clozeIdx = self.card.ord + 1

         field = field.split(":")[1]
      if field.startswith("nc:"):
         thisInfo.a_args.append("nc")
         field = field.split(":")[1]
      
      if thisInfo.kind.on_render.question is not None:
         try:
            if callable(thisInfo.kind.on_render.question):
               thisInfo.kind.on_render.question(thisInfo, is_example)
         except Exception as e:
            replace_pattern(f"(MMTF) An exception occurred in executing the 'on_render' method of input kind '{kind_name}':<br>{type(str(e)).__name__}: {e}")
            continue

      # Check if preview
      if is_example:
         thisInfo.expected = thisInfo.kind.examples.expected.value
      else:
         for f in self.card.note_type()["flds"]:
            if f["name"] == field:
               thisInfo.expected = self.card.note()[field]
               if clozeIdx is not None:
                  # narrow to cloze
                  thisInfo.expected = self._contentForCloze(thisInfo.expected, clozeIdx)
                  
               break

      if thisInfo.expected == "" and not is_example: # empty field
         buf = re.sub(self.typeAnsPat, "", buf, count=1)
      elif thisInfo.expected is None: # no field match
         if clozeIdx:
            replace_pattern(utils.tr.studying_please_run_toolsempty_cards())
         else:
            replace_pattern(utils.tr.studying_type_answer_unknown_field(val=field))
         continue

      if thisInfo.kind is None:
         replace_pattern(f"(MMTF) Could not find input kind '{kind_name}'") # [TRANSLATION REMINDER]
         continue

      try:
         output = thisInfo.kind.qfmt.element(self, thisInfo.q_args, thisInfo.a_args)
         style = thisInfo.kind.qfmt.style

         p_found = ""
         for arg in thisInfo.q_args:
            if arg in thisInfo.kind.q_params:
               output, style = thisInfo.kind.q_params[arg](output, style, thisInfo)
               print("OOOO", arg, output)
            elif strict:
               p_found = arg
               break
         
         if p_found == "":
            replace_pattern(output + "\n<br>")
         else:
            replace_pattern(f"(MMTF) Could not find question-side parameter '{p_found}' of input kind '{thisInfo.kind.name}'")
            continue

         if style is not None and style.strip() != "":
            default_styles += style + "\n\n"

      except Exception as e:
         replace_pattern(f"(MMTF) An exception occurred in retrieving the element of input kind '{kind_name}':<br>{type(str(e)).__name__}: {e}")


   # [HOOK REMINDER]
   buf += """

   <!-- MMTF Default Styles -->
   <style>
   @layer {{
      {}
   }}
   </style>
   """.format(default_styles)

   print(buf)
   return buf

def MMTF_typeAnsAnswerFilter(self: reviewer.Reviewer, buf: str, is_example: bool = False) -> str:
   note = self.card.note()

   if not is_example:
      print("LOADED", self.typedAnswer)

   # compatibility
   buf = re.sub(r"\[\[typebox:(?P<field>[^\]]+)\]\]", (lambda match: f"[[type:{match.group('field')}]]"), buf)

   def replace_pattern(replacement: str) -> None:
      nonlocal buf
      re.sub(self.typeAnsPat, replacement, buf, count=1)

   outputs = []
   default_styles = "" 

   def repl(match, count = [0]):
      i = count[0]
      count[0] += 1

      thisInfo: input_instance = self.typeAnsInfo[i]
      thisInfo.provided = thisInfo.kind.examples.provided.value if is_example else self.typedAnswer[i]

      args = re.split(r'[,\s]+', match.group("args") or "")
      args.extend(thisInfo.a_args)
      thisInfo.a_args = args

      if thisInfo.kind.on_render.answer is not None:
         try:
            if callable(thisInfo.kind.on_render.answer):
               thisInfo.kind.on_render.answer(thisInfo, is_example)
         except Exception as e:
            replace_pattern(f"(MMTF) An exception occurred in executing the 'on_render' method of input kind '{thisInfo.kind.name}':<br>{type(str(e)).__name__}: {e}")


      compare_name = thisInfo.a_args.pop(0) if len(thisInfo.a_args) > 0 and thisInfo.a_args[0] != "" else "_"

      if compare_name in thisInfo.kind.compare_modes:
         thisCompare = thisInfo.compare = thisInfo.kind.compare_modes[compare_name]

         strict = is_in(thisInfo.a_args, "!s")
         do_compare = not is_in(thisInfo.a_args, "nc")

         output = thisCompare(thisInfo, combining = do_compare)
         style = thisInfo.kind.afmt.style

         for arg in thisInfo.a_args:
            if arg in thisInfo.kind.a_params:
               output, style = thisInfo.kind.a_params[arg](output, style, thisInfo, thisCompare)
            elif strict:
               return f"(MMTF) Could not find answer-side parameter '{arg}' of input kind '{thisInfo.kind.name}'"
         
         if style is not None and style.strip() != "":
            default_styles += style + "\n\n"

         return self.typeAnsInfo[i].kind.afmt.element(self, thisInfo.q_args, thisInfo.a_args, body = output if output else "(MMTF) Could not retrieve answer to compare")
      else:
         return f"(MMTF) Could not find comparison mode '{compare_name}' of input kind '{thisInfo.kind.name}'"
      
   buf = re.sub(self.typeAnsPat, repl, buf) + """
   <style>
   @layer {{ .typeans-comparison {{ font-family: monospace; text-align: center; }} {} }}
   </style>
   """.format(default_styles)

   print(buf)
   return buf

def MMTF_maybeTextInput(self: clayout.CardLayout, txt: str, type: str = "q"):
   if type == "q":
      r = self.pseudo_reviewer = pseudo_reviewer()
      r.card = self.rendered_card
      r.typeAnsPat = reviewer.Reviewer.typeAnsPat

      txt = MMTF_typeAnsQuestionFilter(r, txt, True)
      pprint(r.typeAnsInfo)
      txt += """
      <script>
      var typeAnsInfo = {};
      document.querySelectorAll(".typeans").forEach((typeAns, i) => {{
         if (typeAnsInfo[i] != null) {{
            var example = typeAnsInfo[i].kind.examples.provided;
            (new Function(`return ${{ example.make_read_only }};`))()(typeAns, i);
            (new Function(`return ${{ example.set_value }};`))()(typeAns, i, example.value);
         }}
      }})
      </script>
      """.format(json.dumps(r.typeAnsInfo, default=to_dict))
   else:
      txt = MMTF_typeAnsAnswerFilter(self.pseudo_reviewer, txt, True) 
   
   return txt
      
reviewer.Reviewer.typeAnsPat = re.compile(r"\[\[type:(?P<field>[^\]]+)\]\](?:\[(?P<args>[^\]]+)\])?")
reviewer.Reviewer.typeAnsQuestionFilter = MMTF_typeAnsQuestionFilter
reviewer.Reviewer.typeAnsAnswerFilter = MMTF_typeAnsAnswerFilter
reviewer.Reviewer._getTypedAnswer = MMTF_getTypedAnswer
reviewer.Reviewer._onTypedAnswer = MMTF_onTypedAnswer
clayout.CardLayout.maybeTextInput = MMTF_maybeTextInput