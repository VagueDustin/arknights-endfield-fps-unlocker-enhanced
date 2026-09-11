# Original Fate Unlocked artwork

Generated September 11, 2026 using the built-in imagegen tool. These are original brand assets, not game logos. The prompts use Fate Unlocked as the working product name.

## Icon

Saved original: `assets/identity/fate-icon-source.png`.
Production Windows icon: `assets/identity/fate-engine.ico`. The earlier `fate-unlocked.ico` copy records the working name.
Mode: text-to-image, no reference image.

Prompt:

> Create one finished Windows desktop application icon, square 1024x1024, for VagueDustin Enterprises' Arknights Endfield FPS and graphics tuning app, working title Fate Unlocked. This is a brand emblem, not a game character illustration. A single bold custom angular F monogram built from two interwoven metallic gold ribbons, suggesting unlocked forward motion and a woven thread of fate. Very legible silhouette at 32px. Centered emblem fills 72% of a deep midnight navy rounded-square tile. Gold primary #D4AF37, subtle pale-gold edge light, navy #070B1A and #101736. Restrained premium industrial/sci-fi design; flat front view, precise chamfered edges, understated material depth, large negative spaces. No lettering beyond the abstract F-shaped emblem, no words, no numbers, no game logos, no tiny circuitry, no speedometer, no clutter, no mockup or surrounding scene. Tile corners outside the rounded square must be genuinely transparent. Deliver a single production icon, not a sheet of variants.

## Installer art

Saved original: `assets/identity/installer-panel-source.png`.
Production artwork: `assets/identity/installer-panel.bmp` and `installer-mark.bmp`.
Mode: imagegen with the generated icon as its reference image.

Prompt:

> Create a new portrait Windows installer side-panel illustration, aspect ratio 171:314, using the supplied image as the exact brand emblem reference. Deep midnight navy (#070B1A, #101736) background with a restrained layered depth wash. Place the supplied gold woven angular F emblem with its navy rounded tile in the upper third, frontal and crisp, occupying about 65% of the panel width. Preserve the reference emblem design and gold material. Below it, a few broad, very subtle angular gold and navy light paths descend toward the bottom, suggesting forward motion and precision. Generous dark negative space; understated VagueDustin Enterprises utility software aesthetic. No text, no letters other than the reference emblem, no numbers, no screenshot/mockup, no extra logos, no characters, no tiny circuitry, no ornamental fantasy frame. Full-bleed finished portrait artwork suitable for a custom installer sidebar.

`tools/build_product_assets.py` performs deterministic resizing and Windows ICO/BMP conversion. Original generated PNGs are retained unchanged.
