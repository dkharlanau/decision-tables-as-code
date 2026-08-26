# Auditable decision release bundles

A decision release bundle is a portable evidence directory for one approved canonical decision table. It is designed for enterprise change control: the bundle proves which table definition, validation findings, scenarios, semantic change, provenance, review artifact, and generated runtime were released together.

The bundle is deterministic. It contains no generation timestamp, temporary path, hostname, Git checkout path, or other environment-specific value. Building from the same inputs produces the same `manifest.json`, artifact bytes, and `SHA256SUMS`.

## Build a release

```bash
dtac release-build examples/order-routing.yaml \
  --bundle /tmp/order-routing-release \
  --scenarios examples/order-routing.scenarios.yaml \
  --against examples/order-routing-v2.yaml \
  --javascript
```

Release creation fails when the canonical table has validation errors or supplied scenarios fail. This prevents a failing test result from being packaged as if it were approved evidence.

The output directory contains a structure similar to:

```text
order-routing-release/
├── table.yaml
├── baseline.yaml
├── scenarios.yaml
├── review.md
├── manifest.json
├── SHA256SUMS
├── evidence/
│   ├── validation.json
│   ├── inspect.json
│   ├── scenario-report.json
│   └── semantic-diff.json
└── runtime/
    ├── decision.mjs
    └── decision.d.ts
```

`baseline.yaml`, scenarios, and runtime files exist only when their corresponding build inputs/options are supplied.

## Manifest contract

`manifest.json` is the audit index. It includes:

- bundle format/version;
- canonical table ID, name, hit policy, format version, and semantic fingerprint;
- validation result and severity counts;
- executable scenario totals and pass/fail summary;
- semantic-diff classification plus baseline fingerprint;
- rule provenance: owner, source, ticket, rationale, effective window, metadata;
- generated runtime kind/path/hash/size;
- SHA-256 and byte size of every evidence/input/review/runtime artifact.

The manifest intentionally has no current timestamp. A Git commit, Git tag, GitHub Release, transport/change record, or external signing record is the right place to record when an organization approved or published a particular immutable manifest hash.

## Verify independently

A consumer does not need the original Git repository:

```bash
dtac release-verify /tmp/order-routing-release
```

Verification checks:

1. every file declared by the manifest exists;
2. byte size and SHA-256 match the manifest;
3. no undeclared artifact file was inserted;
4. `SHA256SUMS` covers exactly the manifest and declared artifacts;
5. `manifest.json` itself matches its checksum entry;
6. the reloaded canonical `table.yaml` has the semantic fingerprint declared in the manifest.

If `table.yaml`, a runtime, evidence report, review file, baseline, scenarios, or the manifest is changed after release, verification fails.

## Detached signatures

`SHA256SUMS` is the stable detached-signature subject. DTAC deliberately does not manage private signing keys.

An organization can sign that file with its established mechanism, for example SSH signing, GPG, an HSM-backed signing service, or an enterprise artifact-signing platform. The recommended order is:

1. run `dtac release-verify`;
2. cryptographically verify the detached signature over the exact `SHA256SUMS` bytes;
3. check the signer/identity against the organization's approval policy.

This separation keeps DTAC deterministic and key-agnostic while allowing existing enterprise PKI/change-control processes to sign the complete release file set.

Example with OpenSSH signing outside DTAC:

```bash
ssh-keygen -Y sign -f /path/to/signing_key -n dtac-release \
  /tmp/order-routing-release/SHA256SUMS
```

The resulting signature file can be stored beside the bundle or attached to the GitHub/enterprise release record. Because the signed subject itself lists `manifest.json` and every artifact, the signature transitively covers the release content.

## GitHub Release pattern

A practical GitHub flow is:

1. merge the decision-table pull request only after validation/scenario/semantic-diff gates pass;
2. build and verify the release directory in a release job;
3. archive the directory using the organization's deterministic artifact process;
4. attach the archive, its checksum, and optional detached signature to the GitHub Release;
5. put the `manifest.json` SHA-256 in the release notes/change ticket;
6. deploy only runtime artifacts whose hashes are listed in that manifest.

The Git tag/release version answers *when/which product release*. The DTAC manifest answers *exactly which decision semantics and evidence*.

## Enterprise change-management pattern

For SAP/MDG/BRFplus, middleware, master-data, pricing, approval, or migration changes, store these identifiers in rule provenance before building the release:

```yaml
owner: Order Management
source: EU routing workbook
ticket: CHG-1042
rationale: New fulfillment model
effective_from: 2027-01-01
```

Then reference the bundle manifest hash from the enterprise change record. Reviewers can retain the bundle as implementation evidence even when they do not have access to the original engineering repository.

A controlled promotion flow can use the same verified bundle across environments rather than rebuilding the runtime separately for QA and production. That prevents environment-specific regeneration from changing the approved executable decision artifact.

## Why the bundle is a directory

The canonical unit is a directory because archive formats can introduce timestamps, ownership metadata, and platform differences. The DTAC directory content is byte-deterministic. An organization may wrap it in ZIP/TAR/container/artifact-store packaging appropriate to its release platform, while `SHA256SUMS` and `release-verify` continue to define and verify the logical release content after extraction.

## Reproducibility

CI builds the same release twice from the same table/scenarios/baseline/runtime option and compares every file byte-for-byte. This is stronger than only comparing manifest JSON: it catches nondeterminism in YAML serialization, reports, generated runtime, or checksums too.
