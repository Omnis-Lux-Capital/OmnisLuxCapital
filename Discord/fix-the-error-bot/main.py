import discord
from discord.ext import commands
import random
import json
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

# XP tiers
tiers = {
    "user": 5,
    "dev": 10,
    "hacker": 15
}

roles = {
    "user": "User",
    "dev": "Dev",
    "hacker": "Hacker"
}

challenges = {}
user_xp = {}
XP_FILE = "xp_store.json"

# Load XP from file
if os.path.exists(XP_FILE):
    with open(XP_FILE, "r") as f:
        user_xp = json.load(f)

# Load code snippets from JSON
def load_snippets(language, difficulty):
    path = f"snippets/{language}_{difficulty}.json"
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

# Save XP
def save_xp():
    with open(XP_FILE, "w") as f:
        json.dump(user_xp, f, indent=2)

# Assign XP-based role
async def assign_role(member, xp):
    tier = None
    if xp >= 301:
        tier = "Hacker"
    elif xp >= 151:
        tier = "Dev"
    else:
        tier = "User"

    role = discord.utils.get(member.guild.roles, name=tier)
    if role:
        await member.add_roles(role)
        for r in roles.values():
            if r != tier:
                old = discord.utils.get(member.guild.roles, name=r)
                if old and old in member.roles:
                    await member.remove_roles(old)

@bot.event
async def on_ready():
    print(f'Bot is live as {bot.user}')

@bot.command(name='challenge')
async def challenge(ctx, language: str, difficulty: str):
    snippets = load_snippets(language, difficulty)
    if not snippets:
        await ctx.send("No snippets found for that language/difficulty.")
        return

    snippet = random.choice(snippets)
    user_id = str(ctx.author.id)
    challenges[user_id] = {
        "fix": snippet["fix"],
        "attempts": 0,
        "difficulty": difficulty,
        "max_xp": tiers[difficulty]
    }

    await ctx.send(
        f"Fix this ({language}, {difficulty}):\n```{snippet['buggy']}```\n"
        "Type your corrected code directly in this channel. Or type `/showanswer` if you give up."
    )

@bot.command(name='showanswer')
async def show_answer(ctx):
    user_id = str(ctx.author.id)
    if user_id not in challenges:
        await ctx.send("You don't have an active challenge.")
        return

    answer = challenges[user_id]["fix"]
    await ctx.send(f"The correct fix was:\n```{answer}```\nYou earned 0 XP.")
    del challenges[user_id]

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    if not user_xp:
        await ctx.send("No data yet.")
        return

    sorted_xp = sorted(user_xp.items(), key=lambda x: x[1], reverse=True)
    top_3 = sorted_xp[:3]
    msg = "**Top 3 Leaderboard:**\n"
    for i, (uid, xp) in enumerate(top_3, 1):
        user = await bot.fetch_user(int(uid))
        msg += f"{i}. {user.name} — {xp} XP\n"

    await ctx.send(msg)

@bot.command(name='myrank')
async def myrank(ctx):
    user_id = str(ctx.author.id)
    if user_id not in user_xp:
        await ctx.send("You're not ranked yet.")
        return

    sorted_xp = sorted(user_xp.items(), key=lambda x: x[1], reverse=True)
    rank = [uid for uid, _ in sorted_xp].index(user_id) + 1
    xp = user_xp[user_id]

    if xp >= 301:
        tier = "Hacker"
    elif xp >= 151:
        tier = "Dev"
    else:
        tier = "User"

    await ctx.send(
        f"**Your Rank:**\n- Rank: #{rank} out of {len(sorted_xp)} users\n- XP: {xp}\n- Tier: {tier}"
    )

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_id = str(message.author.id)
    if user_id in challenges:
        user_attempt = message.content.strip()
        challenge = challenges[user_id]
        challenge["attempts"] += 1
        correct = challenge["fix"].strip()

        if user_attempt == correct:
            tries = challenge["attempts"]
            earned = max(challenge["max_xp"] - (tries - 1), 0)

            user_xp[user_id] = user_xp.get(user_id, 0) + earned
            await message.channel.send(f"✅ Correct! You earned {earned} XP.")

            await assign_role(message.author, user_xp[user_id])
            save_xp()
            del challenges[user_id]
        else:
            if user_xp.get(user_id, 0) > 0:
                user_xp[user_id] = max(user_xp[user_id] - 1, 0)
                save_xp()
            await message.channel.send("❌ Incorrect! Try again.")

    await bot.process_commands(message)

bot.run(TOKEN)