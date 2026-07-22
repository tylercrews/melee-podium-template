# melee-podium-template
Inspired by Top8er and using assets from Melee-CSProject, this program creates top 8 podium images for doubles tournaments specifically, which are not well supported in top8er.


TODO LIST:
* after importing from start.gg, cross reference with your map of frequently used entrants to auto-select colors (because I think they don't have colors, and/or TOs don't really keep track)
* * need to have a way of keeping track of the colors used so that the most frequent color is the one that shows up. (not sure if startgg keeps track of color use, but that's why it would be helpful)

Fit in tournament location?
more font support - like IMPACT bold, and maybe another option that's far less memey

Redo the background image so the podium is 3d instead of just a square box, the characters should be standing on something lol

support for twitter and bluesky handles - need to come up with some place to put them.

blend the #seed color into the podium by making it the outline color, instead of sticking out with more white


frontend to fill stuff out
* preview mode to make adjustments
* counter for how often the generator has been used, keep a cute counter on the page lol.
start.gg and challonge support from top8er to plug in brackets easily

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
