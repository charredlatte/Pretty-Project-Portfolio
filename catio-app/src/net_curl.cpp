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
#include <condition_variable>
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

std::string read_jar(const std::filesystem::path& jar) {
    std::ifstream in(jar, std::ios::binary);
    std::string token;
    std::getline(in, token);
    while (!token.empty() && (token.back() == '\r' || token.back() == ' ')) token.pop_back();
    return token;
}

// the cookie's value is 64 hex characters; anything else is not one of the gateway's
bool plausible(std::string_view token) {
    if (token.empty() || token.size() > 256) return false;
    for (char c : token) if (!std::isalnum(static_cast<unsigned char>(c)) && c != '-' && c != '_') return false;
    return true;
}

size_t on_body(char* data, size_t size, size_t n, void* out) {
    static_cast<std::string*>(out)->append(data, size * n);
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

// The words between <p class="bad" role="alert"> and </p>, the sign-in page's own refusal.
std::string words_of(const std::string& html) {
    constexpr std::string_view open = "<p class=\"bad\" role=\"alert\">";
    const size_t a = html.find(open);
    if (a == std::string::npos) return {};
    const size_t b = html.find("</p>", a);
    std::string s = html.substr(a + open.size(), b == std::string::npos ? std::string::npos : b - a - open.size());
    for (auto [from, to] : {std::pair<std::string_view, std::string_view>{"&#39;", "'"}, {"&quot;", "\""}, {"&lt;", "<"}, {"&gt;", ">"}, {"&amp;", "&"}}) {
        for (size_t at = s.find(from); at != std::string::npos; at = s.find(from, at + to.size())) s.replace(at, from.size(), to);
    }
    return s;
}

std::string code_for(long status) {
    switch (status) {
        case 401: return "signed_out";
        case 403: return "forbidden";
        case 404: return "not_found";
        case 413: return "too_big";
        case 429: return "locked";
        case 503: return "no_account";
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

    void keep(const std::string& t) {
        token = t;
        std::error_code ec;
        std::filesystem::create_directories(jar.parent_path(), ec);
        // made empty and narrowed to its owner first, so the cookie is never in a file anyone else may read
        { std::ofstream touch(jar, std::ios::binary | std::ios::app); }
        std::filesystem::permissions(jar, std::filesystem::perms::owner_read | std::filesystem::perms::owner_write,
                                     std::filesystem::perm_options::replace, ec);
        std::ofstream out(jar, std::ios::binary | std::ios::trunc);
        out << t << "\n";
    }
    void forget() {
        token.clear();
        std::error_code ec;
        std::filesystem::remove(jar, ec);
    }

    std::string escape(std::string_view s) {
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
        curl_easy_reset(curl);
        const std::string url = origin + path;
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, method);
        curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 0L);   // /login's 303 is the answer, not somewhere to go
        curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 10L);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 60L);
        curl_easy_setopt(curl, CURLOPT_USERAGENT, "KittyChatCafe/0.1");
        curl_easy_setopt(curl, CURLOPT_PROTOCOLS_STR, "https,http");
        curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
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
        if (rc != CURLE_OK) {
            r.err = {"unreachable", curl_easy_strerror(rc)};
            return r;
        }
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &r.status);
        if (set_cookie) *set_cookie = cookie;
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
            if (r.err.code == "signed_out") forget();   // run out or revoked: it would only be refused again
        }
        return r;
    }
};

Gateway::Gateway(std::string origin, std::filesystem::path cookie_jar) : impl_(new Impl) {
    global_init();
    while (!origin.empty() && origin.back() == '/') origin.pop_back();
    impl_->origin = std::move(origin);
    impl_->jar = std::move(cookie_jar);
    if (const std::string t = read_jar(impl_->jar); plausible(t)) impl_->token = t;
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
        r.err.code = "wrong";   // the handle and password, not a cookie run out
    else if (r.ok())
        r.err = {"unexpected", "The gateway answered " + std::to_string(r.status) + " to signing in."};
    return r;
}

bool Gateway::signed_in() const { return !impl_->token.empty(); }
void Gateway::sign_out() { impl_->forget(); }

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
    std::mutex m;
    std::condition_variable cv;
    std::deque<std::pair<std::uint32_t, Job>> in;
    std::deque<std::pair<std::uint32_t, Reply>> out;
    std::uint32_t next = 1;
    int busy = 0;
    bool stop = false;
    std::thread worker;

    Impl(std::string origin, std::filesystem::path j) : gateway(std::move(origin), j), jar(std::move(j)) {
        worker = std::thread([this] { run(); });
    }
    void run() {
        for (;;) {
            std::pair<std::uint32_t, Job> job;
            {
                std::unique_lock<std::mutex> lock(m);
                cv.wait(lock, [this] { return stop || !in.empty(); });
                if (stop) return;
                job = std::move(in.front());
                in.pop_front();
            }
            Reply r = job.second(gateway);
            std::lock_guard<std::mutex> lock(m);
            out.emplace_back(job.first, std::move(r));
        }
    }
};

Net::Net(std::string origin, std::filesystem::path cookie_jar) : impl_(new Impl(std::move(origin), std::move(cookie_jar))) {}

Net::~Net() {
    {
        std::lock_guard<std::mutex> lock(impl_->m);
        impl_->stop = true;
    }
    impl_->cv.notify_all();
    impl_->worker.join();
    delete impl_;
}

std::uint32_t Net::send(Job job) {
    std::uint32_t t;
    {
        std::lock_guard<std::mutex> lock(impl_->m);
        t = impl_->next++;
        impl_->in.emplace_back(t, std::move(job));
        ++impl_->busy;
    }
    impl_->cv.notify_one();
    return t;
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

bool Net::has_cookie() const { return plausible(read_jar(impl_->jar)); }

}  // namespace catio::net
