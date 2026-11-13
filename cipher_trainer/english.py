"""A tiny English model built at import time from an embedded training text (no data files, no downloads).

Letter frequencies are the usual published values for English text. The trigram model is trained on the paragraph below,
which was written for this project; it is small, so scores are smoothed. Good enough to rank candidate plaintexts of
roughly 80+ letters, not a general language detector."""
from __future__ import annotations
import math
from collections import Counter

ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# percent frequency of each letter in English text (classic published table)
FREQ = dict(zip(ALPHA, [8.167, 1.492, 2.782, 4.253, 12.702, 2.228, 2.015, 6.094, 6.966, 0.153, 0.772, 4.025, 2.406,
                        6.749, 7.507, 1.929, 0.095, 5.987, 6.327, 9.056, 2.758, 0.978, 2.360, 0.150, 1.974, 0.074]))
IC_ENGLISH = 0.0667
IC_RANDOM = 1 / 26

CORPUS = """
The morning train left the station a little after seven and the platform was almost empty. A woman in a green coat stood near
the end of it, holding a paper cup and reading a letter that she had read many times before. She did not look up when the
doors opened. Inside, the carriage smelled of coffee and wet umbrellas, and the windows were fogged so that the town outside
was only a gray shape moving slowly past. There was a time when people wrote to each other every week, and the postman knew
every house on the street by the sound of its gate. Now the messages arrive faster than anyone can think about them, and
most of them are forgotten before the next one comes. The old methods of keeping a secret were simple. You took a sentence,
you moved every letter along the alphabet by a fixed number of places, and you trusted that nobody would think to move them
back. Soldiers used it, merchants used it, and children used it to hide notes in school. Then someone noticed that in every
language some letters appear more often than others, and that the most common letter in a long message is almost always the
same one. That single observation broke the whole family of simple ciphers, and it is still the first thing a student learns.
To break a message you count the letters, you compare the counts with what you expect to see, and you make a careful guess.
When the guess is wrong you try another. When it is right the words begin to appear, first one or two and then a whole line,
and the feeling is hard to describe. It is like finding a door in a wall that you had thought was solid. The cleverest systems
tried to hide the counts by using many alphabets in turn, one for each letter of a secret word, but the secret word repeats,
and a repeated word leaves a pattern in the message that can be measured. If the same group of letters appears twice, the
distance between the two places must be a multiple of the length of the key, and with several such pairs the length can be found
from the common factors. After that the problem falls apart into a handful of easy ones, each solved by counting. Another way
to hide a message is not to change the letters at all but to change their order, writing them in a zigzag across a few rails or
in columns under a keyword and reading them off in a different sequence. The letters are all still there, with exactly the same
counts, which is how you know that the trick was a shuffle and not a substitution. Patience matters more than cleverness here.
You try each possible width, you read the result, and you keep the one that looks like language. Machines are good at this kind
of search because they do not get bored and they do not mind being wrong ten thousand times in a row. All they need is a way to
score a guess, a number that goes up when the text looks more like the words people actually use. Common pairs and triples of
letters make a good score, such as the, and, ing, ion, ent, for, tha, nth, was, and ere, because they appear in almost every
sentence ever written. A program that starts from a random key and keeps any change that raises the score will often climb all
the way to the right answer within a few thousand steps. The garden behind the house was quiet that afternoon, and the children
had gone to see their grandmother on the other side of the river. We were told that the bridge would be closed until the water
fell, so we waited, and talked about nothing in particular, and watched the light change on the hills. It is strange how a day
with nothing in it can be remembered better than a day full of events. There were questions that nobody asked and answers that
nobody gave, and the evening came on slowly with the smell of rain on the road. In the end the message was short. It said that
the meeting had been moved to Thursday, that everyone should bring their own papers, and that nothing was to be written down
about the place. We read it twice, put it in the stove, and went to find our coats. Whether you are studying history, playing a
puzzle game, or simply curious about how secrets were kept before computers, these methods teach the same lesson: every system
that hides information also leaves a trace of what it hides, and a patient reader can follow that trace back to the source.
A good teacher will tell you to start with the simplest tests and to write down what you find at each stage. Count the letters
first. Compare the totals with the usual figures for the language. Then ask whether the totals look like language that has
been moved around or like language that has been replaced. The answer tells you which tools to reach for next, and it saves
hours of work. When we finally opened the box we found a small notebook, a brass key, and a map of the harbor with several
places marked in red ink. There was also a page of numbers which meant nothing to us, until my brother pointed out that none
of them was larger than twenty six. Between the lines of the notebook were the names of ships, the dates they had sailed,
and the cargo that each had carried, all written in a neat and careful hand that we did not recognize from any of our family.
Everything we know about the old town comes from letters, receipts and the stories that families told at the kitchen table.
People were walking, talking, reading, working and waiting in the street, and nothing seemed unusual about it. The baker was
baking bread before sunrise because customers came early, and the smell of it reached the end of the road. A carpenter was
building a table, a teacher was checking homework, and a boy was digging in the garden for worms to take fishing. Children
should not walk alone near the river, said the neighbors, because the current is strong and the ground along the bank is
soft after rain. We never knew exactly why the clock stopped, but some people thought it was cold weather and others blamed
the cellar damp. A careful reader looks at each word, checks the grammar, and asks whether the sentence could have been written
by a person. Because letters are chosen by habit, the frequency of common groups such as ing, ed, er, ou, ck and ch gives
the game away. Keep the lamp lit, mind the step, call the doctor, and make sure that every window is closed before you go.
Could you tell me where the station is, how much the ticket costs, and which platform the train will leave from? Of course,
said the clerk, it is just past the market, on the left, beside the church with the tall clock tower. We packed a few clothes,
some food, a blanket, a camera and two books, locked the front door, and drove north along the coast until it was dark. Quick
brown foxes jump over lazy dogs, while zebras and jackals watch from the back of the field, and a quiet wizard mixes his
potion beside the fire. Many people believe that the first message sent across the sea was about weather, but historians
disagree, and their evidence is thin. The captain looked at the chart, then at the sky, then at the crew, and said that
they would sail at first light. Nothing more was said. The ship left the harbor under a cold gray sky, past the lighthouse,
past the rocks, and out into the open water, where the wind was waiting for them.
"""

QUAD_WORDS = ("THE AND THAT HAVE FOR NOT WITH YOU THIS BUT HIS FROM THEY SAY HER SHE WILL ONE ALL WOULD THERE THEIR WHAT OUT "
              "ABOUT WHO GET WHICH WHEN MAKE CAN LIKE TIME NO JUST HIM KNOW TAKE PEOPLE INTO YEAR YOUR GOOD SOME COULD THEM "
              "SEE OTHER THAN THEN NOW LOOK ONLY COME ITS OVER THINK ALSO BACK AFTER USE TWO HOW OUR WORK FIRST WELL WAY EVEN "
              "NEW WANT BECAUSE ANY THESE GIVE DAY MOST US WAS ARE HAD HAS WERE BEEN MESSAGE LETTER SECRET MEET ATTACK DAWN").split()


def clean(text: str) -> str:
    return "".join(c for c in text.upper() if "A" <= c <= "Z")


def _train():
    t = clean(CORPUS)
    tri = Counter(t[i:i + 3] for i in range(len(t) - 2))
    bi = Counter(t[i:i + 2] for i in range(len(t) - 1))
    uni = Counter(t)
    n = len(t)
    return tri, bi, uni, n


_TRI, _BI, _UNI, _N = _train()
_V = 26


def _logp(tri: str) -> float:
    # interpolate trigram, bigram and unigram estimates (Jelinek-Mercer style) so unseen trigrams are not -inf
    a, b, c = tri
    p_uni = (FREQ[c] / 100.0)
    p_bi = (_BI.get(b + c, 0) + 0.5 * p_uni) / (_UNI.get(b, 0) + 0.5) if _UNI.get(b, 0) else p_uni
    p_tri = (_TRI.get(tri, 0) + 0.5 * p_bi) / (_BI.get(a + b, 0) + 0.5)
    return math.log(0.6 * p_tri + 0.3 * p_bi + 0.1 * p_uni)


_CACHE: dict = {}


def trigram_score(text: str) -> float:
    """Mean log-probability per trigram of the letters of `text` (higher is more English-like). Needs >= 3 letters."""
    t = clean(text)
    if len(t) < 3:
        return -99.0
    tot = 0.0
    for i in range(len(t) - 2):
        k = t[i:i + 3]
        v = _CACHE.get(k)
        if v is None:
            v = _CACHE[k] = _logp(k)
        tot += v
    return tot / (len(t) - 2)


def word_hits(text: str) -> int:
    """How many letters of `text` are covered by common English words (greedy scan over a short list; a readability hint)."""
    t = clean(text)
    words = sorted(set(QUAD_WORDS), key=len, reverse=True)
    covered = 0
    i = 0
    while i < len(t):
        for w in words:
            if len(w) >= 3 and t.startswith(w, i):
                covered += len(w); i += len(w); break
        else:
            i += 1
    return covered


def english_score(text: str) -> float:
    """Trigram score plus a small bonus for common-word coverage. Used to pick the best candidate."""
    t = clean(text)
    if len(t) < 3:
        return -99.0
    return trigram_score(t) + 1.0 * word_hits(t) / len(t)


def counts(text: str) -> Counter:
    return Counter(clean(text))


def ic(text: str) -> float:
    """Index of coincidence of the letters of `text`: sum n(n-1) / (N(N-1)). English ~0.0667, uniform random ~0.0385."""
    c = counts(text)
    n = sum(c.values())
    if n < 2:
        return 0.0
    return sum(v * (v - 1) for v in c.values()) / (n * (n - 1))


def chi_squared(text: str) -> float:
    """Chi-squared statistic of the letter counts against English frequencies (lower = closer to English)."""
    c = counts(text)
    n = sum(c.values())
    if not n:
        return float("inf")
    return sum((c.get(l, 0) - n * FREQ[l] / 100.0) ** 2 / (n * FREQ[l] / 100.0) for l in ALPHA)
