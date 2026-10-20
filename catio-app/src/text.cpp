// text.cpp -- the two fonts: the pack's pixel font and the committed Nunito, over SDL_ttf.
//
// The pixel font is opened once at 18px and its words blitted at x css, nearest-neighbour: one font
// pixel a CSS pixel, as the page keeps it (`--px-size: 18px`, "anything else blurs"). Nunito is opened
// at the size it is drawn, in device pixels, because it is a smooth font and should be rasterised for
// the screen it is on.
//
// Each font keeps the textures of the words it has drawn, so a menu standing open costs nothing to
// redraw. The cache is small and simply emptied when full: the words on screen change rarely.

#include <SDL3_ttf/SDL_ttf.h>

#include <algorithm>
#include <map>
#include <memory>
#include <utility>

#include "catio/draw.h"
#include "internal.h"

namespace catio::draw {
namespace {

constexpr size_t kCacheMax = 512;

bool ttf_ready() {
    static bool ok = TTF_WasInit() > 0 || TTF_Init();
    return ok;
}

std::uint32_t key_of(Colour c) { return std::uint32_t(c.r) << 24 | std::uint32_t(c.g) << 16 | std::uint32_t(c.b) << 8 | c.a; }

struct Words {
    SDL_Texture* tex = nullptr;
    float w = 0, h = 0;
};

// The words one font has drawn, for one renderer.
struct Cache {
    SDL_Renderer* owner = nullptr;
    std::map<std::pair<std::string, std::uint32_t>, Words> words;

    void clear() {
        for (auto& [k, w] : words) SDL_DestroyTexture(w.tex);
        words.clear();
    }
    const Words* get(SDL_Renderer* r, TTF_Font* font, std::string_view text, Colour col, SDL_ScaleMode mode) {
        if (text.empty() || !font || !r) return nullptr;
        if (r != owner) clear(), owner = r;
        auto key = std::make_pair(std::string(text), key_of(col));
        if (auto it = words.find(key); it != words.end()) return &it->second;
        if (words.size() >= kCacheMax) clear();
        SDL_Surface* s = TTF_RenderText_Blended(font, text.data(), text.size(), SDL_Color{col.r, col.g, col.b, 255});
        if (!s) return nullptr;
        Words w;
        w.tex = SDL_CreateTextureFromSurface(r, s);
        w.w = float(s->w), w.h = float(s->h);
        SDL_DestroySurface(s);
        if (!w.tex) return nullptr;
        SDL_SetTextureScaleMode(w.tex, mode);
        SDL_SetTextureAlphaMod(w.tex, col.a);
        return &(words[std::move(key)] = w);
    }
    ~Cache() { clear(); }
};

Pt size_of(TTF_Font* font, std::string_view text) {
    int w = 0, h = 0;
    if (font && !text.empty()) TTF_GetStringSize(font, text.data(), text.size(), &w, &h);
    if (font && h == 0) h = TTF_GetFontHeight(font);
    return {float(w), float(h)};
}

// white-space: normal -- a newline, a tab or a run of spaces is one space, as the page shows an ask. One at the
// start stays: " · Waiting" follows a cat's name inline
std::string collapsed(std::string_view text) {
    std::string out;
    bool space = false;
    for (char c : text) {
        if (c == ' ' || c == '\n' || c == '\r' || c == '\t') { space = true; continue; }
        if (space) out += ' ', space = false;
        out += c;
    }
    return out;
}

}  // namespace

// One UTF-8 character off the end.
void pop_char(std::string& s) {
    while (!s.empty() && (static_cast<unsigned char>(s.back()) & 0xC0) == 0x80) s.pop_back();
    if (!s.empty()) s.pop_back();
}

// ---- the pixel font --------------------------------------------------------------------------------

struct Pixel::Impl {
    TTF_Font* font = nullptr;
    std::filesystem::path round_ttf;
    float round_px = 0;
    mutable std::map<int, std::unique_ptr<Body>> rounds;   // the round font, at each css it is drawn at
    mutable Cache cache;
    const Body* round(int css) const {
        if (round_ttf.empty()) return nullptr;
        auto& b = rounds[css];
        if (!b) b = std::make_unique<Body>(), b->open(round_ttf, round_px * float(css));
        return b->ready() ? b.get() : nullptr;
    }
};

Pixel::Pixel() : impl_(new Impl) {}
Pixel::~Pixel() {
    impl_->cache.clear();
    if (impl_->font) TTF_CloseFont(impl_->font);
    delete impl_;
}

bool Pixel::open(const std::filesystem::path& ttf) {
    if (impl_->font || ttf.empty() || !ttf_ready()) return impl_->font != nullptr;
    impl_->font = TTF_OpenFont(ttf.string().c_str(), 18.0f);
    if (impl_->font) TTF_SetFontHinting(impl_->font, TTF_HINTING_MONO);   // a pixel font: whole pixels or nothing
    return impl_->font != nullptr;
}

void Pixel::fallback(const std::filesystem::path& ttf, float px) {
    impl_->rounds.clear();
    impl_->round_ttf = ttf, impl_->round_px = px;
}

void Pixel::close() {
    impl_->cache.clear();
    if (impl_->font) TTF_CloseFont(impl_->font), impl_->font = nullptr;
}

bool Pixel::ready() const { return impl_->font || impl_->round(1); }

Pt Pixel::measure(std::string_view text, int css) const {
    if (!impl_->font) { const Body* r = impl_->round(css); return r ? r->measure(text) : Pt{}; }
    const Pt p = size_of(impl_->font, text);
    return {p.x * css, p.y * css};
}

void Pixel::put(const Ctx& c, std::string_view text, float x, float y, Colour col) const {
    if (!impl_->font) {
        if (const Body* r = impl_->round(c.css)) r->put(c, text, x, y, col);
        return;
    }
    const Words* w = impl_->cache.get(c.canvas->r, impl_->font, text, col, SDL_SCALEMODE_NEAREST);
    if (!w) return;
    const SDL_FRect dst{x, y, w->w * c.css, w->h * c.css};
    SDL_RenderTexture(c.canvas->r, w->tex, nullptr, &dst);
}

// ---- the body font ---------------------------------------------------------------------------------

struct Body::Impl {
    TTF_Font* font = nullptr;
    float px = 0;
    mutable Cache cache;
};

Body::Body() : impl_(new Impl) {}
Body::~Body() {
    impl_->cache.clear();
    if (impl_->font) TTF_CloseFont(impl_->font);
    delete impl_;
}

bool Body::open(const std::filesystem::path& ttf, float px) {
    if (!ttf_ready()) return false;
    if (impl_->font) TTF_CloseFont(impl_->font), impl_->font = nullptr;
    impl_->cache.clear();
    impl_->font = TTF_OpenFont(ttf.string().c_str(), px);
    if (impl_->font) TTF_SetFontHinting(impl_->font, TTF_HINTING_LIGHT);
    impl_->px = px;
    return impl_->font != nullptr;
}

bool Body::ready() const { return impl_->font != nullptr; }
float Body::px() const { return impl_->px; }

Pt Body::measure(std::string_view text) const { return size_of(impl_->font, text); }

std::string Body::cut(std::string_view text, float width) const {
    const std::string s = collapsed(text);
    if (!impl_->font || measure(s).x <= width) return s;
    // the longest run of whole characters that fits with its ellipsis, found by halving
    std::vector<size_t> ends{0};
    for (size_t i = 1; i <= s.size(); ++i) if (i == s.size() || (static_cast<unsigned char>(s[i]) & 0xC0) != 0x80) ends.push_back(i);
    size_t lo = 0, hi = ends.size() - 1;
    while (lo < hi) {
        const size_t mid = (lo + hi + 1) / 2;
        if (measure(s.substr(0, ends[mid]) + "…").x <= width) lo = mid;
        else hi = mid - 1;
    }
    std::string out = s.substr(0, ends[lo]);
    while (!out.empty() && out.back() == ' ') out.pop_back();
    return out + "…";
}

std::string Body::tail(std::string_view text, float width) const {
    const std::string s = collapsed(text);
    if (!impl_->font || measure(s).x <= width) return s;
    std::vector<size_t> starts;   // every character's first byte, and the end
    for (size_t i = 0; i < s.size(); ++i) if ((static_cast<unsigned char>(s[i]) & 0xC0) != 0x80) starts.push_back(i);
    starts.push_back(s.size());
    size_t lo = 0, hi = starts.size() - 1;   // the earliest start whose tail fits with its ellipsis
    while (lo < hi) {
        const size_t mid = (lo + hi) / 2;
        if (measure("…" + s.substr(starts[mid])).x <= width) hi = mid;
        else lo = mid + 1;
    }
    return "…" + s.substr(starts[lo]);
}

std::vector<std::string> Body::wrap(std::string_view raw, float width, int max_lines) const {
    std::vector<std::string> lines;
    const std::string text = collapsed(raw);
    if (!impl_->font || text.empty()) return lines;
    std::string line;
    auto fits = [&](const std::string& s) { return measure(s).x <= width; };
    size_t i = 0;
    while (i < text.size()) {
        size_t j = text.find(' ', i);
        if (j == std::string_view::npos) j = text.size();
        std::string word(text.substr(i, j - i));
        i = j + 1;
        const std::string tried = line.empty() ? word : line + " " + word;
        if (fits(tried)) { line = tried; continue; }
        if (!line.empty()) lines.push_back(line), line.clear();
        // a word wider than the line breaks anywhere (overflow-wrap: anywhere)
        while (!word.empty() && !fits(word)) {
            size_t bytes = 0;
            TTF_MeasureString(impl_->font, word.data(), word.size(), int(width), nullptr, &bytes);
            size_t n = std::max<size_t>(1, bytes);
            while (n < word.size() && (static_cast<unsigned char>(word[n]) & 0xC0) == 0x80) ++n;
            lines.push_back(word.substr(0, n));
            word.erase(0, n);
        }
        line = word;
    }
    if (!line.empty()) lines.push_back(line);
    if (max_lines > 0 && int(lines.size()) > max_lines) {
        std::string last = lines[size_t(max_lines) - 1];
        for (size_t k = size_t(max_lines); k < lines.size(); ++k) last += " " + lines[k];
        lines.resize(size_t(max_lines));
        lines.back() = cut(last, width);
    }
    return lines;
}

void Body::put(const Ctx& c, std::string_view text, float x, float y, Colour col) const {
    const Words* w = impl_->cache.get(c.canvas->r, impl_->font, text, col, SDL_SCALEMODE_LINEAR);
    if (!w) return;
    const SDL_FRect dst{x, y, w->w, w->h};
    SDL_RenderTexture(c.canvas->r, w->tex, nullptr, &dst);
}

}  // namespace catio::draw
