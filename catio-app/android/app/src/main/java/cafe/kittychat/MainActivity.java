// DRAFT: never built. See docs/mobile-app.md.
package cafe.kittychat;

import org.libsdl.app.SDLActivity;

/** SDL runs the whole app; this only names the libraries to load, the native one last. */
public class MainActivity extends SDLActivity {
    @Override
    protected String[] getLibraries() {
        return new String[] { "SDL3", "SDL3_image", "SDL3_ttf", "catio_app" };
    }
}
