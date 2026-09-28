# Pretty-Project-Portfolio

**The Catio**: one page where every Claude project Charlotte has on the go lives as a cat in a
little pixel-art cabin with a fenced garden. Each Claude Code session is a cat that plays while
it works, sleeps when it's done, and **meows** (with a speech bubble saying what it needs) when
it's waiting on her. Chats on claude.ai, like business plans and legal questions, can't be read
by any connector, so she adopts those as cats by hand.

The page is a private claude.ai artifact; its link is in [`artifacts.json`](artifacts.json).

## How it knows what the cats are doing

- **Claude Code sessions** come live from the built-in *Claude Code Remote* connector
  (`list_sessions`), called as Charlotte from inside the page and refreshed every minute. A
  session's `status_bucket` and `post_turn_summary` decide its mood; its GitHub repository
  decides its room.
- **Rooms, renames, moves and adopted chats** live in the artifact's own database, so they
  follow her between phone and PC. Nothing she does on the page is written back to this repo.

| Mood | Session state | Cat |
|---|---|---|
| Meowing | blocked, or its last turn asked for input | Pochi meowing, with a bubble |
| Upset | failed | Pochi crying |
| Something to review | review ready | Mochi in a box |
| Working | working / running | Mochi, tail swishing |
| Asleep | finished or idle | Pochi curled up |

Sleeping sessions older than a week and archived sessions nap upstairs, out of sight.

## Files

- `catio/index.html`: the whole page, with no build step.
- `catio/art/house.png` and `catio/art/ui/`: the cabin and the page's frames, plaques and
  wallpaper, all cut from Cosy Cabin. The rest (`catio/art/licensed/`) is gitignored; see
  [`catio/art/CREDITS.md`](catio/art/CREDITS.md).
- `catio/tools/build-art.py`: rebuilds all the art from the four asset-pack zips.
- `CLAUDE.md`: how to change and republish the page.
