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
* tags without sponsors in top 8 4 podium mode could be a little bigger still
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
* once we have placement numbers rendered instead of static assets, create an alternate counting mode where it puts 1-8 (5th 6th 7th 8th instead of 5th 5th 7th 7th) so that people can use it for PRs as well. Or maybe a top 10 pr mode.
* flying v with first place centered
* top 8er / waddle wednesday layout
* long rectangles just showing the eyes of the characters
* long portraits like the character select screen
* long portraits like the slippi loading screen - I think these are the same as like adventure mode maybe? would be a great source for new poses
* top8.gg has a really cool type of layout where they have title bar, podium-arranged top 3, then 5 on the bottom. But they do all squares. What if I had a half-and-half layout where the top 3 get their characters on short podiums, then the subsequent players get their characters in boxes underneath.
* instead of straight up boxes what if you maximized space by having / vs style diagonal split portraits

## Bracket importing

The UI currently imports public Start.gg and Challonge URLs. Their credentials
stay on the Flask server: Start.gg uses `START_GG_TOKEN` and Challonge uses
`CHALLONGE_API_KEY`. `bracket_import.py` normalizes both providers into the same
internal result format before the frontend fills the tournament and placement
fields.

The module also recognizes Tonamel and ParryGG URLs and contains parsing logic
for responses from both providers, but I do not currently have either service
configured. The live `/api/import` route therefore returns “not configured yet”
for those URLs instead of attempting a request. The existing Tonamel parser can
normalize placement and display-name data from a supplied response. The ParryGG
parser can normalize placements, tags, countries, entrant counts, dates, and
locations, and can identify doubles when every entrant record contains exactly
two users. Enabling either provider still requires implementing and configuring
its authenticated server-side fetch.

### Provider data limitations

Start.gg provides the richest import: tournament and event names, time,
location, entrant count, placements, seeds, participant tags, linked X handles,
and reported game-character selections. Start.gg also reports entrant size, so
an entrant size of two can be imported automatically as doubles. The entrant
display name becomes the team name and its two participant tags become the team
members.

No supported provider supplies a reliable Melee costume/color field, so the
user still reviews those selections. The importer does not treat score strings
or other undocumented values as verified costume data.

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
   - `podium_stats.sqlite3` (contains the persistent PNG download counter. If
     deployed correctly it is probably not in this same app folder)
3. Delete the other old project files and folders in the application root.
   This removes files that may have been renamed or deleted locally, which a
   normal ZIP extraction would otherwise leave behind.
4. Upload `melee-podium-template-deploy.zip` to that application root and
   extract it there.
5. Restart the Python application from cPanel. If the interface does not offer
   a restart button, create or update `tmp/restart.txt` to tell Passenger to
   reload the application.

After deployment, visit `/api/stats` to verify the counter is still present.
Each click on the high-resolution image download increments this SQLite-backed value.
