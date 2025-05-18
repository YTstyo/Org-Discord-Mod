import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import re
from datetime import datetime, timedelta
import sqlite3

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

conn = sqlite3.connect('bot_db.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS guild_settings
             (guild_id INTEGER PRIMARY KEY, log_channel INTEGER, admin_role INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS scam_domains
             (domain TEXT PRIMARY KEY)''')
c.execute('''CREATE TABLE IF NOT EXISTS user_warnings
             (user_id INTEGER, guild_id INTEGER, warnings INTEGER, last_warning TIMESTAMP)''')
conn.commit()

SECURITY_CONFIG = {
    "MAX_MENTIONS": 5,
    "SPAM_INTERVAL": 10,
    "MAX_MESSAGES": 5,
    "SCAM_DOMAIN_FILE": "scam_domains.txt",
    "MAX_CAPS_RATIO": 0.6,
    "AUTO_MOD_ACTIONS": {
        "spam": "mute",
        "scam": "ban",
        "mass_mention": "warn",
        "excessive_caps": "warn"
    }
}

class SecuritySystem:
    def __init__(self):
        self.message_history = {}
        self.scam_domains = set()
        self.load_scam_domains()
    
    def load_scam_domains(self):
        try:
            with open(SECURITY_CONFIG["SCAM_DOMAIN_FILE"], "r") as f:
                self.scam_domains = set(line.strip().lower() for line in f if line.strip())
        except FileNotFoundError:
            self.scam_domains = set()
    
    def add_scam_domain(self, domain):
        domain = domain.lower()
        if domain not in self.scam_domains:
            self.scam_domains.add(domain)
            with open(SECURITY_CONFIG["SCAM_DOMAIN_FILE"], "a") as f:
                f.write(f"{domain}\n")
    
    def is_scam_link(self, content):
        regex = r"(https?:\/\/[^\s]+)"
        urls = re.findall(regex, content)
        for url in urls:
            domain_match = re.search(r"(?:https?:\/\/)?(?:www\.)?([^\/]+)", url)
            if domain_match:
                domain = domain_match.group(1).lower()
                if domain in self.scam_domains:
                    return True
        return False
    
    def is_spam(self, message):
        user_id = message.author.id
        current_time = datetime.now()
        
        if user_id not in self.message_history:
            self.message_history[user_id] = []
        
        self.message_history[user_id] = [
            msg_time for msg_time in self.message_history[user_id]
            if current_time - msg_time < timedelta(seconds=SECURITY_CONFIG["SPAM_INTERVAL"])
        ]
        
        self.message_history[user_id].append(current_time)
        
        return len(self.message_history[user_id]) > SECURITY_CONFIG["MAX_MESSAGES"]

security = SecuritySystem()

def admin_role_required():
    async def predicate(interaction: discord.Interaction):
        c.execute('SELECT admin_role FROM guild_settings WHERE guild_id = ?', (interaction.guild.id,))
        result = c.fetchone()
        if not result or not result[0]:
            return False
        role = interaction.guild.get_role(result[0])
        return role in interaction.user.roles
    return app_commands.check(predicate)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="for suspicious activity"))
    await bot.tree.sync()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    violation_type = await check_message_security(message)
    if violation_type:
        await handle_security_violation(message, violation_type)
        return

    await bot.process_commands(message)

async def check_message_security(message):
    if security.is_spam(message):
        return "spam"
    if security.is_scam_link(message.content):
        return "scam"
    if len(message.mentions) > SECURITY_CONFIG["MAX_MENTIONS"]:
        return "mass_mention"
    if len(message.content) > 0:
        caps_count = sum(1 for c in message.content if c.isupper())
        if caps_count / len(message.content) > SECURITY_CONFIG["MAX_CAPS_RATIO"]:
            return "excessive_caps"
    return None

async def handle_security_violation(message, violation_type):
    try:
        await message.delete()
    except: pass
    
    action = SECURITY_CONFIG["AUTO_MOD_ACTIONS"].get(violation_type, "warn")
    
    c.execute('''INSERT INTO user_warnings (user_id, guild_id, warnings, last_warning)
                 VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                 ON CONFLICT(user_id) DO UPDATE SET
                 warnings = warnings + 1, last_warning = CURRENT_TIMESTAMP''',
              (message.author.id, message.guild.id))
    conn.commit()
    
    try:
        if action == "mute":
            muted_role = await get_or_create_muted_role(message.guild)
            await message.author.add_roles(muted_role)
            await asyncio.sleep(900)
            await message.author.remove_roles(muted_role)
        elif action == "ban":
            await message.author.ban(reason=f"Automatic ban: {violation_type} violation")
    except: pass
    
    await log_mod_action(message, violation_type, action)

async def get_or_create_muted_role(guild):
    muted_role = discord.utils.get(guild.roles, name="Muted")
    if not muted_role:
        muted_role = await guild.create_role(name="Muted")
        for channel in guild.channels:
            await channel.set_permissions(muted_role, send_messages=False, add_reactions=False)
    return muted_role

async def log_mod_action(message, violation_type, action):
    log_channel = get_log_channel(message.guild.id)
    if log_channel:
        embed = discord.Embed(title="Security Alert", color=0xff0000)
        embed.add_field(name="User", value=f"{message.author.mention} ({message.author.id})")
        embed.add_field(name="Violation", value=violation_type.capitalize())
        embed.add_field(name="Action", value=action.capitalize())
        embed.add_field(name="Content", value=message.content[:1000], inline=False)
        await log_channel.send(embed=embed)

def get_log_channel(guild_id):
    c.execute('SELECT log_channel FROM guild_settings WHERE guild_id = ?', (guild_id,))
    result = c.fetchone()
    return bot.get_channel(result[0]) if result else None

@bot.tree.command(name="setup", description="Set up moderation system")
@app_commands.describe(log_channel="Channel for moderation logs", admin_role="Admin role for bot commands")
@app_commands.default_permissions(administrator=True)
async def setup(interaction: discord.Interaction, log_channel: discord.TextChannel, admin_role: discord.Role):
    c.execute('''INSERT INTO guild_settings (guild_id, log_channel, admin_role)
                 VALUES (?, ?, ?)
                 ON CONFLICT(guild_id) DO UPDATE SET
                 log_channel = ?, admin_role = ?''',
              (interaction.guild.id, log_channel.id, admin_role.id,
               log_channel.id, admin_role.id))
    conn.commit()
    await interaction.response.send_message(
        f"Setup complete! Log channel: {log_channel.mention}, Admin role: {admin_role.mention}",
        ephemeral=True
    )

@bot.tree.command(name="report", description="Report a suspicious message")
@app_commands.describe(message_id="ID of the message to report", reason="Reason for reporting")
async def report(interaction: discord.Interaction, message_id: str, reason: str):
    try:
        message = await interaction.channel.fetch_message(int(message_id))
    except:
        await interaction.response.send_message("Message not found!", ephemeral=True)
        return
    
    log_channel = get_log_channel(interaction.guild.id)
    if log_channel:
        embed = discord.Embed(title="User Report", color=0xffa500)
        embed.add_field(name="Reporter", value=interaction.user.mention)
        embed.add_field(name="Reported User", value=message.author.mention)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Message Content", value=message.content, inline=False)
        await log_channel.send(embed=embed)
        await interaction.response.send_message("Report submitted successfully!", ephemeral=True)
    else:
        await interaction.response.send_message("No log channel set up!", ephemeral=True)

@bot.tree.command(name="addscam", description="Add domain to blocklist")
@app_commands.describe(domain="Domain to block")
@admin_role_required()
async def addscam(interaction: discord.Interaction, domain: str):
    security.add_scam_domain(domain)
    await interaction.response.send_message(f"Added {domain} to scam blocklist", ephemeral=True)

@bot.tree.command(name="removescam", description="Remove domain from blocklist")
@app_commands.describe(domain="Domain to unblock")
@admin_role_required()
async def removescam(interaction: discord.Interaction, domain: str):
    domain = domain.lower()
    if domain in security.scam_domains:
        security.scam_domains.remove(domain)
        with open(SECURITY_CONFIG["SCAM_DOMAIN_FILE"], "w") as f:
            f.write("\n".join(security.scam_domains))
        await interaction.response.send_message(f"Removed {domain} from blocklist", ephemeral=True)
    else:
        await interaction.response.send_message("Domain not found in blocklist", ephemeral=True)

if __name__ == "__main__":
    bot.run("BOTTOKEN")