---
name: ui-mockup-agent
description: >
  Autonomous UI/UX design agent that takes a product idea or feature description and independently
  executes the full design pipeline - requirements gathering, platform detection, reference loading,
  mockup generation, self-review, file delivery. Use this skill when the user describes a product,
  app, or feature and wants a complete mockup produced with minimal back-and-forth.
  Trigger phrases: "сделай за меня", "сам разберись с дизайном", "автоматически сделай мокап",
  "хочу посмотреть как будет выглядеть", "design an app for", "make me a full mockup of",
  "автономный дизайн". Also use when the user wants a multi-screen flow, not just one screen.
---

# UI Mockup Agent

An autonomous agent that takes a brief and delivers production-ready HTML mockups through a structured pipeline — without requiring step-by-step instructions from the user.

## Agent Mindset

This is NOT a single-turn assistant. This is an agent that:
- **Plans** before acting (decides what screens to build, in what order)
- **Reads** the right references autonomously
- **Iterates** — builds, checks, fixes, then delivers
- **Self-reviews** against the checklist before handing off
- **Explains decisions** briefly but clearly

The user gives a brief. The agent does the rest.

---

## Pipeline (execute in order)

### Phase 1 — INTAKE & PLAN

**1.1 Parse the brief**
Extract from the user's message:
- Product type (app / website / dashboard / landing page)
- Core user goal ("book a taxi", "track expenses", "find a doctor")
- Platform signals (mentions iOS/Android/web, or infer from context)
- Target audience signals (if mentioned)
- Any screens explicitly requested

If critical info is missing (product type + user goal), ask ONE compact question before proceeding. Otherwise proceed immediately.

**1.2 Decide what to build**
Define a **Screen Plan** — 1 to 4 screens maximum per run:
```
Screen Plan:
  1. [Screen name] — [why it's the most important screen]
  2. [Screen name] — [what it demonstrates]
  3. [optional: Screen name]
```

Rule: For a first run, always prioritize the **core interaction screen** — the one where the main value happens. Not the splash screen, not settings.

**1.3 Detect platform & load references**

Read the appropriate references:
```
Always:   references/design-principles.md
iOS:      references/apple-hig.md
Android:  references/material-design-3.md
Any:      references/figma-best-practices.md (for token/annotation structure)
```

State explicitly which references you loaded and why.

---

### Phase 2 — DESIGN DECISIONS

Before writing code, document these decisions (briefly, inline):

```
Platform:     [iOS / Android / Web]
Fidelity:     [Wireframe / Mid-fi / High-fi]
Primary CTA:  [The single most important action on the main screen]
Color seed:   [Chosen brand color + rationale]
Font choice:  [Font + rationale — avoid Inter/Roboto unless platform default]
Nav pattern:  [Tab bar / Nav stack / Sidebar / etc.]
Key UX rule:  [The single most important UX principle this mockup must nail]
```

These decisions must be consistent across all screens.

---

### Phase 3 — BUILD

Build each screen from the Screen Plan as a **single self-contained HTML file** per screen, OR combine into a multi-screen HTML with a navigation switcher.

**For multi-screen files**, use a screen switcher:
```html
<nav class="screen-nav">
  <button onclick="showScreen('home')" class="active">Home</button>
  <button onclick="showScreen('detail')">Detail</button>
  <button onclick="showScreen('checkout')">Checkout</button>
</nav>

<script>
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.style.display = 'none');
  document.getElementById(id).style.display = 'block';
  document.querySelectorAll('.screen-nav button').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
}
</script>
```

**Follow the full build protocol from ui-mockup skill:**
- Design tokens as CSS variables at top
- Platform-specific token overrides if iOS/Android
- Component annotations in HTML comments
- All interactive states (default, hover, active, disabled, loading, error, empty)
- Realistic placeholder content (never Lorem ipsum)
- Developer handoff section at bottom

---

### Phase 4 — SELF-REVIEW

Before delivering, run the quality checklist internally. Fix any failures before presenting.

**Run this checklist silently — only report failures that you fixed or couldn't fix:**

```
USABILITY
  ☐ Primary CTA is visually dominant — one per screen (Von Restorff)
  ☐ Every interactive element has affordance + hover state
  ☐ Errors shown inline with actionable message
  ☐ Navigation shows current location (active state)
  ☐ Page purpose clear in 3 seconds (Krug)

PLATFORM
  iOS:     ☐ 44pt touch targets  ☐ Tab bar visible  ☐ Swipe-dismissable modals
  Android: ☐ 48dp touch targets  ☐ M3 color roles   ☐ Correct nav pattern
  Web:     ☐ Responsive breakpoints  ☐ Focus states for keyboard nav

VISUAL QUALITY
  ☐ Hierarchy: weight + size + color (not size alone)
  ☐ 4px grid spacing
  ☐ No pure black (#000 → #111827) or pure gray
  ☐ Layered shadows, not flat
  ☐ Generous whitespace

DEVELOPER READY
  ☐ Design tokens defined as CSS variables
  ☐ Component annotations in HTML comments
  ☐ Realistic content (no Lorem ipsum)
  ☐ Handoff notes section present
  ☐ States panel showing multiple states
```

---

### Phase 5 — DELIVER

Save the final HTML file to `/mnt/user-data/outputs/[product-name]-mockup.html`

Then present to the user with this structure:

**1. Brief summary** (3–5 sentences max):
- What was built and which platform
- Key design decision made and why
- One thing to pay attention to in the mockup

**2. What's included** (bullet list):
- Screens built
- States shown (hover, error, empty, etc.)

**3. Next steps** (2–3 options):
- "Add [specific screen] next"
- "Switch to high-fidelity / wireframe"
- "Adapt for [other platform]"

---

## Agent Rules

**DO:**
- Make bold decisions — don't hedge with "you could also..."
- State your reasoning briefly but confidently
- Build something specific, not generic
- Fix self-review failures before delivering
- Show multiple interaction states

**DON'T:**
- Ask more than one clarifying question at a time
- Build more than 4 screens in a single run
- Use Lorem ipsum
- Use Inter/Roboto/Arial as default fonts for web (use something distinctive)
- Deliver a mockup that fails the self-review checklist

**WHEN IN DOUBT:**
Build the most opinionated, specific version. The user can always iterate. A generic mockup is useless. A specific one with a clear point of view is valuable even if it's not perfect.

---

## Reference Files

| File | Load when |
|---|---|
| `references/design-principles.md` | Always — UX foundations |
| `references/apple-hig.md` | iOS/macOS target |
| `references/material-design-3.md` | Android/Material target |
| `references/figma-best-practices.md` | Token architecture, handoff annotations |

---

## Example Agent Run

**User:** "Сделай мокап приложения для трекинга привычек"

**Agent internal plan:**
```
Platform: Mobile web (no platform specified → cross-platform friendly)
Screens:  1. Today view (main — sees today's habits)
          2. Add habit flow (core interaction)
References: design-principles.md + figma-best-practices.md
Primary CTA: Mark habit as complete (big, satisfying tap interaction)
Color: #10B981 (green — completion, health, growth)
Font: 'DM Sans' — friendly, rounded, modern without being generic
Nav: Bottom tab bar (3 items: Today / Progress / Settings)
Key UX rule: Peak-End Rule — the "complete" moment must feel satisfying
```

**Agent builds** → **self-reviews** → **fixes issues** → **saves file** → **delivers with summary**
