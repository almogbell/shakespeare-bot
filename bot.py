import os
import random
import re
import json
import discord
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive

# Initialize Natural Language Toolkit for exact grammar identification
import nltk
from nltk import pos_tag, word_tokenize
try:
    # Check for the newer _eng tagger required by recent NLTK versions
    nltk.data.find('taggers/averaged_perceptron_tagger_eng')
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('averaged_perceptron_tagger', quiet=True)
    nltk.download('averaged_perceptron_tagger_eng', quiet=True)
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------------------------------------------
# DICTIONARY AND CONSTANTS
# ---------------------------------------------------------
DICTIONARY = {}
if os.path.exists("dictionary.json"):
    with open("dictionary.json", "r", encoding="utf-8") as f:
        raw_json = json.load(f)
        for category in raw_json.values():
            DICTIONARY.update(category)
    print(f"Loaded {len(DICTIONARY)} rules from dictionary.json")

SORTED_PATTERNS = sorted(DICTIONARY.keys(), key=lambda p: len(p), reverse=True)

FLAIR_OPENERS = [
    "Hark! ", "Verily, ", "Forsooth, ", "By my troth, ",
    "Prithee, ", "Mark me well, ", "Hold, sirrah! ", ""
]

CLOSERS = [
    ", upon mine honor.", ", i' faith.", ", as heaven wills.",
    ", mark my words.", ", by the rood.", ""
]

MODAL_AUXILIARIES = {"didst", "wilt", "shalt", "canst", "couldst", "wouldst", "hast", "art", "dost"}

# ---------------------------------------------------------
# GRAMMAR AND SYNTAX ENGINE
# ---------------------------------------------------------
def match_case(original: str, replacement: str) -> str:
    """Matches the capitalization of the original word."""
    if original.isupper():
        return replacement.upper()
    elif original and original[0].isupper():
        return replacement.capitalize()
    return replacement

def pre_process_grammar(text: str) -> str:
    """Handles deep structural changes before dictionary mapping."""
    # Negation shift: "do not <verb>" -> "<verb> not"
    text = re.sub(r"(?i)\b(?:do not|don't)\s+([a-zA-Z]+)\b", r"\1 not", text)
    # Question inversion: "do you <verb>" -> "<verb> thou"
    text = re.sub(r"(?i)\b(?:do you|d'you)\s+([a-z]+)\b", r"\1 thou", text)
    return text

def apply_pos_grammar(text: str) -> str:
    """Uses NLTK part-of-speech tags for accurate conjugation and pronouns."""
    tokens = word_tokenize(text)
    tagged = pos_tag(tokens)
    
    transformed = []
    has_modal_aux = any(w.lower() in MODAL_AUXILIARIES for w in tokens)
    
    for i, (word, tag) in enumerate(tagged):
        lower = word.lower()
        prev_tag = tagged[i-1][1] if i > 0 else ""
        prev_word = tokens[i-1].lower() if i > 0 else ""
        
        # Rule 1: Contextual 'you' routing (Thou vs Thee)
        if lower == "you":
            # If 'you' follows a preposition (IN) or a verb (VB/VBD/VBP/VBZ), it is the object ('thee')
            if prev_tag == "IN" or prev_tag.startswith("VB"):
                word = match_case(word, "thee")
            else:
                word = match_case(word, "thou")
            lower = word.lower() 

        # Rule 2: Conjugate verbs following 'thou' (avoiding double conjugation)
        if prev_word == "thou" and tag in ["VB", "VBP", "NN"] and not has_modal_aux:
            if lower not in ["be", "have", "do", "shall", "will", "art", "hast", "dost"]:
                if lower.endswith("e"):
                    word = word + "st"
                else:
                    word = word + "est"
        
        # Rule 3: Conjugate 3rd-person singular present verbs
        elif tag == "VBZ" and lower not in ["is", "has", "does", "'s"]:
            base = lower[:-1]
            if base.endswith("i"):
                base = base[:-1] + "y"
            word = base + "eth"
                
        transformed.append(word)

    # Reconstruct text spacing cleanly
    result = " ".join(transformed)
    result = re.sub(r'\s+([,?.!:\'"])', r'\1', result)
    result = re.sub(r'([\'"])\s+', r'\1', result)
    return result

def extract_discord_entities(text: str):
    placeholders = {}
    def stash(match):
        token = f"__DISC_TOK_{len(placeholders)}__"
        placeholders[token] = match.group(0)
        return token
    clean_text = re.sub(r"<[@#&!a-zA-Z0-9_:]+>|https?://\S+", stash, text)
    return clean_text, placeholders

def restore_discord_entities(text: str, placeholders: dict) -> str:
    for token, original in placeholders.items():
        text = text.replace(token, original)
    return text

def translate_to_shakespearean(text: str) -> str:
    text, placeholders = extract_discord_entities(text)

    # 1. Structural inversions and negations
    text = pre_process_grammar(text)

    # 2. Dictionary substitutions with case matching
    for pattern in SORTED_PATTERNS:
        replacement = DICTIONARY[pattern]
        if "\\" in replacement or "$" in replacement:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        else:
            text = re.sub(pattern, lambda m, r=replacement: match_case(m.group(0), r), text, flags=re.IGNORECASE)

    # 3. Linguistic part-of-speech grammar and pronoun routing
    try:
        text = apply_pos_grammar(text)
    except Exception as e:
        print(f"Grammar tagging error: {e}")

    text = restore_discord_entities(text, placeholders)

    prefix = random.choice(FLAIR_OPENERS)
    suffix = random.choice(CLOSERS)
    return f"{prefix}{text}{suffix}".strip()

# ---------------------------------------------------------
# BOT COMMANDS
# ---------------------------------------------------------
async def get_or_create_webhook(channel: discord.TextChannel) -> discord.Webhook:
    webhooks = await channel.webhooks()
    for wh in webhooks:
        if wh.user == bot.user:
            return wh
    return await channel.create_webhook(name="BardImpersonator")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("Advanced Grammar Bard is active!")

@bot.command(name="s")
async def bard_prefix(ctx: commands.Context, *, message: str):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

    translated = translate_to_shakespearean(message)
    webhook = await get_or_create_webhook(ctx.channel)
    await webhook.send(
        content=translated,
        username=ctx.author.display_name,
        avatar_url=ctx.author.display_avatar.url,
    )

@bot.tree.command(name="bard", description="Speak modern words, delivered as the Bard.")
async def bard_slash(interaction: discord.Interaction, message: str):
    await interaction.response.defer(ephemeral=True)
    translated = translate_to_shakespearean(message)
    webhook = await get_or_create_webhook(interaction.channel)

    await webhook.send(
        content=translated,
        username=interaction.user.display_name,
        avatar_url=interaction.user.display_avatar.url,
    )
    await interaction.followup.send("Delivered anon!", ephemeral=True)


@bot.event
async def on_message(message: discord.Message):
    # 1. Ignore messages from bots and webhooks to prevent infinite translation loops
    if message.author.bot or message.webhook_id:
        return

    # 2. If the message is in your designated auto-translate channel
    if message.channel.id == TARGET_CHANNEL_ID:
        try:
            await message.delete()
        except discord.Forbidden:
            print("Missing permissions to delete messages in this channel.")

        translated = translate_to_shakespearean(message.content)
        webhook = await get_or_create_webhook(message.channel)

        await webhook.send(
            content=translated,
            username=message.author.display_name,
            avatar_url=message.author.display_avatar.url,
        )
        return  # Stop processing here so it doesn't trigger commands twice

    # 3. Ensure prefix commands (!s) still work normally in OTHER channels
    await bot.process_commands(message)
    
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
