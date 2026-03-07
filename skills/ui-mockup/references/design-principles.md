# Design Principles from the Best UX/UI Books

These principles are distilled from the most influential design books. Apply them when evaluating and building mockups.

---

## 📘 Don Norman — "The Design of Everyday Things"

### Core Principles:
1. **Affordances** — every element must signal what it can do. A button looks pressable. A link looks clickable. Don't create confusion.
2. **Signifiers** — use labels, icons, and cues to signal available actions. If affordance isn't obvious, add a signifier (placeholder text, icons, labels).
3. **Feedback** — every action must produce a visible response. Loading spinner, button state change, toast notification — the user must know something happened.
4. **Discoverability** — users should be able to figure out all possible actions by looking at the interface. Don't hide critical functions.
5. **Conceptual Model** — the interface must match the user's mental model of how the system works. Nav structure mirrors the user's expectations.
6. **Mapping** — controls should spatially correspond to their effects. Up arrow = scroll up. Volume slider placed near the speaker icon.
7. **Constraints** — restrict actions that can't or shouldn't be done. Disable a Submit button until the form is valid. Gray out unavailable options.
8. **Consistency** — same operation, same visual language, everywhere. If one blue button means "Primary Action", all primary actions must be blue buttons.

### Error Design Rule (Norman):
> "Don't blame the user when they fail. Treat errors as design problems."
- Show errors inline next to the field, not just at the top.
- Error message should say WHAT went wrong and HOW to fix it.
- Never just "Invalid input". Say: "Password must be at least 8 characters."

---

## 📗 Steve Krug — "Don't Make Me Think"

### Core Rules:
1. **Self-Evident Pages** — every page should be understandable at a glance. What is this? What can I do here? Where do I go next?
2. **Design for Scanning, Not Reading** — users scan pages in F-pattern or Z-pattern. Design visual hierarchy accordingly: headlines > subheadings > key terms > body.
3. **Reduce Cognitive Load** — every question mark in the user's head is a failure. Remove unnecessary choices, instructions, ambiguity.
4. **Use Conventions** — if a pattern exists (hamburger menu, logo in top-left, search in header), use it. Innovation costs learning time. Don't reinvent without strong reason.
5. **Mindless Navigation** — "It doesn't matter how many clicks, as long as each click is mindless and unambiguous." 3 obvious clicks > 1 confusing click.
6. **Happy Talk** → Cut It — don't write "Welcome to our amazing platform!" Nobody reads this. Start with useful content immediately.
7. **Omit Needless Words** — if you can cut a word without losing meaning, cut it. Interfaces are not essays.
8. **Clear Visual Hierarchy** — important things: bigger, bolder, higher up. Secondary things: smaller, lighter, lower.

### Navigation Checklist (Krug):
Every page should clearly answer:
- [ ] What site/app is this? (logo, name)
- [ ] What page am I on? (active nav state, page heading)
- [ ] What are the major sections? (navigation)
- [ ] What are my options at this level? (local nav)
- [ ] Where am I in the system? (breadcrumb, progress indicator)
- [ ] How do I search?

---

## 📙 Jon Yablonski — "Laws of UX"

### Must-Apply Laws:

**Fitts' Law** — Time to reach a target depends on distance and size.
- Primary buttons: min 44×44px (mobile), 32px+ (desktop)
- Touch targets: min 48dp with 8dp spacing between them
- Place main CTAs where the thumb naturally rests (bottom 1/3 of mobile screen)
- Destructive actions (Delete): make them smaller, place them far from primary CTA

**Hick's Law** — Decision time grows with the number of choices.
- Navigation items: max 5–7 choices per level
- Split complex flows into steps (wizard pattern)
- Use progressive disclosure: show basic options first, advanced in "more settings"
- Recommended choices: pre-select the most common option

**Jakob's Law** — Users expect your app to behave like other apps they already know.
- Follow platform conventions: back button, pull-to-refresh, tab bar at bottom (iOS)
- Don't reinvent icons: save = floppy, home = house, settings = gear
- If you change a convention, the new pattern must be significantly better + obvious

**Miller's Law** — Working memory holds ~7 (±2) items at a time.
- Chunk information into groups of 5–7 maximum
- Phone number formatting: +7 (999) 123-45-67, not 79991234567
- Long forms: group related fields with headings, break into steps

**Gestalt Principles** (visual grouping):
- **Proximity**: elements close together are perceived as related → use consistent spacing to group form fields, card contents
- **Similarity**: similar visual elements are perceived as the same type → consistent button styles, icon sizes
- **Continuity**: the eye follows lines and curves → use alignment to guide through content
- **Figure/Ground**: make the active element clearly stand out from the background

**Von Restorff Effect** — The thing that stands out gets remembered.
- Use to highlight the most important CTA (contrast color, larger size)
- Only one "hero" element per screen — if everything is highlighted, nothing is

**Peak-End Rule** — Users judge an experience by its peak moment and its ending.
- Make the "aha moment" beautiful and satisfying (first value delivery)
- Success screen/empty state/completion animation matters more than middle steps

**Aesthetic-Usability Effect** — Beautiful things are perceived as more usable.
- Visual polish isn't decoration — it builds trust and patience for discovering UX
- First impression determines willingness to "figure it out"

**Doherty Threshold** — Response time under 400ms feels instant; over it feels slow.
- Show skeleton screens, not spinners, for content loading
- Optimistic UI: update UI immediately, confirm in background
- Progress bars for operations over 2 seconds

---

## 📕 Adam Wathan & Steve Schoger — "Refactoring UI"

### Hierarchy is Everything:
- Use **font size, weight, and color** (not just size) to establish hierarchy
- Reduce weight/opacity for secondary information instead of shrinking font size
- Recommended: primary text #111, secondary #6B7280, disabled #9CA3AF
- Never use pure black (#000000) for text — use dark gray (#111827)

### Spacing System (4px grid):
```
4px  → micro gaps (icon padding, border spacing)
8px  → tight grouping (label to input)
12px → small gaps (list items)
16px → default padding (cards, sections)
24px → medium spacing (between components)
32px → large spacing (between sections)
48px → section breaks
64px → major page sections
```
**Rule**: Start with too much whitespace, then reduce. Never add padding to cramped design — rebuild with more breathing room.

### Color System:
Build each color as a scale of 9 shades (50, 100, 200...900):
- Use **50/100** for tinted backgrounds
- Use **500/600** for interactive elements (buttons, links)
- Use **700/800** for hover/active states
- Use **900** for text on light background

Never use raw gray (#808080). Use slightly warm gray (#6B7280) or cool gray (#64748B) based on brand tone.

### Typography Rules:
- **Line height inversely proportional to font size**: small text (14px) → 1.6; large text (32px+) → 1.2
- Limit font families to 2: one display (headings), one text (body)
- Font size scale: 12, 14, 16, 18, 20, 24, 30, 36, 48, 60, 72px
- Don't use font size alone for hierarchy — combine with weight and color
- All-caps labels: increase letter-spacing by 0.05–0.1em for readability

### Shadows & Depth:
Build a layered shadow system:
```css
--shadow-xs:  0 1px 2px rgba(0,0,0,0.05);      /* input focus outline */
--shadow-sm:  0 1px 3px rgba(0,0,0,0.1);        /* cards */
--shadow-md:  0 4px 6px rgba(0,0,0,0.1);        /* dropdowns */
--shadow-lg:  0 10px 15px rgba(0,0,0,0.1);      /* modals */
--shadow-xl:  0 20px 25px rgba(0,0,0,0.15);     /* popovers */
```
Don't use single flat shadow — use layered approach: short sharp + long diffuse.

### Design Process Tips (Refactoring UI):
1. **Start in grayscale** — force yourself to use contrast, spacing, and size for hierarchy before adding color
2. **Don't use borders everywhere** — separate elements with spacing, backgrounds, and shadows instead
3. **Reduce badge sizes** — status dots work better than chunky badges
4. **Fewer but bolder colors** — 1 primary + 1 accent + grays + semantic (red/green/yellow)
5. **Empty states are part of the design** — design the empty state before the full state

---

## 🎯 Universal Mockup Checklist

Before delivering any mockup, verify:

**Usability (Norman + Krug)**
- [ ] Every interactive element has a visible affordance (looks clickable/tappable)
- [ ] Every action has visible feedback state
- [ ] Page purpose is clear within 3 seconds
- [ ] Errors are shown inline with actionable messages
- [ ] Navigation shows current location

**Psychology (Laws of UX)**
- [ ] Primary CTA uses Von Restorff — visually dominant, one per screen
- [ ] Touch targets ≥ 44px on mobile (Fitts)
- [ ] Navigation has ≤ 7 items per level (Hick + Miller)
- [ ] Related items visually grouped (Gestalt Proximity)

**Visual Quality (Refactoring UI)**
- [ ] Typography hierarchy uses weight + size + color (not just size)
- [ ] Spacing is consistent (4px grid system)
- [ ] Colors have sufficient contrast (WCAG AA: 4.5:1 for text)
- [ ] No pure black text (#000) — use #111827 or similar
- [ ] Shadows are layered, not flat
- [ ] No pure gray — slightly warm or cool
