import interactions
import asyncio
import os
import datetime
import pickledb
import uuid
import sys
import signal

# Load the bot token from environment variables
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Load or create a PickleDB database to store persistent data
db = pickledb.load('db/pickle.db', True)

# Initialize the bot with default intents and MESSAGE_CONTENT to capture messages
bot = interactions.Client(intents=interactions.Intents.DEFAULT | interactions.Intents.MESSAGE_CONTENT)

# Dictionary to map specific bot IDs to bot names for easy identification
bot_ids = {
    "302050872383242240": "Disboard",
    "1222548162741538938": "Discadia",
    "493224032167002123": "DS.me",
    "835255643157168168": "Unfocused"
}

# Event listener for when the bot becomes online and is ready
@interactions.listen()
async def on_ready():    
    print("Setting up status and activity...")
    # Set the bot's presence (status and activity)
    await bot.change_presence(
        status=interactions.Status.ONLINE,
        activity=interactions.Activity(
            name="for bumps and boops!",
            type=interactions.ActivityType.WATCHING
        )
    )

    print("Checking for active reminders...")

    # Retrieve the role to mention for reminders
    role = db.get('role')
    if not role:
        print("No role has been set up for reminders.")
        return
    
    # Check and reschedule reminders if there are active timers when the bot starts
    for key in ['disboard', 'dsme', 'unfocused']:
        if db.get(f"{key}_reminder_state"):
            scheduled_time = db.get(f"{key}_reminder_scheduled_time")
            reminder_id = db.get(f"{key}_reminder_id")
            if scheduled_time and reminder_id:
                scheduled_time = datetime.datetime.fromisoformat(scheduled_time)
                # Calculate the remaining time until the reminder should be sent
                remaining_time = scheduled_time - datetime.datetime.now()
                if remaining_time > datetime.timedelta(seconds=0):
                    # Reschedule the reminder if time remains
                    print(f"Rescheduling reminder {reminder_id} for {key.title()}.")
                    if key == 'disboard' or key == 'discadia' or key == 'dsme':
                        asyncio.create_task(send_scheduled_message(
                            initial_message=None,
                            reminder_message=f"<@&{role}> It's time to bump on {key.title()}!",
                            interval=remaining_time.total_seconds(),
                            key=key
                        ))
                    else:
                        asyncio.create_task(send_scheduled_message(
                            initial_message=None,
                            reminder_message=f"<@&{role}> It's time to boop on {key.title()}!",
                            interval=remaining_time.total_seconds(),
                            key=key
                        ))
    print("Active reminders have been checked and rescheduled.")
    print("I am online and ready!")


# Event listener to handle message creation (whenever a new message is sent)
@interactions.listen()
async def on_message_create(event: interactions.api.events.MessageCreate):
    bot_id = str(event.message.author.id)
    message_content = event.message.content
    
    # Check if the message is from one of the specific bots (Disboard, Discadia, DS.me, or Unfocused)
    if bot_id in bot_ids:
        bot_name = bot_ids[bot_id]
        print(f"Detected message from {bot_name}.")
    
    # If the message contains an embed, check for specific text to trigger reminders
    if event.message.embeds and len(event.message.embeds) > 0:
        embed = event.message.embeds[0]
        embed_description = embed.description
        if embed_description and "Bump done" in embed_description:
            await disboard()
        elif embed_description and "Your vote streak for this server" in embed_description:
            await dsme()
    else:
        # Look for specific keywords in plain message content
        if "Your server has been booped" in message_content:
            await unfocused()
        elif "has been successfully bumped" in message_content:
            await discadia()

# Function to send scheduled reminder messages after a delay
async def send_scheduled_message(initial_message: str, reminder_message: str, interval: int, key: str):
    # Retrieve the channel where reminders should be sent
    saved_channel = db.get('channel')
    if not saved_channel:
        print("No channel has been set up for reminders.")
        return
    channel = bot.get_channel(saved_channel)
    
    # Send the initial message, if provided
    print(f"Sending initial message: {initial_message}")
    if initial_message:
        await channel.send(initial_message)
    
    # Wait for the specified interval (in seconds)
    await asyncio.sleep(interval)
    
    # Send the reminder message after the delay
    print(f"Sending reminder message: {reminder_message}")
    await channel.send(reminder_message)
    
    # Clean up the reminder from the database after it has been sent
    reminder_id = db.get(f"{key}_reminder_id")
    if reminder_id:
        db.rem(f"{key}_reminder_state")
        db.rem(f"{key}_reminder_scheduled_time")
        db.rem(f"{key}_reminder_id")
        db.dump()

# Function to handle setting up and managing reminders for different services
async def handle_reminder(key: str, initial_message: str, reminder_message: str, interval: int):
    # Check if a reminder is already set for this service
    if db.get(f"{key}_reminder_state"):
        print(f"{key.capitalize()} already has a timer set for a reminder.")
        return

    # Generate a unique ID for this reminder
    reminder_id = str(uuid.uuid4())

    # Store reminder state and timing info in the database
    db.set(f"{key}_reminder_state", True)
    db.set(f"{key}_reminder_scheduled_time", (datetime.datetime.now() + datetime.timedelta(seconds=interval)).isoformat())
    db.set(f"{key}_reminder_id", reminder_id)
    db.dump()
    
    # Retrieve the role to mention for reminders
    role = db.get('role')
    if not role:
        print("No role has been set up for reminders.")
        return
    
    # Send the initial and scheduled reminder message
    await send_scheduled_message(
        initial_message,
        f"<@&{role}> {reminder_message}",
        interval,
        key
    )

# Reminder function for Disboard bot
async def disboard():
    await handle_reminder(
        key='disboard',
        initial_message="Thanks for bumping!",
        reminder_message="It's time to bump on Disboard!",
        interval=2*60*60  # 2-hour interval
    )

# Reminder function for Discadia bot
async def discadia():
    await handle_reminder(
        key='discadia',
        initial_message="Thanks for bumping!",
        reminder_message="It's time to bump on Discadia!",
        interval=24*60*60  # 24-hour interval
    )

# Reminder function for DS.me bot
async def dsme():
    await handle_reminder(
        key='dsme',
        initial_message="Thanks for bumping!",
        reminder_message="It's time to bump on DS.me!",
        interval=2*60*60  # 2-hour interval
    )

# Reminder function for Unfocused bot
async def unfocused():
    await handle_reminder(
        key='unfocused',
        initial_message="Thanks for booping!",
        reminder_message="It's time to boop on Unfocused!",
        interval=2*60*60  # 2-hour interval
    )

# Slash command to set up the bot
@interactions.slash_command(name="setup", description="Setup the role for reminders")
@interactions.slash_option(
    name="channel",
    description="Channel",
    required=True,
    opt_type=interactions.OptionType.CHANNEL
)
@interactions.slash_option(
    name="role",
    description="Role",
    required=True,
    opt_type=interactions.OptionType.ROLE
)
async def setup(ctx: interactions.ComponentContext, channel, role: interactions.Role):
    print(f'Setup requested by {ctx.author.username}.')
    channel_id = channel.id
    role_id = role.id
    print(f"Nova will use <#{channel_id}> and the role <@&{role_id}>!")
    db.set('channel', channel_id)
    db.set('role', role_id)
    db.dump()
    await ctx.send(f"Nova will use <#{channel_id}> and the role <@&{role_id}>!")

# Slash command to check the current status of reminders
@interactions.slash_command(name="status", description="Check the current status of reminders")
async def check_status(ctx: interactions.SlashContext):
    print(f'Status check requested by {ctx.author.username}.')
    channel_id = db.get('channel')

    role = db.get('role')
    role_name = f"<@&{role}>" if role else "Not set!"

    disboard_scheduled_time = db.get('disboard_reminder_scheduled_time')
    disboard_remaining_time = calculate_remaining_time(disboard_scheduled_time)

    discadia_scheduled_time = db.get('discadia_reminder_scheduled_time')
    discadia_remaining_time = calculate_remaining_time(discadia_scheduled_time)

    dsme_scheduled_time = db.get('dsme_reminder_scheduled_time')
    dsme_remaining_time = calculate_remaining_time(dsme_scheduled_time)

    unfocused_scheduled_time = db.get('unfocused_reminder_scheduled_time')
    unfocused_remaining_time = calculate_remaining_time(unfocused_scheduled_time)

    # Send the status message with current reminder info
    await ctx.send(f"**Reminder Status:**\n"
                   f"Channel: <#{channel_id}>\n"
                   f"Role: {role_name}\n"
                   f"Disboard: {disboard_remaining_time}\n"
                   f"Discadia: {discadia_remaining_time}\n"
                   f"DS.me: {dsme_remaining_time}\n"
                   f"Unfocused: {unfocused_remaining_time}")

# Helper function to calculate remaining time from the scheduled time
def calculate_remaining_time(scheduled_time):
    if scheduled_time:
        try:
            scheduled_time = datetime.datetime.fromisoformat(scheduled_time)
            current_time = datetime.datetime.now()
            remaining_time = scheduled_time - current_time

            if remaining_time > datetime.timedelta(seconds=0):
                # Extract hours, minutes, and seconds
                total_seconds = int(remaining_time.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                return f"{hours:02}:{minutes:02}:{seconds:02}"
            else:
                return "Expired!"
        except ValueError:
            return "Invalid time format!"
    return "Not set!"

# Slash command to send a test reminder message
@interactions.slash_command(name="testmessage", description="Send a test message")
async def test_reminders(ctx: interactions.SlashContext):
    role = db.get('role')
    if not role:
        await ctx.send("No role has been set up for reminders.")
        return
    print(f'Test message requested by {ctx.author.username}.')
    await ctx.send(f"<@&{role}> This is a test message!")

# Slash command to maintain developer tag
@interactions.slash_command(name="dev", description="Maintain developer tag")
async def dev(ctx: interactions.SlashContext):
    print(f'Developer tag maintenance requested by {ctx.author.username}.')
    await ctx.send("Developer tag maintained!")

# Slash command to send the GitHub link for the project
@interactions.slash_command(name="github", description="Send link to the GitHub project for this bot")
async def github(ctx: interactions.SlashContext):
    print(f'Github link requested by {ctx.author.username}.')
    await ctx.send("https://github.com/doubleangels/Nova")

# Function to handle bot shutdown on SIGINT
def handle_interrupt(signal, frame):
    db.dump()
    sys.exit(0)

# Register the signal handler for SIGINT
signal.signal(signal.SIGINT, handle_interrupt)

# Start the bot using the provided token
bot.start(TOKEN)
