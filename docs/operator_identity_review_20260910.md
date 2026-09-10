# Pending operator identity: Richmond Counties Energy observation

Review date: 10 September 2026. This decision records uncertainty; it does not
establish that the original operator name or the external website is false.

## Evidence and decision

TfNSW source row **1620** (record `r_2de8112d918bc8ace5e3`) describes two 22 kW AC
plugs at **59 Lennox St, Richmond, 2753**, with the operator label **Counties
Energy**. The source category is Existing Destination Chargers. The original
row, operator label, coordinates and equipment values remain unchanged.

The frozen OCM operator lookup has ID **3547**, title **Counties Energy**, and
website `https://www.countiesenergy.co.nz/articles/ev-charging`. Canonical name
equality previously propagated this website to the Richmond location. Neither
the TfNSW row nor that OCM lookup establishes this NSW site's relationship with
the lookup entity. A `.nz` domain alone also cannot disprove a relationship.
There is no evidence here that justifies replacing the source operator with a
different company.

The reviewed **location + OCM operator ID + attribute + value** assignment is
therefore **withheld pending site-specific identity corroboration**. This is
one AC location; no DC site, site match, connector observation or DC coverage
numerator/denominator is removed by the decision.

The two reproducible originals are:

- [TfNSW CSV](../data/raw/ev_20251216.csv), SHA-256
  `43970e7751b951ab459a1be7bfd6141756c60ff8aa797debf11c5a597109865a`.
- [OCM reference lookup](../data/raw/ocm_reference.json), SHA-256
  `71c7ea6f70e8f360ff13cc64ada578d07c05af0bf9e92b5efeda591ff695f7e8`.

Logical source row numbers count CSV records, including the header as row 1;
embedded newlines mean they need not equal physical text line numbers.

## Representation and guards

[The review ledger](../config/reviewed_operator_assignments.json) binds the
complete original source values, record ID, source row, OCM ID/title, attribute,
candidate value and both original-file hashes. A missing or changed reviewed
record, lookup value or evidence file fails explicitly, requiring renewed
review rather than silently broadening the exclusion.

The `quality_issue` table and `outputs/quality_issues.csv` preserve a warning with
code `operator_assignment_pending_review`. Its JSON detail retains the review
ID/date, source operator, proposed external ID/title/value, both source paths
and hashes, and the reason for withholding. The proposed website is not an
accepted `augmentation` row. Independent validation requires the complete
warning and rejects reintroduced values under the withheld relationship.

`operator_details.csv` describes usable lookup candidates for the current
locations. This lookup row is removed there only because its sole current
assignment is withheld. Downstream URL classification therefore does not use
the pending Counties lookup. If another location with the same operator name
exists, withholding Richmond alone cannot delete that other location's
otherwise unchanged operator information. No domain-country blacklist is used.

Focused checks establish that the pre/post operator-observation sets differ by
exactly this one AC assignment and that every DC operator observation is
unchanged. They also exercise evidence drift, missing and duplicate reviews,
another same-name location, audit deletion and reintroduced assignments. These
checks establish the implementation's scope, not the true operator identity.

## Follow-up

A site-owner, council or operator publication identifying the Richmond venue
and charging operator would resolve the uncertainty. Until such evidence is
available, retain the original label and pending audit without asserting a
replacement identity. Country of incorporation or website suffix is not a
substitute for that site evidence.
