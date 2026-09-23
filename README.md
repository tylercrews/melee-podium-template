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
* recreate podiums and placement numbers as individual assets to go with the new backgrounds
* did new podiums, but some people want to be able to do the old podiums too. Gotta make those
* Add alternative spellings to Entrant tag configurations. For example when an entrant in a bracket is named 'busta' or 'bu$ta' they should both be identified as the favorited entrant 'BU$TA' (capitalization is already ignored)
* See if there's a way to programmatically draw the podiums in whatever color you want - that way people could custom pick whatever colors they want for the podium.
    - different podium color options:
    1. gold, silver, bronze, x colors
    2. smash controller colors (what we have now)
    3. custom 1 - pick all
    4. custom 2 - pick 1 color
    5. custom 3 - pick 2 colors and they alternate
    - this podium color picker would also be good for background colors for the top 8er style, as long as transparent is also an option. Maybe transparent should be an option for the podiums too?
* full layout customizability saving and loading - pick where you want your emblem, title, and metadata to go, the podium colors, your preferred background, etc. You should be able to import a save file and/or paste some code to import/export these layout settings. 
* layout should include "Vods At" and "Streamed At" options with Twitch + Youtube icon shortening so people know where to watch matches
* layout could also have the twitter/bluesky of the TO
* should I also turn start.gg, parry.gg, and challonge urls into their icons for the tournament links?
* handling for parry.gg
* update shoutout page to shoutout Nicolet specifically
* seems like when you use a favorited entrant, then uncheck the box to save changes, and then render, it DELETES the favorited entrant. that's no good
* make it so when you select a new color for a character it doesn't reset the pose you already picked
* if the bottom left has too much text and the bottom right has too much text, also check the bottom center to see if that has less overlap for the watermark
* split sponsor into a designated field, allowing for sponsor to update as a property of a favorited entrant? maybe some kind of options thing? Would be nice for a tag to still get pulled up even if the sponsor changes though.
* in Manage Favorites when adding a new favorite it should be in a popup dialog that's easy to cancel out of, instead of appearing at the bottom of the list
* in manage favorites check out the logic for what happens when you import another person's "Primary" favorited entry for a tag. Does it keep yours or theirs? Maybe make it like a git merge conflict and create a series of popups where you have to choose yours or theirs
* see if decompiled melee can be used to generate melee assets - would need to be a separate repo. But would be amazing to programmatically create claps, victory screens, and tech roll animations. on top of other things.
* "Test template with example entrants" button. Use the gods as entrants, and lets them see if they like what they've done with their template before moving on to filling stuff out or saving.
* color picker - RGBA for background color. -> upload image, and image picker for background. Should give pixel count of the uploaded pic and say how big the image is. Then let them use a multiplier to scale up or down the image, then position it in a frame to select what section the bacground should be.
* Background color for entrants should have presets but still allow a transparency slider on presets.
* Defaulting to Top 4 seems to be confusing users - should have a popup or something. Need to try the url brooke was using to make sure that the upload didn't have some other error, but I think what she was talking about was it just nudging her to do a top 4.
* fix some poses - they feel a little off center. Like Marth pose a and fox pose a feel very off center
* need an option for Random. Usually won't be able to see it from imports, but should be able to set it manually in case someone enters an online tournament
* when you import a character they should default to Default color not random. - Brooke
* when someone has a ton of characters used it looks a little cluttered, would be nice to be able to convert some of the lower-use characters to stock icons instead. 
* have somewhere that explains the middle, left, right multi-char logic for people who get really deep into minmaxing poses
* the text under the podiums, namely the character names in singles, should be vertically aligned. Instead of row 1, row 2 always. So like right now chars with 
* thank brooke for the feedback and compliments

Maybes/Eventuallies:
* if you implement profiles and logins you could make it so that you can have multiple saved tournament preferences attached to your account - like med could pick his TYM layout or his moondog layout and have it already be ready. Profiles would also be able to save custom assets like backgrounds and emblems
    * Need to do some research on costs of login systems, image/blob storage pricing, and see if I would need to limit access to a certain extent before asking for money.
* implementation of multiple backgrounds - solid color (with color picker), transparent, melee themed ones
* get a dedicated domain name? meleepodium.meme ? meleepodium.free? meleepodium.photo? meleepodium.pics ? just need to be sure if I want to keep calling it meleepodium or if we're gonna change the name when we have all the functionality done
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

The UI imports public Start.gg, Challonge, and parry.gg URLs. Their credentials
stay on the Flask server: Start.gg uses `START_GG_TOKEN`, Challonge uses
`CHALLONGE_API_KEY`, and parry.gg uses `PARRY_GG_API_KEY`. `bracket_import.py`
normalizes all three providers into the same
internal result format before the frontend fills the tournament and placement
fields.

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
