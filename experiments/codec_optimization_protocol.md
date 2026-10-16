# E19: shared conventional codec optimization — 16 October 2026

Registered design before implementation/performance outcomes. Finish and audit the unchanged-source E18 continuation first. The optimization is available to every conventional/candidate arm; **it is not a new invention distinction**.

## Compatibility and correctness

Keep GF(256) polynomial 0x11d, generator matrices, selected-basis ordering, systematic rows, exact lengths, zero padding, row consistency checks and manifest/content authentication. Replace per-byte Python multiplication/XOR in `coding.combine` with immutable coefficient translation tables and whole-buffer integer XOR, with a systematic identity-row fast path. Preserve the existing equal-length XOR rejection. Precomputed tables use the existing field product; an independent polynomial oracle checks all 65,536 coefficient/value products through the actual combine path.

Before measurements, verify both profiles against an independent encoder; recover every supported row subset including redundant rows, empty/odd/padded content and larger vectors. Retain rejection of malformed rows, inconsistent redundant rows, nonzero padding and content/row corruption. Construct stores with the historical codec, reopen and execute with the new codec, checking exact object/receipt compatibility. Full regression and source-bound Ubuntu/Windows CI must pass. No safety/authentication checks may be removed for speed.

## Microbenchmark

Use exact historical `coding.py` from source `e8ad2dba831f17749b0f8d27e5a32e63b1e9889a`, verifying its Git blob bytes/digest, against the optimized codec. Save every measured set and exact source hashes. Both implementations operate on identical deterministic input and basis; verify exact returned bytes outside each timed batch. Keep setup/initialization separate. Both profiles, row units 64 and 4096, encode and reconstruction from parity-containing bases. Warm each arm once. Collect 12 complete matched sets, randomized arm order with seed 20261016, each arm executing 100 operations per window. Save batch controller-thread CPU and wall time, ratios, median and deterministic paired bootstrap intervals; include all outcomes, including parity/losses.

Measure cold module execution in five fresh Python processes per implementation, preloading common imports before the measured module execution. This isolates codec module initialization (including coefficient table construction), not interpreter startup or end-to-end application startup. Report allocated translation-table payload bytes separately. Do not transfer a microbenchmark speedup to complete-controller speed or foreground latency.

## Complete controller after changed source

Run a new source-bound calibration, preserving all candidates, at groups 4/6/8/12/16 with the E18 2-second thread-CPU and 1,000 actual/scheduled arrival floors. All 1,200 reads at 500 Hz are retained; all three conventional arms receive the optimized codec. First complete passing candidate for each configuration is frozen before characterization. Never reuse the old-source E18 selection after changing codec source.

If all configurations select, collect ten matched sets per configuration using the same arm order and 5,000-resample descriptive analysis as E18 (120 windows/144,000 reads). A shorter recovery may fail the prior arrival/CPU floors; report inadequacy, do not insert artificial repair delay. Record changed group count and avoid interpreting cross-source windows of different work as paired speed evidence. Identical-software repeatability remains a precision diagnostic. Original PRISM performance gates stay unevaluated without a distinct candidate.

No local regression/microbenchmark/profile/controller campaign may overlap another timed campaign. Native emulator, power-loss evidence, external reproduction and human/filing records remain separate outputs. Publish complete/partial/failed evidence and exact limitations; no numerical result or score increase is preassigned.
