# Reproduction handoff

16 October 2026. Run from a fresh checkout of the exact source commit recorded by the experiment. This packet is preparation for an outside operator; it does **not** assert external reproduction has happened. Record the operator/environment and return unedited raw reports, including failures. Do not run timings alongside verification or other benchmarks.

## Local correctness

Python 3.11, standard library; no service credentials or user data are needed. Use disposable fresh paths. Existing store directories are never reset/reused.

```powershell
git rev-parse HEAD
python --version
python -m prism_c verify --report artifacts/outside-verification.json --traces 10000 --seed 20261011
```

Retain the exact source/test digests, OS/Python/SQLite versions, errors and test/campaign counts. A passing Windows/Ubuntu CI run is already useful platform evidence; it does not substitute for this outside operator/environment record.

## Historical E18

E18 uses runtime/test/original-protocol bytes from `e8ad2dba831f17749b0f8d27e5a32e63b1e9889a`. Its original run and [explicit two-session continuation](../experiments/e18_continuation_protocol.md) must remain recognizable. Do not execute the one-off continuation against arbitrary data; it deliberately requires the audited 64-window prefix. An independent repetition should collect an entirely fresh full campaign on the pinned source, then compare results without merging them into the original attempt.

```powershell
python -m prism_c.zoned_measure profile --root tmp/outside-e18-profile --output artifacts/outside-e18-profile
python -m prism_c.zoned_measure calibrate --root tmp/outside-e18-calibration --output artifacts/outside-e18-calibration
python -m prism_c.zoned_measure confirm --root tmp/outside-e18-characterization --output artifacts/outside-e18-characterization --calibration artifacts/outside-e18-calibration/manifest.json
```

Run each phase to completion before the next. Confirmation refuses source/protocol/Git/calibration mismatch. Preserve each immutable window and checkpoint, original schedule/order, inadequate windows and every completion. Do not cherry-pick successful configurations or change group counts after comparison outcomes.

## Optimized shared codec

Use the later registered source containing the implemented codec and its tests, not the historical E18 source. The [E19 protocol](../experiments/codec_optimization_protocol.md) defines the exact historical reference, 12-set microbenchmark, cold initialization and fresh controller calibration. All conventional arms share the optimization. Running old-source comparisons against newly calibrated larger workloads is not a matched end-to-end speed experiment.

```powershell
python -m analysis.codec_benchmark --root tmp/outside-codec-batches --report artifacts/outside-codec-batches.json
python -m analysis.measure_optimized_codec calibrate --root tmp/outside-e19-calibration --output artifacts/outside-e19-calibration
python -m analysis.measure_optimized_codec confirm --root tmp/outside-e19-characterization --output artifacts/outside-e19-characterization --calibration artifacts/outside-e19-calibration/manifest.json
```

These commands require the exact historical Git blob to be available locally; fetch the recorded reference if a shallow checkout omitted it. Do not fabricate baseline source when unavailable. Preserve batch CPU-clock insufficiency and identical-software repeatability failures.

## Native backend

Read the [native validation contract](../spec/native_zoned_validation.md). First run `python3 analysis/linux_backend_inventory.py` inside the intended Linux environment. The optional `analysis/nullblk_smoke.py --create-owned-nullblk --report <fresh-report>` requires Linux root/configfs and creates only a new owned RAM-backed emulator. It never accepts an existing device path. Review the saved configuration/binding/cleanup result. A blocked module or failed ioctl is a retained result, not a native pass.

This smoke test checks actual kernel write-pointer/report/close/finish/reset behavior and exact raw bytes if it runs successfully. It does not implement the persistent authority's native backend, an NVMe zone-append command, cross-VM identity continuity, distributed operation or power-loss persistence. Those require their specified integration/fault gates. Never direct experimental commands at valuable media.

## Return record

Record operator identity/organization if supplied, date, source commit and hashes, hardware/emulator/OS versions and configuration, exact commands, all raw outputs, failures/deviations and any independently implemented oracle used. Human identity is not inferred from an account or an automated runner. Send nothing externally without the user's explicit instruction.
