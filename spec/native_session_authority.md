# Native-session authority contract (E21)

16 October 2026. Implemented at source `49db8a156b1f62bb8399cdf1f5a979e19d5f2b09`, after completion/audit of E19 timing. The [registered fault protocol](../experiments/native_authority_protocol.md) defines the exact verification gates; [E21 execution](../evidence/results/E21_EXECUTION.md) records actual outcomes and remaining limits. This format is opt-in and separate from `prism-zoned-file-v1`; opening a file authority as native, or native authority as file, must fail.

## Supported continuity and identity

One immutable scope, one admitted finite plan, 4096-byte code rows, online fresh bootstrap, and trusted local authority actors. A private serial supervisor owns one new QEMU controller and its code-row-capacity namespaces. The supervisor and device session survive authority actor exits. A session UUID, controller serial, namespace/capacity map and boot identity bind the authority; a separate store UUID claims the session exactly once. Requests authenticate the private session descriptor and carry the store UUID and owner fence. Administrative file/device tampering is fault injection, not an adversarial security claim.

A recreated descriptor/controller is never adopted merely because an old path, capacity or serial looks plausible. If the supervisor/session disappears, fail closed and expose no appendable credit. There is no supported automatic reboot/VM-loss recovery. Physical persistence of backing bytes does not prove persistence of device write-pointer/incarnation metadata.

## Persistent state and admission

SQLite WAL/FULL stores format/bootstrap state, store/session binding, source manifest epochs/profiles/content/row digests, nominal zone state/incarnations/budgets, owner fence, one witness/cursor, prepared intent, quarantine and unique action receipts. An interrupted offline bootstrap remains INCOMPLETE and cannot be reopened/reused. No plaintext fallback is persisted.

Admission independently authenticates native LIVE bytes and checks the exact initial fingerprint, complete witness replay and target. Every transition retains model protection, source references and open/active/resource budgets. The namespace-local hardware limits do not replace the host's aggregate budget enforcement.

## Takeover and real command drain

Byte operations retain `BEGIN IMMEDIATE` through synchronous RPC and device completion. If an actor dies, the database transaction can roll back while its already accepted/submitted request continues in the supervisor. A new actor therefore must not equate database lock acquisition with native quiescence.

Takeover acquires the authority transaction, requests a supervisor barrier with the next fence, waits for the serial supervisor to finish prior commands/observe their completions, and then publishes the new database fence. The supervisor rejects any later old-fence request before native submission. If the supervisor advances but the database transaction fails, access remains conservative until reconciled; uncertainty cannot publish free capacity or an unacknowledged owner transition. The fault campaign observes a real NVMe submission doorbell before actor kill and delays completion observation, rather than inferring an outstanding command from elapsed time.

## Prepared operations and reconciliation

Native open, close, finish, stage and reset acknowledgement all persist an identity-bound intent before physical action. Identity includes store/session, cursor, pre-state, full action and incarnation; stage adds immutable epoch/target-row digest. Nonphysical reserve/promote/retire/discard/reset-request changes commit with a unique receipt under the same serialized authority. Promotion authenticates actual staged bytes.

Reconciliation accepts only the declared old or exact intended native condition/position for the prepared action. An already completed stage must authenticate against reconstruction from retained native LIVE sources; reset/control adoption must match the identity-bound intended state in the same continuous supervisor session. Retain capacity until atomic receipt/state/cursor publication. Whole-zone reset is never used to undo an uncertain append.

Two aligned 2048-byte native writes expose the half-row fault boundary. A partial/extra/invalid position quarantines the store. All pending/uncertain/quarantined outcomes expose zero appendable credit; native unavailability conservatively charges capacity. FULL/FINISHED's invalid-pointer sentinel is handled as fully charged native capacity, not as an empty position. Finish strands the unwritten tail; diagnostic finish fixtures must not claim the original reclaimed appendable-space objective.

Repeated old cursors return their stored receipt without physical reissue. Stale actor and stale raw native requests are rejected separately. Immutable source/content/regenerated-row checks, parity consistency and zero-padding checks remain in force.

## Verification and remaining boundary

The registered campaign has eight nominal routes, 66 process-exit boundaries, four submitted/unacknowledged-command kills and six identity/intent/session cases, with four additional actor exits used to prepare edge cases. All attempts/failures, native completion statuses, versions, source hashes and operation counts must be retained. Portable state-machine tests do not substitute for actual NVMe/process faults. Local Linux and remote Linux CI repetitions must identify their actual QEMU/Python builds.

An authority actor's successful recovery does not establish persistence after losing the device supervisor. Physical power-cut/device durability, independent outside reproduction and human filing facts remain separate. This is conventional safe-storage engineering; no novel certificate, non-obvious combination or score increase is assumed by the contract.
