# Versioned immutable coding profiles

Version 1 — 12 October 2026. These are fixed local storage contracts, not new coding inventions.

## Registry and representation

`xor-2+1-v1` remains the default: two equal-length data rows and their XOR parity. Its row numbers, padded encoding and historical state fingerprints are unchanged.

`pq-4+2-gf256-v1` uses four data rows and two parity rows. Arithmetic is GF(256), with primitive polynomial `0x11d` (x^8 + x^4 + x^3 + x^2 + 1). The generator rows are:

| Row | Coefficients over the four data rows |
|---|---|
| 0 | 1, 0, 0, 0 |
| 1 | 0, 1, 0, 0 |
| 2 | 0, 0, 1, 0 |
| 3 | 0, 0, 0, 1 |
| 4 (P) | 1, 1, 1, 1 |
| 5 (Q) | 1, 2, 4, 8 |

The four chunks have size `max(1, ceil(original_length / 4))`; the original byte sequence is followed by zero padding. Empty content therefore still has one byte per row. Reconstruction rejects unequal row lengths, invalid row identifiers, inconsistent additional supplied rows and nonzero canonical padding. The default profile uses the analogous two-chunk convention.

Any four of the six rows reconstruct the content. With two missing data rows, the two remaining parity equations have nonzero determinant because their Q coefficients differ; other four-row selections reduce to identity rows and nonzero parity coefficients. The verification campaign independently calculates all 15 four-by-four determinants and reconstructs each selection. The independent oracle uses polynomial multiplication and cofactor inversion; production uses logarithm tables and Gaussian elimination.

The field polynomial and systematic erasure-code construction are established techniques described in [RFC 5510, sections 8.1–8.3](https://www.rfc-editor.org/rfc/rfc5510). This explicit P/Q matrix and local representation do not claim RFC 5510 wire interoperability. No novelty is attributed to adding this codec.

## Model, storage and authority binding

Each immutable stripe names one registry profile. The safety floor is its data-row count, and the terminal target is all its coded rows, on distinct online eligible domains. Thus 4+2 requires four authentic live rows to remain safe and six to finish restoration. Every reservation and live row is checked against the profile's row range. Mixed profiles can share an authority and use disjoint scoped plans.

SQLite stores the profile in the stripe record; an additive migration defaults historical records to `xor-2+1-v1`. Snapshot/cache decoding also defaults an absent historical field to that profile. Default-profile fields are omitted from state fingerprint input to preserve existing witnesses and pending worker intents. Nondefault profiles are included in fingerprints and therefore bind witness, cache and worker command state. Changing a 4+2 stripe to the default invalidates those commitments.

Runtime reconstruction validates precomputed row SHA-256 digests and the original content digest. A worker stages the authority-derived profile row as an opaque payload; receipt completion rechecks current sources, profile-bound state, exact command and physical bytes. Valid extra rows provide a consistency check, but the codec alone cannot detect arbitrary corruption when only four rows remain. Authenticity depends on the immutable digest metadata and trusted local authority.

## Supported limits

Only these two fixed versioned profiles are accepted. Arbitrary generator matrices, configurable fields, mutable content and error correction are excluded. Two-domain erasure tests use simulated domain labels in one local store. They do not establish independent device, rack, power-loss or network fault tolerance. No 4+2 throughput result, controller improvement or patentability score follows from correctness verification.
