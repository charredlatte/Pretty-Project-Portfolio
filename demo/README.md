# The demo page

`demo/index.html` is the tour linked at the top of the repo's README: a playable page for someone who has
never seen the café. It covers the manor and its cats, the five moods, the queen, the seven-step setup
wizard, and what it takes to run your own.

Open `demo/index.html` in any browser, or serve the folder with `python3 -m http.server`. There is no
build step for the page itself and no data of anyone's in it: the cats, projects and repositories are
invented, as the test suite's own are. The only thing it fetches is its three fonts, from Google Fonts,
because that is the one font host a published artifact may use; offline it falls back to the system faces
and loses the pixel look.

The same file is also the artifact's page body. The publish wraps it in its own skeleton, which flattens
this one's `<head>` into the body, where the viewport meta and the styles still apply — so one file
serves both, and the committed copy keeps the full document shell that `landing/index.html` has, rather
than opening in quirks mode.

## Its art is its own

The café's real art comes from six licensed packs that forbid redistribution (`CLAUDE.md`, "Licences: what
may be committed"), so a public page can ship none of it. Everything in `demo/art/` is drawn from nothing
by `demo/tools/sprites.py`, in the café's own skin palette (`catio/art/skin.json`), the way
`landing/tools/scene.py` draws the landing scene. That is why `demo/art/` is committed while
`catio/art/licensed/` is not.

```
python3 demo/tools/sprites.py            # redraw demo/art/
python3 demo/tools/sprites.py --sheet    # and demo/art/.preview.png, every sprite on one strip, to look at
```

It draws the slots `docs/drawing-plan.md` asks for — `cat-work`, `cat-review`, `cat-meow`, `cat-cry`,
`cat-sleep`, `cat-walk-side`, `owner` — plus a crown, a piece of furniture per room, and the triangle the
menus put beside the item under the pointer. `demo/art/sprites.json` records each one's size and frame
count. The fur is one ramp, used nowhere else, so the coats can one day be palette swaps of it rather than
the CSS filters the page uses today.

The type is Press Start 2P, Pixelify Sans and Nunito from Google Fonts, all under the SIL Open Font
License. The pack's own pixel font (`sprout.ttf`) is licensed and never appears here.

## What it keeps in step with

The page is a copy, not an import, so three things can drift. Check them when you change the café:

- **The manor's plan.** `ROOMS`, `LANDING` and `STAIR` are the real boxes, copied from
  `catio-app/generated/manor.json`, which `catio/tools/manor.py` generates. The doorway rectangles are
  not: `manor.json` holds the cats' routes as endpoint pairs, not wall gaps, so the gaps here were
  measured by eye from the rooms either side. Change the plan and both have to be redone. They are
  copied rather than fetched because the page has to work from `file://`, with no server and no build.
- **The wizard's copy.** Every line in the wizard is `openSetup()` in `catio/index.html`, word for word.
  `docs/onboarding/README.md` says which lines the page, the wireframes and the public skill must all
  agree on.
- **The interface rules.** No signs on the map, nothing drawn on the cats, two things on screen, every menu
  one shape, the map panel folded on load, the queen out of every count. `CLAUDE.md` is the source.

It is a demo, not a second café: it has no database, no connectors and no gateway, and it never will.
Anything that needs those belongs in `catio/index.html`.
