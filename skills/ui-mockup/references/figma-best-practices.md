# Figma Best Practices & Design Systems

Source: figma.com/best-practices

---

## Design Token Architecture (3 Tiers)

Always organize tokens in 3 tiers. Never apply raw primitive values directly to components.

```
Tier 1 — PRIMITIVE TOKENS (raw values, reference only)
  color/blue/500     = #3B82F6
  color/blue/600     = #2563EB
  spacing/4          = 16px
  radius/md          = 8px

Tier 2 — SEMANTIC TOKENS (purpose-named, reference primitives)
  color/background/primary         = {color/blue/600}
  color/background/primary-hover   = {color/blue/700}
  color/text/on-primary            = {color/white}
  color/border/default             = {color/gray/300}
  spacing/component/padding-x      = {spacing/4}

Tier 3 — COMPONENT TOKENS (scoped to one component)
  button/primary/background        = {color/background/primary}
  button/primary/background-hover  = {color/background/primary-hover}
  button/primary/text              = {color/text/on-primary}
```

**Why this matters**: Primitive tokens are hidden from publishing. Designers only see semantic tokens. One change cascades everywhere.

### Token Naming Convention
```
[category]/[variant]/[property]-[state]

Examples:
  color/surface/default
  color/text/primary
  color/text/secondary
  color/border/focus
  spacing/gap/sm
  radius/button/pill
  shadow/card/default
  typography/body/md-regular
```

Consistency rule: **Your Figma variable names become your CSS/code variable names**. Agree with developers upfront.

---

## Figma File Structure (for Design Systems)

### Recommended File Organization
```
Design System File
├── Page: 🎨 Foundations
│   ├── Frame: Colors (token swatches)
│   ├── Frame: Typography (all text styles)
│   ├── Frame: Spacing (4px grid examples)
│   ├── Frame: Shadows
│   └── Frame: Icons
│
├── Page: 🧩 Components
│   ├── Frame: Buttons
│   ├── Frame: Inputs & Forms
│   ├── Frame: Navigation
│   ├── Frame: Cards
│   ├── Frame: Feedback (toasts, alerts, modals)
│   └── Frame: Data Display
│
├── Page: 📐 Patterns
│   ├── Frame: Layout patterns
│   ├── Frame: Empty states
│   └── Frame: Loading states
│
└── Page: 📖 Documentation
    └── Usage guidelines & examples
```

### Mockup/Prototype File Organization
```
Product Mockup File
├── Page: 📱 Mobile Screens
├── Page: 🖥 Desktop Screens
├── Page: 🔄 Flows (connected screens)
└── Page: 🗺 Sitemap/IA
```

---

## Component Best Practices

### Naming Components
Use a clear, consistent hierarchy:
```
[Section]/[Component]/[Variant]

Examples:
  Forms/Input/Default
  Forms/Input/Error
  Navigation/Tab Bar/3 Items
  Feedback/Button/Primary/Large
  Feedback/Button/Primary/Small
  Feedback/Button/Secondary/Large
```

Slash naming = automatic grouping in assets panel.

### When to Create a Component
Create a component when:
- Used in 3+ places
- Complex enough that inconsistency would cause problems
- Benefits from centralized updates

Avoid creating components for:
- One-off layout containers
- Simple shapes with no variants
- Content-specific elements (unique hero images, etc.)

### Variants vs. Properties
```
USE VARIANTS when:
  - Visual structure changes significantly (e.g., card with/without image)
  - Multiple independent dimensions exist (size × state × type)
  
USE COMPONENT PROPERTIES when:
  - Toggling visibility of a layer (show/hide icon)
  - Swapping a nested component (icon type)
  - Changing text content
  - Boolean toggle (has border / no border)
```

**Variants rule**: Limit to ~12 variants per component. Beyond that, split into sub-components or use properties.

### Component Anatomy
Every production component should include:
```
Main Component
├── Layer: Background (fill)
├── Layer: Content (auto-layout)
│   ├── Layer: Leading icon (optional, boolean property)
│   ├── Layer: Label (text content property)
│   └── Layer: Trailing icon (optional, boolean property)
└── Documentation: Usage notes in Description field
```

### Auto Layout Rules
- Every component should use Auto Layout (not absolute positioning)
- Use named spacing variables, not hardcoded values
- Set resizing rules explicitly (Fixed, Fill, Hug)
- Min/max width for responsive behavior

---

## Library Management

### Single Library vs. Multiple Libraries
```
Single library works for:
  - Small teams (1–5 designers)
  - Single product
  - Early-stage systems

Multiple libraries work for:
  - Multiple products/brands
  - Separate foundation + components layers
  - Teams with different access needs
  - Design tokens separated from components
```

Figma's recommendation for scale:
```
Primitive Tokens Library (foundation values only)
  ↓
Semantic Tokens Library (references primitives)
  ↓  
Components Library (references semantic tokens)
  ↓
Product Mockups (use components library)
```

### Version Control (Branching)
- Use branches for: major redesigns, new features, breaking changes
- Don't branch for: small fixes, new components, documentation updates
- Always get review before merging branch to main library
- Archive deprecated components — never delete, always document

### Publishing Updates
Before publishing library changes:
1. Check all component variants still work
2. Update descriptions and documentation
3. Announce breaking changes to consumers
4. Mark deprecated components with [DEPRECATED] prefix
5. Provide migration path for breaking changes

---

## Developer Handoff (Dev Mode)

### Annotation Best Practices
Add in every component:
```
Component description: what it does + when to use it
Link to design tokens used
Interaction states documented
Accessibility notes (ARIA role, focus behavior)
Link to code (Storybook, GitHub component)
```

### What Developers Need from Mockups
1. **Exact token names** — not hex values, not "the blue one"
2. **All states** — default, hover, focus, active, disabled, loading, error
3. **Responsive behavior** — how does this change at each breakpoint?
4. **Motion specs** — duration, easing curve, what triggers it
5. **Edge cases** — long text, empty state, maximum items

### Figma Variables → CSS Variables
```
Figma variable: color/background/primary = #3B5BDB
CSS variable:   --color-background-primary: #3B5BDB;

Figma variable: spacing/4 = 16px
CSS variable:   --spacing-4: 16px;

Light mode: [Default] collection mode
Dark mode:  [Dark] collection mode → CSS: prefers-color-scheme: dark
```

---

## Design Systems Maturity Model

**Level 1 — Inconsistent** (no system): Designers create everything from scratch each time. High inconsistency, slow velocity.

**Level 2 — Consistent** (style guide): Colors and fonts are defined. Components exist but aren't enforced. Some consistency.

**Level 3 — Systematic** (component library): Reusable components with variants. Teams contribute. Governance established.

**Level 4 — Scalable** (token-driven): Design tokens sync with code. Theme support. Multiple products covered. True single source of truth.

**Level 5 — Automated** (living system): Token pipeline automated. Usage analytics. Programmatic component generation. Design decisions codified as algorithms.

**Start at Level 1, iterate to higher levels. Don't try to build Level 4 on day one.**

---

## Prototyping for Developer Handoff

### What to Prototype
- Navigation flows (not every screen, just key paths)
- Complex interactions (drag, swipe, scroll behavior)
- Transition animations (entrance, exit, shared element)
- Microinteractions that affect state

### What NOT to Prototype
- Static content displays
- Simple button clicks with obvious destination
- Every single screen (use Flows in annotations instead)

### Prototype Fidelity Levels
```
Lo-fi: Click-through wireframes → validate flows
Mid-fi: Grayscale with real content → validate structure
Hi-fi: Full visual + motion → validate design + get stakeholder sign-off
```

---

## Common Mistakes to Avoid

**Token hygiene:**
- ❌ Hardcoding hex values in components instead of using variables
- ❌ Creating tokens for every single value instead of building a system
- ❌ Inconsistent naming between design and code

**Component complexity:**
- ❌ Building overly complex components that are hard to understand
- ❌ Creating too many variants (>12 in a single component)
- ❌ Nesting components 5+ levels deep without clear reason
- ✅ Start simple, add complexity only when proven necessary

**File organization:**
- ❌ No clear page structure in library files
- ❌ Mixing mockup screens and component library in same file
- ❌ Not documenting deprecated components

**Handoff:**
- ❌ Delivering mockups without showing all states
- ❌ Using non-token values (hardcoded colors/spacing)
- ❌ Missing edge cases (empty, loading, error)
- ❌ Not annotating complex interactions
