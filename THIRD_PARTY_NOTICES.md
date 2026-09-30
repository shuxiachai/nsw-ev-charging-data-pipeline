# Data sources and third-party notices

The MIT license applies to the original project software and project-authored documentation. It does not replace publisher licenses for input data, archived publications or University teaching materials.

On 30 September 2026, the repository owner confirmed authorization to publish the project's data materials. The v0.1.0 snapshot includes the frozen inputs needed for reproduction on that basis. Existing publisher attributions and provider-specific license metadata are retained unchanged.

| Material | Attribution and retained information |
| --- | --- |
| TfNSW charging locations | Transport for NSW; catalogue Creative Commons Attribution information and original metadata retained |
| ABS SA4 boundaries | Australian Bureau of Statistics; original archive and source metadata retained |
| OpenStreetMap observations and geometry | OpenStreetMap contributors; ODbL attribution and source identifiers retained |
| Open Charge Map export | Open Charge Map and the individual upstream providers; per-provider license fields remain in the source reference and `external_site.data_license` |
| JOLT, Ampol and other operator/venue evidence | Original publishers, source URLs, capture times and hashes retained |
| Council and government evidence | Original issuing bodies and full source locators retained |
| Assignment brief and rubric | University of Sydney teaching materials, retained to explain coursework provenance |

The archived OCM reference marks provider 15 as `IsOpenDataLicensed=false` and supplies no license text. Its metadata is retained as supplied; the owner's publication authorization does not rewrite that field as an open-data license. No uniform new license is assigned to the combined third-party snapshot.

The detailed [source register](docs/sources.md), adjacent `.meta.json` files, and DuckDB `source_snapshot` table record provenance. Source URLs, dates, original license fields and evidence relationships should accompany further redistribution.

The fixture under `examples/` is synthetic project-authored data and is covered by the project MIT license. It contains no real charger locations.
