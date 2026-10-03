<operation name="generate_page">
Write the page body for the CONTENT in the untrusted input, following the theme exemplar's structure exactly and using the DERIVED values verbatim.

Work in this order, silently:
1. Read DERIVED first and use its theme-specific values verbatim.
2. Decide which optional elements exist from the empty-field rules.
3. Write every region of the exemplar in order, replacing each placeholder with its exact approved value and repeating blocks once per entry.
4. Re-check: every approved value appears in the field placement shown by the theme exemplar, repeated blocks match the input counts, nothing extra was added, and the JSON is valid.

Return only the JSON object with "lang" and "body_html".
</operation>
