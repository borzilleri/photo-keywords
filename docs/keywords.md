# Keyword Taxonomy (nested)

Human-readable rendering of `taxonomy.json` — the canonical machine source consumed by
`classify.py` and `apply_keywords.py`. **If you edit one, edit the other.** Descriptions follow
the principles in [`writing-keyword-descriptions.md`](./writing-keyword-descriptions.md).

**Hierarchy:** a `parent/child` keyword (e.g. `nature/water`) is what gets written. The
classifier picks the most specific child (or a standalone keyword). A photo may match
**multiple** keywords, or **none** (no match is a valid result — nothing is forced).

**Parents:** the bare parent (`nature`, `urban`, `art`) is written only when
`apply_keywords.py --with-parents` is used, to make broad searches easy.

---

## nature — the natural world

### `nature/landscape`
Wide natural scenery with no single dominant feature.
- **Includes:** mountain ranges, rolling hills, open fields, forests as scenery, deserts, volcanic terrain
- **Not this:** `nature/water` if water dominates · `nature/plants` for a single-plant close-up · `nature/sky` if the sky dominates · `urban/*` if buildings dominate
- **Examples:** a distant mountain range · rolling green hills · an arid volcanic plain

### `nature/water`
A body of water is the dominant subject.
- **Includes:** ocean, lakes, rivers, waterfalls, harbors where water dominates
- **Not this:** `nature/landscape` if land/forest dominates · `nature/sky` if the sky dominates
- **Examples:** waves on a shoreline · a still lake · a waterfall

### `nature/plants`
A plant, flower, or foliage shown as the subject (typically close-up).
- **Includes:** a single flower, a houseplant, leaves/branches in detail, a garden-bed close-up
- **Not this:** `nature/landscape` for wide vegetated scenery · `food` for produce as a dish
- **Examples:** a rose in bloom · a potted succulent · macro of leaves

### `nature/sky`
The sky itself is the clear dominant subject.
- **Includes:** sunsets, sunrises, dramatic clouds, rainbows, stars, auroras
- **Not this:** `nature/landscape`/`nature/water` when land/sea shares the frame meaningfully
- **Examples:** a sky of color at dusk · the milky way · storm clouds filling the frame

### `nature/animals`
An animal is the subject — pets, wildlife, birds, insects, livestock.
- **Includes:** dogs, cats, birds, deer, fish, insects
- **Not this:** `food` if the animal is plated as a meal
- **Examples:** a cat on a couch · a bird on a branch · a squirrel mid-frame

## urban — the human-built environment

### `urban/cityscape`
Streetscapes and cityscapes — the built environment at scene scale.
- **Includes:** skylines, streets, blocks of buildings, town squares, construction sites
- **Not this:** `urban/architecture` when ONE building/detail is the subject · `indoor` for interiors
- **Examples:** a busy shopping street · a skyline across a river · a row of townhouses

### `urban/architecture`
A single building, monument, bridge, or architectural detail as the subject.
- **Includes:** a cathedral facade, a bridge as subject, a staircase/arch detail, one notable structure
- **Not this:** `urban/cityscape` for wide multi-building streetscapes · `art/*` for sculptures/murals
- **Examples:** a clock tower close shot · an ornate doorway · a bridge over a gorge

## art — visual artworks and created imagery

### `art/physical`
Real-world artworks photographed in place.
- **Includes:** paintings, sculptures, murals, installations
- **Not this:** `urban/architecture` for buildings · `document` for text posters
- **Examples:** a painting on a gallery wall · a bronze statue · a street mural

### `art/illustration`
Drawn or digital 2D artwork that is not anime/manga and not game imagery.
- **Includes:** illustrations, comics/cartoons, concept art, digital paintings, stylized poster art
- **Not this:** `art/anime` for anime/manga · `art/game` for game imagery · `document` for UI screenshots
- **Examples:** a fantasy RPG character illustration · a stylized digital figure · a cartoon scene

### `art/anime`
Anime or manga-style artwork or characters.
- **Includes:** anime characters, manga panels, anime-style scenes
- **Not this:** `art/illustration` for non-anime drawn art · `art/game` for in-game imagery
- **Examples:** an anime pilot in a cockpit · a manga-style portrait

### `art/game`
Video-game imagery: screenshots, key art, in-game scenes.
- **Includes:** game screenshots, title/key art, in-game HUD scenes
- **Not this:** `document` for app/website UI screenshots · `art/anime`/`art/illustration` for standalone artwork
- **Examples:** a game title screen · an in-game landscape with HUD

## Standalone

### `food`
Prepared food, dishes, drinks, or ingredients shown as the subject.
- **Includes:** plated meals, coffee/cocktails, baked goods, raw ingredients arranged as food
- **Not this:** `nature/plants` for a growing plant · `nature/animals` for a live animal
- **Examples:** a bowl of pasta · a latte with foam art · a poured glass of beer

### `document`
Text- or UI-dominant captures.
- **Includes:** app/website screenshots, receipts, tickets, whiteboards, pages of text, text-focused signs
- **Not this:** `art/game` for video-game imagery · `art/physical` for posters valued as artwork
- **Examples:** an app screenshot · a photographed receipt · a whiteboard of notes
