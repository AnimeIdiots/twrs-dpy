import discord
from discord.ext import commands
from discord.utils import get
import asyncio
from bot import client
from bot import cursor
from bot import con
import config

global g_guild
global g_channel
global g_adminchannel
global g_message
global g_emoji

async def OnMemberJoin(member):
	if cursor.execute(f"SELECT id FROM users WHERE id = {member.id}").fetchone() is None:
		cursor.execute(f"INSERT INTO users VALUES ('n_{member.name}{member.discriminator}', {member.id}, 0)")	
	con.commit()

async def OnInit():
	global g_guild
	global g_channel
	global g_adminchannel
	global g_message
	global g_emoji
	
	# basic info

	g_guild = client.get_guild(config.guild_id)
	g_channel = g_guild.get_channel(config.channel_id)
	g_adminchannel = g_guild.get_channel(config.adminchannel_id)
	g_message = g_channel.get_partial_message(config.message_id)
	g_emoji = config.emoji

	# users table

	cursor.execute("""CREATE TABLE IF NOT EXISTS users (
		name TEXT,
		id INT,
		cash BIGINT
		) """)
	for member in g_guild.members:
		if cursor.execute(f"SELECT id FROM users WHERE id = {member.id}").fetchone() is None:
			cursor.execute(f"INSERT INTO users VALUES ('n_{member.name}{member.discriminator}', {member.id}, 0)")
	
	cursor.execute("""CREATE TABLE IF NOT EXISTS tickets (
		id_reporter INT,
		id_mod INT,
		message_id INT,
		channel_id INT
		) """)

	cursor.execute("""CREATE TABLE IF NOT EXISTS mods (
		id INT,
		rep INT
		) """)
	
	con.commit()

	await g_message.clear_reactions()
	await g_message.add_reaction(g_emoji)

async def proccess_tickets(payload):
	if(payload.message_id != g_message.id):
		return
	if(payload.member == client.user):
		return
	if(str(payload.emoji) != (g_emoji)):
		await g_message.remove_reaction(payload.emoji, payload.member)
		return
	if cursor.execute(f"SELECT id_reporter FROM tickets WHERE id_reporter = {payload.member.id}").fetchone() is None:
		pass
	else:
		await payload.member.send("You already have active ticket!")
		await g_message.remove_reaction(payload.emoji, payload.member)
		return
	message = await g_adminchannel.send(f"{payload.member.mention} created ticket!")
	await message.add_reaction(g_emoji)
	cursor.execute(f"INSERT INTO tickets VALUES ({payload.member.id}, 0, {message.id}, 0)")
	await payload.member.send("Ticket created, please wait!")
	await g_message.remove_reaction(payload.emoji, payload.member)
	con.commit()

async def proccess_mods(payload):

	mmember = payload.member

	if(payload.member == client.user):
		return
	if(str(payload.emoji) != (g_emoji)):
		await g_adminchannel.get_partial_message(payload.message_id).remove_reaction(payload.emoji, payload.member)
		return
	if(payload.channel_id != g_adminchannel.id):
		return

	if cursor.execute(f"SELECT id_mod FROM tickets WHERE message_id = {payload.message_id}") is None:
		await payload.member.send("Ticket already been closed!")
		await g_adminchannel.get_partial_message(payload.message_id).delete()
		return

	reporter_id = cursor.execute(f"SELECT id_reporter FROM tickets WHERE message_id = {payload.message_id}").fetchone()[0]
	reporter = g_guild.get_member(int(reporter_id))
	if(reporter == None):
		print("blya.....")
		return
	overwrites = {
		g_guild.default_role: discord.PermissionOverwrite(read_messages=False),
		g_guild.me: discord.PermissionOverwrite(read_messages=True),
	}

	cat = await g_guild.create_category(f"ticket_{int(random()*100000)}", overwrites=overwrites)
	chan = await cat.create_text_channel("chat", overwrites=overwrites)
	await chan.set_permissions(reporter, read_messages=True)
	await chan.set_permissions(mmember, read_messages=True)
	cursor.execute(f"UPDATE tickets SET id_mod = {mmember.id} WHERE message_id = {payload.message_id}"); con.commit()
	cursor.execute(f"UPDATE tickets SET channel_id = {chan.id} WHERE message_id = {payload.message_id}"); con.commit()
	await chan.send(f"Заявка: {g_guild.get_member(reporter_id).mention}\nПринял: {payload.member.mention}\n\nНе забудьте в конце поблагодарить хелпера коммандой +rep")

	
@client.command(aliases = ['rep'])
async def __rep(ctx):
	if(cursor.execute(f"SELECT id_reporter FROM tickets WHERE channel_id = {ctx.message.channel.id}").fetchone()[0] == 0):
		return
	chan = g_guild.get_channel(cursor.execute(f"SELECT channel_id FROM tickets WHERE id_reporter = {ctx.author.id}").fetchone()[0])
	msg = g_adminchannel.get_partial_message(cursor.execute(f"SELECT message_id FROM tickets WHERE id_reporter = {ctx.author.id}").fetchone()[0])
	await chan.send("Спасибо за оценку!")
	await asyncio.sleep(3)
	await chan.delete()
	await chan.category.delete()
	await msg.delete()
	if(cursor.execute(f"SELECT rep FROM mods WHERE id = {cursor.execute(f'SELECT id_mod FROM tickets WHERE id_reporter = {ctx.author.id}').fetchone()[0]}").fetchone() == None):
		cursor.execute(f"INSERT INTO mods VALUES ({cursor.execute(f'SELECT id_mod FROM tickets WHERE id_reporter = {ctx.author.id}').fetchone()[0]}, 1)")
	else:
		cursor.execute(f"UPDATE mods SET rep = rep + 1 WHERE id = {cursor.execute(f'SELECT id_mod FROM tickets WHERE id_reporter = {ctx.author.id}').fetchone()[0]}")
	cursor.execute(f"DELETE FROM tickets WHERE id_reporter = {ctx.author.id}"); con.commit()
@client.command(aliases = ['me_mod'])
async def __memod(ctx):
	if(cursor.execute(f"SELECT rep FROM mods WHERE id = {ctx.author.id}").fetchone() == None):
		return
	await ctx.send(f"У вас {cursor.execute(f'SELECT rep FROM mods WHERE id = {ctx.author.id}').fetchone()[0]} репутация")

@client.command(pass_context = True)
async def help(ctx, arg = None):
	if arg == 'economy':
		embed1 = discord.Embed(title='Economy help menu', description = '"%" is a prefix', colour = discord.Color.dark_gold())
		embed1.set_footer(text = 'Request by {}'.format(ctx.author.name), icon_url = ctx.author.avatar_url)
		embed1.add_field(name="balance *nick* *amount*", value = 'Displays balance', inline=True)
		embed1.add_field(name="pay *nick* *amount*", value = 'Transfer money to smbd', inline=True)
		embed1.add_field(name="leaderboard", value = 'Displays top 10 richest players', inline=True)
		embed1.add_field(name="For admins:", value = 'requires admin perms', inline=False)
		embed1.add_field(name="award *nick* *amount*", value = 'Add money to someone\'s balance (Admin only)', inline=True)
		embed1.add_field(name="subtract *nick* *amount*", value = 'Subtracts money from someone\'s balance (Admin only)', inline=True)
		await ctx.send(embed = embed1)
	else:
		embed = discord.Embed(title='Help menu', description = '"+" is a prefix', colour = discord.Color.dark_gold())
		embed.set_footer(text = 'Request by {}'.format(ctx.author.name), icon_url = ctx.author.avatar_url)
		embed.add_field(name="help ", value = 'Displays this message', inline=True)
		embed.add_field(name="help *economy*", value = 'Displays econonomy commands help', inline=True)
		embed.add_field(name="For admins:", value = 'requires admin perms', inline=False)
		embed.add_field(name="clear *amount*", value = 'clear last `amount` messages (as default 5)', inline=True)
		await ctx.send(embed = embed)
