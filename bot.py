import nextcord
import os
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
from nextcord.ui import Button, Select, View, Modal
from pymongo import MongoClient
from keep_alive import keep_alive

intents = nextcord.Intents.default()
intents.message_content = True
bot = commands.Bot(intents=intents, help_command=None)

MONGO_URI = "mongodb+srv://admin:K6njQSA7mtHSI0C4@pixie.98du4.mongodb.net/?retryWrites=true&w=majority&appName=pixie"
BOT_TOKEN = os.getenv("BOT_TOKEN")

client = MongoClient(MONGO_URI)
db = client["application_bot"]
applications_collection = db["applications"]
panels_collection = db["panels"]

OWNER_ID = "1236579599119548426"

def is_owner(interaction: Interaction):
    return str(interaction.user.id) == OWNER_ID

@bot.slash_command(name="application", description="Manage applications")
async def application(interaction: Interaction):
    pass

@application.subcommand(name="create", description="Create a new application question")
async def application_create(interaction: Interaction, question: str = SlashOption(description="Enter the application question")):
    if not is_owner(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    app_id = applications_collection.insert_one({"question": question}).inserted_id
    await interaction.response.send_message(f"Application created with ID `{app_id}` and question: `{question}`", ephemeral=True)

@application.subcommand(name="edit", description="Edit an existing application")
async def application_edit(interaction: Interaction, application_id: str = SlashOption(description="Enter the application ID to edit"), new_question: str = SlashOption(description="Enter the new application question")):
    if not is_owner(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    result = applications_collection.update_one({"_id": application_id}, {"$set": {"question": new_question}})
    if result.modified_count > 0:
        await interaction.response.send_message(f"Application ID `{application_id}` updated to `{new_question}`.", ephemeral=True)
    else:
        await interaction.response.send_message("Application ID not found or no changes made.", ephemeral=True)

@application.subcommand(name="delete", description="Delete an application")
async def application_delete(interaction: Interaction, application_id: str = SlashOption(description="Enter the application ID to delete")):
    if not is_owner(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    result = applications_collection.delete_one({"_id": application_id})
    if result.deleted_count > 0:
        await interaction.response.send_message(f"Application ID `{application_id}` has been deleted.", ephemeral=True)
    else:
        await interaction.response.send_message("Application ID not found.", ephemeral=True)

# Panel commands
@bot.slash_command(name="panel", description="Manage application panels")
async def panel(interaction: Interaction):
    pass

@panel.subcommand(name="create", description="Create or update an application panel")
async def panel_create(interaction: Interaction, panel_name: str = SlashOption(description="Enter the name of the panel"), applications: str = SlashOption(description="Enter application IDs (comma-separated) to include in the panel")):
    if not is_owner(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    application_ids = [app_id.strip() for app_id in applications.split(",")]
    valid_ids = applications_collection.find({"_id": {"$in": application_ids}})
    if len(application_ids) != valid_ids.count():
        await interaction.response.send_message("One or more application IDs are invalid.", ephemeral=True)
        return
    panels_collection.update_one({"name": panel_name}, {"$set": {"applications": application_ids}}, upsert=True)
    await interaction.response.send_message(f"Panel `{panel_name}` created/updated with applications: {', '.join(application_ids)}", ephemeral=True)

@panel.subcommand(name="send", description="Send an application panel")
async def panel_send(interaction: Interaction, panel_name: str = SlashOption(description="Enter the panel name"), channel: nextcord.TextChannel = SlashOption(description="Select the channel")):
    if not is_owner(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    panel = panels_collection.find_one({"name": panel_name})
    if not panel:
        await interaction.response.send_message(f"Panel `{panel_name}` does not exist.", ephemeral=True)
        return
    application_ids = panel.get("applications", [])
    applications = applications_collection.find({"_id": {"$in": application_ids}})
    if not applications:
        await interaction.response.send_message(f"No valid applications found for panel `{panel_name}`.", ephemeral=True)
        return

    options = [nextcord.SelectOption(label=f"Application {i+1}", description=app["question"], value=str(app["_id"])) for i, app in enumerate(applications)]
    embed = nextcord.Embed(title=f"Application Panel: {panel_name}", description="Select an application.", color=0x00FF00)
    view = ApplicationDropdownView(options, channel)
    await channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"Panel `{panel_name}` sent to {channel.mention}.", ephemeral=True)

class ApplicationDropdown(nextcord.ui.Select):
    def __init__(self, options, channel):
        super().__init__(placeholder="Select an application...", options=options)
        self.channel = channel

    async def callback(self, interaction: Interaction):
        selected_id = self.values[0]
        application = applications_collection.find_one({"_id": selected_id})
        if application:
            modal = AcceptDeclineModal(application["question"], self.channel)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("Application not found.", ephemeral=True)

class ApplicationDropdownView(nextcord.ui.View):
    def __init__(self, options, channel):
        super().__init__()
        self.add_item(ApplicationDropdown(options, channel))

class AcceptDeclineModal(nextcord.ui.Modal):
    def __init__(self, question, channel):
        super().__init__(title="Application Response")
        self.channel = channel
        self.question = question
        self.add_item(nextcord.ui.TextInput(label="Response", placeholder="Type your response here... (optional)", required=False))

    async def callback(self, interaction: Interaction):
        decision = "Accepted" if interaction.user else "Declined"
        response = self.children[0].value
        embed = nextcord.Embed(title=f"Application {decision}", description=f"Response: {response}" if response else "No response provided.", color=0x00FF00 if decision == "Accepted" else 0xFF0000)
        await self.channel.send(embed=embed)
        await interaction.response.send_message("Response submitted.", ephemeral=True)

bot.run(BOT_TOKEN)
