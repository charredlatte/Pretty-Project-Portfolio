// net_curl.cpp -- the gateway over libcurl, for a desktop.
//
// One easy handle per Gateway, used on Net's worker thread alone. The cookie is kept by hand (net.h says
// why): read from its file at start, sent as a Cookie header, taken from /login's Set-Cookie, and written
// back to a file only its owner can read. Writes carry X-Catio: 1 and no Origin, which is what the
// gateway's fromCafe() wants. Every failure comes back as the gateway's own {code, error}; a transport
// failure as "unreachable", and /login's HTML refusals as the words on the page it would have shown.

#include "catio/net.h"

#include <curl/curl.h>

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <iterator>
#include <deque>
#include <fstream>
#include <mutex>
#include <system_error>
#include <thread>
#include <utility>
#include <vector>

#include <nlohmann/json.hpp>

namespace catio::net {
namespace {

constexpr std::string_view kCookie = "__Host-catio";

void global_init() {
    static std::once_flag once;
    std::call_once(once, [] { curl_global_init(CURL_GLOBAL_DEFAULT); });
}

// The jar is two lines: the gateway it was given by, then its cookie. A cookie is only ever read back for that
// same gateway, so a different address typed in, or passed, never receives another gateway's credential.
std::string read_jar(const std::filesystem::path& jar, const std::string& origin) {
    std::ifstream in(jar, std::ios::binary);
    std::string from, token;
    std::getline(in, from);
    std::getline(in, token);
    for (std::string* s : {&from, &token})
        while (!s->empty() && (s->back() == '\r' || s->back() == ' ')) s->pop_back();
    return from == origin ? token : std::string{};
}

// Asked between the bytes of a transfer: a non-zero answer abandons it, so closing the app never waits out a timeout.
int on_progress(void* stop, curl_off_t, curl_off_t, curl_off_t, curl_off_t) {
    return stop && static_cast<const std::atomic<bool>*>(stop)->load() ? 1 : 0;
}

// the cookie's value is 64 hex characters; anything else is not one of the gateway's
bool plausible(std::string_view token) {
    if (token.empty() || token.size() > 256) return false;
    for (char c : token) if (!std::isalnum(static_cast<unsigned char>(c)) && c != '-' && c != '_') return false;
    return true;
}

// No answer bigger than the gateway ever gives (a 20 MB file is its largest): a portal's endless page is cut off,
// not held in a phone's memory.
constexpr size_t kMaxBody = 32u << 20;
size_t on_body(char* data, size_t size, size_t n, void* out) {
    auto* body = static_cast<std::string*>(out);
    if (body->size() + size * n > kMaxBody) return 0;   // libcurl ends the transfer
    body->append(data, size * n);
    return size * n;
}

// Set-Cookie: __Host-catio=<token>; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=...
size_t on_header(char* data, size_t size, size_t n, void* out) {
    std::string_view line(data, size * n);
    constexpr std::string_view kSet = "set-cookie:";
    if (line.size() > kSet.size()) {
        std::string head(line.substr(0, kSet.size()));
        for (char& c : head) c = char(std::tolower(static_cast<unsigned char>(c)));
        if (head == kSet) {
            std::string_view v = line.substr(kSet.size());
            while (!v.empty() && v.front() == ' ') v.remove_prefix(1);
            if (v.substr(0, kCookie.size()) == kCookie && v.size() > kCookie.size() && v[kCookie.size()] == '=') {
                v.remove_prefix(kCookie.size() + 1);
                *static_cast<std::string*>(out) = std::string(v.substr(0, v.find_first_of(";\r\n")));
            }
        }
    }
    return size * n;
}

// esc() in harness/gateway/src/signin.js writes &#NN; for & < > " ', so every entity is decoded, named or numbered.
std::string unescape(std::string s) {
    std::string out;
    for (size_t i = 0; i < s.size(); ++i) {
        const size_t semi = s[i] == '&' ? s.find(';', i) : std::string::npos;
        if (semi == std::string::npos || semi - i > 8) { out += s[i]; continue; }
        const std::string ent = s.substr(i + 1, semi - i - 1);
        long code = -1;
        if (ent.size() > 1 && ent[0] == '#') code = std::strtol(ent.c_str() + 1 + (ent[1] == 'x'), nullptr, ent[1] == 'x' ? 16 : 10);
        else if (ent == "amp") code = '&';
        else if (ent == "lt") code = '<';
        else if (ent == "gt") code = '>';
        else if (ent == "quot") code = '"';
        else if (ent == "apos") code = '\'';
        if (code < 0x20 || code > 0x7E) { out += s[i]; continue; }   // only ASCII is ever escaped there
        out += char(code);
        i = semi;
    }
    return out;
}

// The text of every element opening with `open`, in order.
std::vector<std::string> all_of(const std::string& html, std::string_view open, std::string_view close) {
    std::vector<std::string> out;
    for (size_t a = html.find(open); a != std::string::npos; a = html.find(open, a + open.size())) {
        const size_t b = html.find(close, a + open.size());
        if (b == std::string::npos) break;
        out.push_back(unescape(html.substr(a + open.size(), b - a - open.size())));
    }
    return out;
}

// The sign-in page's own refusal: its alert, and when the gateway has no account yet, each warning light that is
// a cross (noAccount() in harness/gateway/src/signin.js: the lights that are fine say nothing she has to do) or,
// with no cross, why the first account still couldn't be made.
std::string words_of(const std::string& html) {
    const auto alert = all_of(html, "<p class=\"bad\" role=\"alert\">", "</p>");
    if (alert.empty()) return {};
    std::string s = alert.front();
    for (const auto& light : all_of(html, "<li class=\"bad\">", "</li>")) s += " " + light;
    for (const auto& why : all_of(html, "<p class=\"bad\">", "</p>")) s += " " + why;
    return s;
}

std::string code_for(long status) {
    switch (status) {
        case 401: return "unauthorized";   // signed_out only when the gateway says so, in its own JSON: not a proxy's page
        case 403: return "forbidden";
        case 404: return "not_found";
        case 413: return "too_big";
        case 429: return "busy";
        case 503: return "unavailable";
        default: return "unavailable";
    }
}

}  // namespace

bool Reply::ok() const { return err.code.empty() && status >= 200 && status < 400; }
bool signed_out(const Reply& r) { return r.err.code == "signed_out"; }

struct Gateway::Impl {
    std::string origin;
    std::filesystem::path jar;
    std::string token;
    CURL* curl = nullptr;
    bool safe = false;                         // https, or the loopback
    const std::atomic<bool>* stop = nullptr;   // Net's: set when the app is closing

    void keep(const std::string& t) {
        token = t;
        std::error_code ec;
        std::filesystem::create_directories(jar.parent_path(), ec);
        // made empty and narrowed to its owner first, so the cookie is never in a file anyone else may read
        { std::ofstream touch(jar, std::ios::binary | std::ios::app); }
        std::filesystem::permissions(jar, std::filesystem::perms::owner_read | std::filesystem::perms::owner_write,
                                     std::filesystem::perm_options::replace, ec);
        std::ofstream out(jar, std::ios::binary | std::ios::trunc);
        out << origin << "\n" << t << "\n";
    }
    void forget() {
        token.clear();
        std::error_code ec;
        std::filesystem::remove(jar, ec);
    }

    std::string escape(std::string_view s) {
        if (s.empty()) return {};   // curl reads a length of 0 as "up to the first NUL"
        char* e = curl_easy_escape(curl, s.data(), int(s.size()));
        std::string out = e ? e : "";
        curl_free(e);
        return out;
    }
    // each segment of a document's path, encoded on its own (the page's encodeURIComponent per segment)
    std::string doc_path(std::string_view doc) {
        std::string out = "/api/db";
        size_t i = 0;
        while (i <= doc.size()) {
            const size_t j = std::min(doc.find('/', i), doc.size());
            out += "/" + escape(doc.substr(i, j - i));
            i = j + 1;
        }
        return out;
    }

    Reply call(const char* method, const std::string& path, std::string_view body, std::string_view type,
               bool write, std::vector<std::string> extra = {}, std::string* set_cookie = nullptr) {
        Reply r;
        if (!curl) { r.err = {"unreachable", "The network isn't ready."}; return r; }
        if (!safe) { r.err = {"insecure", "Your gateway's address must start with https://."}; return r; }
        curl_easy_reset(curl);
        const std::string url = origin + path;
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, method);
        curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 0L);   // /login's 303 is the answer, not somewhere to go
        curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 10L);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 60L);
        curl_easy_setopt(curl, CURLOPT_USERAGENT, "KittyChatCafe/0.1");
#if LIBCURL_VERSION_NUM >= 0x075500
        curl_easy_setopt(curl, CURLOPT_PROTOCOLS_STR, "https,http");
#else   // before 7.85 (Ubuntu 22.04 has 7.81)
        curl_easy_setopt(curl, CURLOPT_PROTOCOLS, long(CURLPROTO_HTTPS | CURLPROTO_HTTP));
#endif
        curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
        curl_easy_setopt(curl, CURLOPT_NOPROGRESS, 0L);
        curl_easy_setopt(curl, CURLOPT_XFERINFOFUNCTION, on_progress);
        curl_easy_setopt(curl, CURLOPT_XFERINFODATA, const_cast<std::atomic<bool>*>(stop));
        if (std::string_view(method) != "GET" && std::string_view(method) != "DELETE") {
            curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body.data());
            curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE_LARGE, curl_off_t(body.size()));
        }
        curl_slist* h = nullptr;
        if (!token.empty()) h = curl_slist_append(h, ("Cookie: " + std::string(kCookie) + "=" + token).c_str());
        if (!type.empty()) h = curl_slist_append(h, ("Content-Type: " + std::string(type)).c_str());
        if (write) h = curl_slist_append(h, "X-Catio: 1");
        h = curl_slist_append(h, "Expect:");   // no 100-continue round trip for a file
        for (const auto& e : extra) h = curl_slist_append(h, e.c_str());
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, h);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, on_body);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &r.body);
        std::string cookie;
        curl_easy_setopt(curl, CURLOPT_HEADERFUNCTION, on_header);
        curl_easy_setopt(curl, CURLOPT_HEADERDATA, &cookie);
        const CURLcode rc = curl_easy_perform(curl);
        curl_slist_free_all(h);
        if (rc == CURLE_WRITE_ERROR) { r.err = {"too_big", "The answer was bigger than your gateway ever sends."}; return r; }
        if (rc != CURLE_OK) {
            r.err = {"unreachable", curl_easy_strerror(rc)};
            return r;
        }
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &r.status);
        if (set_cookie) *set_cookie = cookie;
        // A redirect is the answer only to /login (its 303 and the cookie). Anywhere else something stands in front of
        // the gateway -- a sign-in page, a captive portal -- and its body is not the café's.
        if (r.status >= 300 && r.status < 400 && !set_cookie) {
            r.err = {"redirected", "Something in front of your gateway sent the app elsewhere (" + std::to_string(r.status) +
                                       "), so this wasn't the caf\u00e9's answer."};
            return r;
        }
        if (r.status >= 400) {
            r.err.code = code_for(r.status);
            try {
                const auto j = nlohmann::json::parse(r.body);
                if (j.is_object()) {
                    if (j.contains("code") && j["code"].is_string()) r.err.code = j["code"].get<std::string>();
                    if (j.contains("error") && j["error"].is_string()) r.err.message = j["error"].get<std::string>();
                }
            } catch (...) {
                r.err.message = words_of(r.body);
            }
            if (r.err.message.empty()) r.err.message = "The gateway answered " + std::to_string(r.status) + ".";
            // run out or revoked: it would only be refused again. Not /login's 401, a wrong password, nor a 401 to a
            // gateway this jar's cookie isn't for: neither says anything of the cookie kept (perhaps another gateway's)
            if (r.err.code == "signed_out" && path != "/login" && !token.empty()) forget();
        }
        return r;
    }
};

Gateway::Gateway(std::string origin, std::filesystem::path cookie_jar) : impl_(new Impl) {
    global_init();
    impl_->origin = bare(std::move(origin));
    impl_->jar = std::move(cookie_jar);
    impl_->safe = safe_origin(impl_->origin);
    if (const std::string t = read_jar(impl_->jar, impl_->origin); plausible(t)) impl_->token = t;
    impl_->curl = curl_easy_init();
}

Gateway::~Gateway() {
    if (impl_->curl) curl_easy_cleanup(impl_->curl);
    delete impl_;
}

Reply Gateway::login(std::string_view user, std::string_view password) {
    const std::string form = "user=" + impl_->escape(user) + "&password=" + impl_->escape(password);
    std::string cookie;
    Reply r = impl_->call("POST", "/login", form, "application/x-www-form-urlencoded", false, {}, &cookie);
    if (r.status == 303) {
        if (!plausible(cookie)) r.err = {"no_cookie", "The gateway let you in but gave no cookie to keep."};
        else impl_->keep(cookie);
    } else if (r.status == 401)
        r.err.code = "wrong";        // the handle and password, not a cookie run out
    else if (r.status == 429)
        r.err.code = "locked";       // too many wrong tries
    else if (r.status == 503)
        r.err.code = "no_account";   // the gateway's secrets made no account yet: its message carries the lights
    else if (r.ok())
        r.err = {"unexpected", "The gateway answered " + std::to_string(r.status) + " to signing in."};
    return r;
}

bool Gateway::signed_in() const { return !impl_->token.empty(); }
// POST /logout first, so the cookie stops working at the gateway now, not in a month; then the file goes, whatever
// the gateway said.
void Gateway::sign_out() {
    if (!impl_->token.empty()) impl_->call("POST", "/logout", {}, {}, false);
    impl_->forget();
}

Reply Gateway::docs() { return impl_->call("GET", "/api/db", {}, {}, false); }
// the document's data, sent as the gateway wants it: {"data": {...}}
Reply Gateway::put(std::string_view doc, std::string_view json) {
    return impl_->call("PUT", impl_->doc_path(doc), "{\"data\":" + std::string(json) + "}", "application/json", true);
}
Reply Gateway::patch(std::string_view doc, std::string_view json) {
    return impl_->call("PATCH", impl_->doc_path(doc), "{\"data\":" + std::string(json) + "}", "application/json", true);
}
Reply Gateway::erase(std::string_view doc) { return impl_->call("DELETE", impl_->doc_path(doc), {}, {}, true); }

Reply Gateway::tool(std::string_view name, std::string_view json) {
    return impl_->call("POST", "/api/tools/" + impl_->escape(name), json.empty() ? "{}" : json, "application/json", true);
}

Reply Gateway::file(std::string_view name, std::string_view mime, std::string_view bytes) {
    return impl_->call("POST", "/api/files", bytes, mime.empty() ? "application/octet-stream" : mime, true,
                       {"X-Name: " + impl_->escape(name)});
}
Reply Gateway::unfile(std::string_view id) { return impl_->call("DELETE", "/api/files/" + impl_->escape(id), {}, {}, true); }

Reply Gateway::art(std::string_view path) {
    // the path is the pack file's, "art/licensed/ui/panel.png": its segments are already safe
    return impl_->call("GET", "/" + std::string(path), {}, {}, false);
}

// ---- the worker ----

struct Net::Impl {
    Gateway gateway;
    std::filesystem::path jar;
    std::string origin;
    std::atomic<bool> closing{false};   // abandon the transfer in flight
    std::condition_variable idle;       // a job has finished
    bool working = false, working_first = false;
    std::mutex m;
    std::condition_variable cv;
    struct Waiting { std::uint32_t ticket; Job job; bool first; };
    std::deque<Waiting> in;
    std::deque<std::pair<std::uint32_t, Reply>> out;
    std::uint32_t next = 1;
    int busy = 0;
    bool stop = false;
    std::thread worker;

    Impl(std::string o, std::filesystem::path j) : gateway(o, j), jar(std::move(j)), origin(bare(std::move(o))) {
        gateway.impl_->stop = &closing;
        worker = std::thread([this] { run(); });
    }
    void run() {
        for (;;) {
            Waiting job;
            {
                std::unique_lock<std::mutex> lock(m);
                cv.wait(lock, [this] { return stop || !in.empty(); });
                if (stop) return;
                job = std::move(in.front());
                in.pop_front();
                working = true, working_first = job.first;
                if (job.first) closing = false;   // a /logout is let through even while the app closes
            }
            Reply r = job.job(gateway);
            std::lock_guard<std::mutex> lock(m);
            working = false;
            out.emplace_back(job.ticket, std::move(r));
            idle.notify_all();
        }
    }
};

Net::Net(std::string origin, std::filesystem::path cookie_jar) : impl_(new Impl(std::move(origin), std::move(cookie_jar))) {}

// Closing: what jumped the queue (a sign-out's /logout) is still finished, for up to three seconds; the rest is
// dropped, and a transfer in flight that isn't one of those is abandoned rather than waited out.
Net::~Net() {
    {
        std::unique_lock<std::mutex> lock(impl_->m);
        for (auto it = impl_->in.begin(); it != impl_->in.end();) it = it->first ? std::next(it) : impl_->in.erase(it);
        if (impl_->working && !impl_->working_first) impl_->closing = true;
        impl_->idle.wait_for(lock, std::chrono::seconds(3), [this] {
            if (impl_->working && !impl_->working_first) impl_->closing = true;
            else if (!impl_->in.empty()) impl_->closing = false;   // a /logout of its own: let it through
            return impl_->in.empty() && !impl_->working;
        });
        impl_->stop = true;
        impl_->closing = true;
    }
    impl_->cv.notify_all();
    impl_->worker.join();
    delete impl_;
}

std::uint32_t Net::send(Job job, bool first) {
    std::uint32_t t;
    {
        std::lock_guard<std::mutex> lock(impl_->m);
        t = impl_->next++;
        if (first) impl_->in.push_front({t, std::move(job), true});
        else impl_->in.push_back({t, std::move(job), false});
        ++impl_->busy;
    }
    impl_->cv.notify_one();
    return t;
}

void Net::drop_waiting() {
    std::lock_guard<std::mutex> lock(impl_->m);
    impl_->busy -= int(impl_->in.size());
    impl_->in.clear();
}

bool Net::take(std::uint32_t* ticket, Reply* out) {
    std::lock_guard<std::mutex> lock(impl_->m);
    if (impl_->out.empty()) return false;
    *ticket = impl_->out.front().first;
    *out = std::move(impl_->out.front().second);
    impl_->out.pop_front();
    --impl_->busy;
    return true;
}

int Net::outstanding() const {
    std::lock_guard<std::mutex> lock(impl_->m);
    return impl_->busy;
}

bool Net::has_cookie() const { return plausible(read_jar(impl_->jar, impl_->origin)); }

void Net::forget_cookie() {
    std::error_code ec;
    std::filesystem::remove(impl_->jar, ec);
}

}  // namespace catio::net
