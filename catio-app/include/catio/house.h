// house.h — the café's data, and everything the page derives from it.
//
// This is the module a test drives from a JSON string: it includes no renderer and no transport, so
// "does a closed room get cats?" and "who is really waiting on her?" are answerable without a window
// or a network. It is the native twin of what cafe/runtime.js calls `db`, plus the derivations
// catio/index.html does on top of it (catFromAgent, allCats, roomFor, queenState).
//
// Two sources, not one:
//   documents  GET /api/db — house/main, rooms/*, cats/*, projects/*, queens/house, quizzes/*,
//              routines/*, graphs/*, dashboard/maps, rules/*, audits/*, layouts/*
//   cats       POST /api/tools/list_agents — the `agents` table, with each cat's `waiting` count and
//              its latest `said`. Cats are not documents (harness/gateway/src/house.js).
//
// What this app never reads or writes: snapshot/sessions, sessions/<id>, notes/<id>, brain/<id> and
// outbox/<id>. Those are claude.ai's path, keyed off list_sessions ids a native client never sees. On
// the gateway the same things are the notes and files tables, reached through the tools.
//
// Implemented in src/house.cpp, and tested in test/tests.cpp.

#ifndef CATIO_HOUSE_H
#define CATIO_HOUSE_H

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace catio {

/// The five moods, in MOODS order (catio/index.html), which is also the rank: a cry outranks a meow.
/// Nothing is ever drawn on a cat — hovering it says its mood, as the page's rule has it.
enum class Mood { Cry, Meow, Box, Idle, Sleep };

struct MoodInfo {
    std::string_view label;   ///< "Upset: the last run failed"
    std::string_view brief;   ///< "Upset", "Needs you", "To review", "Working", "Asleep"
    std::string_view kind;    ///< "fail", "need", "gift", "work", "sleep"
    bool needs;               ///< does this one count towards the badge?
};
const MoodInfo& info(Mood m);
std::optional<Mood> mood_from(std::string_view wire);  ///< the gateway's "needs"/"busy"/"review"/…

/// rooms/<key>. No document means an open room with the manor's default name.
struct Room {
    std::string key, name, blurb, model;
    std::vector<std::string> repos;   ///< repo names, or owner/repo
    bool catch_all = false;
    bool closed = false;              ///< dimmed, no queen, gets no cats; cats still walk through
};

/// One cat: a reporting agent (list_agents) or an adopted chat (cats/<id>). Never the queen.
struct Cat {
    std::string id, name, title, ask, link, repo, model;
    std::string project;              ///< the project's key (a slug): projects/<key>, its filing cabinet
    std::string room;                 ///< the room it lives in, already resolved by room_for()
    Mood mood = Mood::Idle;
    int coat = 0;                     ///< one of the eight coats: projects/<key>.coat, else a hash of the key
    std::int64_t updated = 0;
    int waiting = 0;                  ///< files dropped on it and not yet picked up
    bool archived = false;
    bool adopted = false;             ///< from cats/<id> rather than the agents table
    std::string said;                 ///< its latest note, what it brought her
    std::int64_t said_at = 0;
};

/// One of the queen's kept notes. A pinned one is the line she says out loud.
struct Note {
    std::string text;
    bool pinned = false;
    std::int64_t at = 0;
};

/// queens/house. She is deliberately outside cats(): never in a count, a pile or the badge.
struct Queen {
    std::string name, manner, greeting;
    int coat = 0;                     ///< queens/house.coat, else a hash of "queen:house"
    std::vector<Note> keeps;
    std::int64_t read_at = 0;         ///< when her card was last opened; older `said` are handoffs
    bool voice_on = false;
};

/// How away she is: no runner for two minutes is asleep, and her menu says "start her runner".
enum class QueenState { Away, Busy, Here };

struct Question {
    std::string ask;
    std::vector<std::string> options;  ///< 2 to 12; empty means a written answer
    bool written = false;
};

/// quizzes/<id>: her quest log. `kind` is "unblock", "litterbox" or "decision".
struct Quiz {
    std::string id, kind, title, note, hint, from, ref, for_cat;
    std::vector<Question> questions;
    std::int64_t at = 0;
    bool done = false;
};

/// The documents and the cats, and the questions the page asks of them.
class House {
public:
    House();
    ~House();

    // ---- what comes in off the wire -------------------------------------------------------------
    void docs(std::string_view body);                      ///< GET /api/db
    void doc(std::string_view path, std::string_view json); ///< one change; empty json means deleted
    void agents(std::string_view body);                    ///< list_agents
    void quizzes(std::string_view body);                   ///< quizzes

    /// True once a first docs() has landed. A `rooms` collection that arrives with nothing in it is a
    /// café nobody has opened yet: the app shows the wizard rather than an empty house.
    bool ready() const;
    bool never_set_up() const;

    // ---- the house ------------------------------------------------------------------------------
    std::string name() const;                              ///< house/main.name, else "KittyChat Café"
    const Room& room(std::string_view key) const;
    bool open(std::string_view key) const;
    std::string catch_all_room() const;
    /// Where new cats come in: the first open room of the opening order.
    std::string front_door_room() const;

    // ---- the cats -------------------------------------------------------------------------------
    /// Every cat, the queen left out. `everything` includes the archived and the napping.
    const std::vector<Cat>& cats(bool everything = false) const;
    const Cat* cat(std::string_view id) const;
    /// Which room a cat lives in: her move of it, then its repo, then the catch-all. Closed rooms are
    /// skipped, as roomFor() and catchAllRoom() skip them.
    std::string room_for(const Cat& c) const;
    /// What the brand's badge counts: the cats that really wait on her, and nothing else.
    std::vector<const Cat*> needing() const;
    /// The line at the front door: every meowing cat, the longest wait first, upstairs ones included.
    /// Upset and to-review cats stay in their rooms.
    std::vector<const Cat*> queue() const;
    int needing_on(std::string_view floor) const;          ///< the other floor's badge

    // ---- the queen ------------------------------------------------------------------------------
    const Queen& queen() const;
    /// Her seat is the hall's; when the hall is closed she sits in the catch-all room.
    std::string queen_room() const;
    QueenState queen_state() const;
    /// queenMood: asleep when away, at work while she answers, a box when homework or a handoff waits,
    /// meowing when she has something to say aloud, else at work.
    Mood queen_mood() const;
    /// What a cat brought her: a `said` newer than queens/house.readAt.
    std::vector<const Cat*> handoffs() const;
    /// Her hover line counts each kind: "Homework: 2 notes to sort, 1 decision".
    std::vector<const Quiz*> homework(std::string_view kind = {}) const;

private:
    struct Impl;
    Impl* impl_;
};

}  // namespace catio

#endif  // CATIO_HOUSE_H
