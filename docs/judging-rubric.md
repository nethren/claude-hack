# Official judging rubric - AI & Aerospace Technology Track

Source: [original PDF](../references/airbus-track.pdf), physical pages 7-8
(rubric printed 1/2 and 2/2). These pages were visually checked because text
extraction includes hidden/overlapping text from an older layout. This document
uses the visible final rubric, not that extraction noise.

## Weights and scoring

Each criterion is scored from 1 to 5. Total weight is 100%.

| ID | Criterion | Weight | Maximum contribution |
|---|---|---:|---:|
| JR-01 | Problem realism | 20% | 20 |
| JR-02 | Technical soundness | 25% | 25 |
| JR-03 | Honest evaluation | 20% | 20 |
| JR-04 | Trust and traceability | 20% | 20 |
| JR-05 | Impact | 10% | 10 |
| JR-06 | Time discipline | 5% | 5 |

`Weighted score / 100 = sum((criterion score / 5) * criterion weight)`.
For example, 4/5 on technical soundness contributes 20/25 points.

Scale: 1 weak; 2 limited; 3 credible; 4 strong; 5 exceptional evidence.
Each project is evaluated by three judges. Score criteria separately. The brief
rewards sound restraint over presentation polish and asks where the system fails
and how its user would know. Earlier submission does not replace quality.

The separate hackathon-idea-evaluator skill's six scores out of 60 are a planning
aid. They are not this event's rubric, measured results, or winning probabilities.

## JR-01 - Problem realism (20%)

Question: does this solve a specific aerospace workflow problem?

Name the user, current process, and credible cost in time, money or risk. Explain
the selected challenge's constraints rather than aviation in general.

- Strong: credible user, narrow workflow and clear status quo.
- Weak: generic aviation chatbot or a solution searching for a problem.

Project evidence to prepare: a named operational role, one concrete disruption,
current coordination steps and the limits of the prototype's assumptions.

## JR-02 - Technical soundness (25%)

Question: does the prototype work with the right method for each task?

Show an end-to-end build. Use LLMs for reading and explanation; use solvers,
rules or statistics for scheduling, constraints and detection. Test beyond a
scripted demonstration.

- Strong: working inputs/outputs, explicit constraints and a sound LLM/non-LLM split.
- Weak: LLM-only legality checks, opaque risk scores or a hard-coded demo.

Project evidence to prepare: independent calls, parsed messages, deterministic
constraint results, successful and impossible inputs, and reproducible replay.

## JR-03 - Honest evaluation (20%)

Question: what was tested, against what baseline, and where does it fail?

State metrics, data and results. Label synthetic data and its limitations. Show
at least one case where the system is wrong, uncertain or declines, and explain
how the user knows.

- Strong: baseline, measured results and a visible failure with an explanation.
- Weak: success stories only, unsupported accuracy claims or hidden data limits.

Project evidence to prepare: defined scenarios, baseline comparison, validity and
agreement rates, latency/call/token measurements, and a visible failure case.
No results exist in this documentation commit.

## JR-04 - Trust and traceability (20%)

Question: can a qualified person verify the output before acting?

Trace claims to a document/revision/section, timestamped signal or applied rule.
Handle applicability and missing evidence. Keep the qualified person in control.

- Strong: checkable sources, visible uncertainty and clear refusal when needed.
- Weak: confident unsourced answers or claims to replace expert judgement.

Project evidence to prepare: source-row provenance, labelled operational overlays,
unchanged agent messages, applied rule IDs, plan versions and reviewable outcomes.

## JR-05 - Impact (10%)

Question: what improves over the current process, and by how much?

Compare to a stated baseline using relevant measures such as delay minutes,
supplier impact, retrieval quality or false alarms. Distinguish measurements from
estimates.

- Strong: credible before/after measure and realistic adoption constraints.
- Weak: large benefit claims without a baseline or with unstated assumptions.

Project evidence to prepare: modelled delay/preference outcomes under the same
constraints as the baseline. Fuel savings require a labelled fuel model; delay
minutes alone do not establish actual fuel reduction.

## JR-06 - Time discipline (5%)

Question: was the project submitted early and presented efficiently?

Earlier valid submission is better using the recorded submission time. Also
assess a focused presentation completed within three minutes. Give one combined
1-5 score.

- Strong: earlier submission and focused, complete presentation within three minutes.
- Weak: later submission and rushed, unfocused or over-time presentation.

The six-hour build window is user-provided context, not a timing rule printed in
this PDF. The submission procedure and exact deadline are not supplied here.
