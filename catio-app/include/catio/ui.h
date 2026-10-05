// ui.h — what is drawn over the house, and what a tap on it does.
//
// It holds the words she reads (apart from the mood labels, which belong with the rank in house.h).
//
// THE RULES THIS MODULE KEEPS, all of them hers.
//
//   No signs on the map. No room names, badges or stair signs on the art. A room is named on hover;
//   the other floor's tab carries its badge; the brand carries the house's.
//
//   Nothing on the cats. No letters, counts, faces, bubbles, pile numbers, crowns, and no "z Z" over a
//   sleeping cat. Hovering one says what it needs: its name and mood, then its ask or its waiting
//   files. A new fact about a cat goes in its hover line, its menu or its card, never on the sprite.
//
//   Two things on screen and nothing else: the brand (top left, which is the House button) and the map
//   panel (top right; bottom right on a phone).
//
//   Every menu has the same shape, as short as it can be: the name with a badge when cats need her and
//   one line under it; then what matters now; then the actions as a list, the first the default, the
//   pack's triangle beside the one under the pointer. A new action is a list item, and only if it earns
//   its place. A card puts what she came for first and folds the rest under Manage.
//
//   Hover names a thing; a click opens its menu beside it, pinned until a click elsewhere or Escape.
//   A tap does the same. Hover means the pointer really moved onto the thing: when the camera moves or
//   a card closes, the room that slides under a still pointer is not named until she moves.
//
// THE PHONE, which is why this app exists at all. Her UI audit, measured at 390x844:
// "On a phone, the house is tiny, has no room names, and cats can't be tapped" — the house fills about
// an eighth of the screen, cats are 6-12px, the smallest rooms 38x44, buttons 32px and the sound switch
// 22px. Her fixes, taken as the starting point and not a backlog: open zoomed into the most urgent
// room, swipe left and right through the NEXT map, fit the camera to the manor rather than the whole
// grounds, and no target under 44px.
//
// Two layers. The content -- tip_for(), menu_for(), summary(), queen_line() -- is the page's showTip()
// and its menu builders, ported line for line into plain data: no font, no renderer, so a test reads a
// menu the way she would. The Ui class lays that data out in the page's own CSS lengths, multiplied by
// the stage's `css`, draws it from the packs, and answers presses.
//
// Implemented in src/ui.cpp. The one card built is the Cat card; every other card is still to come,
// and its menu item is drawn disabled with "not yet" beside it (cannot() says why) rather than hidden.

#ifndef CATIO_UI_H
#define CATIO_UI_H

#include <cstdint>
#include <filesystem>
#include <string>
#include <string_view>
#include <vector>

#include "catio/art.h"
#include "catio/draw.h"
#include "catio/house.h"
#include "catio/view.h"

namespace catio::ui {

/// The audit's minimum, in CSS pixels (x Stage::css on screen). Every target on a coarse pointer is
/// grown to it: `@media (pointer: coarse) { .mi { min-height: 44px } }` and the cats' hit boxes.
inline constexpr float kTouch = 44.0f;

/// What a press asks the app to do. app.h's act() is the only place one becomes a write.
enum class Action {
    None,
    // looking
    LookIn, WholeHouse, ZoomIn, ZoomOut, ToFloor, FoldMap, MapAt, StillCats, Sound, AddACat, Back,
    // opening
    OpenHouse, OpenCat, OpenQueen, OpenPile, OpenCabinet, OpenBrain, OpenRules, OpenMaps, OpenLook,
    OpenEditRooms, OpenSetup, OpenHomework, OpenLink, Adopt, BringDown, CheckNow, CloseCard, Manage,
    // doing: each one is a write, on her press and never otherwise
    Say, HandIn, AddFiles, Rename, Move, OpenRoom, CloseRoom, SetMood, Pause, Resume, WrapUp, StopQueen,
    KeepNote, PinNote, FetchArtAgain, SignOut
};

/// One action in a menu's list (mi()).
struct Item {
    std::string label;
    Action action = Action::None;
    std::string arg;
    std::string aside;       ///< a quiet note on its right: "3 on the tray"
    bool primary = false;    ///< the default: the first in the list (list())
    bool enabled = true;     ///< a disabled item says "not yet" on its right, and cannot() says why
    int toggle = -1;         ///< a switch (.mi.sw): -1 none, 0 off, 1 on
};

/// A row of a menu: a cat that needs her (catRow: its face, its name, " · " and its ask), or a note the
/// queen keeps (`face` -1, `pinned` for the one she is saying).
struct Row {
    std::string id, name, text;
    int face = -1;           ///< faces.png: MOODS order, then 5, a queen's heart eyes
    bool pinned = false;
};

/// The pieces a menu is made of, in the order the page appends them.
struct Block {
    enum class Kind {
        Sub,     ///< a line of prose (.sub)
        Ask,     ///< the well with an ask or a note in it (.ask-box), a face or a crown beside it
        Cats,    ///< catRows(): up to three cats (five for a pile), then "and N more"
        Keeps,   ///< ul.keeps: what the queen keeps, a star each
        Rule,    ///< the pack's divider
        List,    ///< the actions
        Foot     ///< the credits, at the foot of the House menu
    };
    Kind kind = Kind::Sub;
    std::string text;
    int face = -1;
    bool crown = false;
    bool need = false;       ///< an Ask that is waiting on her (.ask-box.need)
    Action action = Action::None;   ///< an Ask that opens something when pressed
    std::string arg;
    std::vector<Row> rows;
    int more = 0;
    std::vector<Item> items;
};

/// Every menu has the same shape: the name (a face or a crown before it, a badge after it) and one
/// line under it, then its blocks.
struct Menu {
    view::Thing kind = view::Thing::None;
    std::string key;
    std::string title;
    int face = -1;
    bool crown = false;
    std::vector<const Cat*> need;   ///< the badge: the most urgent face, and how many
    std::string sub;                ///< clamped to two lines
    std::vector<Block> blocks;
};

/// The hover line (#tip): the name, a small word, a badge, and what it says.
struct Tip {
    std::string name, small, says;
    std::vector<const Cat*> need;
};

/// The cards. Each puts what she came for first and folds the rest.
enum class Card {
    None, Cat, Queen, QueenSettings, Pile, Adopt, Cabinet, Brain, Rules, Maps, EditRooms, Setup
};

struct Frame {
    const House* house = nullptr;
    const view::Scene* scene = nullptr;
    const view::Cam* cam = nullptr;
    view::Stage stage;
    double now = 0;             ///< seconds, for the sprites
    std::int64_t clock_ms = 0;  ///< the wall clock, for "5 min ago"
    bool coarse = false;        ///< a touch screen: every target grows to kTouch, and there is no hover
    bool still = false;         ///< Still cats
    std::string live;           ///< liveLine(): how the cats are reaching her, in a few words
    std::string status;         ///< the sign under the brand: empty unless something is wrong
};

// ---- the content: no font, no renderer -----------------------------------------------------------

/// "1 upset, 2 meowing, 1 to review, 3 at work, 1 asleep", or "no cats".
std::string summary(const std::vector<const Cat*>& cats);
/// "just now", "5 min ago", "3 h ago", "yesterday", "4 days ago"; empty for no time at all.
std::string ago(std::int64_t then_ms, std::int64_t now_ms);
/// The one line she gives without anything being opened (queenLine).
std::string queen_line(const House& h);
/// The ones that need her, most urgent first (urgentFirst).
std::vector<const Cat*> urgent_first(const std::vector<const Cat*>& cats);
/// What showTip() puts in the line for this thing. Empty name: nothing to say.
Tip tip_for(const Frame& f, const view::Hit& h);
/// roomMenu, houseMenu, pileMenu, queenMenu, catMenu. `adding` is the room menu's "Add a cat" step.
/// An empty title means there is no such thing any more, and no menu.
Menu menu_for(const Frame& f, view::Thing kind, std::string_view key, bool adding = false);

/// placeMenu(): beside its anchor on the right, else the left; on a narrow screen below it, else above;
/// a room that fills the screen gets it in its corner; the House menu under the brand; always inside
/// the stage, and never under the map panel. All in device pixels.
draw::Pt place_menu(const view::Stage& st, view::Thing kind, draw::Rect anchor, draw::Pt size,
                    draw::Rect panel, float hud_bottom);

// ---- the interface -------------------------------------------------------------------------------

class Ui {
public:
    Ui();
    ~Ui();

    /// Open the fonts: the committed Nunito from `assets`, and sprout.ttf from the art cache once it is
    /// there. Call again when the art arrives or the scale changes; it reopens only what changed.
    bool fonts(const std::filesystem::path& assets, const art::Art& art, int css);

    /// Hover names a thing in one line. Ignored on a coarse pointer, and only when it really moved.
    void tip(const Frame& f, const view::Hit& h, bool moved);
    const view::Hit& tipped() const;
    /// A click or tap opens its menu beside it, pinned; on the same thing again, closes it.
    void toggle(const Frame& f, const view::Hit& h);
    void close_menu();
    view::Thing menu_kind() const;
    const std::string& menu_key() const;

    void open(Card c, std::string key = {});
    void close_card();
    Card card() const;
    const std::string& card_key() const;

    /// The map panel, open or folded to its one button. A phone starts folded.
    bool map_open() const;
    void set_map_open(bool open);
    /// Where the map panel is this frame, in device pixels: menus keep clear of it.
    draw::Rect panel(const Frame& f) const;

    /// Is the point over the interface rather than the house?
    bool over(const Frame& f, float x, float y) const;
    /// What is under the point, by the name it was drawn with ("brand", "map:mm", "menu:item:3:0"...).
    std::string_view under(const Frame& f, float x, float y) const;
    /// The pointer moved: light the button, the item or the room on the minimap under it.
    void hover(const Frame& f, float x, float y);
    /// A press held down on a button draws it pressed in.
    void hold(const Frame& f, float x, float y, bool down);
    /// A press, let go. False when it was not on the interface at all.
    bool press(const Frame& f, float x, float y, Action* what, std::string* arg);
    /// A drag on the minimap: the point of the grounds under the finger, as MapAt's argument ("x y" in
    /// art pixels), clamped to the map. False when the drag did not start on it.
    bool map_drag(const Frame& f, float x, float y, std::string* arg) const;
    /// Escape: the card, else the menu. False when neither was open.
    bool escape();

    void draw(const draw::Ctx& c, const Frame& f);

    /// Why an action is not here. This app is always in the page's gateway mode (VIA_GATEWAY): no list
    /// of her claude.ai sessions, no posting into one that does not report to the gateway, no starting
    /// or archiving one, no LLM file sorter. And while it is a draft, most cards are not built yet.
    /// Those items are drawn, disabled, with "not yet" beside them -- never hidden, and never pretended.
    std::string_view cannot(Action a) const;
    /// Whether this build can do it at all.
    bool can(Action a) const;

    /// SC_siosio's licence requires his credit, word for word, and says it must not be intentionally
    /// hidden. The page keeps it at the foot of the screen and the foot of the House menu, because a
    /// phone has no room for a footer; so does this. The words are catio/art/CREDITS.md's.
    std::string_view credits() const;

private:
    struct Impl;
    Impl* impl_;
};

}  // namespace catio::ui

#endif  // CATIO_UI_H
