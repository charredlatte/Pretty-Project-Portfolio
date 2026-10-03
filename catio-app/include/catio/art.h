// art.h — the packs' bytes: fetched from the gateway, cached on disk, handed out as textures.
//
// THE APP SHIPS WITH NO PACK ART, AND NONE OF IT IS EVER COMMITTED.
//
// Every pack but Cosy Cabin forbids redistribution; Game UI Pack Pastel adds "no uploading to a
// repository" and asks that its files not be easily extractable. catio/art/licensed/ is gitignored for
// that reason, and an APK or IPA on a store would redistribute the lot. So the app fetches the art from
// GET /art/* on first run, behind her own sign-in, into app-private storage — the same footing as the
// café the gateway already serves her. A store release needs her own art first; docs/drawing-plan.md is
// that plan. The one font the app commits is an OFL one, for the screens that come before the art.
//
// GET /art/* answers private, max-age=86400 with no ETag and no Last-Modified
// (harness/gateway/src/cafe.js), so there is nothing to revalidate against: the app fetches what the
// cache lacks and otherwise never asks again. "Fetch the art again" in the House menu is the way back.
//
// This module does not fetch. It says what is missing and takes bytes, so the cache can be tested over
// a directory of files with no network at all.
//
// DRAFT: declarations only. Nothing here is implemented yet.

#ifndef CATIO_ART_H
#define CATIO_ART_H

#include <filesystem>
#include <string>
#include <string_view>
#include <vector>

namespace catio::art {

/// One drawable the app holds. The implementation maps this to a renderer texture; this header names no
/// renderer type, so it compiles and reads with no graphics library installed.
struct Texture;

/// Every file the page references, which is the same list CLAUDE.md's publish instructions carry.
/// `pixel` is false only for the Game UI Pastel pieces: that art is smooth, and scaling it with
/// nearest-neighbour is the one way to make it look wrong.
enum class Id {
    // the manor and its grounds
    House, HouseUpper, Decor, Meadow,
    // the furniture sheets: Cosy Cabin (committed in the repo) and the rest
    Furniture, FurnitureLicensed,
    // the cats
    MochiIdle, MochiBox, Pochi,
    // Sprout Lands: the whole interface
    UiPanel, UiButton, UiButtonHover, UiButtonDown, UiButtonGreen, UiButtonPink,
    UiField, UiArrow, UiFrame, UiDivider, UiBubble, UiCorners,
    UiToggle, UiStatus, UiFaces, UiCrown, UiStars, UiCursor, UiCursorPoint, UiPointer, UiLogo,
    // Game UI Pastel: the icons, pixelated, and the map panel, smooth
    UiPastel, PastelPanel, PastelPanelDark, PastelFrame, PastelButton, PastelButtonHover,
    PastelButtonDown, PastelIcons,
    // the pack's pixel font
    SproutFont,
    Count
};

struct File {
    Id id;
    std::string_view path;   ///< as GET /art/<path> wants it, e.g. "art/licensed/ui/panel.png"
    bool pixel;              ///< draw nearest-neighbour; false means smooth
};
/// The one place the list lives.
const std::vector<File>& files();
const File& file_of(Id id);

enum class State {
    Scanning,   ///< reading the cache, before the first frame
    Fetching,   ///< some files are still coming; the stage says "n of m"
    Ok,         ///< everything is here
    Missing     ///< a fetch failed; the stage says the code and offers Retry
};

/// The cache, and the textures over it.
class Art {
public:
    /// `cache_dir` is the platform's own per-app directory. The art must stay app-private: never
    /// external storage on Android, never a shared folder.
    explicit Art(std::filesystem::path cache_dir);
    ~Art();

    /// What the cache already holds, decoded and ready. Runs before the first frame.
    void scan();
    /// What still has to be fetched, in the order worth fetching: the house and the meadow first, so
    /// the manor appears before the last button does.
    std::vector<const File*> missing() const;

    /// Write a fetched file to the cache and decode it. False if the bytes are not a PNG (or a font).
    /// This is where the scale mode is set, from File::pixel.
    bool store(Id id, std::string_view bytes);
    /// Throw the cache away: "Fetch the art again" in the House menu.
    void forget_all();

    State state() const;
    int have() const;
    int total() const;
    /// The error code to show when state() is Missing. The page's NOART message is the wrong words
    /// here: it tells the reader to buy the packs and run build-art.py, and this app can simply fetch.
    std::string_view trouble() const;

    /// Null until that file is in the cache. Every drawing call tolerates a null texture, so the house
    /// fills in piece by piece as the fetches land.
    Texture* texture(Id id) const;

private:
    struct Impl;
    Impl* impl_;
};

}  // namespace catio::art

#endif  // CATIO_ART_H
