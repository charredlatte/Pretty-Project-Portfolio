// art.cpp -- the packs' files: a cache on disk, decoded into surfaces.
//
// The app ships with no pack art and fetches it from the gateway on first run (art.h says why). This
// module does not fetch: it reads what the cache holds, says what is missing, and takes bytes. It holds
// surfaces, not textures -- a texture belongs to a renderer, and draw makes one on first use -- so the
// cache needs no renderer and can be tested over a directory of files.

#include "catio/art.h"

#include <array>
#include <fstream>
#include <system_error>

#include "internal.h"

namespace catio::art {
namespace {

// Every file the page references, as CLAUDE.md's publish list has them; the house and the meadow
// first, so on first run the manor appears before the last button does.
const std::vector<File> kFiles = {
    {Id::House, "art/licensed/house.png", true},
    {Id::Decor, "art/licensed/decor.png", true},
    {Id::Meadow, "art/licensed/meadow.png", true},
    {Id::HouseUpper, "art/licensed/house-upper.png", true},
    {Id::Furniture, "art/furniture.png", true},                 // Cosy Cabin: the one committed sheet
    {Id::FurnitureLicensed, "art/licensed/furniture.png", true},
    {Id::MochiIdle, "art/licensed/mochi-idle.png", true},
    {Id::MochiBox, "art/licensed/mochi-box.png", true},
    {Id::Pochi, "art/licensed/pochi.png", true},
    {Id::UiPanel, "art/licensed/ui/panel.png", true},
    {Id::UiButton, "art/licensed/ui/button.png", true},
    {Id::UiButtonHover, "art/licensed/ui/button-hover.png", true},
    {Id::UiButtonDown, "art/licensed/ui/button-down.png", true},
    {Id::UiButtonGreen, "art/licensed/ui/button-green.png", true},
    {Id::UiButtonPink, "art/licensed/ui/button-pink.png", true},
    {Id::UiField, "art/licensed/ui/field.png", true},
    {Id::UiArrow, "art/licensed/ui/arrow.png", true},
    {Id::UiFrame, "art/licensed/ui/frame.png", true},
    {Id::UiDivider, "art/licensed/ui/divider.png", true},
    {Id::UiBubble, "art/licensed/ui/bubble.png", true},
    {Id::UiCorners, "art/licensed/ui/corners.png", true},
    {Id::UiToggle, "art/licensed/ui/toggle.png", true},
    {Id::UiStatus, "art/licensed/ui/status.png", true},
    {Id::UiFaces, "art/licensed/ui/faces.png", true},
    {Id::UiCrown, "art/licensed/ui/crown.png", true},
    {Id::UiStars, "art/licensed/ui/stars.png", true},
    {Id::UiCursor, "art/licensed/ui/cursor.png", true},
    {Id::UiCursorPoint, "art/licensed/ui/cursor-point.png", true},
    {Id::UiPointer, "art/licensed/ui/pointer.png", true},
    {Id::UiLogo, "art/licensed/ui/logo.png", true},
    {Id::UiPastel, "art/licensed/ui/pastel.png", true},          // Pastel's icons, pixelated by build-art.py
    {Id::PastelPanel, "art/licensed/pastel/panel.png", false},   // the map panel: smooth, never pixelated
    {Id::PastelPanelDark, "art/licensed/pastel/panel-dark.png", false},
    {Id::PastelFrame, "art/licensed/pastel/frame.png", false},
    {Id::PastelButton, "art/licensed/pastel/button.png", false},
    {Id::PastelButtonHover, "art/licensed/pastel/button-hover.png", false},
    {Id::PastelButtonDown, "art/licensed/pastel/button-down.png", false},
    {Id::PastelIcons, "art/licensed/pastel/icons.png", false},
    {Id::SproutFont, "art/licensed/ui/sprout.ttf", true},
};

constexpr size_t kCount = static_cast<size_t>(Id::Count);
bool is_font(Id id) { return id == Id::SproutFont; }

// a TrueType or OpenType font, by its first four bytes: not a portal's page, nor half a file
bool font_head(std::string_view head) {
    return head == std::string_view("\0\1\0\0", 4) || head == "true" || head == "OTTO" || head == "ttcf";
}
bool looks_like_font(const std::filesystem::path& p) {
    std::ifstream in(p, std::ios::binary);
    char head[4] = {};
    return in.read(head, 4) && font_head(std::string_view(head, 4));
}

}  // namespace

const std::vector<File>& files() { return kFiles; }

const File& file_of(Id id) {
    for (const auto& f : kFiles) if (f.id == id) return f;
    return kFiles.front();
}

struct Art::Impl {
    std::filesystem::path cache;
    std::array<Texture, kCount> tex{};
    std::array<bool, kCount> have{};
    bool scanned = false;
    std::string trouble;

    void drop(Id id) {
        Texture& t = tex[static_cast<size_t>(id)];
        if (t.gpu) SDL_DestroyTexture(t.gpu);
        if (t.surface) SDL_DestroySurface(t.surface);
        t = Texture{};
        have[static_cast<size_t>(id)] = false;
    }

    // a PNG into a surface the renderer can take; the font only needs to be there
    bool take(const File& f, SDL_Surface* s) {
        const size_t i = static_cast<size_t>(f.id);
        if (is_font(f.id)) { have[i] = true; return true; }
        if (!s) return false;
        drop(f.id);
        tex[i].surface = s;
        tex[i].pixel = f.pixel;
        have[i] = true;
        return true;
    }
};

Art::Art(std::filesystem::path cache_dir) : impl_(new Impl) { impl_->cache = std::move(cache_dir); }

Art::~Art() {
    for (const auto& f : kFiles) impl_->drop(f.id);
    delete impl_;
}

void Art::scan() {
    for (const auto& f : kFiles) {
        const auto path = impl_->cache / std::string(f.path);
        std::error_code ec;
        if (!std::filesystem::exists(path, ec)) continue;
        if (is_font(f.id) && !looks_like_font(path)) continue;   // a half-written or wrong file: fetched again
        impl_->take(f, is_font(f.id) ? nullptr : SDL_LoadPNG(to_utf8(path).c_str()));
    }
    impl_->scanned = true;
}

std::vector<const File*> Art::missing() const {
    std::vector<const File*> out;
    for (const auto& f : kFiles) if (!impl_->have[static_cast<size_t>(f.id)]) out.push_back(&f);
    return out;
}

std::shared_ptr<Fetched> prepare(Id id, std::string bytes) {
    auto ready = std::make_shared<Fetched>();
    if (is_font(id)) {
        // a TrueType or OpenType font, not a portal's page answered with a 200
        if (!font_head(std::string_view(bytes).substr(0, 4))) ready->trouble = "not_a_font";
    } else {
        SDL_IOStream* io = SDL_IOFromConstMem(bytes.data(), bytes.size());
        ready->surface = io ? SDL_LoadPNG_IO(io, true) : nullptr;
        if (!ready->surface) ready->trouble = "not_a_png";
    }
    if (ready->trouble.empty()) ready->bytes = std::move(bytes);
    return ready;
}

namespace {
// written beside its place, then put there whole: a full disk or a killed app leaves no half a file behind
bool keep(const std::filesystem::path& path, const std::string& bytes) {
    auto part = path;
    part += ".part";
    std::error_code ec;
    std::filesystem::create_directories(path.parent_path(), ec);
    bool ok;
    {
        std::ofstream out(part, std::ios::binary);
        out.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
        ok = bool(out);
    }
    if (ok) std::filesystem::rename(part, path, ec);
    if (!ok || ec) std::filesystem::remove(part, ec);
    return ok && !ec;
}
}  // namespace

bool Art::store(Id id, std::string_view bytes) { return adopt(id, prepare(id, std::string(bytes))); }

bool Art::adopt(Id id, const std::shared_ptr<Fetched>& ready) {
    if (!ready) { impl_->trouble = "not_a_png"; return false; }
    const File& f = file_of(id);
    if (ready->trouble.empty() && !keep(impl_->cache / std::string(f.path), ready->bytes)) ready->trouble = "cache_unwritable";
    if (ready->surface) impl_->take(f, ready->surface), ready->surface = nullptr;   // drawn, even if not kept
    else if (is_font(id) && ready->trouble.empty()) impl_->take(f, nullptr);         // the font is read from its file
    if (!ready->trouble.empty()) { impl_->trouble = ready->trouble; return false; }
    return true;
}

void Art::forget_gpu() {
    for (auto& t : impl_->tex) {
        if (t.gpu) SDL_DestroyTexture(t.gpu);
        t.gpu = nullptr, t.owner = nullptr;
    }
}

void Art::forget_all() {
    for (const auto& f : kFiles) {
        impl_->drop(f.id);
        std::error_code ec;
        std::filesystem::remove(impl_->cache / std::string(f.path), ec);
    }
    impl_->trouble.clear();
}

State Art::state() const {
    if (!impl_->scanned) return State::Scanning;
    if (!impl_->trouble.empty()) return State::Missing;
    return have() == total() ? State::Ok : State::Fetching;
}

int Art::have() const {
    int n = 0;
    for (bool b : impl_->have) n += b;
    return n;
}

int Art::total() const { return static_cast<int>(kFiles.size()); }
std::string_view Art::trouble() const { return impl_->trouble; }

std::filesystem::path Art::path(Id id) const {
    if (!impl_->have[static_cast<size_t>(id)]) return {};
    return impl_->cache / std::string(file_of(id).path);
}

Texture* Art::texture(Id id) const {
    Texture& t = impl_->tex[static_cast<size_t>(id)];
    return t.surface ? &t : nullptr;
}

}  // namespace catio::art
