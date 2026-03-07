# Apple Human Interface Guidelines (HIG)

Source: developer.apple.com/design/human-interface-guidelines/

---

## Three Core Principles (iOS 7+)

### 1. Clarity
The UI must defer to the content. Every pixel, font size, color, and element must serve communication — not decoration. Typography is crisp, icons are precise, adornments are subtle.

**Applied in mockups:**
- Text must be readable at its intended size — no ornamental fonts for body text
- Icons should be outlined/filled consistently — not decorative shapes
- UI chrome (nav bars, tab bars) must be subdued, never competing with content

### 2. Deference
The interface steps aside so content can take center stage. UI elements support the content without overshadowing it.

**Applied in mockups:**
- Use translucency and blurring for overlapping UI layers (modal, sheet, menu)
- Navigation bars: thin, minimal, with just what's needed
- Control chrome should be subtle — thin borders, light backgrounds, no heavy shadows on secondary elements

### 3. Depth
Visual layers and realistic motion communicate hierarchy and spatial context.

**Applied in mockups:**
- Cards and sheets sit above the background (use elevation/shadow)
- Navigation transitions: forward = slide left, back = slide right
- Modals and bottom sheets float above content with dimmed backdrop

---

## Foundations

### Color
- **Semantic color roles** — never assign colors arbitrarily:
  - Blue → primary interactive actions (links, buttons)
  - Red → destructive actions (delete, remove)
  - Green → success, confirmation
  - Gray → disabled, secondary, inactive
  - Orange/Yellow → warnings
- **Dynamic Color** — colors adapt to light/dark mode automatically
- **Never use color as the only differentiator** — always pair color with shape/label/icon (accessibility)
- Contrast minimum: 4.5:1 for normal text, 3:1 for large text (WCAG AA)

### Typography (San Francisco / SF)
- **SF Pro** for iOS/macOS (system font, available via CSS `-apple-system`)
- **Dynamic Type** — users can resize text; your layout must accommodate this
- Type scale (points, approximate):
  ```
  Large Title:  34pt / Bold
  Title 1:      28pt / Regular
  Title 2:      22pt / Regular
  Title 3:      20pt / Regular
  Headline:     17pt / Semibold
  Body:         17pt / Regular
  Callout:      16pt / Regular
  Subhead:      15pt / Regular
  Footnote:     13pt / Regular
  Caption 1:    12pt / Regular
  Caption 2:    11pt / Regular
  ```
- **Left-align body text** — center-alignment only for short strings (titles, empty states)
- Don't use more than 2 font styles per screen

### Layout
- **Safe areas** — respect notch/Dynamic Island/home indicator
- **Standard margins**: 16px (compact) to 20px (regular) from screen edge
- **Minimum touch target**: 44×44 points (always — even if visual element is smaller)
- **Content width**: on iPad, limit content columns to ~70% on landscape
- Grid: 4-column (phone portrait), 8-column (phone landscape / tablet portrait), 12-column (tablet landscape)

### Icons
- Use **SF Symbols** as reference for icon style (thin, consistent stroke weight)
- All icons at same optical weight and fill style (don't mix filled and outlined)
- Icon sizes: 16, 22, 24, 28, 32pt recommended
- Tab bar icons: 25×25pt, Navigation bar icons: 22pt

### Dark Mode
- Every mockup for iOS should show both light and dark variants
- Background system colors:
  ```
  Light: systemBackground     = #FFFFFF
         secondarySystemBg    = #F2F2F7
         tertiarySystemBg     = #FFFFFF
  Dark:  systemBackground     = #000000
         secondarySystemBg    = #1C1C1E
         tertiarySystemBg     = #2C2C2E
  ```
- Labels:
  ```
  Light: primary   = #000000 / secondary = #3C3C43 (60%) / tertiary = #3C3C43 (30%)
  Dark:  primary   = #FFFFFF / secondary = #EBEBF5 (60%) / tertiary = #EBEBF5 (30%)
  ```

---

## Patterns

### Navigation
Three primary navigation patterns in iOS:

| Pattern | Use when | Chrome |
|---|---|---|
| **Navigation Stack** (push/pop) | Hierarchical content drill-down | Nav bar + back button |
| **Tab Bar** | Parallel sections at same level | Bottom tab bar, 3–5 tabs max |
| **Modal Sheet** | Task completion, temporary context | Bottom sheet or full modal, explicit close/done |

Rules:
- Tab bar: always visible except during keyboard input; max 5 tabs
- Back button: always present in nav stack; label = parent title or just "<"
- Modal dismissal: always provide explicit close (button or swipe down)

### Feedback & State
- **Activity indicators**: use for unknown-duration loading (spinner)
- **Progress bars**: use for known-duration operations
- **Skeleton screens**: preferred over spinners for content loading
- **Haptics**: trigger on significant UI events (success, warning, impact)
- **Toast/Alert**: alerts for critical decisions requiring confirmation; banners for non-critical info

### Forms
- Labels above inputs (not placeholder-only)
- Inline validation — show errors immediately on field blur, not on submit
- Keyboard type matches input: email → `.emailAddress`, phone → `.phonePad`, number → `.numberPad`
- Tappable area of each input: full width of screen (not just the text field)

### Empty States
Every list/grid/feed view must have a designed empty state:
- Centered illustration + headline + explanatory body + optional CTA
- Friendly, concise, actionable ("No messages yet" + "Send your first message" button)

### Alerts & Action Sheets
- **Alert**: 2 buttons max (Cancel left, primary right); for destructive: red text, Cancel on left
- **Action Sheet**: 3+ options; on iPad shows as popover, on iPhone from bottom
- Never use alerts for info that doesn't require a decision

---

## Components Reference

### Buttons
```
Primary CTA: Filled, rounded rectangle (cornerRadius: .infinity = pill)
Secondary:   Bordered/outlined
Tertiary:    Text only
Destructive: Text in system red

Sizes:
  Large:  height 50pt, font 17/Semibold
  Medium: height 44pt, font 15/Medium
  Small:  height 28pt, font 13/Regular
```

### List / Table View
- Row height: 44pt minimum
- Accessory types: chevron (navigation), checkmark (selection), info button
- Section headers: uppercase, small, secondary color, 11–12pt
- Swipe actions: red for delete, neutral for others

### Navigation Bar
- Height: 44pt (compact) / 96pt (large title)
- Large title fades to small on scroll
- Max 2 actions on right, 1 (back) on left

### Tab Bar
- Height: 49pt + safe area
- 3–5 items
- Active: filled icon + label in accent color
- Inactive: outlined icon + label in secondary color

### Cards
- cornerRadius: 12–16pt
- shadow: subtle, 0 2px 8px rgba(0,0,0,0.1)
- Padding inside card: 16pt

---

## Accessibility Checklist (HIG)
- [ ] All interactive elements: 44×44pt minimum tap target
- [ ] Color contrast ≥ 4.5:1 (normal text), 3:1 (large text)
- [ ] No color as sole meaning conveyor — always pair with label/icon
- [ ] Dynamic Type supported — layout doesn't break at larger sizes
- [ ] VoiceOver labels on all interactive/informational elements
- [ ] Focus order matches visual reading order
- [ ] Reduce Motion alternative for all animations
