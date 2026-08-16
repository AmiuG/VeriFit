VeriFit
=======

An interactive curve-fitting tool that ranks models by how well they
predict, not how well they fit -- and shows you when to doubt the winner.

You enter (x, y) points in a table or by clicking the graph. VeriFit fits
several candidate models (linear, quadratic, cubic, exponential, power,
logarithmic, flatline), ranks them by cross-validated error rather than
R-squared, and surfaces the evidence behind the ranking: residual
patterns, AICc support, ties, parameter uncertainty, and whether the
winner survives removing any single point.

Video demo
----------
https://youtu.be/QjtiAJIKz28

How to run
----------
1. Put all eight .py files in the same folder:
       main.py, ui.py, graphview.py, engine.py, stats.py,
       models.py, dataset.py, linalg.py
   tests.py and experiment.py are optional extras that check the math
   and the claim behind it.
2. Run main.py.
   
Libraries
---------
cmu_graphics is the only library that needs to be installed:

    pip install cmu-graphics

Does ranking by prediction actually work?
-----------------------------------------
VeriFit claims that ranking models by cross-validated error finds the
right equation more often than ranking them by R squared. experiment.py
tests that claim rather than assuming it. It builds data from an
equation it already knows, hides the equation, and checks which rule
points back at it:

    python3 src/experiment.py

Every setting runs 400 times from one fixed seed, so the numbers below
can be reproduced exactly. Two of the six tables:

    12 points, noise added on top
    true equation   CV names it  or admits a tie  R2 names it  R2 says cubic
    Linear                  74%              92%           0%           100%
    Quadratic               79%              98%           0%           100%
    Exponential             49%              69%           8%            92%
    Logarithmic             88%              98%          57%            43%
    Power                   16%              24%           0%           100%
    average                 61%              76%          13%

    30 points, noise multiplied in
    true equation   CV names it  or admits a tie  R2 names it  R2 says cubic
    Linear                  69%              81%           0%           100%
    Quadratic               79%              94%           0%           100%
    Exponential             78%              86%          18%            82%
    Logarithmic             85%              92%          38%            62%
    Power                   72%              82%           0%           100%
    average                 77%              87%          11%

What the study shows:

1. Cross-validation names the true equation 46% to 77% of the time
   depending on the conditions. R squared manages 5% to 13%.
2. R squared picks the cubic almost every time, whatever made the data.
   That is the whole problem in one column: the cubic has the most
   parameters, so it always fits the points it was given best, and R
   squared rewards exactly that.
3. When cross-validation does not name the true equation, it usually
   says the top two are too close to call, and the true equation is
   one of them. Counting those, the app is right or honestly uncertain
   76% to 87% of the time. Being unsure out loud is not the same kind
   of mistake as being confidently wrong.

Where it struggles, and why
---------------------------
The study also found two real limits, which are worth stating plainly.

Power data is hard. Over the x range tested, y = 2x^1.5 and a quadratic
are nearly the same curve, so cross-validation picks the quadratic most
of the time. This is less a failure of the scoring rule than a fact
about the data: with points only over that stretch, the two equations
genuinely do predict alike. It is exactly the situation the tie message
is for.

Noise has to match how the model is fitted. VeriFit fits the
exponential and power models by taking logarithms, which is the right
move when data is wrong by a percentage (populations, money, decay) and
the wrong move when it is wrong by a fixed amount. The tables show it:
with noise multiplied in, the exponential is recovered 78% of the time
at 30 points and gets better as points are added, as it should. With
noise added on top, the same model drops to 15% and gets worse with
more points, because more points make the mismatch easier to see.
Growth data usually carries multiplied noise, so the fit suits the
common case, but the limit is real.

Tests
-----
tests.py checks the math files (linalg, stats, models, dataset, engine)
against answers worked out by hand. It does not need cmu_graphics:

    python3 src/tests.py

Keyboard shortcuts
------------------
         s        load the next sample dataset (there are five,
                  each showing off one thing the ranking can do)
         u        undo the last data change
         f        reframe the graph around the data
         r        show the Residuals tab
         p        show the Predict tab
         v        show the Sensitivity tab
         i        show the Influence tab (runs the leave-one-out sweep)
         q        show the R2 vs CV tab
         h        open the help overlay (any key closes it)
         1 - 7    expand the model card at that rank
         arrows   pan the graph window (while a cell is being
                  edited, up/down scroll the table instead)
         + / -    zoom the graph in and out

Mouse controls
--------------
         Click a table cell        edit it (type, then enter to commit,
                                   tab to move to the next cell)
         Click the draft row       add a new point by typing
         Click x on a table row    delete that point
         Click o on a table row    exclude/include that point (excluded
                                   points stay visible but are not fitted)
         Click the graph           add a point there (in Predict mode this
                                   moves the prediction marker instead)
         Click a card's swatch     show/hide that model's curve
         Click a card              expand/collapse its details
         Window button (top right of the Graph panel)
                                   opens a popover to type exact graph
                                   bounds; tab cycles the four boxes,
                                   enter applies, escape closes
         Sample button (top right of the header)
                                   opens the list of sample datasets;
                                   the one currently loaded stays
                                   highlighted
         Sensitivity tab           drag a slider to move a parameter
                                   within +/-2 standard errors; Reset
                                   refits and restores the scores

Notes for grading
-----------------
The Influence tab refits the whole model set once per data point, so on
larger datasets it takes a moment to appear. Excluded points, the
x-offset shown in the status bar, and "unavailable" models (with the
reason each could not be fitted) are all deliberate features, not bugs.
Blocks of code written with AI assistance are marked with comment
banners naming the model and date; everything else is my own work.
