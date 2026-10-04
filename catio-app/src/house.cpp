// house.cpp -- the café's data, and what the page derives from it.
//
// Each rule names the page's original in catio/index.html: AGENT_MOODS and catFromAgent, catFromAdopted,
// projectOf and lookOf (the coat), roomFor and catchAllRoom, queenRoom, queenOf, queenState. On the
// gateway there is no list_sessions, so a cat is an agent or an adopted chat and nothing else.

#include "catio/house.h"

#include <algorithm>
#include <array>
#include <chrono>
#include <map>

#include <nlohmann/json.hpp>

#include "catio/manor.h"

namespace catio {
namespace {

using json = nlohmann::json;

// MOODS, in rank order.
constexpr std::array<MoodInfo, 5> kMoods{{
    {"Upset: the last run failed", "Upset", "fail", true},
    {"Meowing for you", "Needs you", "need", true},
    {"Brought you something to review", "To review", "gift", true},
    {"Busy working", "Working", "work", false},
    {"Asleep: nothing to do", "Asleep", "sleep", false},
}};

// NAMES and QUEEN_NAMES, as in the page: a cat with no name of its own gets one from a hash of its id.
constexpr std::array<std::string_view, 32> kNames{
    "Praline", "Noisette", "Biscotte", "Caramel", "Figue", "Brioche", "Madeleine", "Pistache", "Tartine", "Chouquette",
    "Galette", "Canelé", "Miso", "Yuzu", "Sésame", "Cannelle", "Muscade", "Olive", "Prune", "Myrtille", "Cerise", "Guimauve",
    "Nougat", "Réglisse", "Clafoutis", "Crumble", "Macaron", "Mirabelle", "Pomme", "Gaufre", "Tofu", "Matcha"};
constexpr std::array<std::string_view, 12> kQueenNames{
    "Mémé", "Duchesse", "Joséphine", "Colette", "Berthe", "Augustine", "Odette",
    "Simone", "Marguerite", "Hortense", "Célestine", "Philomène"};
constexpr std::string_view kManner =
    "Elizabethan English, warm and a touch grand: \"my lady\", \"prithee\", \"'tis\", \"mayhap\", \"anon\". "
    "The news first, plain enough to act on; the flourish after.";
constexpr std::string_view kGreeting = "Good morrow, my lady. What wouldst thou have of me?";
constexpr int kCoats = 8;                  // COATS.length
constexpr std::string_view kQueenId = "queen";
constexpr std::string_view kQueenRoom = "hall";
// OPENING: the rooms in the order a new café opens them, public to private. The first open one is where new cats come in.
constexpr std::array<std::string_view, 10> kOpening{
    "living", "dining", "kitchen", "study", "sunroom", "garden", "brain", "bedroom", "bath", "hall"};

std::int64_t now_ms() {
    using namespace std::chrono;
    return duration_cast<milliseconds>(system_clock::now().time_since_epoch()).count();
}

// The page's hash: FNV-1a over the string's code points (for...of on a JS string walks code points).
std::uint32_t fnv(std::string_view s) {
    std::uint32_t h = 2166136261u;
    for (size_t i = 0; i < s.size();) {
        const unsigned char c = static_cast<unsigned char>(s[i]);
        std::uint32_t cp = c;
        int n = 1;
        if (c >= 0xF0) { cp = c & 0x07; n = 4; }
        else if (c >= 0xE0) { cp = c & 0x0F; n = 3; }
        else if (c >= 0xC0) { cp = c & 0x1F; n = 2; }
        for (int k = 1; k < n && i + k < s.size(); ++k) cp = (cp << 6) | (static_cast<unsigned char>(s[i + k]) & 0x3F);
        i += n;
        h ^= cp;
        h *= 16777619u;
    }
    return h;
}

std::string lower(std::string_view v) {
    std::string out(v);
    for (auto& ch : out) if (ch >= 'A' && ch <= 'Z') ch = static_cast<char>(ch - 'A' + 'a');
    return out;
}

// slug: lower-case, runs of anything but [a-z0-9_-] become one dash, trimmed, at most 80, else "none".
std::string slug(std::string_view v) {
    std::string out;
    bool dash = false;
    for (char ch : lower(v)) {
        const bool keep = (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || ch == '_' || ch == '-';
        if (keep) { out += ch; dash = false; }
        else if (!dash) { out += '-'; dash = true; }
    }
    const auto b = out.find_first_not_of('-');
    if (b == std::string::npos) return "none";
    out = out.substr(b, out.find_last_not_of('-') - b + 1);
    if (out.size() > 80) out.resize(80);
    return out.empty() ? "none" : out;
}

std::string str(const json& o, const char* key) {
    auto it = o.find(key);
    return it != o.end() && it->is_string() ? it->get<std::string>() : std::string{};
}
std::int64_t num(const json& o, const char* key) {
    auto it = o.find(key);
    return it != o.end() && it->is_number() ? it->get<std::int64_t>() : 0;
}
bool flag(const json& o, const char* key) {
    auto it = o.find(key);
    return it != o.end() && it->is_boolean() && it->get<bool>();
}

}  // namespace

const MoodInfo& info(Mood m) { return kMoods[static_cast<size_t>(m)]; }

// AGENT_MOODS: the gateway's words for how a cat is.
std::optional<Mood> mood_from(std::string_view wire) {
    if (wire == "needs") return Mood::Meow;
    if (wire == "failed") return Mood::Cry;
    if (wire == "review") return Mood::Box;
    if (wire == "busy") return Mood::Idle;
    if (wire == "done") return Mood::Sleep;
    return std::nullopt;
}

struct House::Impl {
    bool ready = false;
    std::map<std::string, json, std::less<>> docs;   // "<collection>/<id>" -> data
    json agents = json::array();
    json quizzes = json::array();

    // derived, rebuilt on every change
    std::map<std::string, Room, std::less<>> rooms;
    std::vector<Cat> cats, everything;
    Queen queen;
    std::vector<Quiz> homework;

    const json* doc(std::string_view path) const {
        auto it = docs.find(path);
        return it == docs.end() ? nullptr : &it->second;
    }

    void rebuild(const House& h) {
        rooms.clear();
        for (const auto& g : manor::geom()) {
            Room r;
            r.key = g.key;
            r.name = g.name;
            if (const json* d = doc("rooms/" + g.key)) {
                if (auto n = str(*d, "name"); !n.empty()) r.name = n;
                r.blurb = str(*d, "blurb");
                r.model = str(*d, "model");
                r.catch_all = flag(*d, "catchAll");
                r.closed = flag(*d, "closed");
                if (auto it = d->find("repos"); it != d->end() && it->is_array())
                    for (auto& x : *it) if (x.is_string()) r.repos.push_back(x.get<std::string>());
            }
            rooms[r.key] = std::move(r);
        }

        // her renames and moves of one cat: sessions/<id> on claude.ai, keyed by the cat's id here
        auto tweak = [&](const std::string& id) -> const json* { return doc("sessions/" + id); };

        auto finish = [&](Cat c, const std::string& project_name) {
            c.project = slug(project_name);
            const json* t = tweak(c.id);
            if (t) if (auto n = str(*t, "name"); !n.empty()) c.name = n;
            if (c.name.empty()) c.name = std::string(kNames[fnv(c.id) % kNames.size()]);
            int coat = static_cast<int>(fnv(c.project) % kCoats);
            if (const json* p = doc("projects/" + c.project))
                if (auto it = p->find("coat"); it != p->end() && it->is_number_integer()) {
                    const int v = it->get<int>();
                    if (v >= 0 && v < kCoats) coat = v;
                }
            c.coat = coat;
            // roomFor: her move first -- but only to a room that exists and is open, else the cat's own room
            // still gets its turn before the repo and the catch-all
            if (t)
                if (auto r = str(*t, "room"); !r.empty() && manor::of(r) && h.open(r)) c.room = r;
            c.room = h.room_for(c);
            return c;
        };

        cats.clear();
        everything.clear();
        // adopted chats: catFromAdopted
        for (const auto& [path, d] : docs) {
            if (path.rfind("cats/", 0) != 0) continue;
            Cat c;
            c.adopted = true;
            c.id = "adopted:" + path.substr(5);
            const std::string m = str(d, "mood");
            c.mood = m == "needs" ? Mood::Meow : m == "busy" ? Mood::Idle : Mood::Sleep;
            c.title = str(d, "title");
            if (c.title.empty()) c.title = "A chat";
            if (c.mood == Mood::Meow) { c.ask = str(d, "note"); if (c.ask.empty()) c.ask = "You marked this as needing you."; }
            c.updated = num(d, "updatedAt") ? num(d, "updatedAt") : num(d, "adoptedAt");
            c.link = str(d, "link");
            c.room = str(d, "room");
            c.name = str(d, "name");
            const std::string project = str(d, "project");
            Cat done = finish(std::move(c), project.empty() ? str(d, "title").empty() ? "A chat" : str(d, "title") : project);
            cats.push_back(done);
            everything.push_back(done);
        }
        // agents that report to the gateway: catFromAgent. The queen is not work to be done.
        for (const auto& a : agents) {
            if (!a.is_object()) continue;
            const std::string id = str(a, "id");
            if (id.empty() || id == kQueenId) continue;
            Cat c;
            c.id = "agent:" + id;
            c.mood = mood_from(str(a, "mood")).value_or(Mood::Sleep);
            c.title = str(a, "title");
            if (c.title.empty()) c.title = str(a, "name");
            if (c.title.empty()) c.title = id;
            if (info(c.mood).needs) { c.ask = str(a, "ask"); if (c.ask.empty()) c.ask = "Waiting for you."; }
            c.repo = str(a, "repo");
            c.model = str(a, "model");
            c.updated = num(a, "updated");
            c.waiting = static_cast<int>(num(a, "waiting"));
            c.archived = flag(a, "archived");
            c.room = str(a, "room");
            c.name = str(a, "name");
            const std::string session = str(a, "session");
            c.link = str(a, "via") == "claude-code" && !session.empty()
                ? "https://claude.ai/code/session_" + session.substr(session.find('_') == std::string::npos ? 0 : session.find('_') + 1)
                : str(a, "link");
            if (auto s = a.find("said"); s != a.end() && s->is_object()) { c.said = str(*s, "text"); c.said_at = num(*s, "at"); }
            // projectOf, for an agent: its project, else the last part of its repo, else "No repository"
            std::string project = str(a, "project");
            if (project.empty() && !c.repo.empty()) project = c.repo.substr(c.repo.rfind('/') + 1);
            if (project.empty()) project = "No repository";
            Cat done = finish(std::move(c), project);
            everything.push_back(done);
            if (!done.archived) cats.push_back(done);
        }
        // MOODS rank first, then the most recently heard from
        auto order = [](const Cat& a, const Cat& b) {
            return a.mood != b.mood ? a.mood < b.mood : a.updated > b.updated;
        };
        std::stable_sort(cats.begin(), cats.end(), order);
        std::stable_sort(everything.begin(), everything.end(), order);

        // queenOf: queens/house. (Notes kept by the room queens of before, queens/<room>, are hers until her
        // first save; that is a migration the page carries and this app need not.)
        queen = Queen{};
        const json* q = doc("queens/house");
        queen.name = q ? str(*q, "name") : std::string{};
        if (queen.name.empty()) queen.name = std::string(kQueenNames[fnv("queen:house") % kQueenNames.size()]);
        queen.manner = q && !str(*q, "manner").empty() ? str(*q, "manner") : std::string(kManner);
        queen.greeting = q && !str(*q, "greeting").empty() ? str(*q, "greeting") : std::string(kGreeting);
        queen.read_at = q ? num(*q, "readAt") : 0;
        queen.coat = static_cast<int>(fnv("queen:house") % kCoats);
        if (q)
            if (auto c = q->find("coat"); c != q->end() && c->is_number_integer()) {
                const int v = c->get<int>();
                if (v >= 0 && v < kCoats) queen.coat = v;
            }
        if (q) {
            if (auto v = q->find("voice"); v != q->end() && v->is_object()) queen.voice_on = flag(*v, "on");
            if (auto n = q->find("notes"); n != q->end() && n->is_array())
                for (auto& x : *n)
                    if (x.is_object() && !str(x, "text").empty())
                        queen.keeps.push_back(Note{str(x, "text"), flag(x, "pinned"), num(x, "at")});
        }
        std::stable_sort(queen.keeps.begin(), queen.keeps.end(), [](const Note& a, const Note& b) {
            return a.pinned != b.pinned ? a.pinned : a.at > b.at;
        });

        homework.clear();
        for (const auto& z : quizzes) {
            if (!z.is_object() || str(z, "status") == "done") continue;
            Quiz w;
            w.id = str(z, "id");
            w.kind = str(z, "kind");
            if (w.kind.empty()) w.kind = "unblock";
            w.title = str(z, "title");
            w.note = str(z, "note");
            w.hint = str(z, "hint");
            w.from = str(z, "from");
            w.ref = str(z, "ref");
            w.for_cat = str(z, "for");
            w.at = num(z, "at");
            if (auto qs = z.find("questions"); qs != z.end() && qs->is_array())
                for (auto& x : *qs) {
                    Question qn;
                    qn.ask = str(x, "q");
                    qn.written = flag(x, "free");
                    if (auto o = x.find("options"); o != x.end() && o->is_array())
                        for (auto& y : *o) if (y.is_string()) qn.options.push_back(y.get<std::string>());
                    w.questions.push_back(std::move(qn));
                }
            homework.push_back(std::move(w));
        }
        std::stable_sort(homework.begin(), homework.end(), [](const Quiz& a, const Quiz& b) { return a.at < b.at; });
    }
};

House::House() : impl_(new Impl) {}
House::~House() { delete impl_; }

void House::docs(std::string_view body) {
    json j = json::parse(body, nullptr, false);
    impl_->docs.clear();
    if (j.is_object())
        if (auto d = j.find("docs"); d != j.end() && d->is_object())
            for (auto& [path, data] : d->items()) impl_->docs[path] = data;
    impl_->ready = true;
    impl_->rebuild(*this);
}

void House::doc(std::string_view path, std::string_view body) {
    if (body.empty()) impl_->docs.erase(std::string(path));
    else impl_->docs[std::string(path)] = json::parse(body, nullptr, false);
    impl_->rebuild(*this);
}

void House::agents(std::string_view body) {
    json j = json::parse(body, nullptr, false);
    impl_->agents = j.is_object() && j.contains("agents") && j["agents"].is_array() ? j["agents"] : json::array();
    impl_->rebuild(*this);
}

void House::quizzes(std::string_view body) {
    json j = json::parse(body, nullptr, false);
    impl_->quizzes = j.is_object() && j.contains("quizzes") && j["quizzes"].is_array() ? j["quizzes"] : json::array();
    impl_->rebuild(*this);
}

bool House::ready() const { return impl_->ready; }

bool House::never_set_up() const {
    if (!impl_->ready) return false;
    return std::none_of(impl_->docs.begin(), impl_->docs.end(),
                        [](const auto& d) { return d.first.rfind("rooms/", 0) == 0; });
}

std::string House::name() const {
    const json* h = impl_->doc("house/main");
    std::string n = h ? str(*h, "name") : std::string{};
    return n.empty() ? "KittyChat Café" : n;
}

const Room& House::room(std::string_view key) const {
    static const Room none;
    auto it = impl_->rooms.find(key);
    return it == impl_->rooms.end() ? none : it->second;
}

bool House::open(std::string_view key) const { return !room(key).closed; }

// catchAllRoom: the room marked catch-all, if it is open; else the first open room of the opening order.
std::string House::catch_all_room() const {
    for (const auto& g : manor::geom())
        if (room(g.key).catch_all) {
            if (open(g.key)) return g.key;
            break;
        }
    for (auto k : kOpening) if (open(k)) return std::string(k);
    return "living";
}

std::string House::front_door_room() const {
    for (auto k : kOpening) if (open(k)) return std::string(k);
    return "living";
}

// queenRoom: the hall's seat, unless the hall is closed.
std::string House::queen_room() const {
    const manor::Geom* g = manor::of(kQueenRoom);
    return g && g->queen && open(kQueenRoom) ? std::string(kQueenRoom) : catch_all_room();
}

const std::vector<Cat>& House::cats(bool everything) const { return everything ? impl_->everything : impl_->cats; }

const Cat* House::cat(std::string_view id) const {
    for (const auto& c : impl_->everything) if (c.id == id) return &c;
    return nullptr;
}

// roomFor: the room it was given, if that room exists and is open; else the open room whose repos list
// its repo (by full name or by the part after the slash); else the catch-all.
std::string House::room_for(const Cat& c) const {
    if (!c.room.empty() && manor::of(c.room) && open(c.room)) return c.room;
    const std::string repo = lower(c.repo), name = repo.substr(repo.rfind('/') + 1);
    if (!repo.empty())
        for (const auto& g : manor::geom()) {
            if (!open(g.key)) continue;
            for (const auto& r : room(g.key).repos) {
                std::string x = lower(r);
                x.erase(0, x.find_first_not_of(" \t"));
                x.erase(x.find_last_not_of(" \t") + 1);
                if (!x.empty() && (x == repo || x == name)) return g.key;
            }
        }
    return catch_all_room();
}

std::vector<const Cat*> House::needing() const {
    std::vector<const Cat*> out;
    for (const auto& c : impl_->cats) if (info(c.mood).needs) out.push_back(&c);
    return out;
}

// The line at the front door: the meowing cats only -- upset and to-review cats stay in their rooms --
// the longest wait first. view.h keeps when the app first saw each one wait; until then, the oldest word.
std::vector<const Cat*> House::queue() const {
    std::vector<const Cat*> out;
    for (const auto& c : impl_->cats) if (c.mood == Mood::Meow) out.push_back(&c);
    std::stable_sort(out.begin(), out.end(), [](const Cat* a, const Cat* b) {
        return a->updated != b->updated ? a->updated < b->updated : a->id < b->id;
    });
    return out;
}

// The other floor's badge counts a cat where it stands: a meowing one stands in the queue, in the hall.
int House::needing_on(std::string_view floor) const {
    const manor::Level want = floor == "upper" ? manor::Level::Upper : manor::Level::Ground;
    int n = 0;
    for (const Cat* c : needing()) {
        const manor::Level at = c->mood == Mood::Meow ? manor::Level::Ground : manor::level_of(c->room);
        if (at == want) ++n;
    }
    return n;
}

const Queen& House::queen() const { return impl_->queen; }

// queenState: away when her runner hasn't been heard from for two minutes; busy while she answers.
QueenState House::queen_state() const {
    for (const auto& a : impl_->agents)
        if (a.is_object() && str(a, "id") == kQueenId) {
            if (now_ms() - num(a, "updated") > 2 * 60 * 1000) return QueenState::Away;
            return str(a, "mood") == "busy" ? QueenState::Busy : QueenState::Here;
        }
    return QueenState::Away;
}

Mood House::queen_mood() const {
    switch (queen_state()) {
        case QueenState::Away: return Mood::Sleep;
        case QueenState::Busy: return Mood::Idle;
        case QueenState::Here: break;
    }
    if (!homework().empty() || !handoffs().empty()) return Mood::Box;
    const auto& keeps = impl_->queen.keeps;
    return std::any_of(keeps.begin(), keeps.end(), [](const Note& n) { return n.pinned; }) ? Mood::Meow : Mood::Idle;
}

// What the cats brought her: a word newer than when her card was last opened.
std::vector<const Cat*> House::handoffs() const {
    std::vector<const Cat*> out;
    for (const auto& c : impl_->cats) if (!c.adopted && c.said_at > impl_->queen.read_at) out.push_back(&c);
    return out;
}

std::vector<const Quiz*> House::homework(std::string_view kind) const {
    std::vector<const Quiz*> out;
    for (const auto& w : impl_->homework) if (kind.empty() || w.kind == kind) out.push_back(&w);
    return out;
}

}  // namespace catio
