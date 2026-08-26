# Dependency-free JavaScript runtime

`dtac js-export` compiles one canonical decision table into a standalone ECMAScript module. The generated file has no DTAC runtime dependency and no npm dependency: the reviewed table plus the evaluator required to execute it are embedded in one `.mjs`/`.js` file.

This is useful when decision logic is governed in Git/Python CI but must run in Node.js, a browser bundle, a serverless function, middleware, or another JavaScript service.

## Generate a runtime

```bash
dtac js-export examples/order-routing.yaml \
  --output generated/order-routing.mjs \
  --types-output generated/order-routing.d.ts
```

The module exports:

```js
import { evaluate, matchingRules, tableId, hitPolicy } from "./order-routing.mjs";

const result = evaluate({
  country: "DE",
  customer_type: "B2B",
  order_value: 6000,
});

console.log(result);
```

The result contract matches the native engine:

```json
{
  "table_id": "order-routing",
  "matched_rule_ids": ["de-b2b-high"],
  "outputs": {
    "route": "enterprise-desk",
    "approval": "senior"
  }
}
```

## Effective-dated rules

Generated code never reads the current date. Pass the same explicit evaluation date used by native DTAC:

```js
import { evaluate } from "./effective-routing.mjs";

const result = evaluate(
  { country: "DE" },
  { asOf: "2027-01-01" },
);
```

A JavaScript `Date` is also accepted and normalized to its UTC `YYYY-MM-DD` date. If an effective-dated rule is present and `asOf` is omitted, evaluation fails instead of silently using today.

## Semantic parity

The generated evaluator implements the same native hit policies:

- `unique`;
- `first`;
- `collect`.

It implements scalar equality, list membership, wildcard presence checks, `eq`, `ne`, `in`, `not_in`, `gt`, `gte`, `lt`, `lte`, `between`, `exists`, and `regex` conditions.

CI executes generated ESM with Node.js and compares outputs plus matched rule IDs against the native Python engine using the repository scenario packs. A dedicated parity fixture also exercises every condition operator and `collect`.

## Regex portability

Python and JavaScript regular-expression dialects are not identical. DTAC emits portable regular expressions with full-match semantics by anchoring the JavaScript `RegExp`. Known Python-only constructs such as Python named capture/backreference syntax and Python inline flags are rejected during generation instead of being silently translated.

If a project relies on engine-specific regex behavior, keep that rule in a target-specific adapter or rewrite the expression into a portable form before generation.

## TypeScript declaration

`--types-output` generates a small `.d.ts` alongside the ESM module. It describes the runtime API without requiring TypeScript itself at generation or runtime.

The declaration intentionally uses `Record<string, unknown>` for fact and output objects because the canonical v1 table format is dynamically shaped. Strong per-field generated types can be added later without changing the JavaScript runtime contract.

## Browser use

The generated module uses standard ECMAScript features only: objects, arrays, `Date`, `RegExp`, and ESM exports. There is no filesystem, Node-only API, network access, dynamic code loading, or package import in the runtime itself.

A bundler may include the generated module like ordinary application code, or modern browsers may import it directly where ESM is supported.

## Recommended release flow

Treat the canonical YAML/JSON table as the source of truth and the JavaScript file as a generated release artifact.

A practical flow is:

1. validate the canonical table;
2. run scenario packs and coverage checks;
3. inspect semantic diff against the previous approved version;
4. run `dtac js-export`;
5. execute parity tests against the generated module;
6. record the canonical-table fingerprint and generated-file hash in the release evidence;
7. publish/deploy the generated module only after the same pull request is approved.

For repositories that commit generated artifacts, regenerate them in CI and fail when the checked-in output differs. For repositories that do not commit generated code, generate it only in the release job and preserve its checksum with the release.

The planned decision release-bundle layer can package these hashes together with validation, scenarios, provenance, and semantic-change evidence.

## Product boundary

The generated module executes one canonical table. Multi-table package orchestration remains explicit: either execute the package through DTAC or generate/deploy individual table runtimes and implement the already-declared package bindings in the target orchestration layer.

Generation fails on invalid canonical tables and on semantics known not to be portable to the JavaScript runtime. It does not silently remove rules, provenance-driven effective dates, or unsupported regex constructs.
