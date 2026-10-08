# 3D Viewer

A web-based 3D model viewer for phone browsers (iOS and Android). Models are
GLB files stored in Google Drive and fetched with the Drive API v3. Built
with three.js as static files only, hosted on GitHub Pages.

| File | Purpose |
| --- | --- |
| `viewer.html` | The customer-facing viewer. The only viewer. |
| `link-builder.html` | Internal tool: paste a Drive link, get the viewer link (with the API key in it). |
| `drive-test.html` | Diagnostic page from Phase 1, kept for troubleshooting. |
| `record-test.html` | Diagnostic page: what MediaRecorder and the share sheet actually do on a given phone. Groundwork for Phase 3. |
| `version.json` | The current version string, nothing else. Every page checks it on startup and reloads once if it is behind. |
| `tests/harness.html` | Regression harness. Serve the repo root (`python -m http.server`) and open it: checks the versions agree, that no body markup renders stray text (a broken comment), and the edit screen layout at 320, 385 and 480 px. |

## Deploying: the self-update check

GitHub Pages sends `Cache-Control: max-age=600` and that header cannot be
changed. Samsung Internet holds pages longer still, and a tab that is already
open serves from memory cache indefinitely. This bit us twice: a deploy went out,
the origin was verifiably correct, and the phone kept showing the previous build.

So every page now checks for itself. On startup it fetches `version.json` with
`cache: 'no-store'` **and** a unique timestamp in the query string, because
either one alone has been seen to be ignored. If the served version differs from
the page's own, the page reloads once with `_v=<new version>` appended, keeping
every existing parameter.

**The loop guard is the `_v` parameter itself.** A reload happens only when `_v`
is absent or carries a *different* version from the one just fetched. That gives
three properties worth stating:

- each version causes at most one reload;
- a page still stale after its reload, because a cache will not let go, carries
  on rather than looping forever;
- a bookmarked link holding an old `_v` still updates, because `_v` is compared
  against the fetched version rather than merely tested for presence.

Anything unexpected means carrying on with the page as it is: a failed fetch, a
2 second timeout, an empty file. The check is started *before* the model request
but is deliberately not awaited, so the two run in parallel and it can never
delay the model. The only way it interrupts anything is by reloading.

With `debug=1` the viewer logs the page version, the served version and the
decision it made.

### When you change a version

`VIEWER_VERSION` must be bumped and `version.json` updated **in the same
commit**, along with the `PAGE_VERSION` constants in the two diagnostic pages.
Four places:

| File | Constant |
| --- | --- |
| `version.json` | the whole file |
| `viewer.html` | `VIEWER_VERSION` |
| `record-test.html` | `PAGE_VERSION` |
| `link-builder.html` | `PAGE_VERSION` |

A disagreement would either make every phone reload forever or never update at
all, so this is enforced by the harness rather than left to discipline: the core
regression fails if `version.json` and `VIEWER_VERSION` differ, and the
self-update harness additionally checks all three pages and asserts the shared
check block is byte-identical across them.

The three pages share one version string. That means a change to only
`record-test.html` still bumps the viewer, costing one unnecessary reload. That
is the price of a single `version.json`, and it is cheap.

If you ever need to force a specific build by hand, `_v` is a safe parameter to
set yourself: the viewer never reads it as a setting.

## Target browsers

iOS Safari, Android Chrome and **Samsung Internet**. Samsung Internet is not
optional: it is the default browser on Galaxy phones, it is the browser the
project is tested on, and its dark mode behaves differently from Chrome's in a
way that shapes the whole UI (see below).

## Phase 2: The viewer (`viewer.html`)

The customer taps a link and sees the model. There is nothing to fill in and
nothing to set up:

```
https://neoantiqueworks.github.io/3d-viewer/viewer.html?model=DRIVE_FILE_ID&k=API_KEY
```

### URL parameters

| Parameter | Values | Default | Meaning |
| --- | --- | --- | --- |
| `model` | Drive file ID | (required) | Which GLB to load. A full Drive share link is also accepted. |
| `k` | Google API key | (required) | The key for the Drive request. Missing means the friendly error. See "The API key" below. |
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
module script in `viewer.html`: both background colors, all
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

**No API key may exist in any file of this repository, ever.** The repository
is public; a key committed to it was found and suspended by Google. The
harness fails if any file it scans contains a string shaped like a Google API
key, and `tests/check-no-keys.py` scans every tracked file:

```
python tests/check-no-keys.py
```

The key travels in the link as the `k` parameter instead. The self-update
reload keeps every parameter, `k` included.

The key has an HTTP referrer restriction for `https://neoantiqueworks.github.io/*`,
so the Drive request must carry a referrer. `viewer.html` and `drive-test.html`
set `<meta name="referrer" content="strict-origin-when-cross-origin">` and pass
the same policy explicitly on the Drive `fetch`, which sends at least the origin
over https. Never use a policy that drops the referrer. The restriction means
real models cannot be loaded from `file://` or `localhost`; that is accepted.

The full key is never shown on screen or in the log. With `debug=1` every log
line is passed through a mask (first 4 and last 4 characters), which covers the
page URL in the diagnostics and Google's error bodies, which echo the key back.
The address bar still shows the link as opened; that is the browser's, not
the page's.

## Phase 2: Link builder (`link-builder.html`)

Internal tool. Paste a Drive share link or a bare file ID, pick the starting
material and background, and copy the finished viewer link. A parameter is
only added to the link when the choice differs from the viewer's own default,
so the common case stays short.

The background selector has three options. **Auto (follows material)** is the
default and adds no `bg` parameter, which is what lets each material's own
default background apply. Light and Dark force the starting background
instead.

The API key goes in step 1. It is stored in this browser's localStorage only,
never in the repository, shown masked (a password field), and **Forget**
removes it. The link on screen shows the key masked; **Copy** and **Open to
test** use the full link. The page makes no Drive request: it only parses a
string and builds a URL. `VIEWER_URL` at the top of its script is the only
thing to change if the GitHub Pages address ever changes.

## Fluent UI: tried and removed

An earlier build layered Fluent UI Web Components v3 on this page, loaded from
CDN with no bundler. It was removed, and the reasoning is worth keeping.

Once every control had to be painted into a canvas to survive Samsung Internet's
forced dark mode, Fluent stopped contributing anything visible. Its surfaces live
in shadow DOM styled by CSS tokens, which is exactly what gets rewritten, and a
page cannot paint into another element's shadow root. So the buttons became
`appearance="transparent"` shells wrapped around canvas, and `fluent-spinner` and
`fluent-text` had to be replaced by canvas painting for the same reason. What was
left was the interaction model: semantics, focus behaviour and the pressed
animation.

On the device the two builds were **indistinguishable**. Against that, Fluent
cost 86 KB gzipped (`web-components-all.min.js` 73,399 B plus `@fluentui/tokens`
12,566 B, about 20 percent on top of the 419 KB the page already fetches for
three.js), from a second CDN origin that the UI could not render without, and it
depended on a tokens package published only under a `1.0.0-alpha` tag. It also
blocked the page's own `touch-action` and tap-highlight rules from reaching the
controls.

What survived the removal is `CONFIG.ui.brandColor` (`#5b5fc7`), which tints every
icon button and the active rings, and the Fluent System Icon path data, which is
inlined and filled into canvas with `Path2D`. three.js is now the only CDN
dependency.

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

## Phase 3: the edit screen

Inside `viewer.html`, same page, no navigation. The **Edit** button at the bottom
centre of the main screen opens it.

### What it does

Edit freezes the current view as a still, gradient background included, and shows
it full screen with a drawing layer on top. Orbit is disabled while editing.

| Position | Control |
| --- | --- |
| Left column, bottom to top | Pen, Undo, Clear, pen colour |
| Bottom centre | Record voice |
| Bottom right | Share |
| Top right | Close |

Every control is canvas-painted like the main screen: a brand-coloured disc with
a white glyph. The pen colour button carries a ring in the current colour, and
tapping it reveals a row of six: red (default), blue, yellow, green, black,
white.

The pen sits at the bottom of the column, nearest the thumb, which is why the
column is `column-reverse` with the DOM in pen, undo, clear, colour order.

### Recording

While voice records, the drawing canvas records too, so the result is **one**
video containing the image, any strokes drawn meanwhile, and the voice.

The record button becomes a red stop disc with a visible `mm:ss` timer. Tapping
it ends the recording. Starting a new one replaces the previous. The maximum
length is `CONFIG.edit.maxRecordSeconds`, default 120 s, enforced with an
automatic stop.

Three details that matter:

- **The file is finalized on Stop, not on Share.** `navigator.share` has to be
  called synchronously inside the tap, and that cannot be done after awaiting a
  recorder stop. Building the File in `onstop` is what makes the share path work.
- **The recording is not taken at device pixel size.** A separate canvas is
  capped to `CONFIG.edit.recordLongSide` (default 1280) on its long side, with
  both dimensions forced even because H.264 encoders commonly require it, and the
  edit canvas is copied into it each frame. The shared still image is unaffected
  and keeps the full display resolution.
- **That per-frame copy also keeps the stream alive.** A canvas that is never
  drawn to can stop producing frames for `captureStream`, which a static
  annotated image would otherwise do.

Format chain, from `CONFIG.edit.videoTypes`: MP4 first, then the best video type
the browser supports. If none works, the record button shows a clear disabled
state (a greyed disc with a slashed microphone) and only the annotated image can
be shared. No separate audio file, no transcoding.

The microphone is requested on the first tap of the record button and never
before. If it is denied, the button goes to the same disabled state and drawing
and image sharing keep working.

### Sharing and closing

Share sends the video if a recording exists, otherwise the annotated image at
full display resolution. Every shared file gets a plain MIME type and a matching
extension, via `plainMimeType()` and `extensionForType()`.

After sharing, the edit screen **stays open and the recording is kept**, so it can
be sent more than once. Only **Close** discards the recording and the strokes;
re-entering Edit starts from a fresh capture of the current view.

### Strokes

Strokes are data, not pixels: each is a colour, a width and a list of points, and
every change redraws from the still and replays them. Undo is a pop, Clear empties
the list. Points are stored **normalised** to the canvas, so a rotation or resize
replays them in the right place.

### Debug output

With `debug=1`, the edit screen logs the chosen recorder type and the type the
recorder actually used, the recorded byte size and duration, the recording canvas
dimensions against the configured cap, the microphone outcome and track settings,
the stroke count when sharing an image, the shared file name, type and size, and
`navigator.userActivation.isActive` at the moment of each share call.

At startup the diagnostics also report `MediaRecorder`, `captureStream`,
`getUserMedia` and `canShare` availability, which of the configured video types
this browser supports, and the recording cap settings.

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

The project's key is restricted to HTTP referrers on
`https://neoantiqueworks.github.io/*`, so run this page from GitHub Pages; from
`file://` Google rejects the key. The page contains no key: type it in. The log
masks it, including inside Google's error bodies.

### Running the test

1. Open `drive-test.html` on GitHub Pages.
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
