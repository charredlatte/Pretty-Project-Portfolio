// net.h — every byte to and from the gateway, and nothing else.
//
// The app is the owner of one café, over HTTPS, to the gateway alone (harness/gateway/). It cannot take
// the OAuth path that claude.ai takes: the Worker's client registration refuses any redirect URI outside
// claude.ai and claude.com (harness/gateway/src/index.js), so a native client signs in with her password
// and carries the cookie, exactly as the café page on the gateway's own address does.
//
// This header names no libcurl type, no SDL type and no JSON type, on purpose. Bodies are strings, so a
// test can drive the layer above from a recorded reply, and so the implementation can be libcurl on a
// desktop and the platform's own HTTP on a phone (see docs/mobile-app.md, "HTTPS on a phone").
//
// Implemented for a desktop in src/net_curl.cpp, over libcurl, and tested against a stand-in gateway
// (test/test_net.py), never hers. The phones' bodies -- net_android.cpp, net_apple.cpp -- are still to come.

#ifndef CATIO_NET_H
#define CATIO_NET_H

#include <cstdint>
#include <filesystem>
#include <functional>
#include <string>
#include <string_view>

namespace catio::net {

/// The gateway's error envelope: every failure answers {code, error} with Cache-Control: no-store.
struct Err {
    std::string code;        ///< "signed_out", "forbidden", "not_found", "tool_error", "unavailable"…
    std::string message;     ///< the `error` field, already fit to show her
};

/// One reply. `body` is the raw bytes: art is a PNG here just as a document read is JSON.
struct Reply {
    long status = 0;
    std::string body;
    Err err;
    bool ok() const;
};

/// 401 {code:"signed_out"} — the cookie has run out (30 days) or been revoked. Sign in again.
bool signed_out(const Reply&);

/// An origin as the jar, the requests and the sign-in screen all write it: no spaces round it, no slash after it.
inline std::string bare(std::string origin) {
    while (!origin.empty() && (origin.back() == '/' || origin.back() == ' ')) origin.pop_back();
    const size_t start = origin.find_first_not_of(' ');
    return start == std::string::npos ? std::string{} : origin.substr(start);
}

/// Plain http only to this machine (the tests' stand-in): anywhere else her password and cookie would cross
/// the network in the clear. The host is read as a URL reads it -- after any user@, up to the port or the
/// path -- so "http://localhost:x@far.example" is far.example, and refused.
inline bool safe_origin(const std::string& origin) {
    if (origin.rfind("https://", 0) == 0) return true;
    if (origin.rfind("http://", 0) != 0) return false;
    const std::string rest = origin.substr(7);
    const std::string authority = rest.substr(0, rest.find_first_of("/?#"));
    if (authority.find('@') != std::string::npos) return false;
    std::string host = authority;
    if (host.rfind("[::1]", 0) == 0) host = "[::1]";
    else host = host.substr(0, host.find(':'));
    return host == "127.0.0.1" || host == "localhost" || host == "[::1]";
}

/// The routes, one method each. Writes carry `X-Catio: 1` and no Origin, which is what fromCafe() in
/// harness/gateway/src/cafe.js checks; a native client sends no Origin, so it passes.
///
/// Not thread-safe: one Gateway lives on Net's worker thread.
class Gateway {
    friend class Net;

public:
    /// `origin` is "https://catio-gateway.<her subdomain>.workers.dev". The cookie jar holds
    /// __Host-catio (Secure, HttpOnly, SameSite=Strict, 30 days) and is the app's whole credential: a
    /// file of its own, readable by its owner alone, holding the cookie's value and nothing else. It is
    /// kept by hand rather than by libcurl's cookie engine, which (rightly) refuses a __Host- cookie
    /// over plain HTTP -- and the stand-in gateway the tests run is plain HTTP on the loopback. The file
    /// names the gateway it came from, and a cookie is only read back for that gateway.
    ///
    /// An origin that is not https:// is refused ("insecure") unless it is this machine's loopback.
    /// A redirect is an error ("redirected") on every route but /login: something stands in front of
    /// the gateway, and what it answers is not the café's.
    Gateway(std::string origin, std::filesystem::path cookie_jar);
    ~Gateway();

    /// POST /login, form-encoded `user` and `password`. 303 and the cookie on success; 401 wrong,
    /// 429 locked out, 503 no account yet -- its message then carries each of the gateway's warning
    /// lights that is a cross, which say which Cloudflare secret to fix.
    Reply login(std::string_view user, std::string_view password);
    bool signed_in() const;
    /// Sign out: POST /logout, asking the gateway to stop honouring the cookie now, then forget it. The file
    /// is deleted, not merely emptied, whatever the gateway answered. A reply of 401 signed_out forgets it
    /// too: the cookie has run out, and keeping it would only be refused again.
    void sign_out();

    /// GET /api/db → {"docs": {"<collection>/<id>": {…}}}.
    ///
    /// This is NOT the whole house: House::docs() returns only the `docs` table
    /// (harness/gateway/src/house.js:488). The cats live in the `agents` table and arrive through
    /// tool("list_agents"); notes and dropped files likewise, through "comments" and "inbox".
    Reply docs();

    /// PUT / PATCH / DELETE /api/db/<collection>/<id>, at most 1 MB. `json` is the document's data, an
    /// object; it is sent as the gateway wants it, {"data": json}. PATCH merges it into the document,
    /// and answers not_found when there is none. `doc` is "<collection>/<id>" — an even number of
    /// segments, or the gateway refuses it — and each segment is encoded on its own.
    Reply put(std::string_view doc, std::string_view json);
    Reply patch(std::string_view doc, std::string_view json);
    Reply erase(std::string_view doc);

    /// POST /api/tools/<name> with the arguments object, run as `owner`: every tool the gateway has, a
    /// superset of /mcp. `inbox` with mark:true is destructive — pass it only when really delivering.
    Reply tool(std::string_view name, std::string_view json);

    /// POST /api/files, raw body, X-Name URI-encoded → {id, url, sizeBytes, contentType}. 20 MB cap.
    Reply file(std::string_view name, std::string_view mime, std::string_view bytes);
    Reply unfile(std::string_view id);

    /// GET /art/<path> → the pack's bytes, cookie-gated. Served private, max-age=86400 with no ETag
    /// and no Last-Modified (harness/gateway/src/cafe.js), so there is nothing to revalidate against:
    /// the app fetches what its cache lacks and otherwise never asks again. See art.h.
    Reply art(std::string_view path);

private:
    struct Impl;
    Impl* impl_;
};

/// A unit of work for the net thread. It runs off the frame, so no frame ever waits on the network.
using Job = std::function<Reply(Gateway&)>;

/// One worker thread, one queue in, one queue out. `send` hands back a ticket; the frame loop drains
/// `take` once a frame and matches tickets to what it asked for.
class Net {
public:
    Net(std::string origin, std::filesystem::path cookie_jar);
    ~Net();

    /// `first` jumps the queue -- signing out goes before the art still waiting to be fetched -- and is
    /// still finished when the app closes, for up to three seconds; everything else is dropped then.
    std::uint32_t send(Job job, bool first = false);
    /// Drop every job not yet started (signing out: the art and reads queued for the account that left).
    void drop_waiting();
    /// False when nothing has come back this frame.
    bool take(std::uint32_t* ticket, Reply* out);
    /// How many jobs are still out — the app shows a quiet spinner above zero.
    int outstanding() const;
    /// Whether the jar holds a cookie, read at start: the app opens on the sign-in screen without one.
    bool has_cookie() const;
    /// Delete the cookie's file at once, on the caller's thread: signing out must not wait on the queue.
    void forget_cookie();

private:
    struct Impl;
    Impl* impl_;
};

}  // namespace catio::net

#endif  // CATIO_NET_H
