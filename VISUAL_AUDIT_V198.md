# CupNavi v.1.198 – Visual Audit & Design Consolidation

## Audit summary
The product contains 20 historical style blocks. The main visual issue is not lack of styling but competing generations of styling. This causes inconsistent component density, borders, typography and focus/hover behavior between screens.

## Priority findings

| Priority | Area | Finding | Action |
|---|---|---|---|
| P0 | Consistency | Multiple style generations override the same Streamlit primitives | Add one final authoritative design layer |
| P0 | Accessibility | Focus, disabled and contrast states differ by component | Normalize globally |
| P1 | Forms | Input/select/textarea/date controls vary in height/radius/border | Standardize control system |
| P1 | Buttons | Primary/secondary visual weight varies between screens | Standardize hierarchy and states |
| P1 | Tables | Native and HTML tables look like different products | Normalize header, spacing, borders and hover |
| P1 | Containers | Cards/panels use too many radii/shadows | Reduce to a restrained surface system |
| P1 | Public view | Strong content hierarchy but inherited styles create occasional visual drift | Normalize hero, cards, bracket and navigation |
| P1 | Admin | Context cards/navigation still expose framework-like styling | Normalize surfaces and typography |
| P2 | Popovers | Portal components can inherit theme colors unexpectedly | Explicit light product surface |
| P2 | Responsive | Different legacy breakpoints overlap | Final 1024/768/390 rules |
| P2 | Motion | Transitions exist without one product rule | Add reduced-motion contract |

## Design system
Spacing: 4 / 8 / 12 / 16 / 24 / 32 / 48 px.
Controls: 40 px desktop, 44 px mobile.
Core radii: 7 / 10 / 14 px.
Core surfaces: one background, one white surface, one subtle surface.
Primary green is reserved for primary actions and active state.
Shadows are intentionally rare.

## Cleanup performed
Only selectors belonging to removed share implementations were removed. Older global style blocks are not deleted wholesale because they may still support specialized components. Their visual effects are overridden by the final v1.198 authority layer.

## Functional scope
No business logic, database model, permissions, scheduling logic, reporting logic or lifecycle behavior is changed by this redesign.
