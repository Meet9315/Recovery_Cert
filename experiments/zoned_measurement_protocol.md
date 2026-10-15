# E18: scoped attribution, workload calibration and matched baseline characterization

15 October 2026. Freeze source/tests/this protocol before collection. E17's two-set/400-arrival pilot and negative/parity observations are already known and remain immutable. No distinct PRISM candidate exists. This delivery measures conventional behavior and collector adequacy; it cannot earn novelty or automatically pass the original candidate performance gates.

## Fixed configuration and sequence

Use `python -m prism_c.zoned_measure <profile|calibrate|confirm> --root <fresh-runtime-root> --output <fresh-evidence-directory>`. Confirmation additionally requires `--calibration <calibration-output>/manifest.json`. All paths must be new except the read-only calibration input. Runtime stores go under ignored `tmp/`; manifests and immutable per-window JSON shards are tracked. Each shard has a SHA-256 digest. Save failures/insufficient attempts and stop on collection/integrity errors; do not replace an unfavorable window.

Evidence checkpoints are append-only numbered JSON files, and the final `manifest.json` is created once after the phase finishes. No rename or overwrite of earlier evidence is required. Development reproduced the sandbox's denial of a rename in its Windows temporary directory; the archive was changed to this append-only design before registration. This is experiment evidence storage, not a new device-durability guarantee.

Run full source verification and source CI before measurements. **Do not overlap local profiling, calibration, confirmation or other local test campaigns.** No other controlled local benchmark will run during collection. This is not a guarantee of an idle OS, filesystem, antivirus or application; actual latency/lateness and identical-software variation remain evidence.

Four configurations: profiles 2+1/4+2, spare headroom absent/present. Row unit fixed **4096 bytes**, foreground object fully protected 2+1 with two units, as in E17. Conventional disjoint component plans are composed with explicit closes, one open token and `groups` active tokens. Immutable content, source authentication, prepared intents, uncertain-outcome accounting and source generation guards remain unchanged. Every arm within a matched set has identical scope/content/budgets. This smaller configuration family is a newly declared experiment, not deletion of E17's small strata or results.

## Scoped diagnosis (separate from comparative timings)

Eight fresh stores: four configurations, joint/restricted-separated arms, four repair groups. Profile planning, admission and all saved actions separately with cProfile's default elapsed timer. Save all function call counts, exclusive/cumulative elapsed times and coarse whole-phase controller-thread CPU/wall times. Group exclusive elapsed costs as coding, hashing, SQLite, file I/O, serialization, model validation, planning, authority and other runtime.

No foreground worker in diagnostic profiles. Profiler overhead is included; inclusive values overlap and are not summed. Function elapsed cost includes waiting/scheduling and is **not** labeled CPU. Coarse CPU counters are used only for whole phases. This identifies observed hot paths under instrumentation, not causal production CPU shares or a speed benchmark. The ordinary uninstrumented collector is used for calibration/confirmation. Python's [profiler documentation](https://docs.python.org/3.11/library/profile.html) explicitly distinguishes profiling from benchmarking; [time documentation](https://docs.python.org/3.11/library/time.html#time.thread_time) defines thread CPU separately. Failed profiled phases retain their partial statistics/error.

## Adaptive calibration, fixed before comparative outcomes

For each configuration try **4, then 6, then 8 repair groups**. Each candidate requires two complete matched sets of the three E17 arms: `joint`, identical `joint_repeat`, restricted `separated`, with saved seeded random order. Seed **20261018**. Each window offers exactly **1200 reads at 500 Hz**, retains all arrivals/queue/service/completions/errors and verifies exact content, complete terminal replay and receipts via the unchanged E17 collector.

Select the **first** group count for which all six windows satisfy:

- All 1200 request identities exactly once, no errors, correct latency/service arithmetic and exact object/foreground bytes.
- At least **2 seconds whole-controller thread CPU**, covering snapshot/planning/admission/actions/terminal cursor check, in every arm. This larger floor responds to E17's observed 15.625-ms CPU increments; it does not promise statistical precision.
- At least **1000 scheduled arrivals and 1000 actual enqueues before restoration** in every arm. Late scheduling cannot create a false adequately loaded repair window merely by assigning past arrival timestamps.

Preserve all six candidate windows even if one is insufficient. A failed candidate's lower group count cannot be silently omitted or selected on a favorable subset. Do not add artificial repair delays. If none of the three group counts passes, report selection INSUFFICIENT and refuse confirmation. Collection success and workload adequacy are distinct fields.

Freeze selection in the completed calibration manifest. Confirmation checks complete configuration/arm coverage, first-passing workload, all shard digests/quality and exact source/protocol/Git identity; save calibration manifest SHA-256. No mid-confirmation resizing or dropped failures.

## Ten-set characterization

For each of the four frozen configurations collect **ten** fresh matched sets of all three arms: **40 matched sets / 120 windows / 144000 offered requests**. New randomized order uses seed **20261019**. Bootstrap/setup and final verification costs remain separately recorded, and the loaded controller path includes all actual planning, locks, transactions, authentication/reconstruction and append/reset synchronization. No profiler instrumentation in these windows.

Primary completeness/adequacy requires all 120 windows/144000 exact requests and every window meeting the above CPU/actual-arrival floors. Continue and retain all later windows if a measured sample is insufficient; abort only an integrity/collection failure. Any final insufficiency prevents an adequacy-PASS conclusion, without cherry-picking/replacing that window.

For each configuration save all ten per-set **joint/other ratios** for full controller CPU, restoration wall and empirical window p99, separately against identical joint and restricted separated. Save their arithmetic mean and a predeclared 5000-resample paired percentile 95% interval (indices 125 and 4874 of ascending draws), deterministic seed 20261018 plus configuration index. Resample whole observed matched sets; these intervals do not remove temporal/host dependence, establish production SLAs, or provide a general p99 population guarantee.

The identical-software p99 repeatability screen is established only if a configuration is adequately sampled and its joint/repeat mean-ratio interval is entirely within **[0.95, 1.05]**. An interval outside that range records repeatability NOT ESTABLISHED, not a software integrity failure. This is a diagnostic of the experiment's ability to resolve a small effect, **not the original 5% PRISM foreground gate**. Preserve this result even when the joint arm looks faster than restricted GC-first.

Joint/restricted gains are conventional scheduling effects. Joint/repeat compares identical software. Always report `candidate_mechanism_present=false`, `original_prism_gate_evaluated=false`, `patent_rating_changed=false`. No original 20%-CPU or 5%-foreground gate can pass from this experiment in the absence of a distinct equally compared candidate.

## Verification and next boundary

Focused tests must reject missing/duplicate/late-enqueued samples, calibration shard/source alteration, incomplete/changed arm inputs, invalid counters and favorable-only candidate selection. Test actual profiled byte execution and preserve phase errors. Full regression uses 10000 traces, seed 20261011; source CI on Ubuntu/Windows retains the 1000-trace setting. Bind final manifests/verification/current runtime source hashes and protocol digest; preserve all E16/E17 evidence unchanged.

This advances E16-E baseline characterization, attribution and adequacy beyond the pilot. A negative precision/adequacy result is a completed experiment, not proof of invention. Native device/emulator status, reset acknowledgement/power-loss evidence, external reproduction and unknown human filing facts remain separate E16-F/filing tasks. Readiness stays the previously assessed **55/100**.
