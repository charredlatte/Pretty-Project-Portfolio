// catio_net_check -- every route of net.h, called in turn, one JSON line out per call. test/test_net.py runs
// it against a stand-in gateway on the loopback and checks both sides. Never point it at her gateway.
//
//   catio_net_check <origin> <cookie jar> <step>...
//
// Steps: login:<user>:<password>  docs  put:<doc>:<json>  patch:<doc>:<json>  erase:<doc>  tool:<name>:<json>
// file:<name>:<mime>:<text>  unfile:<id>  art:<path>  signed_in  sign_out  net:docs (through Net's worker thread)

#include <chrono>
#include <cstdio>
#include <string>
#include <thread>

#include <nlohmann/json.hpp>

#include "catio/net.h"

namespace {

std::string field(const std::string& step, int n) {   // the n-th ':'-separated part; the last takes the rest
    size_t at = 0;
    for (int i = 0; i < n; ++i) {
        at = step.find(':', at);
        if (at == std::string::npos) return "";
        ++at;
    }
    return step.substr(at);
}
std::string part(const std::string& step, int n) {
    const std::string rest = field(step, n);
    return rest.substr(0, rest.find(':'));
}

void say(const std::string& step, const catio::net::Reply& r, bool in = false) {
    nlohmann::json j{{"step", step}, {"status", r.status}, {"ok", r.ok()}, {"code", r.err.code}, {"message", r.err.message},
                     {"size", r.body.size()}, {"body", r.body}};
    if (in) j["signed_in"] = true;
    std::printf("%s\n", j.dump(-1, ' ', false, nlohmann::json::error_handler_t::replace).c_str());
    std::fflush(stdout);
}

}  // namespace

int main(int argc, char** argv) {
    using namespace catio::net;
    if (argc < 3) {
        std::fprintf(stderr, "catio_net_check <origin> <cookie jar> <step>...\n");
        return 2;
    }
    Gateway g(argv[1], argv[2]);
    for (int i = 3; i < argc; ++i) {
        const std::string step = argv[i], verb = step.substr(0, step.find(':'));
        if (verb == "login") say(step, g.login(part(step, 1), field(step, 2)));
        else if (verb == "docs") say(step, g.docs());
        else if (verb == "put") say(step, g.put(part(step, 1), field(step, 2)));
        else if (verb == "patch") say(step, g.patch(part(step, 1), field(step, 2)));
        else if (verb == "erase") say(step, g.erase(field(step, 1)));
        else if (verb == "tool") say(step, g.tool(part(step, 1), field(step, 2)));
        else if (verb == "file") say(step, g.file(part(step, 1), part(step, 2), field(step, 3)));
        else if (verb == "unfile") say(step, g.unfile(field(step, 1)));
        else if (verb == "art") say(step, g.art(field(step, 1)));
        else if (verb == "signed_in") std::printf("{\"step\": \"signed_in\", \"value\": %s}\n", g.signed_in() ? "true" : "false");
        else if (verb == "sign_out") { g.sign_out(); std::printf("{\"step\": \"sign_out\"}\n"); }
        else if (verb == "net") {
            Net n(argv[1], argv[2]);
            const auto ticket = n.send([](Gateway& w) { return w.docs(); });
            std::uint32_t t = 0;
            Reply r;
            for (int k = 0; k < 2000 && !n.take(&t, &r); ++k) std::this_thread::sleep_for(std::chrono::milliseconds(5));
            say(t == ticket ? step : step + ":lost", r);
        } else {
            std::fprintf(stderr, "catio_net_check: what step is %s?\n", step.c_str());
            return 2;
        }
        std::fflush(stdout);
    }
    return 0;
}
