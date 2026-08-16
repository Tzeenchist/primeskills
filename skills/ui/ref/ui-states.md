# The five states

Every component a person interacts with has five. A design that describes only
the last one is a mockup.

| state | the question it answers | failure when skipped |
|---|---|---|
| **empty** | there is nothing yet — what now? | the user sees a blank area and assumes it broke |
| **loading** | something is happening | the user clicks again, and again |
| **error** | it failed — what can I do? | "something went wrong" and a dead end |
| **partial** | some of it arrived | half a screen presented as if whole |
| **success** | it worked | — |

## Empty teaches

An empty state says what would be here and how to put something here. It is the
one screen every new user sees, so it does more onboarding than the onboarding.
"No results" is not an empty state; "No invoices yet — create one" is.

## Loading is honest

Show progress where the wait has a length, a placeholder where it does not.
Never block the whole screen for a change that touches one row. If the wait can
exceed a few seconds, say what is happening.

## Error is actionable

Three parts: what happened, why if you know, what the user can do next. A retry
that repeats the same failing call is not an action. Never show a stack trace,
never show an internal identifier alone.

## Partial is the forgotten one

Some rows loaded, one widget failed, the second page is missing. Decide whether
the component degrades or refuses. Both are valid; silently showing incomplete
data as complete is not.

## Keyboard

- Every interactive element is reachable by tab, in reading order.
- Enter activates, escape closes, and focus returns somewhere sensible after a
  dialog closes or an item is deleted.
- Focus is visible. Removing the outline without replacing it breaks the page
  for anyone not using a pointer.
- Nothing is reachable only by hover.

## Contrast and targets

Text meets contrast against its actual background, including inside states you
built later. Touch targets are large enough to hit without aiming. Both come
from the design system's tokens; a one-off value is a finding.
