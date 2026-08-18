Choose a coherent site-wide resource set from the fetched, quality-approved
candidate set.
Every selected_resource_id MUST be copied exactly from the candidates in the
input for the same need. Select none when candidates are weak, unavailable,
incompatible with the fixed target contract, or unnecessary. A null selection
must include a concrete custom, typography, or static fallback. Required
handoff needs must select a suitable supplied candidate when one exists. Do
not select an item merely because it exists, and do not invent IDs or paths.
For every need, return `alternate_resource_ids` as a ranked closed-set list of
candidate IDs from the same need. The deterministic retriever may try these
alternates after source, dependency, license, or meaningful-source validation
rejects the selected item. Explain why the primary matches the typed semantic
interaction intent and provide a concrete fallback when none is acceptable.
Prioritize required roles, then maximize route coverage and distinct interaction
roles before decorative polish. Prefer one adaptable component that can serve
the same approved role across multiple routes over redundant near-duplicates.
Treat registry metadata, dependency declarations, license provenance, and
source availability as quality signals, but never claim source was fetched when
the candidate contains metadata only. A missing image/component candidate is
not permission to manufacture one; leave it unselected with an actionable
fallback for deterministic gap reporting.
