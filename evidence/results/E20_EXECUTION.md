# E20 native-emulator command and codeword-route gate

16 October 2026. [Registered route protocol](../../experiments/native_qemu_protocol.md), [native acceptance contract](../../spec/native_zoned_validation.md). This is actual QEMU NVMe ZNS command/byte integration with the nominal conventional planner. **Persistent-authority/native fault integration and power-loss evidence remain pending.** No new invention or score increase is inferred.

The user confirms a Linux VM/emulator is available. [Inventory](linux-backend-inventory-e20.json) records WSL kernel 6.18.33.1 with zoned support but no null_blk module or KVM. QEMU was installed in Ubuntu from package `1:6.2+dfsg-2ubuntu6.31`. The exact binary hash is recorded in successful reports: `55862c768c21fa7d3e72ca1b24797d8ab5b406eb5ef4c9ab9c2280f4e0b8f330`. [Linux runtime environment](native-environment-e20.json) records Python and source/test hashes. This analysis harness runs on Linux's available Python; the full prototype correctness/CI reports use Python 3.11.

No existing image/device is accepted. Every instance creates new owned sparse images and a random controller serial, uses halt-only firmware under TCG, and has no guest OS/user disk. The qtest transport writes actual NVMe queue entries/doorbells and reads completion queues; model repair bytes are submitted through NVMe read/write and zone-management commands. These are positioned sequential NVMe writes, **not NVMe zone-append commands**. Emulator command latency is not a storage performance benchmark.

## Preserved attempts

| Attempt | Outcome |
|---|---|
| [Command smoke r1](qemu-zns-e20-r1.json) | Failed: packaged TCG does not expose qtest `clock_step`; no device correctness failure is inferred. |
| [Command smoke r2](qemu-zns-e20-r2.json) | PASS: 15 actual successful NVMe completions; exact serial binding, write-pointer increment, readback, close, finish, reset and reuse. Exact harness source is preserved at commit `2ceaa22`. |
| [Byte routes r1](qemu-zoned-routes-e20-r1.json) | Failed on first promotion: harness used empty action stripe fields; this model binds promotion identity through the extent. No stage/reset was silently retried. |
| [Byte routes r2](qemu-zoned-routes-e20-r2.json) | PASS: eight new instances, **84 exact prefix readbacks and 893 successful NVMe completions**. The corrected lookup reads the promoted extent identity; all failed evidence/stores remain. |

The corrected driver uses one fresh namespace per model zone, 1 MiB addressable zone size and actual usable capacity exactly one or two 4096-byte code rows. Namespaces bind zone name/namespace ID/capacity and the instance's controller serial. The host checks the model's aggregate open/active budgets; per-namespace hardware limits do not independently enforce the same aggregate budget. Simulated domains do not become physically independent disks.

| Profile | Spare | Joint stage bytes | Restricted separated stage bytes | Outcome |
|---|---|---:|---:|---|
| 2+1 | No | 4096 | 8192 | Both exact/protected |
| 2+1 | Yes | 4096 | 4096 | Both exact/protected; parity retained |
| 4+2 | No | 4096 | 8192 | Both exact/protected |
| 4+2 | Yes | 4096 | 4096 | Both exact/protected; parity retained |

After bootstrap, the expected encoded-row buffers are deleted. Repairs reconstruct from rows read from the emulated namespace, with immutable row/content/regenerated-row digest checks. Expected plaintext remains a verification oracle, not a repair fallback. Every nominal prefix checks authoritative report condition/capacity and the defined pointer for non-full states. QEMU reports an invalid/sentinel pointer for FULL/FINISHED; those states are checked by condition/capacity and retained model charge rather than treated as free space.

## Remaining native boundary

This closes the initial absence of any actual zoned device-command/byte test. It does not integrate prepared SQLite intents with a long-lived emulator session, reconcile commands after driver death, prove a serial survives device recreation, or handle a delayed pre-takeover command. No partial-write/lost-ack/power-cut/native-reset-uncertainty fault matrix is claimed. QEMU backing bytes alone do not establish persistence of volatile write-pointer metadata after emulator restart.

The durable native adapter therefore remains gated on explicit session/device identity continuity, command drain and uncertainty reconciliation under the [acceptance contract](../../spec/native_zoned_validation.md). Independent outside reproduction and human filing records also remain unresolved. The native routes are conventional engineering evidence; current subjective patent-readiness remains **55/100**.
