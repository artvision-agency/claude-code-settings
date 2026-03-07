# Material Design 3 (M3) — Google's Design System

Source: m3.material.io

---

## Core Philosophy: "Material You"

M3 shifts from a unified "Google look" to **personal, adaptive, expressive** interfaces. The system adapts to each user (dynamic color from wallpaper), each device (responsive across phone/foldable/tablet/desktop), and each brand (customizable tokens).

Three design values:
1. **Personal** — adapts to user preferences (dynamic color, theming)
2. **Adaptive** — responsive across screen sizes and form factors
3. **Expressive** — emotionally resonant through color, shape, motion

---

## Color System

### Tonal Palettes
Every M3 theme is generated from a **single source color** → algorithm creates 5 tonal palettes (13 tones each: 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99, 100):
- Primary palette
- Secondary palette
- Tertiary palette
- Neutral palette
- Neutral Variant palette

### Color Roles (Semantic Mapping)
Don't use raw hex values — reference color roles:

| Role | Light | Dark | Usage |
|---|---|---|---|
| `primary` | deep brand | lighter brand | Key interactive elements, main buttons |
| `on-primary` | white | dark | Text/icons on primary background |
| `primary-container` | light tint | dark tint | Tinted backgrounds, chips |
| `on-primary-container` | dark | light | Text on primary-container |
| `secondary` | muted mid | muted | Less prominent components |
| `tertiary` | accent | accent | Contrasting highlights |
| `surface` | near-white | near-black | Card, sheet, dialog backgrounds |
| `surface-variant` | subtle tint | dark tint | Alternative surface |
| `on-surface` | dark | light | Primary text on surfaces |
| `on-surface-variant` | medium | medium | Secondary text, icons |
| `outline` | medium | medium | Borders, dividers |
| `error` | red | light red | Error states |

### Dynamic Color (Android 12+)
The system extracts the user's wallpaper colors and seeds the entire palette. When designing, mock with a known brand color but architect the system to be **wallpaper-adaptive**.

### Contrast Guidance
- Normal text: minimum 4.5:1 (WCAG AA) — target 7:1 (WCAG AAA) for body text
- Large text: minimum 3:1
- UI components: minimum 3:1

---

## Typography

### M3 Type Scale (15 base styles + 15 emphasized = 30 total)

| Role | Size | Weight | Line Ht | Letter Sp |
|---|---|---|---|---|
| Display Large | 57sp | 400 | 64sp | -0.25 |
| Display Medium | 45sp | 400 | 52sp | 0 |
| Display Small | 36sp | 400 | 44sp | 0 |
| Headline Large | 32sp | 400 | 40sp | 0 |
| Headline Medium | 28sp | 400 | 36sp | 0 |
| Headline Small | 24sp | 400 | 32sp | 0 |
| Title Large | 22sp | 400 | 28sp | 0 |
| Title Medium | 16sp | 500 | 24sp | +0.15 |
| Title Small | 14sp | 500 | 20sp | +0.1 |
| Body Large | 16sp | 400 | 24sp | +0.5 |
| Body Medium | 14sp | 400 | 20sp | +0.25 |
| Body Small | 12sp | 400 | 16sp | +0.4 |
| Label Large | 14sp | 500 | 20sp | +0.1 |
| Label Medium | 12sp | 500 | 16sp | +0.5 |
| Label Small | 11sp | 500 | 16sp | +0.5 |

**Rules:**
- Displays: hero headers, expressive moments
- Headlines: section titles, dialog titles
- Titles: list items, card titles, navigation
- Body: paragraphs, descriptions
- Labels: buttons, chips, form labels, tabs

Default font: **Roboto** (or Roboto Flex for variable font)

---

## Shape System

M3 uses **5 shape levels** based on corner radius:

| Token | Radius | Used for |
|---|---|---|
| Extra Small | 4dp | Chips, input fields, snackbars |
| Small | 8dp | Small buttons, small cards, menu items |
| Medium | 12dp | Cards, dialogs, medium sheets |
| Large | 16dp | Navigation rail, large cards |
| Extra Large | 28dp | FAB, side sheets, large dialogs |
| Full | 50% (pill) | FAB (extended), icon buttons, badges |

**Shape expresses personality** — rounded = friendly/approachable, angular = technical/precise.

---

## Elevation & Surfaces

M3 uses **tonal elevation** (not just shadows) — surfaces get slightly tinted at higher elevations:

| Level | dp | Tint opacity | Usage |
|---|---|---|---|
| 0 | 0dp | 0% | Canvas, background |
| 1 | 1dp | 5% | Cards, switches, menu items |
| 2 | 3dp | 8% | FAB (rest), navigation drawer |
| 3 | 6dp | 11% | FAB (hover), navigation bar |
| 4 | 8dp | 12% | App bars |
| 5 | 12dp | 14% | Dialogs, side sheets |

**Key insight**: In dark mode, tonal elevation adds `primary` color tint to surface — no harsh shadows needed.

---

## Components

### Buttons (5 variants)

```
Filled Button       → primary background — highest emphasis
Filled Tonal Button → primary-container background — medium-high
Elevated Button     → surface + shadow — medium
Outlined Button     → transparent + border — medium-low  
Text Button         → no background/border — lowest
```

Anatomy: [optional icon] + label text, pill shape (cornerRadius: full), height 40dp, padding: 24dp horizontal

### Navigation

| Component | Use case | Position |
|---|---|---|
| Navigation Bar | 3–5 top-level destinations, mobile | Bottom |
| Navigation Rail | 3–7 destinations, tablet | Left side |
| Navigation Drawer | 5+ destinations, complex hierarchy | Left overlay or permanent |

Navigation Bar specs:
- Height: 80dp
- Icon + label always visible for active item
- Inactive: icon only or icon + label (configurable)

### FAB (Floating Action Button)
- Large FAB: 96×96dp, for hero actions
- Regular FAB: 56×56dp
- Small FAB: 40×40dp
- Extended FAB: variable width, includes text label
- Always uses `primary-container` or `surface` tinting

### Cards (3 variants)
```
Elevated:  surface + level-1 elevation shadow
Filled:    surface-variant, no shadow
Outlined:  surface + outline border
```
All cards: cornerRadius Medium (12dp), padding 16dp

### Text Fields (2 variants)
```
Filled:   colored surface-variant background, bottom border only active indicator
Outlined: transparent background, full border
```
Both: 56dp height, 16dp horizontal padding, label floats on focus

### Dialogs
- Max width: 280–560dp
- cornerRadius: Extra Large (28dp)
- Always have: title (optional), body, 1–2 text buttons
- Dismiss: tap backdrop or explicit button

---

## Motion System

### Easing Curves
```
Emphasized:          cubic-bezier(0.2, 0, 0, 1.0)   — most transitions
Emphasized Decelerate: cubic-bezier(0.05, 0.7, 0.1, 1.0) — element entering
Emphasized Accelerate: cubic-bezier(0.3, 0, 0.8, 0.15)  — element leaving
Standard:            cubic-bezier(0.2, 0, 0, 1.0)   — simple state changes
Standard Decelerate: cubic-bezier(0, 0, 0, 1.0)
Standard Accelerate: cubic-bezier(0.3, 0, 1, 1)
```

### Duration Tokens
```
Short 1:  50ms   → micro interactions (ripple start)
Short 2:  100ms  → small component changes (checkbox)
Short 3:  150ms  → icons, FAB collapse
Short 4:  200ms  → chips, buttons state change
Medium 1: 250ms  → tooltips, snackbars
Medium 2: 300ms  → search bar expand, list item
Medium 3: 350ms  → cards, small dialogs
Medium 4: 400ms  → bottom sheets (small)
Long 1:   450ms  → nav drawer, full-screen transitions
Long 2:   500ms  → complex shared element transitions
Long 3:   550ms
Long 4:   600ms  → onboarding animations
Extra Long 1–4: 700ms–1000ms → expressive moments
```

### Motion Principles
- **Purposeful** — every animation should communicate meaning (what changed, why, where)
- **Natural** — physics-based easing, not linear
- **Spatial awareness** — elements enter from logical direction (forward = new screen from right, back = previous screen from left)
- **Respect Reduce Motion** — provide static alternatives for all animations

---

## Responsive Layout

### Breakpoints
```
Compact (phone portrait): 0–599dp      — 4 columns, 16dp margins
Medium (phone landscape/small tablet): 600–839dp — 8 columns, 24dp margins  
Expanded (tablet/desktop): 840dp+     — 12 columns, 24dp margins
```

### Navigation Adaptation
```
Compact  → Navigation Bar (bottom)
Medium   → Navigation Rail (left)
Expanded → Navigation Drawer (persistent left)
```

### Content Pane
On expanded screens, use **list-detail** or **supporting pane** patterns instead of stacking.

---

## Design Tokens in M3 (3-tier system)

```
Tier 1: Reference tokens (raw palette values)
  ref.palette.primary40 = #6750A4

Tier 2: System tokens (semantic roles)  
  sys.color.primary = {ref.palette.primary40}

Tier 3: Component tokens
  comp.elevated-button.container-color = {sys.color.surface}
```

**Rule**: Only ever reference Tier 2 (system) tokens in component design. Never hardcode raw values.

---

## M3 vs M2 Quick Comparison

| Aspect | M2 | M3 |
|---|---|---|
| Color | Static brand palette | Dynamic, seed-based tonal palettes |
| Shapes | Mostly rectangular | Shape tokens with 5 levels |
| Elevation | Drop shadows | Tonal surface tinting + subtle shadows |
| Typography | Complex 13-style scale | Simplified 15-style scale with roles |
| Navigation | Consistent patterns | Adaptive (bar → rail → drawer) |
| Motion | Standard easing | Physics-based, expressive easing |
| Buttons | 3 variants | 5 variants |
