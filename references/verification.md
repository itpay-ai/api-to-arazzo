# Verification scope

Run `uv run python -m unittest discover -s tests -v` for local checks. They cover source preservation, typed required inputs/body constraints, bounded acyclic local references, prior-response mappings in the internal Arazzo artifact, own-credential metadata, invalid types/future references/cycles, parser limits and credential rejection without value disclosure. BYOK tests reject workflow authoring, pricing, hosted credentials and prefilled confirmations.

Reports describe offline evidence only. Generated test inputs remain empty with `needs_user_test_input`. The example API is fictitious. These tests establish neither real endpoint execution nor server acceptance, credential access or a universal compatibility guarantee. Separate Hub integration results must be recorded against the BYOK contract before claiming them; historical commercial-package checks do not prove the private import path.
