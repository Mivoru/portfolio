# Portfolio Michala Votýpky

Static site, no build step. Open `index.html` through any static server.

- `concept/`: spec concept sources (social artboards, promo timeline, landing page, e-mail).
- `tools/render_stills.py`: renders `concept/social.html` artboards to `assets/img/concept/`.
- `tools/render_print.py`: renders `concept/print.html` to `assets/img/print/` (print art and 3D textures).
- `tools/blender_scenes.py`, `tools/composite_3d.py`: render the 3D scenes headlessly and flatten them on the brand colour.
- `tools/render_promo.py`: renders `concept/promo.html` frames and the synthesized soundtrack to `assets/video/promo.mp4`.
- `js/motion.js`: smooth scrolling, scroll reveals, header timecode and cursor effects. `js/vendor/lenis.min.js` is Lenis 1.1.20 (MIT).

The Digitoo work is an unofficial concept. Keep that label on every published piece.
