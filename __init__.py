from __future__ import annotations

import re, os, json
from pathlib import Path

from aqt import gui_hooks, reviewer, clayout, mw, utils
from .hooks import MMTF_hooks
from .dev_tools import *

addon_path = mw.addonManager.addon_from_module(__name__)
resources_path = Path(mw.addonManager.addonsFolder()) / addon_path / "resources"

# Handle different card contexts (reviewer, card layout editor, card preview)
def on_card_will_show(html, card, card_kind):
   card_template = card.note().note_type()['tmpls'][card.ord]

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
   """.format(json.dumps(self.typeAnsInfo, default=lambda o: o.__dict__)),
   self._onTypedAnswer)

def MMTF_onTypedAnswer(self: reviewer.Reviewer, answers):
   print("RETRIEVED", answers)
   self.typedAnswer = [] if answers is None else (json.loads(answers) or [])
   self._showAnswer()

def MMTF_typeAnsQuestionFilter(self: reviewer.Reviewer, buf: str) -> str:

   # compatibility
   buf = re.sub(r"\[\[typebox:(?P<field>[^\]]+)\]\]", (lambda match: f"[[type:{match.group('field')}]][multi]"), buf)

   self.typeAnsPat = re.compile(r"\[\[type:(?P<field>[^\]]+)\]\](?:\[(?P<args>[^\]]+)\])?")

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

      field = match.group("field")
      print(field)
      thisInfo.args = match.group("args") or ""
      thisInfo.args = re.split(r'[,\s]+', thisInfo.args)
      kind_name = thisInfo.args[0]
      if kind_name is None or kind_name.strip() == "":
         kind_name = "single"

      try:
         thisInfo.kind = getattr(input_kinds, kind_name)
      except Exception:
         replace_pattern(f"(MMTF) Could not find input kind '{kind_name}'") # [TRANSLATION REMINDER]
         continue

      # [HOOK REMINDER FOR CUSTOM INPUT PREFIXES]
      # if it's a cloze, extract data
      if field.startswith("cloze:"):
         # get field and cloze position [HOOK REMINDER]
         clozeIdx = self.card.ord + 1
         field = field.split(":")[1]
      if field.startswith("nc:"):
         thisInfo.args.append("nc")
         field = field.split(":")[1]

      for f in self.card.note_type()["flds"]:
         if f["name"] == field:
            thisInfo.expected = self.card.note()[field]
            if clozeIdx is not None:
               # narrow to cloze
               thisInfo.expected = self._contentForCloze(thisInfo.expected, clozeIdx)
               
            break

      if thisInfo.expected == "": # empty field
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
         replace_pattern(thisInfo.kind.qfmt.element(self, *thisInfo.args))
         style = thisInfo.kind.qfmt.style
         if style is not None and style.strip() != "":
            default_styles += style + "\n\n"

      except Exception as e:
         replace_pattern(f"(MMTF) An exception occurred in retrieving the element of input kind '{kind_name}:\n{type(str(e)).__name__}: {e}'")


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

def MMTF_typeAnsAnswerFilter(self: reviewer.Reviewer, buf: str) -> str:
   note = self.card.note()

   print("LOADED", self.typedAnswer)

   # compatibility
   buf = re.sub(r"\[\[typebox:(?P<field>[^\]]+)\]\]", (lambda match: f"[[type:{match.group('field')}]]"), buf)

   def replace_pattern(replacement: str) -> None:
      nonlocal buf
      re.sub(self.typeAnsPat, replacement, buf, count=1)

   outputs = []
   default_styles = ""
   for i, answer in enumerate(self.typedAnswer):
      thisInfo: input_instance = self.typeAnsInfo[i]
      thisInfo.provided = answer
      compare_name = thisInfo.args[1] if len(thisInfo.args) > 1 else ""
      thisCompare = thisInfo.kind.compare_modes[compare_name]
      if thisCompare:
         outputs.append(thisCompare(thisInfo, combining = ("nc" in thisInfo.args)))
         style = thisInfo.kind.afmt.style
         if style is not None and style.strip() != "":
            default_styles += style + "\n\n"
      else:
         outputs.append(f"(MMTF) Could not find comparison mode '{compare_name}' of input kind")

   def repl(match, count = [0]):
      i = count[0]
      return self.typeAnsInfo[i].kind.afmt.element(self, *thisInfo.args, body = outputs[i] if i < len(outputs) else "(MMTF) Could not retrieve answer to compare")
      
   buf = re.sub(self.typeAnsPat, repl, buf) + """
   <style>
   @layer {{ .typeans-comparison {{ font-family: monospace; text-align: center; }} {} }}
   </style>
   """.format(default_styles)

   print(buf)
   return buf

def MMTF_maybeTextInput(self, txt: str, type: str = "q"):
   if not ("[[type:" in txt or "[[typebox:"): return txt
      
   def typeansSingleRepl(match: re.Match) -> str:
      if type == "q":
         return "<center><input id='typeans' class='typeans typeans-single' type=text value='example' readonly></center>"
      
      return "<div class='typeans-comparison'>{}</div>".format(self.mw.col.compare_answer("example", "sample"))
   def typeansMultiRepl(match: re.Match) -> str:
      if type == "q":
         return '<center><textarea class="typeans typeans-multi" id=typeans readonly>this\nis\nan\nexample</textarea></center>'

      if match.group(2) == "contextual":
         return self.mw.col.compare_answer("this__is__an__example", "that__is__a__sample").replace("__", "<b>")
      else:
         result = []
         for comparison in [["this", "that"], ["is", "is"], ["an", "a"], ["example", "sample"]]:
            result.append(self.mw.col.compare_answer(comparison[0], comparison[1]))

         return '<div class="typeans-comparison"><code id=typeans>' + "<br>".join(result).replace("<br><span id=typearrow>&darr;</span><br>", "<span id=typearrow> → </span>").replace('<code id=typeans>', "").replace("</code>", "") + "</code></div>"
      
   return re.sub(r'\[\[typebox:([^\]]+?)\](?:\[([^\]]+?)\])?\]', typeansMultiRepl, re.sub(r"\[\[type:.+?\]\]", typeansSingleRepl, txt))
      

reviewer.Reviewer.typeAnsQuestionFilter = MMTF_typeAnsQuestionFilter
reviewer.Reviewer.typeAnsAnswerFilter = MMTF_typeAnsAnswerFilter
reviewer.Reviewer._getTypedAnswer = MMTF_getTypedAnswer
reviewer.Reviewer._onTypedAnswer = MMTF_onTypedAnswer
clayout.CardLayout.maybeTextInput = MMTF_maybeTextInput