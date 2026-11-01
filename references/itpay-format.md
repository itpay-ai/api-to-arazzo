# ItPay private BYOK package contract

The bundled `itpay-api-package.schema.json` contains the canonical metadata definitions, including historical commercial definitions for compatibility. This Skill uses only the private BYOK authoring definition. Its `$id` is an identifier rather than a network dependency. `arazzo-1.0.1.schema.yaml` validates the internal standard artifact; all schema resolution is local.

The manifest retains `format: itpay.api-package.v1`, stable `source_key`, empty server-generated `revision`, `entry_path: openapi.json`, and `authoring`. Preserve the source key across revisions. Filenames are fixed. Import only the OpenAPI source and manifest; retain the Arazzo file internally. Original API definitions, security declarations, required fields, schemas, examples and extensions remain in `openapi.json`; credential literals must be removed by the owner before preparation.

Authoring uses `version: itpay.byok-package.v1` and contains only `service`, `source`, `credentials`, `operations`, `terms_version` and `confirmations`. Service identity/name and optional PNG/JPEG icon are allowed. Source attribution and selected operation IDs/test inputs are preserved. Credentials must use `source: own`; credential IDs are references, never key values. Workflow authoring, pricing, hosted credentials, resale, refund and publication proposals are excluded. Standard Arazzo documents remain internal specification artifacts and do not add a user workflow configuration step.

Skill output must leave `confirmations: []`. The website submission separately requires `terms` and `api_rights`; only the uploader can supply them. The terms version is metadata, not acceptance evidence. Runtime results, verification, provider identity and server acceptance cannot be invented.

The helper supports a bounded HTTP JSON subset. Unsupported semantics fail explicitly. Empty test inputs mean a suitable test case is still needed. Offline validation and private import do not establish successful execution or authorize any request, including requests that cost money or change state.
