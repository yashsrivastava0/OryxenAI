# Pinned theme fixture

`index.html` and `styles.css` are the single portfolio theme that Content
Architect's page content is shaped to (see D-118) and that the future Code
Generator will write against: it produces the real `index.html`, attaches this
`styles.css` unchanged, then verifies and previews the result (D-116, D-121).

These files are reference input only. The application does not serve them and
no stage renders them: previewing belongs to the Code Generator, not Content
Architect.

The Code Generator now exists. The packaged, byte-pinned copy of this theme (with
its local fonts, hero art, manifest and executable markup contract) lives in
`src/oryxenai/themes/editorial_forest/v1/`; a test fails if its stylesheet drifts
from `styles.css` here. These files remain reference input only.
