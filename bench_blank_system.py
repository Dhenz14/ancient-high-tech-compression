"""
Benchmark: V5 Blank System vs V4 baseline.

Compares:
  - v4 (current best): sequential encode -> brotli q=11
  - v5 (blank system): encode_v5 -> brotli q=11
  - raw brotli: just brotli q=11 on UTF-8 bytes

Reports pre-brotli sizes, post-brotli sizes, and delta vs v4.
Any text that regresses means Phase 3 is ❌ DITCHED.
"""
import sys
sys.path.insert(0, '.')

import brotli
from src.sequential.encoder import SequentialEncoder
from src.sequential.blank_encoder import encode_v5
from src.sequential.decoder import SequentialDecoder
from src.wordid.dictionary import Dictionary

d = Dictionary()
enc4 = SequentialEncoder(d)
dec = SequentialDecoder(d)

ARTICLE = "The history of science is a story of human curiosity and determination. From the ancient Greeks who first asked questions about the nature of the world to the modern researchers who probe the depths of space and the structure of atoms, people have always been driven to understand the universe around them. In the beginning, science was not separate from philosophy. Thinkers like Aristotle and Plato tried to explain the world through reason alone, without the benefit of experiments or measurements. It was not until the Renaissance that the scientific method began to take shape. Francis Bacon argued that knowledge should be built on observation and experiment, not just logic and tradition. Galileo turned his telescope to the sky and discovered that the earth was not the center of the universe. Newton showed that the same force that makes an apple fall from a tree also keeps the moon in orbit around the earth. These discoveries changed the way people thought about the world and their place in it. The industrial revolution brought science into everyday life. Steam engines, railways, and factories transformed society. Medicine advanced as doctors began to understand the causes of disease. In the twentieth century, science gave us computers, space travel, and the ability to split the atom. Today, science continues to push the boundaries of what we know and what we can do. From artificial intelligence to gene therapy, the frontiers of knowledge are expanding faster than ever before."
BLOG = "I was walking down the street yesterday when I saw something that completely changed my perspective on life. There was an old man sitting on a bench, feeding pigeons, and he looked so peaceful and content. I stopped and talked to him for a while. He told me he had been coming to that same bench every day for thirty years, ever since his wife passed away. He said the pigeons were his friends now, and they never judged him or asked him to be anything other than what he was. I think about that conversation often. In our busy lives, we forget that happiness does not come from having more things or being more successful. It comes from simple moments of connection and peace. The old man on the bench had figured out something that most of us spend our whole lives searching for."
NEWS = "The national economy added more jobs than expected last month, according to figures released by the government on Friday. The report showed that employment in the manufacturing sector had been growing steadily for the past six months, driven in part by new investment in clean energy projects. Economists said the results were better than anticipated, though they cautioned that uncertainty in global markets could slow growth in the months to come. The unemployment rate fell to its lowest level in more than a decade, a development that most analysts described as a sign of broad economic health. Wages continued to rise, particularly for workers in the service industry, where demand for labor has been strong. The central bank said it would hold interest rates steady for the time being, given the positive outlook for employment. Officials at several large companies announced plans to expand operations over the coming year, adding thousands of positions across the country. In the technology sector, demand for skilled workers remained high, and firms reported difficulty filling open roles despite offering competitive salaries. Community colleges have responded by developing new programs aimed at preparing workers for jobs in the field. The housing market showed mixed results, with prices rising sharply in major cities while remaining flat in many rural areas. Analysts said the gap between urban and rural markets had been widening for several years, raising concerns about inequality. Government officials said they were committed to addressing the issue, though they acknowledged that solutions would take time and require cooperation at all levels. A separate report released on the same day found that consumer confidence had risen to its highest point in more than two years, suggesting that households were feeling more secure about their financial situation."
TECH = "Version control is one of the most valuable tools available to any software developer. At its core, a version control system allows you to track changes to your files over time, so that you can return to an earlier state if something goes wrong. Learning to use it well is one of the best investments you can make as a professional. To get started, you need to install the software on your machine and create a new repository for your project. A repository is simply a folder that the system monitors for changes. Once you have set up the repository, you can begin adding files. Every time you make a set of changes that you want to preserve, you create a commit, which is a snapshot of the current state of your work. One of the most powerful features is the ability to work on branches. A branch is a separate line of development that runs alongside the main codebase. You can use a branch to build a new feature or fix a problem without affecting the rest of the project. When you are satisfied with the result, you merge the branch back into the main line. Working with a team becomes much easier when everyone uses the same system. Instead of sending files by email or trying to combine changes by hand, the software handles the process automatically. It records who made each change and when, so that the full history of the project is always available. It is also important to write clear messages when you create a commit. A good message explains not just what changed, but why the change was made. This makes it much easier to understand the project history later, especially when you need to trace the source of a problem. Taking a few extra seconds to write a useful message is always worth the effort in the long run."
STORY = "The library was nearly empty on that cold Tuesday morning. Margaret had been coming here for years, ever since she moved to the city, and she knew every corner of the old building. She settled into her usual chair beside the window and opened her book, but she found it hard to focus. There was something on her mind that she could not quite let go of. After a while, a young man sat down at the table across from her. She had noticed him before, always with a stack of notebooks and a worn leather bag. He caught her eye and smiled, and she nodded in return. Do you come here often, he asked, setting down his things. Most mornings, she said. It is the only place in the city where I can think clearly. He laughed softly. I know exactly what you mean. I had been working from home for almost a year before I found this place. I could not get anything done. They talked for a while about the neighborhood, about the books they were reading, about the small things in daily life that are easy to miss. Margaret found herself relaxing in a way she had not expected. She had been so caught up in her own worries that she had forgotten how good it felt to simply sit and talk with someone. By the time she looked up at the clock, more than an hour had passed. She gathered her things and stood to leave. Same time tomorrow, the young man asked. Perhaps, she said, and smiled. She stepped out into the cold air and felt, for the first time in weeks, that the day ahead might not be so difficult after all. The street was busy with the morning crowd, but she walked slowly, in no particular hurry."
INFORMAL = "okay so i finally tried that new coffee place everyone keeps talking about and honestly? totally worth it. the line was ridiculous but my friend was like just trust me and she was right. got this oat milk latte thing and it was so good i almost went back for a second one. also ran into someone i used to work with which was kind of awkward but whatever. we did the whole oh wow how are you thing for like two minutes and then both pretended we had somewhere to be. classic. anyway the rest of the day was pretty low key. finished that show i was watching which was a whole thing because the ending made absolutely no sense and now i have so many questions. texted my sister about it and she had thoughts. we ended up on the phone for like an hour just going back and forth about what it all meant. honestly one of my favorite kinds of conversations. made pasta for dinner because i did not feel like thinking about it. been doing that a lot lately. sometimes you just need the easy choice you know? feeling pretty good overall though. work has been stressful but i feel like i am getting a handle on things. slowly but surely. going to try to get to bed at a reasonable hour tonight because last week was a disaster on that front and i could really feel it by friday. anyway that is pretty much all that is going on. nothing dramatic. just regular life stuff. hope everyone is doing well out there."
ALL_MIXED = " ".join((ARTICLE + " " + BLOG + " " + NEWS + " " + TECH + " " + STORY + " " + INFORMAL).split())

texts = {
    "Article x1":  " ".join(ARTICLE.split()),
    "Article x10": " ".join((" ".join([ARTICLE]*10)).split()),
    "Blog post":   " ".join(BLOG.split()),
    "News":        " ".join(NEWS.split()),
    "Tech doc":    " ".join(TECH.split()),
    "Story":       " ".join(STORY.split()),
    "Informal":    " ".join(INFORMAL.split()),
    "All mixed":   ALL_MIXED,
}

print("=" * 85)
print("PHASE 3: V5 BLANK SYSTEM vs V4 BASELINE")
print("Dictionary: %d words" % d.size)
print("=" * 85)
print()
print("Round-trip verification (100%% accuracy required):")

all_ok = True
for name, text in texts.items():
    blob5 = encode_v5(text, d)
    result = dec.decode(blob5)
    ok = (result == text)
    if not ok:
        all_ok = False
        w1, w2 = text.split(), result.split()
        for i in range(min(len(w1), len(w2))):
            if w1[i] != w2[i]:
                print("  FAIL %s at word %d: %r != %r" % (name, i, w1[i], w2[i]))
                break
        if len(w1) != len(w2):
            print("  FAIL %s: length %d != %d" % (name, len(w1), len(w2)))
    else:
        # Count blanks
        n_blanks = (blob5[4] << 8) | blob5[5]
        print("  %-12s PASS  (%d blanked tier-1 tokens)" % (name, n_blanks))

if not all_ok:
    print("\nROUND-TRIP FAILURES — Phase 3 is BROKEN, cannot benchmark.")
    import sys; sys.exit(1)

print()
print("-" * 85)
print("%-12s %6s %6s | %8s %8s | %8s %8s | %s" % (
    "Text", "Raw", "Blank#",
    "V4-raw", "V5-raw",
    "V4+brotli", "V5+brotli",
    "Delta"
))
print("-" * 85)

total_v4 = 0
total_v5 = 0
regressions = 0

for name, text in texts.items():
    raw = text.encode('utf-8')

    # v4
    blob4 = enc4.encode(text)
    v4_raw = len(blob4)
    v4_br = len(brotli.compress(blob4, quality=11))

    # v5
    blob5 = encode_v5(text, d)
    n_blanks = (blob5[4] << 8) | blob5[5]
    v5_raw = len(blob5)
    v5_br = len(brotli.compress(blob5, quality=11))

    delta = v5_br - v4_br
    if delta > 0:
        verdict = "WORSE +%d" % delta
        regressions += 1
    elif delta < 0:
        verdict = "BETTER %d" % delta
    else:
        verdict = "same"

    total_v4 += v4_br
    total_v5 += v5_br

    print("%-12s %6d %6d | %8d %8d | %8d %8d | %s" % (
        name, len(raw), n_blanks,
        v4_raw, v5_raw,
        v4_br, v5_br,
        verdict
    ))

print("-" * 85)
total_delta = total_v5 - total_v4
print("%-12s %6s %6s | %8s %8s | %8d %8d | %s" % (
    "TOTAL", "", "",
    "", "",
    total_v4, total_v5,
    ("WORSE +%d" if total_delta > 0 else "BETTER %d") % abs(total_delta)
))
print()
print("=" * 85)
if regressions == 0 and total_delta < 0:
    print("PHASE 3: PASSES ✓ — %d bytes saved total across all texts" % abs(total_delta))
    print("Next step: commit as v3.0 and proceed to Phase 4 (cascade)")
elif regressions == 0 and total_delta == 0:
    print("PHASE 3: NEUTRAL — 0 bytes saved. Not worth the complexity.")
    print("Decision: DITCH Phase 3, proceed to Phase 5 (morphological fallback)")
else:
    print("PHASE 3: FAILS ✗ — %d regressions, total %+d bytes" % (regressions, total_delta))
    print("Decision: DITCH Phase 3, revert to v4 baseline, proceed to Phase 5")
print("=" * 85)
