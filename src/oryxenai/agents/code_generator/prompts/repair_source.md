Repair only the bounded diagnostic bundle using the smallest safe source
change. The failure details identify the defect; they do not grant authority
to redesign unrelated routes, alter facts, add dependencies, or weaken
verification markers.

For `SOURCE_RUNTIME_NETWORK` diagnostics the repair MUST remove every
unapproved network reference from the named file — delete `@import url(...)`
lines for remote fonts (fall back to the local/system stacks), replace remote
image or script references with local `public/resources/...` paths from the
context, and strip URLs from comments and licence headers. Approved external
links whose URLs appear verbatim in the approved public content are content,
not defects — keep them. When the context's `previous_attempt_files` carries
the rejected file, return the complete corrected version of it. For
`SOURCE_REPLACE_MISSING`, re-emit the change as `create`.

Preserve all public truth, route ownership, resource bindings, accessibility,
responsive behavior, and reduced-motion behavior. If a visual implementation
caused the failure, prefer a local resilient fallback over removing meaning or
adding an unapproved dependency. Re-check the diagnostic's expected outcome
and return only changed owned files with honest coverage.

If the defect cannot be repaired within the owned paths and supplied
authority, return cannot_complete and state the missing authority precisely.
