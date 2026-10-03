# The one font the app ships

`sprout.ttf` — the pack's pixel font, which every title, label and button in the café is set in — is
Cup Nooble's, non-commercial and no redistribution. It comes down from the gateway with the rest of the
art (`art.h`). The page's body font, Nunito, comes off Google Fonts over the network.

So on first run, before it has signed in and fetched anything, **the app has nothing to draw a letter
with** — including on the sign-in screen that does the fetching, and on the "fetching the café's art"
line, and on any error either of them has to show.

One OFL font belongs here, committed: **Nunito-Regular.ttf** ([SIL Open Font License 1.1][ofl], which
allows redistribution, and already the page's `--body`). It is not in this draft because the draft has
no code to load it; add it with the first body in `src/`.

[ofl]: https://openfontlicense.org/

Nothing else goes in this directory. No pack art, ever — see `art.h`.
