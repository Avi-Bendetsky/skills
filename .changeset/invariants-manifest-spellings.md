---
"mattpocock-skills": patch
---

`scripts/check-invariants.sh` no longer lets an unpromoted skill ship in the plugin manifest under a spelling the gate did not recognise. A trailing slash (`./skills/in-progress/x/`) or a missing `./` (`skills/personal/x`) used to read as "not listed" and the gate stayed green; both now fail rule 4, and any other non-canonical spelling (`./skills/./x/y`, `../`, an absolute path) fails rule 6, which now requires `./skills/<bucket>/<skill>`. A public skill listed without the `./` now fails rule 6 rather than rule 2. Covered by the new `scripts/check-invariants.test.mjs`, which the `Skill invariants` workflow runs.
