# Narrative discipline

Applies ONLY to the narrative JSON prose fields: subject, tldr, volume_driver,
key_wins, key_updates, next_steps, reg_int, reg_bd, ecosystem, product_shipped,
product_dev. Never rewrite a figure, a WoW %, a goal string, or a table cell to
satisfy anything below. Numbers come from the data JSON and are not editable here.

This is a leadership summary. It exists to say what changed, why, and who owns
the next move. The reader already has the dashboard.

## 1. Volume driver (mandatory every week, never omitted)

Every report answers four things about trading volume:

1. Direction and magnitude. Taken from the data JSON, including the organic vs
   non-organic split. Never editorialized.
2. Why. The cause of the move.
3. The fix, with a named owner.
4. By when.

Rules for the "why":

- A cause may only be stated if it has a source: a Slack permalink, a meeting
  note, or a named person who said it. Cite it in the candidates block.
- If no sourced cause exists, write "Cause unconfirmed" and name who is
  investigating. Never infer a cause from the numbers alone. A correlation in the
  data is not a cause.
- Separate primary from contributing causes. Do not stack them as equals.
- If the fix has no ETA, write "ETA needed from <owner>" rather than omitting the
  field or inventing a date.

Volume down and unexplained is the worst outcome. Volume down with a cause, an
owner, and a date is a complete answer even when the news is bad.

## 2. The read (human-written, never generated)

The top block is written by Matt. The routine emits it as a placeholder:

  [MATT: the read — what mattered most this week and why]

Never fill this in. Never paraphrase the TLDR into it. Never generate a
substitute. If it ships as a placeholder, that is the correct failure: it is
visible and it is honest. Generated judgment is worse than absent judgment,
because the reader cannot tell it is hollow.

To support it, emit a candidates block above the read (see section 5). The
routine's job is retrieval and shortlisting. The judgment is human.

## 3. Bullet discipline

Every bullet carries a named owner and a date, or it gets cut. "Coming soon",
"in progress", "being validated", "refresh coming", "tightening criteria" are
not updates. Name who ships what by when, or drop the line.

Wins are shipped outcomes. A signed-pipeline count, a subsidized buy, or a
meeting held is not a win. If there is no real win, write "No wins this week"
rather than promoting a status line into the Key Wins slot.

Lead with impact, not activity. "Shipped X" is activity. "Shipped X, which moved
Y" is impact. If a shipped item moved no number, say so plainly or cut it.

Placeholders stay placeholders. If a source feed is missing, emit the
[MATT: ...] placeholder unchanged. Never write prose to fill an empty section.

## 4. Scrub before it ships

Cut on sight:

- Vague force words: primed, poised, strong, robust, significant, momentum,
  traction, seamless, unlock, elevate, leverage, transform. Each one marks a
  place a specific was avoided. Replace with the number, or cut the clause.
- "It's not just X, it's Y" and its cousins.
- Triads. Two real specifics beat three rhythmic abstractions.
- Hedges: aims to, designed to, is expected to, may, typically, often.
- Openers and filler: "In today's...", "Notably,", "Importantly,", rhetorical
  questions, "In conclusion".

Call a thing by one name. Pick Doma, or the protocol, or the platform, and reuse
it in every bullet. Cycling synonyms for one thing is the strongest machine tell
there is. Repetition of the right word reads human.

Write short and uneven. One long clause followed by a four-word landing beats
eight sentences of even length.

Fix by subtraction. Deleting a hollow line is the fix. Replacing it with a
better-written hollow line is the same bug repeating.

## 5. Candidates block (working aid, deleted before send)

Emit at the very top, clearly marked as internal scratch. Purpose: give Matt the
shortlist so he can write the read without re-deriving the week.

- Diff vs last week's report: what statuses changed, what numbers crossed a
  threshold, what is newly present or newly absent. Things mostly do not change
  week to week, so the diff IS the shortlist.
- Metric moves ranked by magnitude, each with the organic vs non-organic split
  already attributed.
- Candidate causes, quoted with a Slack permalink or meeting-note link. Label
  each as unconfirmed. Do not rank them by plausibility; that is Matt's call.
- Exec questions asked this week: any thread where Fred, Inder, or Bob asked
  about a metric. Quote and link.
- Shipped items that moved a number, separated from shipped items that did not.

## 6. Self-check before emitting

Re-read the narrative fields once, cold, asking only: would a savvy reader call
this mechanical? If a bullet would still read true with a competitor's name
pasted in, it says nothing. Cut it.

Then confirm: is the volume driver complete with cause, owner, and date? Is the
read still a placeholder rather than something generated? If either fails, fix
before emitting.
