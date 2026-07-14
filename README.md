# melee-podium-template
Inspired by Top8er and using assets from Melee-CSProject, this program creates top 8 podium images for doubles tournaments specifically, which are not well supported in top8er.


TODO LIST:
Entrant class rework:
* Entrant should have the properties tag, and Characters[].
* an array of characters allows for multiple char selection, and putting tag with the char in one place simplifies the parameters
support Multiple Character Selection: (thanks for the idea, Zach)
* each entrant should have an array of the characters they used
* the characters need to be filtered via a set or something, so that the same char isn't repeated multiple times.
* * need to have a way of keeping track of the colors used so that the most frequent color is the one that shows up. (not sure if startgg keeps track of color use, but that's why it would be helpful)
* the characters need to have a sort order in the backend, so that way the larger characters are drawn first, and then smaller chars like pichu are drawn later.

Fit in tournament location?
more font support - like IMPACT bold, and maybe another option that's far less memey

Redo the background image so the podium is 3d instead of just a square box, the characters should be standing on something lol

support for twitter and bluesky handles - need to come up with some place to put them.

blend the #seed color into the podium by making it the outline color, instead of sticking out with more white


frontend to fill stuff out
* preview mode to make adjustments
* counter for how often the generator has been used, keep a cute counter on the page lol.
start.gg and challonge support from top8er to plug in brackets easily


way down the road:
player profiles - have auto selections for frequently used people, maybe by some kind of profile system so you can log in and have people you know.