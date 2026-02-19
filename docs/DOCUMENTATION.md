# Documentation

## Introduction
Have you ever wanted to have a card that lets you type in both a word and its grammatical gender? Or perhaps you have a list of verb conjugations to memorize? Or you need to recite a speech? **Multiple Multi-Line Type Fields (MMTF)** may be the add-on for you! It adds the ability to display and grade multiple type-in-the-answer fields and even custom input kinds.

MMTF uses a method called "monkey patching" to modify Anki's source code: it directly overwrites some functions. Thus, if you have downloaded another add-on that tries to overwrite the same functions, either MMTF or the other add-on will succeed. MMTF is being built as a framework for other developers as well as users, so it is intended to be used as the sole "monkey patcher" that other add-ons can hook into.

For this documentation, "native" refers to base Anki, and "built-in" refers to base MMTF.

<br>

## Creating a Type Field
If you didn't know, you can create a native type-in-the-answer field by simply including `{{type:FIELD}}` (where `FIELD` is the name of the desired text field) somewhere in both sides of a card. To learn more, please see the [official Anki manual](https://docs.ankiweb.net/templates/fields.html#checking-your-answer).

Under the hood, `{{type:FIELD}}` is replaced with `[[type:FIELD]]`. Consequently, MMTF supports both styles. This documentation will use the former to more closely resemble native Anki.

A general type field *constructor* looks like this: `{{type:PREFIX:FIELD}}[KIND Q-ARGS]` (front) and `{{type:PREFIX:FIELD}}[COMPARE-MODE A-ARGS]` (back). That looks a little complicated, so let's break that down.
- For both sides, we begin with a set of double braces (`{{ }}`) or brackets (`[[ ]]`). This is the *directive*.
- Within the directive, we then put `type:`. `type` lets the html filter know that we are creating a type-in-the-answer field. The colon (`:`) is used as a delimiter between *prefixes*. All prefixes are the same as in native Anki. Do not put spaces around the delimiters.
    - Because MMTF has added no new elements to the directive, it functions without error when the add-on is deactivated.
    - `nc`: disables character combining when grading. This allows diacritics (accent marks) to be ignored.
    - `cloze`: narrows the expected answer to an occlusion corresponding to the card order as part of cloze deletion.

<br>

- Third, we enter the name of the text field belonging to the card's note type.
- Fourth, we can optionally specify additional *arguments* with a new set of single brackets (`[ ]`) right outside the directive. This set holds the *specification* (or "spec").
    - Arguments can be separated by whitespace (`a b c`) or commas (`a, b, c` or `a,b,c`).
    - **On the front**: the first argument is always the name of the input kind. Custom input kinds can implement other argument keywords (*parameters*) that affect the front view.
    - **On the back**: the first argument is always the name of the compare mode, the function that grades your answer. Similarly, custom input kinds can implement their own parameters that affect the grading or back view.
    - If a directive has no spec (`{{type:FIELD}}`), or if a spec is empty (`{{type:FIELD}}[ ]`), the input kind and the compare mode are assumed to be `hybrid` and `_`, respectively. `_` also works as shorthand for `hybrid`.

<br>

You may also use `[[typebox:FIELD]]` instead of `{{type:FIELD}}[multi]` to maintain compatibility with cards based on syntax used by [Multi-Line Type Answer Box - 2](https://ankiweb.net/shared/info/1018107736). However, it is recommended that you use MMTF's directive-spec syntax.

<br>

## Using Input Kinds
Input kinds have three main attributes: format, answer retrieval, and compare modes. Format determines how inputs appear. Answer retrieval tells MMTF how to get typed answers from visual elements before the card is flipped. Compare modes tell MMTF how to grade those answers. It is necessary that the default compare mode be named `_`.

There are three built-in input kinds: `single`, `multi`, and `hybrid`.
- `single` replicates the functionality of the native Anki type field. It is displayed as an HTML `input` element of `type` `"text"`. You can only type one line of text.
    - One compare mode:
        - `_`: reuses vanilla Anki grading.
    - One answer-side parameter:
        - `linear`: removes line breaks between expected and provided text, flowing left to right instead of up to down.

- `multi` is displayed as an HTML `textarea` element. You can type multiple lines of text and break lines with <kbd>Shift + Enter</kbd>.
    - Two compare modes:
        - `_`: compares the expected and provided text line-by-line, splitting them with a `→` symbol. This is best for a clean list.
        - `delimited`: compares the expected and provided text character-by-character, replacing line-breaks with an uncommon delimiter (`__@MMTF$__`) to prevent Anki from stripping them. This is best for a textual excerpt or code snippet.

- `hybrid` is a *pseudo-kind*. If the expected answer has any line breaks, it converts itself to `multi`. If not, it becomes `single`.
    - You may use any compare mode or parameters from `single` or `multi`.

There are also some parameters that belong to all type fields. For the following, "q" means "question-side," and "a" means "answer-side."
- `c[NUMBER]` (q): narrows the `expected` answer to cloze deletion of number `[NUMBER]` instead of the card order number.
- `!s` (q, a): enables "strict mode," which throws an error if met with an invalid argument.

<br>

## Styling Type Fields
Once your type fields are functional, you might wonder how you could get them to fit your card type's aesthetic. Fortunately, since type fields are rendered as HTML elements, they can be styled with CSS, just like the rest of the card! Below is a list of selectors that may be used.
- Native selectors:
    - `#typeans`: both the type field (front) and the comparison (back).
    - `.typeGood`: correctly placed or typed characters.
    - `.typeMissed`: missing or skipped characters.
    - `.typeBad`: incorrectly placed or typed characters.
    - `#typearrow`: the arrow pointing from the provided to the expected answer in the comparison.

- MMTF selectors:
    - `.typeans`: only the type field (front).
        - `.typeans-single`: same as `.typeans` but exclusive to the `single` input kind.
        - `.typeans-multi`: same as `.typeans` but exclusive to the `multi` input kind.

    - `.typeans-comparison`: the `div` element containing the comparison (back).
        - `.typeans-comparison-single`: same as `.typeans-comparison` but exclusive to the `single` input kind.
        - `.typeans-comparison-multi`: same as `.typeans-comparison` but exclusive to the `multi` input kind.

<br><br>


# Developer Guide

## Preface
Now that you know how to use built-in input kinds and parameters, you may want to create your own. This can be done by integrating a custom add-on with MMTF's public systems. If you are new to developing Anki add-ons, I suggest you first look at the [add-on writing guide](https://addon-docs.ankiweb.net/).

<br>

## Creating an Input Kind
W.I.P.