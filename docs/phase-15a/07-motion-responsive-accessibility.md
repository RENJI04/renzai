# Motion, responsive behavior, and accessibility

Motion uses CSS transitions and keyframes only. Navigation, buttons, cards,
drawers, feedback, and page content use short 100-250 ms interactions. There is
no looping decoration, bounce, parallax, fake streaming, or animation-delayed
work. `prefers-reduced-motion: reduce` removes nonessential animation and
transitions while preserving every state in text and structure.

Desktop keeps the dense sidebar/content model. Laptop and tablet layouts reduce
columns progressively. At mobile widths the shell uses a drawer, KPI and form
grids stack, wide tables remain horizontally usable or simplify into compact
rows, and essential account, analysis, and incident actions remain available.

The redesign preserves semantic headings, main/navigation/complementary
landmarks, real labels, table structure, status/alert announcements, skip link,
keyboard interaction, visible focus, high-contrast text, and non-color-only
badges. Browser checks cover the skip link, drawer, focus, landmarks, and reduced
motion. This is regression evidence, not a claim of formal WCAG certification.
