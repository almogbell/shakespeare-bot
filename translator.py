"""Single-pass, context-aware Shakespearean translation; no external API."""
import json
import random
import re
from pathlib import Path

IDIOMS = {
 "i don't know":"I know not", "i do not know":"I know not",
 "can you help me":"canst thou aid me", "how are you":"how art thou",
 "do you":"dost thou", "did you":"didst thou", "can you":"canst thou",
 "will you":"wilt thou", "would you":"wouldst thou",
 "you are":"thou art", "you're":"thou art", "you have":"thou hast",
 "you've":"thou hast", "you will":"thou wilt", "you'll":"thou wilt",
 "you don't":"thou dost not", "you do not":"thou dost not",
 "i'm":"I am", "i can't":"I cannot", "i won't":"I shall not",
 "don't":"do not", "doesn't":"doth not", "isn't":"is not",
 "aren't":"are not", "wasn't":"was not", "weren't":"were not",
 "no cap":"in very truth", "for real":"in very truth",
 "touch grass":"take thyself to the meadows",
 "skill issue":"a lack of prowess", "spill the tea":"reveal the secret tidings",
 "that was fire":"that was splendid", "this is fire":"this is splendid",
 "was fire":"was splendid", "i saw you":"I saw thee",
 "see you":"see thee", "help you":"aid thee", "thank you":"I thank thee",
 "with you":"with thee", "to you":"to thee", "for you":"for thee",
 "about you":"of thee", "yourself":"thyself", "yours":"thine",
 "your":"thy", "you":"thou", "yes":"aye", "hello":"well met",
 "goodbye":"fare thee well", "friend":"good fellow",
 "friends":"good fellows", "very":"most", "really":"truly",
 "terrible":"wretched", "great":"splendid", "but":"yet",
 "before":"ere", "soon":"anon"
}
AMBIGUOUS = {"fire","tea","cap","bet","period","work","working","shade",
 "slay","slaying","based","valid","w","l","goat","snack","flex",
 "troll","lag","make","made"}
PROTECTED = re.compile(
 r"<(?:@!?|@&|#)\d+>|<a?:[A-Za-z0-9_]+:\d+>|https?://[^\s<>]+|"
 r"(?<!\w)@\w+|"+chr(96)+r"{1,3}[\s\S]*?"+chr(96)+r"{1,3}", re.I)
VERBS = {"are":"art","have":"hast","has":"hast","do":"dost",
 "does":"dost","will":"wilt","shall":"shalt","can":"canst",
 "could":"couldst","would":"wouldst","know":"knowest",
 "think":"thinkest","want":"desirest","like":"likest",
 "love":"lovest","see":"seest","speak":"speakest","need":"needest",
 "say":"sayest","play":"playest","look":"lookest","feel":"feelest",
 "believe":"believest","understand":"understandest"}

def _rules(path):
    with open(path, encoding="utf-8") as f:
        dictionary = json.load(f)
    rules = dict(IDIOMS)
    for category in ("gaming_and_discord","phrases_and_commands","nouns_and_salutations"):
        for pattern, replacement in dictionary.get(category, {}).items():
            literal = pattern
            if literal.startswith(r"\b") and literal.endswith(r"\b"):
                literal = literal[2:-2]
            if re.search(r"\\|[\[\]().*+?{}|^$]", literal):
                continue
            if literal.lower() not in AMBIGUOUS:
                rules.setdefault(literal.lower(), replacement)
    return [(re.compile(r"(?<!\w)"+re.escape(k)+r"(?!\w)", re.I), v)
            for k,v in sorted(rules.items(),key=lambda item:-len(item[0]))]

def _case(source, target):
    if source.isupper() and len(source)>1:
        return target.upper()
    if source[:1].isupper() and source.lower() not in ("i","i'm"):
        return target[:1].upper()+target[1:]
    return target

def _translate_plain(text, rules):
    occupied = [False]*len(text)
    matches = []
    for pattern, replacement in rules:
        for m in pattern.finditer(text):
            if any(occupied[m.start():m.end()]):
                continue
            occupied[m.start():m.end()] = [True]*(m.end()-m.start())
            matches.append((m.start(),m.end(),_case(m.group(),replacement)))
    matches.sort()
    out, pos = [], 0
    for start,end,replacement in matches:
        out.extend((text[pos:start],replacement))
        pos = end
    out.append(text[pos:])
    result = "".join(out)
    alternatives = "|".join(map(re.escape,sorted(VERBS,key=len,reverse=True)))
    return re.sub(r"(?i)(\bthou\s+)("+alternatives+r")\b",
                  lambda m:m.group(1)+VERBS[m.group(2).lower()],result)

class BalancedTranslator:
    def __init__(self, dictionary_path=None, flair_probability=0.08):
        self.rules = _rules(dictionary_path or Path(__file__).with_name("dictionary.json"))
        self.flair_probability = flair_probability

    def translate(self, text, *, flair=True):
        if not text or not text.strip():
            return text
        # Process the original segments only: replacements cannot trigger more rules.
        pieces, pos = [], 0
        for match in PROTECTED.finditer(text):
            pieces.append(_translate_plain(text[pos:match.start()],self.rules))
            pieces.append(match.group())
            pos = match.end()
        pieces.append(_translate_plain(text[pos:],self.rules))
        result = "".join(pieces)
        if flair and len(text.split())>=5 and random.random()<self.flair_probability:
            result = random.choice(("Hark! ","Prithee, ","Verily, "))+result
        return result

_default = None
def translate_to_shakespearean(text):
    global _default
    if _default is None:
        _default = BalancedTranslator()
    return _default.translate(text)
