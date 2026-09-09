# Installation security checks

Brave Search Pro uses Hermes' native GitHub plugin installer and community
scanner. Installation and enabling are separate: approve only `tools.override`
when the enable command requests capability consent.

Version 0.2.1 uses manifest format 1 because the Hermes v0.21.1 and current
installers reject format 2. The runtime still reads the capability declaration
from format 1. No scanner configuration change is required.

The earlier dangerous verdict came from a literal dummy credential in a Tavily
error-redaction test. Current tests use a clearly non-credential value and still
assert that upstream errors cannot disclose it. Do not install that historical
revision or bypass a dangerous verdict.

## Reviewed findings

The v0.21.1 and current upstream scanners classify the following findings as
medium severity and return `safe` for the distributed repository. These are
reviewed by source reachability, rather than hidden from the scan:

| Finding | Location and reachability | Review and disposition |
| --- | --- | --- |
| Process execution | `src/hermes_brave_search/doctor.py` | User-invoked diagnostic runs a fixed `hermes plugins list --json` argument list, without a shell, with a timeout. No user-supplied command text. Retained. |
| Process execution | `tests/` | Test-only Python, Node and shell subprocesses exercise real integration boundaries in temporary homes. Not imported by plugin registration. Retained with full coverage. |
| Package and clone commands | CI, contribution guidance, installation examples and their tests | Development instructions or explicit user-run commands. Production backend installation uses the scanned plugin manager. Desktop-only clones are separate. Retained. |
| Environment-file references | Installation guidance and doctor messages | Paths explain profile credentials; these findings do not print credential values or read a secret file into output. Retained. |
| Large PNG | `docs/assets/brave-hermes-hero.png` | Static documentation image, not executable plugin content. Retained. |

`tests/test_distribution.py` checks the real upstream manifest parser, installer
version guard, community scan policy and deprecated-import scanner. CI runs it
with current Hermes. The existing plugin-manager tests verify that denying
override permission preserves the built-in tool and that a subsequent explicit
grant enables the intended handler.

The source archive includes the runtime, tests, scripts and public documentation.
An explicit package file selection prevents local caches, plans and verification
homes from entering a build. The wheel contains the Python package and entry-point
metadata. Both artefacts must pass scanning before release.

Any new high or critical finding, a non-safe verdict, or a deprecated runtime
import fails the distribution gate. Investigate and fix it before publishing;
do not weaken the scanner, suppress a meaningful test or allow deprecated imports.
