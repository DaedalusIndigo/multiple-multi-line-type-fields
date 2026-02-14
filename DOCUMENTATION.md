# Documentation

## Introduction
Have you ever wanted to have a card that lets you type in both a word and its grammatical gender? Or perhaps you have a list of verb conjugations to memorize? Or you need to recite a speech? **Multiple Multi-Line Type Fields (MMTF)** may be the add-on for you! It adds the ability to display and grade multiple type-in-the-answer fields and even custom input kinds.

MMTF uses a method called "monkey patching" to modify Anki's source code: it directly overwrites some functions. Thus, if you have downloaded another add-on that tries to overwrite the same functions, either MMTF or the other add-on will succeed. MMTF is being built as a framework for other developers as well as users, so it is intended to be used as the sole "monkey patcher" that other add-ons can hook into.

## Creating a type field
If you didn't know, you can create a native type-in-the-answer field by simply including `{{type:FIELD}}` (where `FIELD` is the name of the desired text field) somewhere in both sides of a card. To learn more, please see the [official Anki manual](https://docs.ankiweb.net/templates/fields.html#checking-your-answer).

Under the hood, `{{type:FIELD}}` is replaced with `[[type:FIELD]]`. The latter is the syntax that MMTF has reappropriated. A general type field looks like this: `[[type:PREFIX:FIELD]][KIND ARGS]`. That looks a little complicated, so let's break that down.
- We first begin with a set of double brackets (`[[ ]]`). This is the *constructor*.
- Within the constructor, we then put `type:`. `type` lets the html filter know that we are creating a type-in-the-answer field. The colon (`:`) is used as a *delimiter* (gap) between specified settings. These settings are known as *prefixes*. MMTF supports all vanilla Anki prefixes (`nc`, `cloze`). Do not put spaces around the delimiters.
- Third, we enter the name of the text field belonging to the card's note type.
- Fourth, we can optionally specify an *input kind* and additional *arguments* with a new set of single brackets (`[ ]`) right outside the constructor. This set marks the *mutator*.
    - Terms inside the mutator can be separated by whitespace (`a b c`) or commas (`a, b, c` or `a,b,c`).
    - The first term is always the name of the input kind. The second term is always the name of the compare mode.
    - If the constructor has no mutator (`[[type:FIELD]]`), or if the mutator is empty (`[[type:FIELD]][]`), the input kind is assumed to be `single`.
    - MMTF collects mutator data only from the front side of the card, so it is best to not have one at all on the back. Do not forget to use the constructor on both sides!

There is also `[[typebox:FIELD]]` instead of `[[type:FIELD]][multi]` to maintain compatibility with cards based on syntax used by [Multi-Line Type Answer Box - 2](https://ankiweb.net/shared/info/1018107736).

## Using input kinds
Input kinds have three main attributes: format, answer retrieval, and compare modes. Format determines how inputs appear. Answer retrieval tells MMTF how to get typed answers from visual elements before the card is flipped. Compare modes tell MMTF how to grade those answers. It is customary that `_` represents the default compare mode of an input kind.

There are two built-in input kinds: `single` and `multi`.
- `single` replicates the functionality of the native Anki type field. It is displayed as an HTML `input` element of `type` `"text"`. You can only type one line of text.
    - `_` is its only compare mode. It  reuses vanilla Anki grading.

- `multi` is displayed as an HTML `textarea` element. You can type multiple lines of text and break lines with `Shift + Enter`.
    - `_` compares the expected and provided text line-by-line, splitting them with a `→` symbol. This is best for a clean list.
    - `delimited` compares the expected and provided text character-by-character, replacing line-breaks with an uncommon delimiter (`__@MMTF$__`) to prevent Anki from stripping them. This is best for a textual excerpt or code snippet.