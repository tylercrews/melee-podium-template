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

Open `http://127.0.0.1:5173/`. Vite proxies API and character-asset requests to the Flask server on port 5000.

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
- Elenrique3 for creating the original Top8er 2023 design. It's truly a nearly perfect design other than the lack of doubles support. And Malarki_ again for coming up with the eyes template.
- Nicolet I would like to thank in particular for sending me the repo for the startgg USB reporting, and DevDogg for connecting me with them
- AeonSSB, Cjag01, radzo73, and caha1an, who created the [Melee-CSProject](https://github.com/AeonSSB/Melee-CSProject) that I got the original poses from.
- [CeLL on this old Smashboards thread](https://smashboards.com/threads/character-stock-icon-dump.390494/) for posting a dump of all the character stock icons.
- [Mr. C](https://www.spriters-resource.com/gamecube/ssbm/asset/46039/) for the Sheik stock icons.
- Also shoutout to [SmashBoards](https://smashboards.com/) in general - what an amazing site still.
- Big thank you to Shenal and Brooke Bustamove for the positivity and feedback and for actually using this thing when I thought nobody was.
- Shouts out to Shenfest, only reason I'm back in the game.
- North Carolina Melee!! Love y'all.


TODO LIST:
* create some "quick select" options on the first loading screen that skip all of the layout-specific settings and make it easier to just use quickly.
* new pinwheel-style layout that shen showed me
* in legacy podiums mode the pink (left) podium looks the TINIEST bit bigger than the other. It's really not that noticeable, but compared to the two fifth place podiums it does because the orange and teal seem a lot better aligned
* header and metadata should have sliders for font size pickable by the user, maybe even get granular with the metadata fields each having different font sizes
TEST THIS * need to figure out how larger counts of included entrants work with the preset coloring. Like do you do rainbow shades in between? Shades per row? Shades per placement number (for the top 16 one)? idk.
* make eye tweaks for singles and doubles

* split sponsor into a designated field, allowing for sponsor to update as a property of a favorited entrant? maybe some kind of options thing? Would be nice for a tag to still get pulled up even if the sponsor changes though.
* README/Documentation/FAQ/How To have somewhere that explains the middle, left, right multi-char logic for people who get really deep into minmaxing poses. Should also explain the point of logging in and whatnot.
* in manage favorites check out the logic for what happens when you import another person's "Primary" favorited entry for a tag. Does it keep yours or theirs? Maybe make it like a git merge conflict and create a series of popups where you have to choose yours or theirs
* fix some poses - they feel a little off center. Like Marth pose a and fox pose a feel very off center
* need an option for Random character selection. Usually won't be able to see it from imports, but should be able to set it manually in case someone enters an online tournament
* bugfix - when someone manages to make top 8 but didn't win any games then it doesn't keep track of any of their characters (lol). Yes this did happen lol. Maybe we can keep track of both characters won with and all characters and let the person decide which one to use for them/everyone. Maybe when you import there's like a dialog where you can confirm everything you're bringing in for each entrant. And that could let you see autocorrect stuff from your saved entrants and have you decide whether or not to keep it like a zip code correction screen

Maybes/Eventuallies:
* see if decompiled melee can be used to generate melee assets - would need to be a separate repo. But would be amazing to programmatically create claps, victory screens, and tech roll animations. on top of other things.
* add a contact section if anyone encounters errors or something - later once version is more stable and I know there's less to do
* support for twitter and bluesky handles - need to come up with some place to put them.
* Stress-test browser memory limits for guest image uploads, then implement safe in-memory tournament-logo and background selection for users who are not signed in.

Different Layout Styles One Day:
* a template that combines podiums and eyes - similar to podium top 8 4 podiums, but expands a lot. Might work even better for PRs and top 16s
* once we have placement numbers rendered instead of static assets, create an alternate counting mode where it puts 1-8 (5th 6th 7th 8th instead of 5th 5th 7th 7th) so that people can use it for PRs as well. Or maybe a top 10 pr mode.
* flying v with first place centered
* top 8er / waddle wednesday layout
* long rectangles just showing the eyes of the characters
* long portraits like the character select screen
* long portraits like the slippi loading screen - I think these are the same as like adventure mode maybe? would be a great source for new poses
* top8.gg has a really cool type of layout where they have title bar, podium-arranged top 3, then 5 on the bottom. But they do all squares. What if I had a half-and-half layout where the top 3 get their characters on short podiums, then the subsequent players get their characters in boxes underneath.
* instead of straight up boxes what if you maximized space by having / vs style diagonal split portraits

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

LocalStorage and LocalStorage Management page.
* should be able to store 300-350 entrants per MB, and localstorage can have up to 5MB, but I don't really want to push it.
* should be able to specify whether or not you want to save entrants when creating them
* should be able to import+export
* should be able to add/remove from the management screen
* also warn people that if they clear storage or use another device they'll disappear

way down the road:
player profiles - have auto selections for frequently used people, maybe by some kind of profile system so you can log in and have people you know.


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

TODO Refactor Plan:

The folder audit found that bracket importing and Firebase already have useful
package boundaries, but most image-generation code still lives as a connected
set of modules in the repository root. Those modules should be moved in stages,
because their imports, asset paths, tests, and deployment packaging are closely
related. `DrawPodium.py` is still an active compatibility dependency and cannot
be treated as dead code yet. `app.py` is also still responsible for several
unrelated API areas, while the frontend's `MakerApp.tsx` remains the main state
and workflow coordinator.

Suggested end-state grouping:

```text
bracket_import/          # Already completed: provider clients and normalization
firebase_services/       # Already grouped: authenticated cloud operations
rendering/
  creation.py            # Overall composition coordinator
  background_builder.py
  content_renderer.py
  formatting_assets.py
  format_preview.py
  preview_layers.py
  podium_colors.py
  legacy/
    DrawPodium.py
    legacy_podium_content_renderer.py
    constants.py
    portrait_pose_labels.py
    portrait_scale_adjustment_for_each_mode.py
    portrait_scale_adjustment_to_character_relativity.py
domain/
  models.py
  creation_modes.py
  mode_preferences.py
scripts/
  build_deployment_zip.py
  generate_background_thumbnails.py
  generate_preview_layers.py
assets/                  # Optional final pass because these paths are widely used
  backgrounds/
  characters/
  fonts/
  formatting/
frontend/src/
  features/workflow/
  features/saved-data/
  components/
  lib/
```

Recommended order if this refactor is approved later:

1. Record a clean baseline by running the complete Python suite and frontend
   production build. Make one focused commit per phase so moves can be reviewed
   and reverted independently.
2. Move the three generation/deployment utilities into `scripts/`. Update their
   project-root discovery rather than relying on the current working directory,
   then update README commands and deployment tests. This is the lowest-risk
   folder move.
3. Create `rendering/` and move the modern rendering modules together. Keep
   `creation.py` as the composition coordinator, use package-relative imports,
   and avoid mixing Flask request handling into this package. Move tests or
   update imports in the same commit.
4. Put the active compatibility renderer under `rendering/legacy/`. Do not
   delete or substantially rewrite `DrawPodium.py` during the move. First give
   it a stable package boundary; then migrate its responsibilities into modern
   modules through later, separately tested changes.
5. Create `domain/` for serializable models, mode selection, and preference
   schemas. Do this after `rendering/` so dependency direction can consistently
   flow from API/UI adapters to domain models to rendering, without circular
   imports.
6. Split `app.py` into focused Flask blueprints for bracket importing, format
   rendering/previews, built-in assets, and statistics. Keep a small root
   `app.py` application entry point and keep `passenger_wsgi.py` at the root for
   cPanel compatibility.
7. Reorganize the React source by feature. Extract workflow state and actions
   from `MakerApp.tsx` into focused hooks/components only after the backend
   paths are stable. Keep shared API/authentication utilities under `lib/` and
   avoid changing behavior and folder structure in the same commit.
8. Consider consolidating static files under `assets/` last. Background,
   character, font, formatting, preview-layer, test, and deployment paths all
   depend on their current locations, making this the highest-risk move. Use a
   single project-root asset resolver rather than adding new relative paths in
   each renderer.
9. Update `build_deployment_zip.py` after every phase and verify the archive
   contains every imported Python package, the built frontend, preferences, and
   runtime assets while continuing to exclude credentials, caches, the local
   SQLite counter, and generated archives.
10. After each phase, run all Python tests, build the frontend, import the Flask
    application, and manually verify one legacy and one customizable full-image
    download. Do not combine removal of old code with a folder move until the
    moved version has passed those checks.

Items that should remain in place unless their behavior is deliberately being
changed include `preferences/`, the reviewed visual test outputs, archived
design documentation, and `podium_stats.sqlite3`. Generated deployment ZIPs,
Python caches, frontend build output, and temporary render files should remain
ignored rather than committed.
