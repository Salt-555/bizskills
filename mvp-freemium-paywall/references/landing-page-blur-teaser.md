# Landing Page Preview-Blur Teaser

A freemium conversion pattern for landing pages: show a working demo with some results visible, then blur the remaining results behind a frosted glass overlay with a centered purchase CTA. This is distinct from the app paywall — it lives on the public-facing landing page (`/`) to convert cold traffic.

## How It Differs from the App Paywall

| Aspect | App Paywall (`/app`) | Landing Page Teaser (`/`) |
|--------|---------------------|--------------------------|
| Purpose | Gate full feature access after sign-up | Convert cold ad traffic before sign-up |
| Mechanism | Structural lock cards in document flow | Absolute overlay with blur effect |
| CTA | "Unlock All" button inside each panel | Single centered CTA over blurred area |
| User state | Has started using the app | Hasn't interacted yet |

## Pattern

### Grid Layout

```
┌─────────────┬─────────────┐
│  ✅ Herbs   │  ✅ Crystals │   ← Visible (first 2 cards)
├─────────────┼─────────────┤
│  🔒 Candle  │  🔒 Day      │   ← Blurred + overlay
│  🔒 Moon    │  🔒 Element  │
│  🔒 Incense │             │
│  ┌─────────────────────┐  │
│  │    🔒 "$12 once"    │  │   ← Frosted overlay, centered CTA
│  └─────────────────────┘  │
└─────────────┴─────────────┘
```

### CSS

```css
/* The grid container for demo results */
.demo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
  position: relative;
}

/* Individual blur on the premium cards */
.demo-card.premium {
  filter: blur(3px);
  opacity: 0.15;
}

/* Frosted glass overlay */
.blur-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 55%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(1px);
  border-radius: 0 0 12px 12px;
  z-index: 2;
}

.blur-overlay .lock-icon { font-size: 1.5rem; }
.blur-overlay .lock-text { font-size: 0.85rem; color: #666; margin-bottom: 0.5rem; }

.unlock-btn {
  background: #C5A55A;
  color: #0A0A0A;
  padding: 0.6rem 1.4rem;
  border-radius: 6px;
  text-decoration: none;
  font-weight: 600;
  font-size: 0.9rem;
}
```

### Placement in worker.js

Inside `LANDING_PAGE_HTML`, after the demo result cards, add the overlay div. It must be a sibling of the grid, not inside it, so it can position relatively to the grid container.

```html
<div class="demo-grid" id="demoResults">
  <!-- Free cards (herbs, crystals) — rendered normally -->
  <!-- Premium cards (candle, day, moon, element, incense) — add .premium class -->
  <!-- Blurred overlay with CTA centered over the premium area -->
  <div class="blur-overlay">
    <span class="lock-icon">🔒</span>
    <span class="lock-text">Full compass — one-time payment</span>
    <a href="https://buy.stripe.com/..." class="unlock-btn">$12 once</a>
  </div>
</div>
```

### JS Placement (programmatic, not pixel-hardcoded)

The overlay must position itself at exactly where the first blurred card starts. NEVER hardcode `top` in pixels. Use this pattern:

```css
.demo-blur-wrap {
  position: absolute;
  left: 0; right: 0;          /* stretch horizontally */
  background: rgba(250,248,243,.65);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;        /* center CTA vertically */
  justify-content: center;    /* center CTA horizontally */
  z-index: 10;
  border-radius: 8px;
  pointer-events: none;       /* don't block interactions */
}
```

```javascript
// After showing results and DOM has settled:
requestAnimationFrame(function(){
  var blur = r.querySelector('.demo-blur-wrap');
  var firstBlurred = r.querySelector('.demo-cat.blurred');
  if(blur && firstBlurred){
    var rect = firstBlurred.getBoundingClientRect();
    var containerRect = r.getBoundingClientRect();
    var top = rect.top - containerRect.top;
    blur.style.top = top + 'px';
    blur.style.height = (containerRect.height - top) + 'px';
  }
});
```

Key details:
- `requestAnimationFrame` ensures layout has settled before measuring
- `getBoundingClientRect().top` gives the exact pixel boundary between visible and blurred cards
- The overlay height covers exactly from first blurred card to the bottom of the container
- `pointer-events: none` on the overlay ensures it doesn't block clicks on the free cards
- The CTA button (child of overlay) has normal pointer events so it remains clickable

## Pitfalls

1. **NEVER use hardcoded pixel values for overlay `top`** — `top:110px` breaks when card heights change, text reflows, or viewport changes. Always measure the actual DOM position of the first blurred card programmatically in JS and set `overlay.style.top` to `card.offsetTop + 'px'`. The user explicitly requires programmatic placement, not eyeballing.
2. **Overlay covers interactive elements** — The overlay must be positioned over the blurred area only, not over the free cards. Calculate height to cover only the bottom rows.
3. **Blur too strong/weak** — `filter: blur(3px)` with `opacity: 0.15` on the cards creates a clear "there's content behind here" signal without being fully opaque. Adjust based on card density.
4. **Grid reflow on dropdown change** — The grid container height changes when category results render. The overlay's `height: 55%` percentage works because it's relative to the grid, but if the grid collapses, the overlay may cover content it shouldn't.
5. **Mobile responsiveness** — On narrow screens, the grid may become single-column and taller. The overlay `height: 55%` still works but the CTA may push against the middle of the grid. Acceptable; test on mobile viewport.
6. **Don't confuse with app paywall** — The app paywall uses structural lock cards (not overlays). This pattern is ONLY for the landing page teaser. Mixing them creates maintenance confusion.

## Working Example

`~/.hermes/mvps/coven-compass/src/worker.js` — `LANDING_PAGE_HTML` contains the live implementation in the `/` route handler.
