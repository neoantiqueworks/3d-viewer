# 3D Viewer

A web-based 3D model viewer for phone browsers (iOS and Android). Models are
GLB files stored in Google Drive and fetched with the Drive API v3. Built
with three.js as static files only, hosted on GitHub Pages.

| File | Purpose |
| --- | --- |
| `viewer.html` | The customer-facing viewer. This is the page you send out. |
| `link-builder.html` | Internal tool: paste a Drive link, get the viewer link. |
| `drive-test.html` | Diagnostic page from Phase 1, kept for troubleshooting. |
| `record-test.html` | Diagnostic page: what MediaRecorder can actually produce on a given phone. Groundwork for Phase 3. |
| `viewer-fluent.html` | Design experiment: the same viewer with its UI rebuilt on Fluent UI Web Components. |

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

### Android Chrome auto dark theme

Android Chrome applies its own **Auto Dark Theme** to any page that does not
declare that it handles dark mode itself. The algorithm inverts lightness while
preserving hue, which turns the light beige background into a dark brown and
darkens the round button swatches. The WebGL canvas is generally exempt, so the
result is a page where the CSS-painted parts and the canvas disagree.

The fix is to declare support for both schemes, which this page does twice, in
the `<meta name="color-scheme">` tag and in `color-scheme` on `:root`. Do not
remove either.

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

## Design experiment: Fluent UI variant (`viewer-fluent.html`)

The same viewer with its UI layer rebuilt on
[Fluent UI Web Components](https://github.com/microsoft/fluentui) v3, for
comparison against the hand-rolled UI. It is generated from `viewer.html`
rather than hand-copied, so the CONFIG block, DEBUG and `debug=1`, the URL
parameters, the gradient backgrounds, the per-material default background, the
patina shader, the Drive fetch, share and close are byte-identical between the
two files. Only the UI layer differs.

### Loading without a bundler

The package README documents a single pre-bundled module script from CDN. This
page pins exact versions:

| Module | Purpose |
| --- | --- |
| `@fluentui/web-components@3.1.3/dist/web-components-all.min.js` | Registers every component and exports `setTheme`. |
| `@fluentui/tokens@1.0.0-alpha.24/+esm` | Supplies `webLightTheme` and `webDarkTheme`. |

Both were checked to be self-contained, with no bare import specifiers, so a
browser can load them directly with no import map and no build step.

Theming is required by the library, not optional: the components are styled
entirely through CSS variables that `setTheme` writes. The page calls it from
`applyFluentTheme()`, which `applyBackground()` invokes, so the Fluent theme
follows the active background.

### Components used

- `fluent-button` for every icon button: close, share, edit, light, dark, retry
  and "Open again".
- `fluent-spinner` for loading.
- `fluent-text` for the error and end screen messages.
- Fluent System Icons (from `@fluentui/svg-icons`, MIT) for dismiss, share,
  edit, weather-sunny and weather-moon. The path data is inlined, so the page
  costs no extra requests and does not depend on the icon CDN.

The three material swatches stay custom, because the control *is* a color
circle, but they take their size from the same `--swatch` token as the Fluent
buttons and draw their selected and focus states from Fluent tokens
(`--colorCompoundBrandStroke`, `--colorStrokeFocus2`) so they match.

### Download cost

Measured, not estimated:

| Module | Raw | Gzip |
| --- | --- | --- |
| `web-components-all.min.js` | 308,613 B | 73,399 B |
| `@fluentui/tokens` | 78,456 B | 12,566 B |
| **Fluent total** | **387,069 B** | **85,965 B** |
| three.js (`three.module.js` + `three.core.js`), for scale | 2,120,885 B | 419,512 B |

So Fluent adds about **86 KB gzipped**, roughly a 20 percent increase over what
the page already downloads for three.js, from a second CDN origin.

### Known risks on phones

Everything below is reasoned from the package contents, not observed on a
device, because this environment has no browser:

- **Button sizing.** This page needs `clamp()` sized buttons so the bars cannot
  overlap at 320 px. Fluent sizes its own buttons internally, so the host is
  sized here and `::part(control)` is stretched to fill it. If that part name
  is not exposed, the buttons keep the right footprint but their internal
  control may not fill it, leaving the tap target visually smaller.
- **Flash of unstyled controls.** Until the module registers the elements they
  are unknown, meaning `display: inline` and unstyled. They are hidden until
  `:defined` matches, so on a slow phone connection the buttons appear a moment
  after the model rather than appearing wrong.
- **A second CDN is now a hard dependency for the UI.** If jsDelivr fails for
  the Fluent modules, the 3D view and every handler still work, but the
  controls stay invisible. `viewer.html` has no such dependency.
- **The theme package is alpha.** `@fluentui/tokens` is only published under a
  `1.0.0-alpha` tag, and it is the documented source of the themes.
- **Shadow DOM and the canvas.** The buttons live in shadow roots, so the
  `touch-action: manipulation` and `-webkit-tap-highlight-color` rules that
  `viewer.html` applies to its own buttons do not reach Fluent's internal
  control. Double-tap zoom and tap highlight behaviour on the controls may
  differ from the custom build on both iOS Safari and Android Chrome.

Both pages log which build they are in the `debug=1` diagnostics, and the
Fluent one additionally reports whether `fluent-button`, `fluent-spinner` and
`fluent-text` actually registered.

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
