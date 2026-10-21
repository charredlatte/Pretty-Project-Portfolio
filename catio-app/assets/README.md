# The one font the app ships

`sprout.ttf` -- the pack's pixel font, which every title, label and button in the café is set in -- is
Cup Nooble's, non-commercial and no redistribution. It comes down from the gateway with the rest of the
art (`art.h`). The page's body font, Nunito, comes off Google Fonts over the network.

So without something here, on first run, before it has signed in and fetched anything, **the app would
have nothing to draw a letter with** -- including on the sign-in screen that does the fetching, and on
any error either of them has to show. Until `sprout.ttf` arrives, the titles stand in in Nunito Bold, as
the page's own `--pixel` falls back to a round font.

So this folder holds **Nunito** ([SIL Open Font License 1.1][ofl], no Reserved Font Name, which allows
redistributing it modified, with the licence beside it: `OFL.txt`), at the three weights the page's CSS
sets body text in:

| | |
|---|---|
| `Nunito-Medium.ttf` | 500, the body's own: prose, a menu's line, the hover line's words |
| `Nunito-Bold.ttf` | 700: the hover line's small word, an ask, a fact's name; and the titles' stand-in |
| `Nunito-ExtraBold.ttf` | 800: an aside, a count, a pip |

Each is Google Fonts' variable Nunito cut to one weight and to Latin-1, the general punctuation and the
four arrows: 30 KB, not 277. `../tools/fonts.py` makes them from one pinned commit of
github.com/google/fonts, so running it again gives the same bytes.

[ofl]: https://openfontlicense.org/

Nothing else goes in this directory. No pack art, ever -- see `art.h`.
