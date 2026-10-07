# 3D Viewer

A web-based 3D model viewer for phone browsers (iOS and Android). Models are
GLB files stored in Google Drive and fetched with the Drive API v3. Built
with three.js as static files only, hosted on GitHub Pages.

| File | Purpose |
| --- | --- |
| `viewer.html` | The customer-facing viewer, built on Fluent UI Web Components. This is the page you send out, and where all future work goes. |
| `viewer-classic.html` | The earlier hand-rolled UI, kept for comparison and as a fallback. Same behaviour. |
| `link-builder.html` | Internal tool: paste a Drive link, get the viewer link. |
| `drive-test.html` | Diagnostic page from Phase 1, kept for troubleshooting. |
| `record-test.html` | Diagnostic page: what MediaRecorder and the share sheet actually do on a given phone. Groundwork for Phase 3. |

Both viewers are generated from one set of shared blocks, and a parity harness
asserts that fourteen behavioural regions are byte-identical between them, so
only the UI layer differs.

## Target browsers

iOS Safari, Android Chrome and **Samsung Internet**. Samsung Internet is not
optional: it is the default browser on Galaxy phones, it is the browser the
project is tested on, and its dark mode behaves differently from Chrome's in a
way that shapes the whole UI (see below).

## Phase 2: The viewer (`viewer.html`)

The customer taps a link and sees the model. There is nothing to fill in and
nothing to set up:

```
https://neoantiqueworks.github.io/3d-viewer/viewer.html?model=DRIVE_FILE_ID
```

### URL parameters

| Parameter | Values | Default | Meaning |
| --- | --- | --- | --- |
| `model` | Drive file ID | (required) | Which GLB to load. A full Drive share link is also accepted. |
| `mat` | `chrome`, `bronze`, `anthracite` | `chrome` | Material shown on arrival. |
| `bg` | `light`, `dark` | follows the material | Background shown on arrival. Overrides the material's own default, for the initial state only. |

Invalid values fall back to the default silently, because the customer cannot
do anything about a bad link. Use `link-builder.html` to build these links
instead of writing them by hand.

### Background follows the material

Each material declares the background it looks best against, as
`defaultBackground` next to that material in `CONFIG`:

| Material | Default background |
| --- | --- |
| Chrome | Dark |
| Aged bronze | Dark |
| Anthracite | Light |

Tapping a material button applies the material **and** switches to that
material's background. The customer can then override it with the two
background buttons, and that choice holds until the next material tap, which
applies the new material's default again.

On arrival the background follows the starting material, so a plain
`?model=...` link opens chrome on dark. A `bg` parameter overrides that for the
initial state only; from the first material tap onwards the material decides
again.

### The screen

Icon-only round buttons, no text, no navigation:

| Position | Button |
| --- | --- |
| Top left | Light background, dark background |
| Top right | Close |
| Bottom left | Chrome, aged bronze, anthracite |
| Bottom center | Edit (Phase 3, hidden for now) |
| Bottom right | Share |

One finger orbits, two fingers pinch to zoom and pan.

**Share** captures the current view as a JPEG, model and background only with
no buttons in the image, and opens the system share sheet through the Web
Share API, so it can go to WhatsApp or mail. If the browser cannot share
files, the image is downloaded instead.

**Close** tries `window.close()`. Browsers only allow that for windows a
script opened, so when it is refused the page turns into a plain end screen
with one "Open again" button.

### Materials

All three presets are applied to the whole model, replacing whatever the GLB
contained. The models are exported from 3ds Max as geometry only and may have
no UV coordinates at all, so **no material uses a texture map**:

- **Chrome** and **anthracite** are plain `MeshStandardMaterial` with color,
  metalness and roughness only. With no textures there is nothing to map.
- **Aged bronze** gets its variation from a shader injected into
  `MeshStandardMaterial` via `onBeforeCompile`. It evaluates a 3D value-noise
  field at the **world position** of each pixel, which is a solid texture: no
  projection, no seams and no UVs. Upward-facing surfaces rub brighter, and a
  fresnel term brightens silhouette edges, the way real bronze wears.
  three.js still does all the lighting and the reflections.

Reflections come from `RoomEnvironment`, which three.js builds procedurally
and bakes into a small cubemap once at startup. No HDRI file is downloaded, so
phones get metal reflections with no extra network traffic.

### Backgrounds

Each background is a subtle vertical gradient, slightly darker toward the
bottom, with both stops in `CONFIG.background`:

| Preset | Top | Bottom |
| --- | --- | --- |
| Light | `#eae2d5` | `#d7d0c4` |
| Dark | `#15161a` | `#0d0e11` |

The gradient is drawn **inside the WebGL canvas** as `scene.background`, not as
CSS behind the canvas. That is deliberate for two reasons:

- Share reads the canvas, so a CSS background would be missing from the shared
  image. Rendering it in the canvas means the screenshot matches the screen.
- three.js derives the background material's tone mapping from the texture
  color space, so tagging the gradient as sRGB bypasses ACES tone mapping and
  the configured hex values arrive on screen unshifted.

It is a backdrop only. Reflections and material response come from
`scene.environment`, which the background never touches, so switching the
background cannot change how a material looks. The overlay screens and the
browser UI tint follow the same two values through the `--bg-top` and
`--bg-bottom` CSS variables.

Every tunable value lives in the single `CONFIG` block at the top of the
module script in `viewer.html`: the API key, both background colors, all
material values, the share image format and the camera framing.

### Debug output

Two ways to switch it on:

- **`?debug=1` in the URL** turns the on-screen log panel on without editing
  anything. This is the one that matters in practice, because a phone has no
  reachable browser console.
- **`const DEBUG_ALWAYS_ON = false;`** at the top of the module script forces it
  on for every visit.

With both off, the page is silent and shows no technical detail at any time.
Tap the log panel to dismiss it. Everything also goes to the console.

With the panel on, the page prints a diagnostic block at startup: viewer
version, three.js revision, user agent, device pixel ratio, window and canvas
sizes, `ColorManagement.enabled`, `renderer.outputColorSpace`, the tone mapping
mode, **whether the background is tone mapped** (should be `false`), the active
material and background with both gradient colors, where the background choice
came from, the resolved CSS variables, whether the system prefers a dark color
scheme, and the GPU vendor/renderer strings.

`VIEWER_VERSION` near the top is printed in that block. Bump it when shipping,
so a stale cached page on a phone can be told apart from a current one.

### Forced dark mode, and why every control is painted on canvas

Measured on a Galaxy S25 Ultra running **Samsung Internet 30** (Chromium 143),
with the on-screen diagnostics: the WebGL background rendered the beige gradient
**correctly**, while the CSS-coloured controls did not. The light-background
button came out dark brown instead of `#eae2d5`, and the chrome material button
came out dark grey instead of light silver.

So the browser was rewriting **CSS colours** while leaving **canvas pixels**
alone. Samsung Internet's dark mode does this regardless of the
`color-scheme` declaration, which it ignores.

Three things were ruled out with evidence rather than assumption, before the
device data arrived:

- **Tone mapping on the background.** three.js sets the background material's
  `toneMapped` flag from the texture colour space
  (`WebGLBackground.js`: `toneMapped = getTransfer(colorSpace) !== SRGBTransfer`),
  and that expression was executed against r186 to confirm it yields `false` for
  an sRGB texture. The arithmetic rules it out independently: ACES on linear
  0.823 returns about 0.80, which encodes back to 232, essentially unchanged.
- **Shader precision.** The background fragment shader is a bare `texture2D`
  fetch with no arithmetic; precision cannot darken a colour that far.
- **A stale cached page.** The previous build's light colour was `#e8e8ea`, a
  light grey, so a stale page would have looked grey rather than brown.
  `VIEWER_VERSION` is printed in the diagnostics to settle this at a glance.

**The fix.** Canvas is the only surface proven immune on that device, so every
coloured control is now painted into its own canvas and nothing takes its colour
from CSS:

| Control | How it is drawn |
| --- | --- |
| Three material swatches | Canvas: the material colour, plus a ring in the brand colour when active. |
| Light and dark background buttons | Canvas: a brand-coloured disc with a Fluent sun or moon glyph, plus a light ring when active. |
| Close, share, edit, retry | Canvas: a brand-coloured disc with the Fluent glyph filled via `Path2D`. |
| Loading spinner and percentage | Canvas, animated with `requestAnimationFrame`. |
| Error card and end screen | Canvas: the background gradient, the wrapped message and the pill button, all painted. |

`color-scheme: only light` is declared in both the meta tag and on `:root` as a
guard for the browsers that do honour it, but it is not relied on.

Two consequences worth knowing:

- The message screens paint their text, so the real text stays in the DOM as a
  screen-reader-only element, which is also the string the painter reads. The
  pill button is a transparent real control positioned from the same geometry as
  the painted pill, so the artwork and the hit area cannot drift apart.
- Painted controls must be redrawn when state or viewport changes, because the
  button sizes are `clamp()`ed against viewport width. `repaintUi()` is called
  from `applyBackground`, `applyMaterial` and the resize handler.

The one colour still expressed in CSS is the keyboard focus ring, which is
cosmetic, and both a light outline and a dark shadow are drawn so one of them
always contrasts.

### Responsive button scaling

Each bar is a three-column grid, `1fr auto 1fr`, holding a start group, a
centered group and an end group. Overlap is therefore structurally impossible:
when the material group needs more room than its share, the column grows and
the center button shifts slightly rather than anything colliding.

Button sizes and gaps are `clamp()` expressions tied to viewport width, so they
scale from a 320 px phone up to 480 px and then stop. The bottom bar has at
least 67 px of free space at every width in that range, and the smallest touch
target stays at 38 px.

The earlier version positioned each cluster independently, which let the
centered button overlap the material buttons on a narrow phone.

### The API key

The key is a constant in `CONFIG` in `viewer.html`. Key secrecy is not a goal
for this project; restrict the key to the Google Drive API in Google Cloud
Console instead.

Because the key is committed, GitHub secret scanning will reject the first
push that contains it. The rejection message prints an unblock URL like
`https://github.com/neoantiqueworks/3d-viewer/security/secret-scanning/unblock-secret/<id>`.
Open it while signed in as the repository owner, choose to allow the secret,
then push again.

## Phase 2: Link builder (`link-builder.html`)

Internal tool. Paste a Drive share link or a bare file ID, pick the starting
material and background, and copy the finished viewer link. A parameter is
only added to the link when the choice differs from the viewer's own default,
so the common case stays short.

The background selector has three options. **Auto (follows material)** is the
default and adds no `bg` parameter, which is what lets each material's own
default background apply. Light and Dark force the starting background
instead.

This page makes no network requests and contains no API key: it only parses a
string and builds a URL. `VIEWER_URL` at the top of its script is the only
thing to change if the GitHub Pages address ever changes.

## The Fluent UI layer

`viewer.html` is built on [Fluent UI Web Components](https://github.com/microsoft/fluentui)
v3. `viewer-classic.html` keeps the earlier hand-rolled UI with identical
behaviour, for comparison and as a fallback.

### Loading without a bundler

The package README documents a single pre-bundled module script from CDN. Exact
versions are pinned:

| Module | Purpose |
| --- | --- |
| `@fluentui/web-components@3.1.3/dist/web-components-all.min.js` | Registers every component and exports `setTheme`. |
| `@fluentui/tokens@1.0.0-alpha.24/+esm` | Supplies `webLightTheme` and `webDarkTheme`. |

Both were checked to be self-contained, with no bare import specifiers, so a
browser loads them directly with no import map. Note that `setTheme` lives in the
main package but the themes do **not**, and that the tokens package is still
published only under an alpha tag.

Theming is required rather than optional: the components are styled entirely
through CSS variables that `setTheme` writes. `applyFluentTheme()` is called from
`applyBackground()`, so the theme follows the active background, and it is
wrapped in `try`/`catch` because a CDN failure must not take the 3D view down.

### Brand colour

`CONFIG.ui.brandColor`, default `#5b5fc7`, is the single source. It tints every
icon button and the active ring on the material swatches, and after each
`setTheme` call `applyBrandTokens()` overwrites the Fluent brand tokens with it,
so the light and dark themes share one brand. The hover and pressed shades are
derived from it, so changing the one value moves everything.

Those tokens are written to `document.body`, which is the element `setTheme`
targets by default; a value set higher up would lose to it.

White glyphs on `#5b5fc7` measure **5.38:1**, comfortably past the 3:1 a glyph
needs, and the ratio does not change between themes because the disc colour is
fixed. The selected background button uses a light ring instead of a brand ring,
since a brand ring on a brand disc would be invisible.

### What Fluent actually provides here

This is worth being precise about, because the forced-dark work changed it.
Fluent's own surfaces live in shadow DOM styled by CSS tokens, which is exactly
what Samsung Internet rewrites, and shadow DOM cannot be painted into from the
page. So the buttons use `appearance="transparent"` and the visible disc is the
canvas slotted inside them.

What Fluent contributes is therefore the interaction model rather than the
fill: component semantics, keyboard and focus behaviour, and the pressed
animation. `fluent-spinner` and `fluent-text` were dropped for the same reason
and replaced by canvas painting.

If you would rather have Fluent's own spinner and text visuals and accept that a
forced dark mode will recolour them, that is a one-line change back.

### Download cost

Measured, not estimated:

| Module | Raw | Gzip |
| --- | --- | --- |
| `web-components-all.min.js` | 308,613 B | 73,399 B |
| `@fluentui/tokens` | 78,456 B | 12,566 B |
| **Fluent total** | **387,069 B** | **85,965 B** |
| three.js (`three.module.js` + `three.core.js`), for scale | 2,120,885 B | 419,512 B |

About **86 KB gzipped**, roughly a 20 percent increase over what the page already
downloads, from a second CDN origin. `viewer-classic.html` has no such
dependency, which is part of why it is kept.

### Remaining risks on phones

- **Shadow DOM blocks the page's touch CSS.** `touch-action: manipulation` and
  `-webkit-tap-highlight-color` do not reach Fluent's internal control, so
  double-tap zoom and tap highlight on the buttons may differ from
  `viewer-classic.html`.
- **The UI depends on a second CDN.** If jsDelivr fails for the Fluent modules
  the 3D view and every handler still work, but the controls stay invisible.
- **Button sizing** relies on `::part(control)` being exposed to stretch the
  internal control to the host size.

The `debug=1` diagnostics report which build is running, the brand colour, and
whether `fluent-button` actually registered.

## Phase 3 groundwork: record capability test (`record-test.html`)

Diagnostic page, not a customer page. Phase 3 wants one video file containing a
still image, strokes drawn on it and a voice recording, playable in WhatsApp on
both iOS Safari and Android Chrome. Whether that is possible at all depends on
what `MediaRecorder` will actually produce on each phone, which cannot be
determined from a desktop or from documentation.

The page reports, all on screen:

1. Whether `MediaRecorder`, `canvas.captureStream`, `getUserMedia`,
   `navigator.share` and `navigator.canShare` exist, and whether the context is
   secure.
2. Every `MediaRecorder.isTypeSupported()` result for 16 video and 7 audio
   candidate types, best first.
3. What a real 5 second canvas-plus-microphone recording produces, including
   **the mimeType the recorder actually chose**, which is often not the one
   requested, plus the byte size and bitrate.
4. Whether the browser can play back the file it just recorded.
5. Whether the system share sheet accepts it.

The canvas is animated while recording, with a moving dot, a stroke that grows
and an on-canvas timer. That is partly because a canvas which is never drawn to
can stop emitting frames, and partly so playback proves real frames were
captured rather than one frozen one.

Run it over **https**, not the local LAN address: `getUserMedia` and
`navigator.share` both require a secure context.

### Share isolation, and the plain MIME rule

Measured on Samsung Internet 30 (Chromium 143): recording works and produces
`video/mp4` with H.264 and AAC, 5 seconds is about 208 KB, playback reports
320x320, and `navigator.canShare({files:[video]})` returns `true`. Then
`navigator.share` is refused about 13 ms after the tap with
`NotAllowedError: Permission denied`.

The Web Share specification permits `NotAllowedError` for only two reasons: a
permissions policy denial, or missing transient activation. A rejected file type
should surface as `TypeError`. So the spec alone does not explain this.

Chromium does. From
`third_party/blink/renderer/modules/webshare/navigator_share.cc`, the message
text identifies which code path produced the error:

| Message | Cause |
| --- | --- |
| `Must be handling a user gesture to perform a share request.` | Activation missing or already consumed |
| `An earlier share has not yet completed.` | A previous share is still open |
| `Permission denied`, thrown synchronously with a console warning | Renderer-side size or filename check |
| `Permission denied`, arriving asynchronously | The **browser process** returned `ShareError::PERMISSION_DENIED` |

The observed error is the last one, and the ~13 ms delay fits a mojo round trip.
That is where the browser-side file allowlist lives, and crucially
`navigator.canShare` only runs the **renderer-side** checks. So `canShare`
passing and `share` then failing is exactly the shape of a browser-side file
type rejection, and such allowlists are keyed on **plain** MIME types.

`record-test.html` therefore offers five share buttons, each calling
`navigator.share` directly inside its own tap with no `await` beforehand, so
activation cannot be what differs between them:

| Button | Isolates |
| --- | --- |
| a) video, plain `video/mp4` | The hypothesis |
| b) video, original type with codec parameters | Current behaviour |
| c) PNG snapshot | Whether simple file types work |
| d) text only, no file | Whether Web Share works at all |
| e) a `text/plain` file | Whether files are refused as a class |

Each logs the exact File name, type and size, the `canShare` result,
`navigator.userActivation.isActive` immediately before the call, and the full
error name and message mapped back to the Chromium path above.

Reading the result: if (d) works and every file fails, the browser refuses files
as a class. If (c) and (e) work and (a) works while (b) fails, the MIME
parameters were the cause.

**The plain MIME rule is already applied in both viewers.** `plainMimeType()`
strips parameters, and `shareFile()` normalises the type at the share boundary,
which is the single door every shared file goes through, including Phase 3's
recorded video.

## Phase 1: Drive fetch test (`drive-test.html`)

A test page that shows a GLB from Google Drive can be downloaded in
the browser and displayed. It has fields for an API key and a Drive file ID,
a Load button, a 3D view with orbit controls, and an on-screen status log.

The page is a single file and works both when opened directly from disk
(`file://`) and when served from GitHub Pages. three.js 0.186.1 is loaded
from jsDelivr, so an internet connection is required.

### One-time setup

1. Google Cloud Console: select or create a project, then open
   APIs & Services > Library and enable **Google Drive API**.
2. APIs & Services > Credentials > Create credentials > **API key**. Copy it.
3. Google Drive: right-click the GLB > Share > General access:
   **Anyone with the link**. Copy the link (or just the file ID).

Optional: the key can be restricted to the Drive API and/or to HTTP referrers
under Credentials; a referrer restriction blocks `file://` use.

### Running the test

1. Open `drive-test.html` (double-click it, or serve it on GitHub Pages).
2. Paste the API key and the file ID or the full share link.
3. Press **Load** (or Enter).

The key is remembered in this browser (localStorage) while
"Remember key in this browser" is checked. **Forget** removes it.
A `?model=FILE_ID` URL parameter pre-fills the file ID field.

### Reading the status log

| Log shows | Meaning |
| --- | --- |
| `HTTP 200` then `Format check: GLB` and `Parse result` | Everything works. |
| `HTTP 400` + `API_KEY_INVALID` | Key is wrong or incomplete. |
| `HTTP 403` + `SERVICE_DISABLED` / `accessNotConfigured` | Drive API is not enabled in the key's project. |
| `HTTP 403` other | File not shared publicly, or download is restricted. |
| `HTTP 404` | Wrong file ID, or the file is not shared as "Anyone with the link". |
| `Request failed: TypeError` | Network or CORS failure; the browser console (F12) shows the reason. |
| `Format check failed` | The response is not a GLB (the first bytes are printed). |

Note: Drive may send the file compressed, so `Content-Length` can be smaller
than `Bytes received`. That is normal.

### Debug output

Set `const DEBUG = true;` at the top of the module script in
`drive-test.html` to mirror the log to the browser console and show error
stacks. With `false`, nothing is written to the console.
