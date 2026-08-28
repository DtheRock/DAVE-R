# Triage: planned, expedited, emergency

Added in spec 1.0.0 to close the largest gap in the original framework.

## The problem this fixes

DAVE+R's discipline is "log first, enforce second." Both published scenarios open
with an attack already causing damage - 503s hitting paying customers, loyalty
accounts being drained - and then run 5 and 7 day shadow windows. In the
credential-stuffing case that means knowingly absorbing a week of account takeovers
to protect conversion.

That may well be the right call. The problem is the framework gave no way to *make*
that call. Emergency change appeared once, as a single line in Module D governance,
and never touched the lifecycle. A practitioner under real pressure either skips
DAVE+R entirely or follows it and eats avoidable losses.

## The three tracks

| Track | When | Shadow window | Approval | Backfill |
| :--- | :--- | :--- | :--- | :--- |
| `planned` | No harm accruing, or harm is tolerable and accepted in writing | Adapter default (7-14d) | Accountable owner | n/a |
| `expedited` | Harm accruing, containable, evidence obtainable fast | Adapter expedited (1-5d) | Accountable owner, explicit | Within adapter window |
| `emergency` | Active material harm, every hour costs | Hours, or none | Accountable owner + incident commander | Mandatory, adapter window |

Windows come from the adapter, not from this file: `min_shadow_days` per track.

## What the track buys and what it does not

An emergency track buys a **shortened shadow window**. It does not buy an exemption
from evidence. Gate E-7 blocks an emergency cycle from closing until the baseline,
the evasion analysis and the change record have been backfilled to the standard of a
planned cycle. The rush is a timing concession, not a governance one.

## The gate

D-6 fires when `harm_accruing` is true. If the team still chooses `planned`, the
accountable owner must sign an acceptance and the brief must state `harm_rate` - what
a day of not acting costs. This turns an implicit choice into an explicit, attributable
one, which is the entire point.

## How to ask

Do not ask "what triage track is this?" Nobody thinks in those terms mid-incident.
Ask:

> Is this causing damage right now, or is it a risk you are getting ahead of?

Then, if damage is happening:

> Roughly what does a day of not acting cost - in fraud losses, downtime, or
> customer impact?

You classify from the answers. Show the human the classification and the shadow
window it implies, and let them push back.

## The pressure case

When someone wants to skip Validate entirely, the useful move is not to refuse. It is
to name the trade: emergency track, shadow measured in hours, enforcement authorized
by the accountable owner, and a backfill obligation that the gates will enforce
whether or not anyone remembers. That is faster than arguing and it keeps the audit
trail intact.
