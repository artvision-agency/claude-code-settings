---
name: ui-mockup
description: Create UI/UX mockups ready for development, grounded in principles from the best design books and official design systems (Apple HIG, Material Design 3, Figma best practices, Don Norman, Steve Krug, Laws of UX, Refactoring UI). Use this skill when the user asks to design a screen, page, app interface, or UI component as a mockup, prototype, or wireframe. Also trigger when the user says things like "нарисуй интерфейс", "сделай мокап", "покажи как будет выглядеть", "макет экрана", "прототип страницы", "UI для...", or wants to visualize an app idea before building it. Outputs interactive HTML mockups with correct visual hierarchy, design tokens, annotated components, and developer-ready structure. Always use this skill for any mockup, wireframe, or UI design request.
---

# UI Mockup Skill

Create interactive, developer-ready UI mockups as single HTML files. Every mockup follows industry best design standards — from both design theory and official platform guidelines.

## Reference Materials (read when relevant)

| File | When to read |
|---|---|
| `references/design-principles.md` | **Always** — core UX principles from Norman, Krug, Laws of UX, Refactoring UI |
| `references/apple-hig.md` | iOS/macOS/iPadOS apps — HIG navigation, components, type scale, Dark Mode |
| `references/material-design-3.md` | Android/web apps — M3 color roles, elevation, shape tokens, motion |
| `references/figma-best-practices.md` | Token structure, component annotations, design system handoff |

Always read `design-principles.md`. Read platform references when target platform is known.

---

## Step 1: Clarify & Detect Platform

Before building, identify:
- **Screen/feature**: What page or component to design?
- **Platform**: iOS app / Android app / Web / Cross-platform?
- **Viewport**: Mobile (375px), Tablet (768px), or Desktop (1280px+)?
- **Fidelity**: Wireframe (structure only) or High-fidelity (full colors)?
- **Stack hint**: React, Vue, Swift, Kotlin, plain HTML?

**Platform determines which design system to follow:**
```
iOS / macOS     → Read apple-hig.md → Use SF fonts, HIG nav patterns, 44pt targets
Android         → Read material-design-3.md → Use M3 color roles, adaptive nav, M3 shapes
Web (generic)   → Use design-principles.md → Custom tokens, flexible patterns
Cross-platform  → Blend: M3 structure + HIG touch targets + Refactoring UI visual quality
```

If the user gives enough context, start immediately.

---

## Step 2: Apply Design Thinking (from books)

Before writing code, make these decisions:

### Hierarchy Strategy (Refactoring UI)
Identify the **1 primary action** on this screen. Everything else is secondary or tertiary. Write it down:
```
Primary:   [e.g., "Submit Order" button]
Secondary: [e.g., Form fields, product info]
Tertiary:  [e.g., Help link, back button]
```
This hierarchy drives font size, weight, color, and placement decisions.

### User's Mental Model (Don Norman)
Ask: "What does the user expect this screen to do?" Design to match that model, not the developer's mental model of the system.

### Cognitive Load Check (Krug + Hick's Law)
Count the choices on the screen. If there are more than 7 primary choices, consider:
- Progressive disclosure (hide advanced options)
- Grouping with Gestalt proximity
- Breaking into steps (wizard)

---

## Step 3: Design Tokens First

Define all tokens as CSS variables at the top of the file:

```css
:root {
  /* Colors — never use pure black or pure gray */
  --color-primary:     #3B5BDB;
  --color-primary-h:   #2F4AC7;   /* hover */
  --color-primary-a:   #2440B0;   /* active */
  --color-bg:          #F8F9FA;
  --color-surface:     #FFFFFF;
  --color-border:      #E5E7EB;
  --color-text:        #111827;   /* NOT #000 */
  --color-text-sec:    #6B7280;   /* secondary */
  --color-text-dis:    #9CA3AF;   /* disabled */
  --color-error:       #EF4444;
  --color-success:     #22C55E;
  --color-warning:     #F59E0B;

  /* Typography */
  --font-display: 'Your Display Font', serif;
  --font-body:    'Your Body Font', sans-serif;
  --font-mono:    'JetBrains Mono', monospace;

  /* Type Scale (line-height inversely proportional to size) */
  --text-xs:   12px; --lh-xs:   1.5;
  --text-sm:   14px; --lh-sm:   1.5;
  --text-base: 16px; --lh-base: 1.6;
  --text-lg:   18px; --lh-lg:   1.5;
  --text-xl:   24px; --lh-xl:   1.4;
  --text-2xl:  30px; --lh-2xl:  1.3;
  --text-3xl:  36px; --lh-3xl:  1.2;
  --text-4xl:  48px; --lh-4xl:  1.1;

  /* 4px Grid Spacing */
  --sp-1:  4px;   --sp-2:  8px;   --sp-3: 12px;
  --sp-4: 16px;   --sp-5: 20px;   --sp-6: 24px;
  --sp-8: 32px;   --sp-10: 40px;  --sp-12: 48px;
  --sp-16: 64px;

  /* Radius */
  --r-sm:  4px;  --r-md: 8px;
  --r-lg: 12px;  --r-xl: 16px;  --r-full: 9999px;

  /* Layered Shadows (Refactoring UI pattern) */
  --sh-xs: 0 1px 2px rgba(0,0,0,.05);
  --sh-sm: 0 1px 3px rgba(0,0,0,.1), 0 1px 2px rgba(0,0,0,.06);
  --sh-md: 0 4px 6px rgba(0,0,0,.07), 0 2px 4px rgba(0,0,0,.06);
  --sh-lg: 0 10px 15px rgba(0,0,0,.1), 0 4px 6px rgba(0,0,0,.05);
  --sh-xl: 0 20px 25px rgba(0,0,0,.1), 0 10px 10px rgba(0,0,0,.04);
}
```

**Fidelity rule**: For wireframes — use only `--color-bg`, surface, border, and 3 shades of gray. Color comes later.

### Platform-Specific Token Overrides

**For iOS (Apple HIG):**
```css
:root {
  /* HIG system colors */
  --color-primary:   #007AFF;   /* systemBlue */
  --color-error:     #FF3B30;   /* systemRed */
  --color-success:   #34C759;   /* systemGreen */
  --color-warning:   #FF9500;   /* systemOrange */
  --color-bg:        #F2F2F7;   /* secondarySystemBackground */
  --color-surface:   #FFFFFF;   /* systemBackground */
  --color-text:      #000000;   /* label */
  --color-text-sec:  rgba(60,60,67,0.6); /* secondaryLabel */
  /* Typography: use system font stack */
  --font-body: -apple-system, 'SF Pro Text', sans-serif;
  --font-display: -apple-system, 'SF Pro Display', sans-serif;
  /* Radius: HIG uses these standard values */
  --r-card:   12px;   /* cards */
  --r-input:  10px;   /* inputs */  
  --r-button: 12px;   /* buttons (not pill for iOS standard) */
  --r-pill:   9999px; /* for pill buttons */
}
```

**For Android (Material Design 3):**
```css
:root {
  /* M3 uses generated tonal palettes — seed from brand color */
  --md-primary:                #6750A4;  /* customize */
  --md-on-primary:             #FFFFFF;
  --md-primary-container:      #EADDFF;
  --md-on-primary-container:   #21005D;
  --md-surface:                #FEF7FF;
  --md-on-surface:             #1C1B1F;
  --md-on-surface-variant:     #49454F;
  --md-outline:                #79747E;
  --md-surface-variant:        #E7E0EC;
  /* M3 Shape tokens */
  --r-xs:    4px;   /* chips, input fields */
  --r-sm:    8px;   /* small cards, menus */  
  --r-md:    12px;  /* cards, dialogs */
  --r-lg:    16px;  /* navigation rail, large cards */
  --r-xl:    28px;  /* FAB, side sheets */
  --r-full:  9999px;
  /* M3 Typography */
  --font-body: 'Roboto', sans-serif;
  --text-body-lg: 16px; --lh-body-lg: 1.5; /* 24sp / 16sp = 1.5 */
  --text-body-md: 14px; --lh-body-md: 1.43;
  --text-title-lg: 22px; --lh-title-lg: 1.27;
  --text-headline-sm: 24px; --lh-headline-sm: 1.33;
}
```

---

## Step 4: Apply Usability Principles While Building

### Affordances & Signifiers (Don Norman)
```html
<!-- Every interactive element must look interactive -->
<!-- Buttons: have depth/background that says "press me" -->
<!-- Links: have underline or distinct color -->
<!-- Inputs: have visible border and cursor:text -->
```

Ensure every interactive element has:
- Hover state (cursor: pointer + visual change)
- Focus state (visible focus ring — never remove outline without replacement)
- Disabled state if applicable
- aria-label if icon-only

### Feedback States (Norman's Feedback Principle)
Show ALL states for key interactive elements:
```html
<!-- Show in the mockup: Default / Hover / Loading / Success / Error / Disabled -->
<button class="btn btn-default">Submit</button>
<button class="btn btn-loading"><span class="spinner"></span> Saving...</button>
<button class="btn btn-success">✓ Saved!</button>
<button class="btn" disabled>Unavailable</button>
```

### Error Design (Norman: "Never blame the user")
```html
<!-- Inline, actionable, tells how to fix -->
<div class="field-group has-error">
  <label>Email</label>
  <input type="email" value="not-an-email" />
  <span class="field-error">⚠ Enter a valid email — e.g. name@domain.com</span>
</div>
```

### Touch Targets (Fitts' Law)
```css
/* Mobile: minimum 44×44px touch targets */
.btn       { min-height: 44px; padding: 10px 20px; }
.icon-btn  { width: 44px; height: 44px; }
.list-item { min-height: 48px; }
/* Space between adjacent targets: min 8px */
.btn + .btn { margin-left: 8px; }
```

### Navigation (Krug's 6 Questions)
Every screen must visually answer:
- What app/site is this? → Logo or app name
- What page am I on? → Active nav state + page heading
- What are major sections? → Primary navigation
- Where am I in a flow? → Breadcrumb or step indicator
- How do I search? → Search within 1 tap

### Visual Scanning (Krug: Design for Scanning)
Structure content for F/Z pattern reading:
```
HERO HEADING  ← largest, leftmost
  Supporting subheading
  [Primary CTA]  ← ONE dominant element (Von Restorff)

Section Title
  Content group    Content group    Content group
  [Secondary link]
```

---

## Step 5: Component Annotations

Every major section gets an HTML comment:
```html
<!-- 
  COMPONENT: ProductCard
  Props: { product: { id, name, price, image, rating, inStock } }
  State: isInCart (boolean), isFavorited (boolean)
  Events: onAddToCart(), onToggleFavorite()
  Notes: 
    - Disable "Add to Cart" when !inStock
    - Image ratio: 4:3, object-fit: cover
    - Min touch target on action buttons: 44px
    - Max 2 lines of title text (line-clamp: 2)
-->
```

---

## Step 6: Interaction States Panel

Add a sticky panel for switching states:
```html
<div class="states-panel" style="position:fixed;bottom:16px;left:50%;transform:translateX(-50%);
     background:#1F2937;border-radius:24px;padding:6px;display:flex;gap:4px;z-index:100">
  <button onclick="setState('default')" class="sp-btn active">Default</button>
  <button onclick="setState('loading')"  class="sp-btn">Loading</button>
  <button onclick="setState('error')"    class="sp-btn">Error</button>
  <button onclick="setState('empty')"    class="sp-btn">Empty</button>
  <button onclick="setState('success')"  class="sp-btn">Success</button>
</div>
```

**Always design the empty state first** (Refactoring UI principle — empty state is part of the product).

---

## Step 7: Responsive Switcher

```html
<div class="vp-switcher" style="position:fixed;top:16px;right:16px;display:flex;gap:4px;z-index:100">
  <button onclick="setVP(375)">📱</button>
  <button onclick="setVP(768)">📟</button>
  <button onclick="setVP(1280)">🖥</button>
</div>
<script>
function setVP(w) {
  const frame = document.querySelector('.mockup-frame');
  if (frame) frame.style.width = w + 'px';
}
</script>
```

---

## Step 8: Placeholder Content

**Never use Lorem ipsum.** Write realistic, plausible content:
```html
<!-- ❌ Bad -->
<h1>Lorem ipsum dolor sit amet</h1>

<!-- ✅ Good -->
<h1>Review your order before checkout</h1>
<p>2 items · Free delivery by Thursday, 6 March</p>
```

Image placeholders:
```html
<div style="width:100%;aspect-ratio:16/9;background:#E5E7EB;
     display:grid;place-items:center;color:#9CA3AF;
     font-size:12px;border-radius:var(--r-md)">
  1200 × 675
</div>
```

Avatar placeholders:
```html
<div style="width:40px;height:40px;border-radius:50%;background:#4F46E5;
     display:grid;place-items:center;color:#fff;font-size:14px;font-weight:600">
  АИ
</div>
```

---

## Step 9: Developer Handoff Notes

At the bottom of every mockup, include a `<details>` section:
```html
<details style="margin:48px 24px;font-family:monospace">
  <summary style="cursor:pointer;color:#6B7280;font-size:14px">📋 Developer Handoff Notes</summary>
  <div style="padding:20px;background:#F9FAFB;border-radius:8px;margin-top:8px;font-size:13px;line-height:1.6">

    <h3>Components to create:</h3>
    <ul>
      <li><code>Button</code> — variants: primary/secondary/ghost/danger; sizes: sm/md/lg</li>
      <li><code>InputField</code> — states: default/focus/error/disabled; label + hint text</li>
      <li>[List all components visible in mockup]</li>
    </ul>

    <h3>Design tokens:</h3>
    <pre style="background:#F3F4F6;padding:12px;border-radius:6px;overflow:auto">
/* Copy CSS :root block from top of this file into your tokens.css */</pre>

    <h3>Accessibility:</h3>
    <ul>
      <li>Tab order: [describe expected tab sequence]</li>
      <li>Color contrast: primary button text passes WCAG AA (≥4.5:1) ✓</li>
      <li>Required ARIA: [list roles/labels needed]</li>
    </ul>

    <h3>API endpoints needed:</h3>
    <ul>
      <li>GET /api/... → [description]</li>
    </ul>

    <h3>Edge cases to implement:</h3>
    <ul>
      <li>Empty state: [description]</li>
      <li>Long text: [max chars / truncation rule]</li>
      <li>Error: [which fields, what messages]</li>
    </ul>

  </div>
</details>
```

---

## Fidelity Levels

### Wireframe Mode
- Palette: 5 grays only (#F9FAFB, #E5E7EB, #D1D5DB, #6B7280, #111827)
- No decorative shadows, gradients, or color
- Focus on layout, hierarchy, information architecture
- Borders instead of elevation for cards

### High-Fidelity Mode
- Full token system: colors, typography, shadows, transitions
- Google Fonts (distinctive choices — avoid Inter/Roboto as default)
- Hover/focus/active transitions (150–200ms ease-in-out)
- Realistic content (no Lorem ipsum)
- Micro-interaction at the key "win" moment (Peak-End Rule)

---

## Output Requirements

Single self-contained `.html` file:
- All CSS in `<style>` tag
- All JS in `<script>` tag
- Google Fonts via `<link>` (optional: Font Awesome via CDN for icons)
- No broken external dependencies
- Opens correctly without internet (except fonts)

---

## Platform-Specific Checklist

**iOS (Apple HIG)**
- [ ] Tab bar: 3–5 items, visible at bottom, height 49pt + safe area
- [ ] Navigation stack: back button present, title centered or large-title variant
- [ ] All touch targets: 44×44pt minimum
- [ ] Bottom sheet/modal: swipe-to-dismiss supported, explicit Done/Cancel button
- [ ] SF font stack used: `-apple-system`
- [ ] Safe areas respected: no content behind notch/home indicator
- [ ] Dark mode variant shown (system colors auto-adapt)
- [ ] Destructive actions: red, placed separately from primary CTA

**Android (Material Design 3)**
- [ ] Navigation: Bar (mobile) → Rail (tablet) → Drawer (desktop)
- [ ] Color roles used: `primary`, `on-primary`, `surface`, `on-surface` (not hex)
- [ ] Tonal elevation: cards use surface-variant or elevation tinting (not flat shadows)
- [ ] Shape tokens applied: correct corner radius level for each component
- [ ] FAB: present if there's a primary action; positioned bottom-right
- [ ] M3 button hierarchy: Filled > Tonal > Elevated > Outlined > Text
- [ ] Motion: Emphasized easing (cubic-bezier(0.2, 0, 0, 1)) for key transitions
- [ ] Min touch target: 48dp (not 44px — slightly larger than iOS)

**Web (Cross-platform)**
- [ ] Responsive breakpoints defined: 375 / 768 / 1280
- [ ] Navigation adapts: hamburger → horizontal nav → sidebar
- [ ] Typography scales correctly at all viewports
- [ ] Focus states visible for keyboard navigation

## Final Checklist Before Delivering

**Usability (Norman)**
- [ ] Every button/link has hover + focus + active state
- [ ] Errors are inline with "how to fix" message
- [ ] Disabled states clearly communicate unavailability

**Scanning (Krug)**
- [ ] Page purpose clear within 3-second glance
- [ ] Strong heading → subheading → body hierarchy
- [ ] Navigation shows current location (active state)

**Psychology (Laws of UX)**
- [ ] One visually dominant CTA per screen (Von Restorff)
- [ ] Touch targets ≥ 44px on mobile (Fitts)
- [ ] Navigation ≤ 7 items per level (Hick + Miller)
- [ ] Related items visually grouped (Gestalt Proximity)

**Visual Quality (Refactoring UI)**
- [ ] Hierarchy uses weight + size + color, not size alone
- [ ] Spacing follows 4px grid
- [ ] No pure black text (#000 → use #111827)
- [ ] Layered shadows, not single flat shadow
- [ ] Generous whitespace (start with more, reduce if needed)

**Developer Ready**
- [ ] Design tokens as CSS variables at top
- [ ] Component annotations in HTML comments
- [ ] Developer handoff notes at bottom
- [ ] Realistic placeholder content (no Lorem ipsum)
- [ ] States panel or annotated state variants shown
