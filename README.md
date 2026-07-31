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
2. Run main.py.
   
Libraries
---------
cmu_graphics is the only library that needs to be installed:

    pip install cmu-graphics

Keyboard shortcuts
------------------
         s        load the sample dataset /n
         u        undo the last data change
         f        reframe the graph around the data
         r        show the Residuals tab
         p        show the Predict tab
         v        show the Sensitivity tab
         i        show the Influence tab (runs the leave-one-out sweep)
         q        show the R2 vs CV tab
         1 - 7    expand the model card at that rank
         up/down  scroll the data table

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
