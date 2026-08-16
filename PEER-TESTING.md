Peer testing
============

The point of this is not to find out whether people can use VeriFit. It
is to find out whether people who use it reach *better* conclusions than
they would have without it. Those are different questions, and only the
second one matters.

So the thing being measured is not "did they click everything". It is
"did they end up believing the right amount".


Three datasets, three right answers
-----------------------------------
Each link opens with the data already loaded. Do not say which is which.

1. A clear winner. The quadratic really is the best model and the
   evidence is strong. A well calibrated tester says quadratic, and
   says it confidently.

   https://amiug.github.io/VeriFit/#d=1%3A15.5%2C2%3A26.8%2C3%3A33.9%2C4%3A40.3%2C5%3A42.6%2C6%3A44.1%2C7%3A41.8%2C8%3A38.7%2C9%3A31.2%2C10%3A23.4

2. A genuine tie. Linear and power fit this almost identically and the
   data cannot separate them. A well calibrated tester says so, rather
   than picking whichever sits on top.

   https://amiug.github.io/VeriFit/#d=1%3A2.4%2C2%3A5.1%2C3%3A6.2%2C4%3A9.4%2C5%3A10.1%2C6%3A13.4%2C7%3A14%2C8%3A17.6%2C9%3A18.1%2C10%3A21.4%2C11%3A22.2%2C12%3A25.6

3. One point decides it. Row 4 is wild, and removing it changes the
   winner. A well calibrated tester notices the answer is fragile
   before committing to it.

   https://amiug.github.io/VeriFit/#d=1%3A-14.2%2C2%3A-10.8%2C3%3A-8.3%2C4%3A24%2C5%3A-2.1%2C6%3A1.2%2C7%3A4.6%2C8%3A7.8%2C9%3A11.3%2C10%3A14.7%2C11%3A17.2%2C12%3A21.1


How to run it
-------------
Five people is enough. More than that and the same problems keep
turning up. One at a time, about ten minutes each.

Send one link and ask one question:

    Which equation describes this data, and how sure are you?

Then say nothing. This is the hard part and the whole experiment. Every
hint given is a hint that will not be there when a stranger opens the
link, and the silence is what reveals which parts of the app explain
themselves.

Only if they are properly stuck, after a minute or so, ask what they
have tried. Note where they stalled: that spot is the finding.


What to write down
------------------
For each person and each dataset:

    their answer, and the confidence they gave it
    whether they read the verdict at all
    on the tie, did they notice the two models were level
    on the outlier, did they check influence before answering
    the first thing they clicked
    anything they said out loud that sounded confused

Do not write down whether they found every feature. An unused feature is
only a problem if not using it led them somewhere wrong.


Reading the results
-------------------
Good signs:

    the tie is called a tie
    the fragile answer is called fragile
    somebody says a number is smaller without being told to look

Bad signs, and what each one means:

    everyone reads the top row and stops
        the ranking looks like a scoreboard rather than an argument

    nobody opens the verdict
        it is hidden behind a button it should not be behind

    the tie is answered confidently
        the tie message is not carrying, and is the single most
        important sentence the app writes

    people trust the outlier answer
        influence is buried, and should announce itself when the
        ranking actually is fragile

Fix the two most common confusions, then run it again with two fresh
people. Two rounds is usually enough.


A last question worth asking
----------------------------
After the three datasets, ask this one:

    A model fits your points almost perfectly. Is that good?

Somebody who has understood VeriFit will hesitate, and then say it
depends on whether the model predicts as well as it fits. Somebody who
has been clicking through it without absorbing the idea will say yes.

That answer is the real measure of whether the app taught anything.
