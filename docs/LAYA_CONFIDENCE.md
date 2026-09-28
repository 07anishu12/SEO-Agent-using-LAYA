# Laya confidence contract

Inspected installed `laya-mlx==0.2.0`, `laya_mlx/agent.py` and `common.py`.
All ten SEO questions are `choice` questions evaluated by the same local
checkpoint (`aac6fef/laya-mlx`); these are question outputs, not ten separately
trained SEO classifiers.

For each question, the runtime divides option logits by the configured
temperature, applies softmax, and chooses `argmax(p)`. Its `confidence` field is
**1 − H(p)/log(number_of_options)**: normalized Shannon entropy reduction. It
is not the probability of the chosen option, nor a top-two margin, nor measured
SEO correctness. The selected option probability is
`answer['probabilities'][answer['choice']]`. Both quantities must be retained.
The nested `action.act_probability` is the model's separate act head; it is
not the answer to SEOJEV's `action` question and must not gate SEO work orders.

Thus `verdict.choice='real_issue', confidence=0.0007` is mathematically
consistent: probabilities approximately 0.5155/0.4845 give entropy confidence
0.0007. It represents an almost tied binary choice, not 0.07% probability of
`real_issue`. Using category entropy as validity confidence conflates two
different questions and suppresses valid verdicts for uncertain categories.

The runtime validates positive finite temperatures and clamps them to
[0.5, 5]. Temperature changes the probability distribution/entropy, but a
positive scale does not change argmax. The shipped warning identifies
`choice:11+ = 0.1006`, applied as 0.5. Current questions use 2, 3, 4, or 8
options, so that warning does not affect any current SEO question. Preserve
the warning and record raw/applied temperatures; do not suppress it or change
the checkpoint. If questions later use an affected bucket, its probabilities
must be treated as uncalibrated.

Reproduce measurement:
`.venv/bin/python3 scripts/laya_probe.py --count 200`.
The probe directly calls the installed MLX runtime on real database evidence,
bypassing SEOJEV's fallback-prone analyzer and all caches. Full answers,
probabilities, inputs, checkpoint identity, and summary statistics are written
to `reports/laya_probe.json`. No decision thresholds have been changed before
this measurement.

## Measured 200-candidate probe

Checkpoint revision: `20aed815fc6acde75733882e7ec0e3f28aeb9717`.
All 200 predictions completed; no inference errors. The table reports selected
option probabilities (min / median / p90 / max):

| Question | Min | Median | p90 | Max |
|---|---:|---:|---:|---:|
| verdict | .5767 | .8658 | .9272 | .9543 |
| category | .2267 | .31895 | .4005 | .8731 |
| severity | .4264 | .5623 | .6460 | .6781 |
| scope | .3946 | .73515 | .8642 | .9245 |
| root_cause | .3640 | .43095 | .5112 | .5820 |
| canonical_indexability | .3716 | .45285 | .5231 | .5797 |
| content_assessment | .3949 | .5509 | .6058 | .6458 |
| cannibalization | .3466 | .4944 | .6642 | .7467 |
| internal_linking | .5004 | .54775 | .6401 | .7025 |
| action | .2606 | .89925 | .9593 | .9866 |

Verdict entropy median is .43115; category entropy median is .18095. The model
chose real_issue for all sampled opportunities, so this is **not a labeled
noise evaluation** and cannot establish accuracy or guarantee a noise fraction.
All severity outputs were medium. These limitations must remain visible; do
not manufacture a noise verdict to satisfy a target acceptance percentage.

## Routing policy

Decision confidence is `min(P(chosen verdict), P(chosen action))`. Keep the
two component probabilities, every head's entropy confidence, and complete
probability distributions. Do not multiply probabilities: no independence
assumption is supported by this probe.

Config defaults: verdict minimum **.60**, action minimum **.50**, auto-accept
minimum for both **.90**. The .60 verdict boundary excludes the observed
near-tie tail (.5767 minimum), requiring at least a .20 binary margin. The .50
action boundary excludes the observed uncertain .2606 tail and requires a
majority over all other actions combined. .90 is near the measured action
median (.89925) and above the verdict median (.8658), reserving auto-accept
for jointly concentrated answers. These are conservative routing thresholds,
not calibrated probabilities of SEO correctness. They are explicit policy
choices informed by this measured distribution, not learned accuracy cutoffs.

Noise verdicts always suppress. Real issues below either minimum suppress;
the remaining real issues route to HUMAN_REVIEW unless both probabilities
meet .90. Both HUMAN_REVIEW and AUTO_ACCEPT flow into work orders. Configured
worker error-rate limit defaults to **0**, consistent with zero failures in
the probe; malformed heads, persistence failures, and incomplete queues are
fatal regardless of a nonzero allowed inference error rate.

Applying this policy to the probe yields 41 AUTO_ACCEPT, 125 HUMAN_REVIEW,
and 34 SUPPRESS (all 34 have action probability below .50; two also have
verdict probability below .60). None is relabeled as noise.
