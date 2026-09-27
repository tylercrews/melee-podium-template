# melee-podium-template

## Local development

Run the Flask API and Vite frontend in separate PowerShell terminals. All commands below start from the repository root.

### One-time setup

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
cd .\frontend
npm ci
cd ..
```

If you need bracket imports or Firebase features, copy `.env.example` to `.env` and replace only the relevant placeholders with your local credentials. Do not commit `.env` or service-account JSON files.

### Start the backend

In the first terminal:

```powershell
.\.venv\Scripts\python.exe -m flask --app app run --debug --port 5000
```

The API will be available at `http://127.0.0.1:5000`.

### Start the frontend

In the second terminal:

```powershell
cd .\frontend
npm run dev
```

Open `http://127.0.0.1:5173/melee-podium-template/`. Vite proxies API and character-asset requests to the Flask server on port 5000.

### Local checks

Run the Python test suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s .\test -p "*_test.py"
```

Type-check and build the frontend:

```powershell
cd .\frontend
npm run build
```

## Thanks To

- [Malarki_](https://x.com/Malarki_), who I commissioned to expand the pool of character poses and did an amazing job.
- [Top8er](https://www.top8er.com/), an amazing site that my local scene was using all the time, only inspired me to create this podium template because there wasn't an option for doubles. Huge thanks for being [open source](https://github.com/ShonTitor/Top8er) (shouts out to ShonTitor, agiera, and jmlee337); it was a huge help for figuring out the start.gg and Challonge bracket importing.
- AeonSSB, Cjag01, radzo73, and caha1an, who created the [Melee-CSProject](https://github.com/AeonSSB/Melee-CSProject) that I got the original poses from.
- [CeLL on this old Smashboards thread](https://smashboards.com/threads/character-stock-icon-dump.390494/) for posting a dump of all the character stock icons.
- [Mr. C](https://www.spriters-resource.com/gamecube/ssbm/asset/46039/) for the Sheik stock icons.
- Also shoutout to [SmashBoards](https://smashboards.com/) in general - what an amazing site still.
- North Carolina Melee!! Love y'all.


## Current roadmap

The six-step Podium workflow is implemented. The remaining known product and
architecture work is:

- Finish and review the Eyes and Squares layout preferences and renderers; both
  modes remain deliberately disabled in the UI.
- Move favorite entrants from browser-local storage to the authenticated
  Firestore `entrants` collection so they follow a user between devices.
- Stress-test browser memory limits before enabling guest logo and background
  uploads.
- Replace the compatibility preview renderer with the strict creation pipeline
  once all active Podium preference files are reviewed and marked ready.
- Add live Tonamel fetching if Tonamel becomes a supported UI provider; only
  response normalization exists today.
- Continue decomposing `DrawPodium.py` as legacy rendering behavior is moved
  into focused renderer modules.

## Repository layout

- `bracket_import/` contains bracket URL recognition, provider clients, USB
  Reporting decoding, and provider-neutral normalization.
- `firebase_services/` owns authenticated Firestore and Cloud Storage access.
- `frontend/` contains the React/Vite application.
- `preferences/` contains versionable mode and layout data.
- `backgrounds/`, `char_assets/`, `fonts/`, and `formatting_assets/` contain
  renderer assets.
- `test/` contains focused unit tests, generation helpers, and reviewed visual
  outputs.

## Bracket importing

The UI imports public Start.gg, Challonge, and parry.gg URLs. Their credentials
stay on the Flask server: Start.gg uses `START_GG_TOKEN`, Challonge uses
`CHALLONGE_API_KEY`, and parry.gg uses `PARRY_GG_API_KEY`. The
`bracket_import/` package normalizes all three providers into the same internal
result format before the frontend fills the tournament and placement fields.

The module also recognizes Tonamel URLs and can normalize a supplied Tonamel
response, but the live route does not yet fetch from that provider. A parry.gg
tournament page works when it contains a single Melee event; for tournaments
with multiple Melee events, paste the event standings or bracket URL so the
importer can select the intended event.

### Provider data limitations

Start.gg provides a broad import: tournament and event names, time,
location, entrant count, placements, seeds, participant tags, linked X handles,
and reported game-character selections. Start.gg also reports entrant size, so
an entrant size of two can be imported automatically as doubles. The entrant
display name becomes the team name and its two participant tags become the team
members.

parry.gg provides the richest character import when individual games were
reported: the importer reads each team member's selections and maps its reported
Melee color variant to the renderer. Brackets without game reports still import
their results and leave characters for review. Start.gg imports costume colors
when a set was submitted with Replay Reporter's optional
[USB Reporting format](https://github.com/jmlee337/replay-manager-for-slippi/blob/main/src/docs/color.md).
That format stores a Slippi costume index in the hundreds portion of each
entrant's per-game stock count. Ordinary scores remain uncolored for review,
and out-of-range stock-glitch indices are ignored.

Challonge supplies bracket entrant names and seeds, but it does not reliably
tell us whether those names represent singles players or doubles teams, and it
does not supply the two player identities, Melee characters, or costumes for a
doubles team. After a Challonge request succeeds, the UI explicitly asks whether
the bracket is singles or doubles. In doubles mode the Challonge entrant name is
placed in the **Team name** field, while the two member fields are left for the
user to complete.

### Challonge placements and incomplete brackets

Challonge normally provides `final_rank`, and those ranks are used directly.
However, a bracket can have every match completed while Challonge still reports
its state as `awaiting_review`; during that state every participant's
`final_rank` may be `null`, and the participant list may still be in seed order.
To avoid mistaking seeds for placements, the Challonge request also includes
match results. For single- and double-elimination brackets, the importer derives
provisional ranks from completed losses only when the match graph proves that
all participants except one have been eliminated. It preserves tied placements
for players eliminated in the same round.

If a bracket is genuinely incomplete, has unresolved matches, has more than one
possible survivor, or uses a tournament type whose elimination rules are not
implemented, the importer does not invent final placements. Missing placements
remain `null` in the normalized result. Because the podium form itself is
positional, provider-order entrants may still fill its placement cards; that
must not be treated as a final standing. The user should finish/review the
bracket in Challonge or manually correct and verify every podium field before
rendering.

Favorite entrants currently use browser-local storage and can be imported,
exported, added, edited, filtered, and removed from Manage Saved Data. They do
not yet sync through the signed-in user's Firestore account, so clearing browser
storage or switching devices will not retain them.


## Firebase backend

The project uses Firebase Authentication, Cloud Firestore, and Cloud Storage
for Firebase. The React login UI sends Firebase ID tokens to the protected
Flask API, which scopes stored formats, images, and fonts to the verified user.

The intended request flow is:

1. The React client signs a user in with Google or email/password through the
   Firebase Web SDK.
2. The client sends its short-lived Firebase ID token to Flask over HTTPS in an
   `Authorization: Bearer ...` header.
3. Flask verifies the token and uses the verified `uid` to select that user's
   data. The API never trusts a user ID submitted by the browser.
4. Firestore stores one document per saved layout or entrant. Cloud Storage
   stores uploaded image bytes, while Firestore stores private image metadata.

User resources follow these paths:

```text
users/{uid}/layouts/{layoutId}
users/{uid}/entrants/{entrantId}
users/{uid}/images/{imageId}
```

Layouts refer to uploaded images by stable image ID instead of embedding image
data or saving an expiring download URL. The server validates PNG, JPEG, and
WebP content before upload and creates short-lived URLs only after confirming
the authenticated user owns the metadata record.

Firebase Admin uses `GOOGLE_APPLICATION_CREDENTIALS`, whose value is an
absolute path to a service-account JSON stored outside the repository and web
root. The Storage bucket name is supplied separately through
`FIREBASE_STORAGE_BUCKET`. These values belong only in an ignored local `.env`
or the hosting provider's private application environment; real paths,
credentials, and bucket names must never be committed or exposed to browser
code. Hosted deployments may keep multiple server-only variables in a dotenv
file outside the web root; `PODIUM_SECRETS_FILE` can override the default file
in the hosting account's home directory without putting an account-specific
path in source control.

Because Firebase Admin uses privileged server credentials, it bypasses
Firestore and Storage Security Rules. The Flask service therefore enforces
ownership from the verified token on every operation. Client access should
remain denied until direct browser access is intentionally implemented with
tested rules.

See [docs/firebase-backend.md](docs/firebase-backend.md) for the endpoint
contract, configuration placeholders, data envelope, upload limits, and
deployment checklist.

## Deploying to cPanel

The application serves the built frontend from `frontend/dist`. Build that
frontend before creating each deployment ZIP.

### Build the release locally

From the project root in PowerShell:

```powershell
cd .\frontend
npm run build
cd ..
.\.venv\Scripts\python.exe .\build_deployment_zip.py
```

This creates `melee-podium-template-deploy.zip`. It contains the backend,
character assets, fonts, and the newly built `frontend/dist` files. It does not
contain `podium_stats.sqlite3`.

### Install or update the release in cPanel

1. Open the Python application's **application root** in cPanel File Manager.
2. Keep these existing items:
   - `public/` (created by cPanel for the application).
   - `tmp/` (used by Passenger/cPanel to restart the application).
   - `podium_stats.sqlite3` (contains the persistent PNG download counter. If
     deployed correctly it is probably not in this same app folder)
3. Delete the other old project files and folders in the application root.
   This removes files that may have been renamed or deleted locally, which a
   normal ZIP extraction would otherwise leave behind.
4. Upload `melee-podium-template-deploy.zip` to that application root and
   extract it there.
5. Install/update the Python dependencies from `requirements.txt` using
   cPanel's Python application dependency installer or the application's
   virtual-environment `pip`.
6. Confirm the Python application environment contains
   `GOOGLE_APPLICATION_CREDENTIALS` and `FIREBASE_STORAGE_BUCKET` as described
   in [docs/firebase-backend.md](docs/firebase-backend.md).
7. Restart the Python application from cPanel. If the interface does not offer
   a restart button, create or update `tmp/restart.txt` to tell Passenger to
   reload the application.

After deployment, visit `/api/stats` to verify the counter is still present.
Each click on the high-resolution image download increments this SQLite-backed value.
