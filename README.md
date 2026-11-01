# API to Arazzo

An open Agent Skill for preparing an API as an ItPay Arazzo package, then uploading it manually through API Hub. Works with Agents that support the [Agent Skills format](https://agentskills.io/specification).

## Install and use

```sh
npx skills add itpay-ai/api-to-arazzo
```

Ask your Agent:

> Use api-to-arazzo to prepare this API for ItPay. Preserve the source API, build the Arazzo workflow, validate locally, and give me the three files for manual upload.

See [SKILL.md](SKILL.md) for the workflow and [the package contract](references/itpay-format.md) for fields. Upload `openapi.json`, `workflow.arazzo.json`, and `itpay-manifest.json` in **API Hub → My API → Upload specification**. Store key values in **My Key**.

## Run locally

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync --frozen
uv run python scripts/prepare.py --openapi assets/examples/openapi.json --out output/weather --source-key weather-api --service-id weather-api --name 'Weather API'
uv run python scripts/validate.py output/weather
uv run python -m unittest discover -s tests -v
```

Preparation and validation run offline. The helpers support HTTP JSON operations, bounded acyclic local references and typed multi-step Arazzo workflows. Remote or recursive references, conditional actions, nested workflows and unsupported serialization are rejected explicitly. This is a supported subset, not a universal API converter. Offline success does not establish live correctness or publish an API. Test inputs still require user review. The Skill does not upload through MCP, hold secret values, accept terms or execute payments.

See [verification scope](references/verification.md) for tested behavior and limits.

## License and provenance

New Skill instructions and tooling: MIT. The vendored Arazzo schema: Apache-2.0; see [NOTICE](NOTICE), [license](licenses/ARAZZO-SCHEMA-APACHE-2.0.txt), and [source hashes](references/third-party-sources.json). No private API credentials or adapter implementation are included.
