Generate teaching comments and hints for this Go puzzle using the data below.

For each wrong move, explain:
1. What happens after the wrong move (the board consequence)
2. How the opponent punishes it (using the refutation PV)
3. Why the correct move is better

For the correct move, explain:
1. What the move achieves strategically
2. Why it is the vital point

For hints, provide exactly 3 tiers:
1. The technique name only
2. A reasoning hint that guides without revealing the answer
3. A coordinate hint using `{!xy}` SGF notation for the correct move's SGF coordinate

Use the teaching_signals data to inform your explanations. Pay attention to:
- `delta` and `score_delta` for how bad each wrong move is
- `refutation_pv` for the punishment sequence
- `refutation_type` for the nature of the punishment
- `log_policy_score` for how obvious/hidden the correct move is
- `policy_entropy` for how many plausible moves exist
