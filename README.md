# API to Arazzo

An open Agent Skill that prepares an API for private **ItPay My API** import using the user's own key (BYOK). It creates local specification files for manual import and does not configure workflow orchestration, pricing, resale or publication. Works with Agents supporting the [Agent Skills format](https://agentskills.io/specification).

## Install and use

```sh
npx skills add itpay-ai/api-to-arazzo
```

Ask your Agent:

> Use api-to-arazzo to prepare this API for private ItPay My API use with my own key. Preserve the source, validate locally, and give me the API source and metadata for manual import.

See [SKILL.md](SKILL.md) and [the package contract](references/itpay-format.md). Import `openapi.json` and `itpay-manifest.json` in **API Hub → My API → Upload specification**. Keep `workflow.arazzo.json` as an internal standard artifact; do not select it for the private API import. Keep secret values in **My Key**; personally confirm terms and API rights on the website.

## Run locally

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync --frozen
uv run python scripts/prepare.py --openapi assets/examples/openapi.json --out output/weather --source-key weather-api --service-id weather-api --name 'Weather API'
uv run python scripts/validate.py output/weather
uv run python -m unittest discover -s tests -v
```

Preparation and validation run offline. The bounded HTTP JSON subset supports acyclic local references and typed Arazzo mappings. Remote or recursive references, conditional actions, nested workflows and unsupported serialization fail explicitly. This is not a universal API converter. Offline success and private import do not prove successful API execution. Test inputs require review; the Skill never uploads, accepts terms, holds secret values or executes requests.

See [verification scope](references/verification.md) for limits.

## License and provenance

New Skill instructions and tooling: MIT. The vendored Arazzo schema: Apache-2.0; see [NOTICE](NOTICE), [license](licenses/ARAZZO-SCHEMA-APACHE-2.0.txt), and [source hashes](references/third-party-sources.json). No private credentials or adapter implementation are included.
