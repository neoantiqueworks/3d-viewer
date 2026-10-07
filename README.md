# 3D Viewer

A web-based 3D model viewer for phone browsers (iOS and Android). Models are
GLB files stored in Google Drive and fetched with the Drive API v3. Built
with three.js as static files only, hosted on GitHub Pages.

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
