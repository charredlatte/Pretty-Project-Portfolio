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
// DRAFT: declarations only. Nothing here is implemented yet.

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

/// The routes, one method each. Writes carry `X-Catio: 1` and no Origin, which is what fromCafe() in
/// harness/gateway/src/cafe.js checks; a native client sends no Origin, so it passes.
///
/// Not thread-safe: one Gateway lives on Net's worker thread.
class Gateway {
public:
    /// `origin` is "https://catio-gateway.<her subdomain>.workers.dev". The cookie jar holds
    /// __Host-catio (Secure, HttpOnly, SameSite=Strict, 30 days) and is the app's whole credential.
    Gateway(std::string origin, std::filesystem::path cookie_jar);
    ~Gateway();

    /// POST /login, form-encoded `user` and `password`. 303 and the cookie on success; 401 wrong,
    /// 429 locked out (five wrong tries in fifteen minutes), 503 no account yet.
    Reply login(std::string_view user, std::string_view password);
    bool signed_in() const;
    /// Forget the cookie. The file is deleted, not merely emptied.
    void sign_out();

    /// GET /api/db → {"docs": {"<collection>/<id>": {…}}}.
    ///
    /// This is NOT the whole house: House::docs() returns only the `docs` table
    /// (harness/gateway/src/house.js:488). The cats live in the `agents` table and arrive through
    /// tool("list_agents"); notes and dropped files likewise, through "comments" and "inbox".
    Reply docs();

    /// PUT / PATCH / DELETE /api/db/<collection>/<id>, body {"data": {…}}, at most 1 MB.
    /// `doc` is "<collection>/<id>" — an even number of segments, or the gateway refuses it.
    Reply put(std::string_view doc, std::string_view json);
    Reply patch(std::string_view doc, std::string_view json);
    Reply erase(std::string_view doc);

    /// POST /api/tools/<name> with the arguments object, run as `owner`. All fourteen tools are here,
    /// a superset of /mcp. `inbox` with mark:true is destructive — pass it only when really delivering.
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

    std::uint32_t send(Job job);
    /// False when nothing has come back this frame.
    bool take(std::uint32_t* ticket, Reply* out);
    /// How many jobs are still out — the app shows a quiet spinner above zero.
    int outstanding() const;

private:
    struct Impl;
    Impl* impl_;
};

}  // namespace catio::net

#endif  // CATIO_NET_H
