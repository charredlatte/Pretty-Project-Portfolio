// voice.h — the queen's voice.
//
// In the page this is one call: speak() wraps the browser's speechSynthesis, an en-GB voice unless she
// picks another, and speakTurn() says each complete sentence as her answer streams in. One function,
// deliberately, so a paid voice could be a second branch.
//
// Natively there is no such thing to wrap. It is three backends and a platform bridge:
//   Android   android.speech.tts.TextToSpeech, over JNI, and an audio-focus request
//   Apple     AVSpeechSynthesizer
//   desktop   nothing worth shipping; the null backend
//
// SO v1 SHIPS SILENT. Her card is perfectly readable without it, nothing else in the app needs any of
// it, and a draft branch should not carry a JNI bridge nobody has run. The interface is declared here
// so the shape is agreed and the card can be built with the switch already in it; the backends come
// behind -DCATIO_TTS=ON when the rest works.
//
// DRAFT: declarations only, and not in v1 at all. Nothing here is implemented yet.

#ifndef CATIO_VOICE_H
#define CATIO_VOICE_H

#include <string>
#include <string_view>
#include <vector>

namespace catio::voice {

/// queens/house.voice: {on, name, rate, pitch, lang}. The page's default is an en-GB voice.
struct Settings {
    bool on = false;
    std::string name;
    std::string lang = "en-GB";
    float rate = 1.0f;
    float pitch = 1.0f;
};

struct Available { std::string name, lang; };

/// True when this build has a backend at all. False on a desktop build, and in v1 everywhere.
bool present();
std::vector<Available> voices();

/// Say a whole utterance. False when there is no backend, which is not an error: the card simply shows
/// her words without saying them.
bool say(std::string_view text, const Settings& s);

/// Her answer arrives a token at a time. This holds the tail and says only complete new sentences, so
/// she is never heard reading half a word — what speakTurn() does in the page.
class Turn {
public:
    Turn();
    ~Turn();
    void begin(const Settings& s);
    /// Feed the turn as it streams; whole sentences are spoken as they complete.
    void grow(std::string_view so_far);
    void end();
    /// Stop is `manage {cat: "queen", action: "pause"}` on the gateway; this only silences the voice.
    void hush();

private:
    struct Impl;
    Impl* impl_;
};

}  // namespace catio::voice

#endif  // CATIO_VOICE_H
