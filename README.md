# melee-podium-template

## Thanks To

- [Malarki_](https://x.com/Malarki_), who I commissioned to expand the pool of character poses and did an amazing job.
- [Top8er](https://www.top8er.com/), an amazing site that my local scene was using all the time, only inspired me to create this podium template because there wasn't an option for doubles. Huge thanks for being [open source](https://github.com/ShonTitor/Top8er) (shouts out to ShonTitor, agiera, and jmlee337); it was a huge help for figuring out the start.gg and Challonge bracket importing.
- AeonSSB, Cjag01, radzo73, and caha1an, who created the [Melee-CSProject](https://github.com/AeonSSB/Melee-CSProject) that I got the original poses from.
- [CeLL on this old Smashboards thread](https://smashboards.com/threads/character-stock-icon-dump.390494/) for posting a dump of all the character stock icons.
- Also shoutout to [SmashBoards](https://smashboards.com/) in general - what�what an amazing site still.
- North Carolina Melee!! Love y'all.


TODO LIST:
* archive some of the worse poses - zelda+sheik, captain falcon pose a (his back foot will never be on the platform unless i make him a little baby man), bowser pose b (so damn wide and short)
* need to get poses for characters named to be something that makes more sense (instead of a, b, etc)
* add support for people to use their own backgrounds?? - maybe cut the podiums out and add a transparent layer behind

Fit in tournament location?

support for twitter and bluesky handles - need to come up with some place to put them.

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

## Render counter deployment

Each successfully generated PNG increments a persistent SQLite counter, available at /api/stats and shown in the page header. By default the database is podium_stats.sqlite3 beside app.py. For deployment, mount durable storage and set PODIUM_STATS_DB to a path on that volume; otherwise providers with ephemeral filesystems will reset the total on redeploy.
