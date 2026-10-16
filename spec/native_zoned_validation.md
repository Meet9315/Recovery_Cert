# Native zoned backend validation boundary

16 October 2026. This is the device/emulator acceptance contract, not a claim that a local file adapter implements native ZNS or power-loss durability. The user confirms a Linux VM/emulator is available. Read-only host discovery must establish the actual installed backend and version before selecting a concrete driver.

## Selection and identity

Prefer a newly created disposable memory-backed Linux `null_blk` zoned device for kernel block-interface conformance if the running kernel provides it; use a unique per-run configfs directory and pin the exact kernel/driver configuration. A RAM-backed device can test write-pointer/reset semantics and process behavior, not persistence after VM/power loss. If unavailable, inspect an installed QEMU ZNS backend; record exact QEMU/guest versions and configuration, a unique namespace serial/identity, capacity versus zone size, logical-block alignment and backing-image digest. Do not infer capabilities from executable presence alone.

Do not operate on existing user disks, mounted devices, imported namespaces or a device selected only by a volatile name such as `/dev/nvme0n1`. A destructive smoke test may address only a newly created owned emulator namespace, with its identity, unique creation configuration and expected geometry verified immediately before I/O. Existing devices are read-only inventory. Out-of-band reset/recreation must cause a binding failure or conservative quarantine; a path or old write pointer alone does not prove device identity or incarnation.

## Backend operations and mandatory gates

| Operation | Required behavior/evidence |
|---|---|
| Report | Obtain authoritative start, capacity, write pointer, condition and open/active limits; distinguish addressable zone size from usable capacity. |
| Read | Enforce sector alignment/range and verify exact object/row content against the existing immutable manifest. |
| Sequential write/append | Submit only aligned in-capacity writes with serialized position ownership, record actual completion/returned position, inspect authoritative position after uncertain completion, and never rewind an unexplained append. A positioned sequential write must not be called an NVMe zone-append command. |
| Close/finish/reset | Use the real backend operation and inspect its resulting state; never substitute file truncation. Finish strands the unwritten tail. Charge capacity/open/active resources until the required outcome is reconciled. |
| Drain/takeover | Serialize or explicitly drain outstanding operations before reuse/reset. A database fence cannot revoke an already submitted device command by itself. |
| Identity/restart | Reject a different device/namespace generation. Document which identities survive process exit, emulator restart and VM/power loss; refuse unsupported transitions. |
| Crash consistency | Persist the intent before device action, synchronize according to backend guarantees, authenticate adoption, then commit cursor/receipt. Preserve partial/invalid/ambiguous outcomes. |

A native smoke test is a gate for a later durable adapter integration, not a substitute for the full admission/source-retention/receipt protocol. Keep the file format/version distinct from any native authority format. Do not silently route a file store to a raw device.

## Fault and reproduction matrix

For both 2+1/4+2 profiles and tight/spare capacity, run before/after intent, physical action and metadata-commit process exits, exact prefix reads, no duplicate append/reset, stale worker rejection and conservative capacity accounting. Add a delayed in-flight write/reset scenario only with an actual backend mechanism that supports controllable delay. Inject partial/corrupt write and lost acknowledgement distinctly from a process dying before submission.

An emulator reset/restart test must explicitly document backing-data and controller-metadata persistence. It is not an actual power-cut experiment unless the power-loss model is implemented and validated. Physical media power-cut tests require suitable disposable hardware and a defined controller/flush model. If a capability is unavailable, retain a BLOCKED/NOT TESTED outcome rather than a pass from mocks.

Independent reproduction requires another operator/environment to execute the pinned protocol and return raw artifacts and version/source hashes. CI and an oracle implemented inside this project are useful separate checks but are not an independent external review. No email/message is sent without the user's explicit instruction.

Primary interface context: [Linux null block documentation](https://docs.kernel.org/block/null_blk.html) describes memory backing; [QEMU NVMe documentation](https://www.qemu.org/docs/master/system/devices/nvme.html) documents zoned namespace configuration and separate capacity/size parameters. These current documents are interface references, not dated novelty evidence.
