# melee-podium-template

## Thanks To

- [Malarki_](https://x.com/Malarki_), who I commissioned to expand the pool of character poses and did an amazing job.
- [Top8er](https://www.top8er.com/), an amazing site that my local scene was using all the time, only inspired me to create this podium template because there wasn't an option for doubles. Huge thanks for being [open source](https://github.com/ShonTitor/Top8er) (shouts out to ShonTitor, agiera, and jmlee337); it was a huge help for figuring out the start.gg and Challonge bracket importing.
- AeonSSB, Cjag01, radzo73, and caha1an, who created the [Melee-CSProject](https://github.com/AeonSSB/Melee-CSProject) that I got the original poses from.
- [CeLL on this old Smashboards thread](https://smashboards.com/threads/character-stock-icon-dump.390494/) for posting a dump of all the character stock icons.
- [Mr. C](https://www.spriters-resource.com/gamecube/ssbm/asset/46039/) for the Sheik stock icons.
- Also shoutout to [SmashBoards](https://smashboards.com/) in general - what an amazing site still.
- North Carolina Melee!! Love y'all.


TODO LIST:
* add a favicon
* make it so that the counter only increments when the render is Downloaded, not when it is generated - also see if the preview is lower res and tell the user that it's lower res (change download to Download High Resolution)
* attempt to identify when the "make your own" link text is going to get overwritten by text, and see if it would not be overwritten on the other corner, and if so flip it to the other side
* add a checkbox to explicitly ignore the url link when rendering - the link is already optional, but they might not think to delete it
* feels like for top 3 singles the 2nd place (left podium) anchor is a little too skewed to the right
* fix some poses - they feel a little off center. Like Marth pose a and fox pose a feel very off center

Maybes/Eventuallies:
* formatting positioners - if you want the title centered or to the side, if you want the metadata on the right (default) or swapped with the title
* add a contact section if anyone encounters errors or something - later once version is more stable and I know there's less to do
* Fit in tournament location?
* support for twitter and bluesky handles - need to come up with some place to put them.
* add support for people to use their own backgrounds?? - maybe cut the podiums out and add a transparent layer behind

* What if you had a tournament graphic input, and you could slot it in to the left of the title+subtitle, or to the left of the tourney info (but below where the title is, kind of in the middle) - inspired by like GOML, it would be nice if big big tournaments had the ability to use the graphics they've paid for. They'd need a scale slider to adjust the size, similar to the char portraits
* similar to the tournament graphic, what if the user could upload a font, then you give them the ability to adjust the size and thickness the same way that I've adjusted my fonts.

Different Layout Styles One Day:
* flying v with first place centered
* top 8er / waddle wednesday layout
* long rectangles just showing the eyes of the characters
* long portraits like the character select screen
* long portraits like the slippi loading screen - I think these are the same as like adventure mode maybe? would be a great source for new poses
* top8.gg has a really cool type of layout where they have title bar, podium-arranged top 3, then 5 on the bottom. But they do all squares. What if I had a half-and-half layout where the top 3 get their characters on short podiums, then the subsequent players get their characters in boxes underneath.
* instead of straight up boxes what if you maximized space by having / vs style diagonal split portraits

## Bracket-import groundwork

`bracket_import.py` now recognizes public Start.gg, Challonge, Tonamel, and
ParryGG bracket links and normalizes the data returned by their APIs into one
provider-neutral result format.  It deliberately retains data that cannot yet
be drawn (source URL, event, dates, seeds, handles, country, and raw metadata)
instead of throwing it away.

Start.gg can provide tournament/event name, start time, city/country, entrant
count, placements, seeds, player tags, linked X handles, and game character
selections.  Character selections require the Start.gg character-ID map and
the event's game/selection payload.  No supported provider offers a reliable
Melee costume/color field: Start.gg score encoding has been used as a heuristic
by Top8er, but it is not treated as verified here.  Challonge contributes names,
seeds, and final ranks; Tonamel contributes placement/display-name data; and
ParryGG contributes placements, tags, country, entrant count, and tournament
date/location when present.

Start.gg explicitly identifies an event's entrant size, so an entrant size of
two imports as doubles.  Its entrant display name is retained as the team name
and its two participant tags are retained as team members.  ParryGG can do the
same when its entrant records expose exactly two users.  Challonge and Tonamel
bracket-result payloads do not reliably state whether a display name is a team,
so their imports stay `unknown` until a UI allows confirmation.

The module currently parses API JSON rather than embedding credentials in this
desktop project.  A future URL-import UI should obtain server-side credentials
for Start.gg (GraphQL bearer token), Challonge (API/OAuth), Tonamel (OAuth
client credentials), and ParryGG (API-key/gRPC), then pass each response to the
matching `parse_*` function.  `startgg_query()` supplies the safe base GraphQL
request for the first provider.

LocalStorage and LocalStorage Management page.
* should be able to store 300-350 entrants per MB, and localstorage can have up to 5MB, but I don't really want to push it.
* should be able to specify whether or not you want to save entrants when creating them
* should be able to import+export
* should be able to add/remove from the management screen
* also warn people that if they clear storage or use another device they'll disappear

way down the road:
player profiles - have auto selections for frequently used people, maybe by some kind of profile system so you can log in and have people you know.


# testing locally
(backend)
flask --app app run --port 5000

(frontend)
cd .\frontend
npm run dev

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
   - `podium_stats.sqlite3` (contains the persistent PNG render/download
     counter. (If deployed correctly it is probably not in this same app folder)
3. Delete the other old project files and folders in the application root.
   This removes files that may have been renamed or deleted locally, which a
   normal ZIP extraction would otherwise leave behind.
4. Upload `melee-podium-template-deploy.zip` to that application root and
   extract it there.
5. Restart the Python application from cPanel. If the interface does not offer
   a restart button, create or update `tmp/restart.txt` to tell Passenger to
   reload the application.

After deployment, visit `/api/stats` to verify the counter is still present.
Each successfully generated PNG increments this SQLite-backed value.
