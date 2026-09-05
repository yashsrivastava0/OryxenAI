You are redesigning the authentication / sign-in experience of my application, OryxenAI.

I am attaching:

1. REFERENCE IMAGE — the new visual direction I want.
2. OLD SCREENSHOTS — the current `/sign-in` implementation that must be replaced/redesigned.

Treat the reference image as VISUAL DIRECTION, not something to blindly reproduce pixel-for-pixel.

Your job is to understand the existing codebase first, preserve the real authentication architecture, and redesign the current sign-in experience into a polished, production-quality 2026 interface with strong frontend personality.

==================================================
PRODUCT CONTEXT
==================================================

OryxenAI is NOT a generic chatbot and NOT a generic AI website builder.

It is an AGENTIC PORTFOLIO-GENERATION STUDIO.

It transforms raw human experience — resumes, career history, achievements, project notes, etc. — into one bespoke, verified, deployable personal portfolio.

The user moves through a deliberate creative pipeline:

01 — DISCOVERY
Clarify the person's story, goals, achievements, audience and positioning.

02 — CONTENT
Architect the portfolio structure, routes, sections and finished copy.

03 — DESIGN
Establish visual direction, typography, colors, layout and motion.

04 — PREPARE
Compile verified build briefs and required assets.

05 — BUILD
Generate the actual portfolio code and verify the layouts.

06 — PREVIEW
Inspect the completed portfolio in Desktop, Tablet and Mobile views.

This is ONE living portfolio, not a dashboard containing many projects.

The core philosophy is:

"Where is my portfolio right now, and what is the next step?"

Every important stage has an explicit human approval handoff.

Nothing should feel like:
- a chatbot wrapper
- an AI template generator
- a crypto landing page
- a generic SaaS dashboard
- an AI-generated Dribbble shot

==================================================
CURRENT TECH STACK
==================================================

Do NOT unnecessarily replace or expand the stack.

Frontend:
- Preact 10
- TypeScript
- Vite
- Vitest
- Vanilla CSS
- CSS custom properties / design tokens
- Inline/code-native SVG icons
- Self-hosted fonts where already available
- No Tailwind
- No heavy UI framework
- No unnecessary animation library

Auth/server integration:
- FastAPI
- Jinja2 server templates
- Vanilla JavaScript ES modules for auth bootstrap
- Supabase JS
- Google OAuth PKCE

IMPORTANT:
Do NOT migrate the sign-in page to another framework just to accomplish the redesign.

Do NOT add Framer Motion, GSAP, Tailwind, shadcn, Material UI, Bootstrap or another dependency unless an existing dependency already provides something genuinely necessary.

Prefer:
- CSS
- CSS keyframes
- transitions
- inline SVG
- a tiny amount of vanilla JS when needed

==================================================
FIRST: INSPECT BEFORE EDITING
==================================================

Before making changes, inspect the project and locate:

- the `/sign-in` route
- its Jinja/template markup
- its current CSS
- auth-related static JS
- `app-auth-bootstrap.mjs` or equivalent
- Supabase Google OAuth trigger
- existing typography/font loading
- existing CSS design tokens
- existing responsive rules
- any shared shell/header code

Understand the authentication flow BEFORE changing the UI.

Do not rewrite working OAuth logic merely because the visual design changes.

The frontend redesign must remain compatible with the existing server-rendered authentication architecture.

==================================================
REAL AUTHENTICATION LOGIC — PRESERVE THIS
==================================================

The real flow is approximately:

Visit `/`
→ session checked
→ unauthenticated user goes to `/sign-in`
→ user presses "Continue with Google"
→ Supabase Google OAuth PKCE
→ `/auth/callback`
→ user is resolved
→ new user may be sent to `/onboarding`
→ existing admitted user goes to `/app`

There is therefore no need to invent a traditional:
- email field
- password field
- "forgot password"
- password signup form

Google is the main authentication mechanism.

DO NOT add fake authentication features simply because other login pages have them.

For new users, the same Google authentication can eventually lead into onboarding.

Therefore do not add a fake separate signup form.

If helpful, under the Google CTA use:

"New here? Your workspace is created after verification."

rather than inventing a second authentication system.

==================================================
WHY THE CURRENT SCREEN MUST CHANGE
==================================================

Study the OLD screenshots.

The current implementation has several problems:

1. Authentication is buried below the fold.

2. The giant:
   "Make the work legible before making it public."
   headline consumes too much of the first viewport.

3. A user visiting `/sign-in` has to scroll before reaching the main action.

4. The visual hierarchy prioritizes marketing copy above authentication.

5. There is excessive empty vertical space.

6. "IDENTITY PROOF" and the explanatory left panel feel technical and generic.

7. The auth surface feels like documentation rather than entering a premium creative application.

8. The current page does not visually communicate the OryxenAI agentic workflow.

9. The page feels static.

10. The current layout is not using the application's unique product architecture as its visual identity.

The redesign should solve these problems.

==================================================
PRIMARY UX OBJECTIVE
==================================================

A first-time visitor should understand within approximately 3–5 seconds:

1. This is OryxenAI.
2. It turns professional experience into a finished portfolio.
3. The workflow is guided and staged.
4. The user's work remains under their control.
5. They can enter using Google.
6. Authentication is the obvious primary action.

On normal desktop/laptop screens the Google authentication CTA MUST be visible WITHOUT SCROLLING.

This includes approximately:

1366×768
1440×900
1536×864
1920×1080

Do not design only for a giant Figma artboard.

==================================================
VISUAL DIRECTION
==================================================

Use the attached new reference image as the main visual direction.

The visual system is called:

"EDITORIAL SWISS — THE LIVING DRAFT"

It should feel like:

- a high-end editorial design studio
- an architectural working document
- a creative instrument
- a serious professional product
- deliberate modernist typography
- a living system rather than a static landing page

It should NOT look like generic "AI software."

==================================================
DESIGN TOKENS
==================================================

Respect the existing OryxenAI design language.

Primary palette:

Canvas:
#F3F0E8

Paper:
#FCFBF7

Ink:
#171A19

Graphite:
#626660

Hairline rule:
#D3CFC4

OryxenAI signal / electric cobalt:
#3157E7

Positive:
#287356

Attention:
#A9601E

Critical:
#B33F3A

Use cobalt carefully.

It should feel valuable because it appears selectively.

Do NOT turn the entire UI blue.

==================================================
TYPOGRAPHY
==================================================

Use the application's editorial typography.

Display:
Newsreader / existing editorial serif / Georgia fallback

Sans:
system-ui / Inter where already available

Mono:
ui-monospace / SFMono / Consolas

The serif should provide personality.

The sans typography should make the application functional and modern.

The mono typography should be used sparingly for:

- stage numbers
- status labels
- tiny metadata
- system-like annotations

Do not turn everything into uppercase tracking.

==================================================
CORE DESKTOP COMPOSITION
==================================================

Create an intentional asymmetric desktop composition.

Approximate structure:

LEFT / PRODUCT STORY:
~55–58%

RIGHT / AUTHENTICATION:
~42–45%

Do NOT mechanically use these percentages if another proportion works better.

The page should feel designed, not mathematically divided.

Use approximately 100svh / 100dvh as the first-screen composition where appropriate, while allowing natural height when required.

--------------------------------------------------
A. TOP HEADER
--------------------------------------------------

Create a slim architectural header.

Left:

ORYXENAI logo / wordmark

Beside it, subtle descriptor:

AGENTIC PORTFOLIO STUDIO
FROM EXPERIENCE TO IMPACT

Right side may contain only very restrained utility content if routes genuinely exist.

Do NOT invent a giant navigation menu.

Possible tiny items only if they already exist:
About
Docs
Privacy
Terms

Otherwise leave it minimal.

Use a thin hairline beneath the header.

--------------------------------------------------
B. LEFT JOURNEY RAIL
--------------------------------------------------

This is important.

Instead of a meaningless illustration, use OryxenAI's REAL WORKFLOW as visual personality.

Create a narrow vertical stage rail:

01
DISCOVERY
Your story

02
CONTENT
Your narrative

03
DESIGN
Your look

04
PREPARE
The brief

05
BUILD
The site

06
PREVIEW
Go live

Connect stages with subtle hairlines.

This rail is NOT actual logged-in user progress on `/sign-in`.

It is a preview of the OryxenAI process.

Do not falsely imply the unauthenticated user is currently in Discovery.

Instead use a travelling cobalt "signal" animation through the rail to represent the product pipeline.

--------------------------------------------------
C. MAIN LEFT HERO
--------------------------------------------------

Do NOT restore the enormous old headline.

Use a controlled editorial hero.

Possible eyebrow:

TRANSFORM YOUR EXPERIENCE

Possible hero:

"From experience
to opportunity."

or:

"Turn experience
into a portfolio
worth reviewing."

Use the final wording that works most naturally with the layout.

Supporting copy should explain the product accurately:

"OryxenAI turns your experience into a bespoke, verified portfolio through a guided creative pipeline — from discovery and content architecture to design, build and preview."

Or refine this into concise, natural product copy.

Keep it around 2–3 short lines.

Below it use 3 compact value indicators.

For example:

GUIDED BY SPECIALIZED AGENTS
Discovery → content → design → build.

BUILT AROUND YOU
One portfolio. One evolving narrative.

YOU APPROVE EVERY HANDOFF
Nothing moves forward without your review.

These should look editorial, not like generic SaaS feature cards.

Avoid three floating rounded cards.

Use hairline dividers and typography.

==================================================
VISUAL / DECORATIVE SYSTEM
==================================================

The reference image includes strong visual texture.

However, DO NOT simply insert random AI-generated mountains because they look impressive.

The final implementation should preferably use CODE-NATIVE graphics.

Create an abstract architectural / terrain / document-system composition using:

- inline SVG
- clipping masks
- CSS gradients used VERY subtly
- thin contour lines
- grid geometry
- paper texture
- architectural forms
- structured coordinates
- rules and nodes

It can evoke:
- source material
- transformation
- structure
- architecture
- compilation
- a living draft

without looking like "AI galaxy art."

If an existing approved brand image already exists, it may be integrated carefully.

Otherwise prefer CSS/SVG rather than introducing a large random stock image.

==================================================
SIGNATURE ANIMATION — THE LIVING DRAFT
==================================================

This is the signature OryxenAI motion language.

Build a thin cobalt signal line.

It should feel like an editorial proofing mark or architectural drawing becoming active.

On the sign-in page:

A cobalt signal can slowly travel through:

Discovery
→ Content
→ Design
→ Prepare
→ Build
→ Preview

Then rest before repeating.

Suggested cycle:
8–12 seconds

Do NOT make it continuously frantic.

Each stage node can receive:
- subtle 1–2px expansion
- temporary cobalt state
- label opacity increase

The connector activates briefly as the signal passes.

No glowing neon cyberpunk effect.

No large bloom.

No particles.

No sparkles.

==================================================
PAGE ENTRANCE ANIMATION
==================================================

On first load:

0ms:
canvas appears

~80ms:
header rules and structural lines resolve

~140–350ms:
small metadata / stage rail softly appears

~180–600ms:
hero text reveals using a restrained vertical clip or mask

~250–650ms:
supporting copy fades + translates approximately 8px

~300–700ms:
auth surface resolves

Everything should feel finished within ~700–850ms.

Do NOT create a 3-second intro animation.

The user came here to sign in.

==================================================
AUTHENTICATION SURFACE
==================================================

The authentication area is the primary functional object.

It should be above the fold.

Use either:

- a very subtle paper sheet/card

OR

- a bounded architectural panel

Do NOT create an exaggerated floating glass panel.

Recommended hierarchy:

tiny cobalt dot / label:
WELCOME TO ORYXENAI

Headline:

"Sign in to your
private workspace."

Supporting sentence:

"Continue with Google to access your OryxenAI studio."

Then the main CTA.

[G] Continue with Google       →

The button should be approximately 54–60px high on desktop.

It should use:
- deep carbon background
- white text
- proper Google mark if already available/allowed
- restrained radius around 8–10px
- strong focus state

Not a gigantic pill.

Below it include only useful trust information.

For example:

GOOGLE-SECURED ACCESS
No additional password to remember.

PRIVATE BY DEFAULT
Your portfolio stays inside the workspace until you choose otherwise.

HUMAN APPROVAL
Nothing is published through a surprise automated handoff.

And:

"No credit card required."

Do not overload this area.

==================================================
DO NOT USE FAKE SOCIAL PROOF
==================================================

The attached reference may visually contain testimonials, profile photos, creator counts, etc.

DO NOT copy fake data from the reference.

Do NOT invent:

"Trusted by 10,000 creators"

Do NOT invent user testimonials.

Do NOT invent customer avatars.

If genuine product metrics/testimonials do not exist, leave them out.

Use real product principles instead.

==================================================
WHAT TO DO WITH THE OLD BRAND LINE
==================================================

Keep:

"Make the work legible before making it public."

But demote it.

It should become a signature detail rather than the giant hero.

Possible placements:

- narrow right-side vertical annotation
- lower-left editorial caption
- footer statement
- subtle line beside the journey rail

It should NOT occupy half the screen anymore.

==================================================
GOOGLE CTA INTERACTION
==================================================

Hover:

- background changes extremely subtly
- arrow translates ~3–4px
- border/shadow responds slightly
- duration ~140–180ms

Focus-visible:

use a clear cobalt outline/focus treatment.

Active:

translate at most 1px.

When clicked:

DO NOT instantly create an unrelated spinner.

Disable repeated activation.

Show a state such as:

"Opening Google…"

Optionally animate a thin cobalt line across the lower edge of the button.

Then allow the existing Supabase redirect to occur.

If OAuth initialization fails:
restore the CTA and show a concise inline error.

==================================================
MICROINTERACTIONS
==================================================

Add refined microinteractions without overdoing them.

Examples:

1. Small header metadata softly changes opacity on hover.

2. Journey rail labels become slightly more legible as the Living Draft signal reaches them.

3. Editorial rules may extend by 6–12px on relevant hover states.

4. Arrow icons move 3–4px rather than bouncing.

5. Auth sheet may react to pointer position by an EXTREMELY subtle 1–2px optical highlight shift.

Do not create full-card 3D tilting.

6. Tiny cobalt cursor/proofing mark may blink at a low frequency in one deliberate location.

There should never be ten unrelated animations playing simultaneously.

==================================================
MOTION PERFORMANCE
==================================================

Prefer animating:

transform
opacity
clip-path where reasonable

Avoid repeatedly animating:

width
height
top
left
large box shadows
expensive filters

The page should remain smooth on an ordinary laptop.

Do not use a canvas/WebGL scene for something that can be accomplished through SVG/CSS.

==================================================
ACCESSIBILITY
==================================================

Implement:

- semantic buttons and links
- keyboard navigation
- visible focus states
- correct contrast
- min ~44px interactive touch targets
- sensible tab order
- no information available exclusively through hover

Respect:

@media (prefers-reduced-motion: reduce)

Reduced-motion behavior should:

- stop the repeating Living Draft traversal
- remove parallax
- remove masked motion
- retain simple short fades where appropriate
- never block authentication

==================================================
RESPONSIVE DESIGN
==================================================

This redesign MUST be genuinely responsive.

Do not merely shrink the desktop artboard.

--------------------------------------------------
LARGE DESKTOP
--------------------------------------------------

Use full split editorial composition.

Journey rail + hero left.

Authentication right.

Everything important above fold.

--------------------------------------------------
LAPTOP / MEDIUM DESKTOP
--------------------------------------------------

Reduce:
- hero font size
- decorative geometry
- outer padding
- vertical gaps

Do not push the auth CTA below the viewport.

This is critical.

--------------------------------------------------
TABLET
--------------------------------------------------

Collapse the left visual complexity.

Possible structure:

header

short hero + process indicator

auth panel

condensed stage rail

Authentication still has stronger priority than decoration.

--------------------------------------------------
MOBILE
--------------------------------------------------

Do NOT use a miniature version of the desktop split layout.

Recompose it.

Recommended order:

ORYXENAI

small descriptor

short headline

1–2 lines explanation

Continue with Google

privacy / approval reassurance

condensed horizontal or vertically collapsed process:

01 Discover
02 Content
03 Design
04 Prepare
05 Build
06 Preview

Then optional brand line.

The Google CTA should appear very early.

Avoid forcing a mobile user to scroll through a giant marketing hero before authentication.

Use:

min-height: 100svh

rather than relying only on 100vh where mobile browser chrome may interfere.

No horizontal overflow at 375px.

==================================================
SPACING / GEOMETRY
==================================================

Follow a 4px rhythm:

4
8
12
16
24
32
48
64

Control radius:
~8px

Paper/sheet radius:
~12–16px

Pills only where pills semantically make sense.

Borders:
1px solid design-token rule

Use very restrained shadows.

For example approximately:

0 4px 20px -4px rgba(23, 26, 25, 0.06)

Avoid huge blurred shadows.

==================================================
ANTI-"AI SLOP" RULES
==================================================

STRICTLY AVOID:

- purple/blue gradient blobs
- excessive glassmorphism
- neon glowing borders
- glowing AI orbs
- robot icons
- sparkles everywhere
- generic stars
- fake dashboards
- fake analytics
- fake AI-generated testimonials
- giant pill buttons everywhere
- infinite floating objects
- random 3D chrome objects
- excessive rounded cards
- giant gradient typography
- fake progress percentages
- circular AI loading meters
- "Ask AI anything" copy
- generic "AI-powered future" slogans

This should feel like ORYXENAI, not "AI SaaS Template #47."

==================================================
IMPORTANT PRODUCT LANGUAGE
==================================================

Use terminology that reinforces the actual product:

Portfolio
Discovery
Content
Design
Prepare
Build
Preview
Living Draft
Review
Approve
Workspace
Narrative
Verified
Handoff

Use the word "agentic" sparingly.

Don't repeatedly say "AI-powered."

Show what the product does instead.

==================================================
DO NOT BREAK THESE THINGS
==================================================

Do not change:

- Supabase OAuth behavior
- PKCE flow
- callback route
- session logic
- backend access/capacity decisions
- `/onboarding`
- `/access-not-approved`
- `/account-unavailable`
- existing `/app` routing
- auth security logic

This task is primarily a frontend/auth UX redesign.

Do not use the redesign as an excuse for an unrelated architecture rewrite.

==================================================
IMPLEMENTATION QUALITY
==================================================

Refactor the existing sign-in markup/CSS when appropriate rather than stacking more styles on top of broken old styles.

Remove obsolete sign-in CSS once the new version replaces it.

Avoid:
- duplicate media queries
- conflicting selectors
- !important everywhere
- inline style clutter
- magic absolute positioning that works only at 1920px

Prefer:
- named layout regions
- CSS custom properties
- grid/flex
- clamp()
- min()
- max()
- logical responsive rules

Use absolute positioning only for genuinely decorative elements.

==================================================
TESTING
==================================================

After implementation, test the actual sign-in page at least at:

1920×1080
1536×864
1440×900
1366×768
1024×768
768×1024
430×932
390×844
375×812

Verify:

- no horizontal overflow
- Google CTA visible without scroll on common desktop/laptop screens
- readable typography
- nothing overlaps
- hero does not dominate authentication
- stage rail does not collide with content
- navigation/header remains usable
- OAuth CTA still works
- focus-visible works
- reduced motion works
- no layout jump after fonts load
- no JS console errors

Run the project's relevant existing frontend/tests/build checks.

==================================================
FINAL RESULT I WANT
==================================================

I want the sign-in experience to feel like I entered a sophisticated creative studio before I even authenticate.

The reference image should influence:

- composition
- editorial hierarchy
- typography
- architectural rules
- restrained depth
- process visualization
- premium feel

But the implementation should be MORE product-specific than the reference.

The final result should communicate:

"Your experience enters here.
OryxenAI structures it through a deliberate agentic pipeline.
You remain in control.
Sign in and enter the studio."

The primary user journey must remain extremely simple:

ARRIVE
→ understand what OryxenAI does
→ see Google authentication immediately
→ sign in
→ continue through the existing auth/onboarding flow.

Make the page memorable because of OryxenAI's own visual language, not because it has more effects.

==================================================
WORKFLOW FOR YOU
==================================================

Proceed autonomously:

1. Inspect the relevant implementation.
2. Identify what is currently causing the oversized/poor hierarchy.
3. Preserve working auth logic.
4. Redesign the markup.
5. Rebuild the sign-in CSS cleanly.
6. Add the restrained Living Draft animation.
7. Implement responsive states.
8. Add reduced-motion support.
9. Test the route.
10. Run build/tests.
11. Fix any regression you find.

Do not stop after producing a plan.

Actually implement the redesign.

When finished, give me a concise report containing:

- files changed
- major UX changes
- animations added
- responsive behavior
- auth behavior preserved
- tests/build run
- anything that still needs manual verification

Do not redesign unrelated OryxenAI application screens during this task.