from tickets import proccess_mods, proccess_tickets
from tickets import OnInit, OnMemberJoin
import discord
from discord.ext import commands
from discord.utils import get
import sqlite3
import tracemalloc
from random import random

# IMPORTANT TOOLS

con = sqlite3.connect('server.db')
cursor = con.cursor()

tracemalloc.start()
intents = discord.Intents.all()

client = commands.Bot(command_prefix='+', intents = intents)
client.remove_command("help")

@client.event
async def on_raw_reaction_add(payload):
	await proccess_mods(payload)
	await proccess_tickets(payload)

@client.event
async def on_member_join(member):
	await OnMemberJoin(member)

@client.event
async def on_ready():
	OnInit()
	await client.change_presence(status=discord.Status.idle,activity=discord.Game("Twisters are cool"))
	print ("bot is now online")

# ECONOMY

@client.command(aliases = ['balance', 'cash'])
async def __balance(ctx, member: discord.Member = None):
  if member is None:
    await ctx.send(embed = discord.Embed(
      description = f"""Баланс пользователя **{ctx.author}** составляет **{cursor.execute("SELECT cash FROM users WHERE id = {}".format(ctx.author.id)).fetchone()[0]} монет **"""
      ))
  else:
    await ctx.send(embed = discord.Embed(
      description = f"""Баланс пользователя **{member}** составляет **{cursor.execute("SELECT cash FROM users WHERE id = {}".format(member.id)).fetchone()[0]} монет **"""
      ))

@client.command(aliases = ['leaderboard', 'lb'])
async def __leaderboard(ctx):
	amount = ctx.message.content[4:]
	embed = discord.Embed(title = 'Топ 10 сервера')
	counter = 0
	for row in cursor.execute("SELECT name, cash FROM users ORDER BY cash DESC LIMIT 10"):
	  counter += 1
	  embed.add_field(
	  	name = f'#{counter} | `{row[0][2:]}`',
	  	value = f'Баланс: {row[1]}',
	  	inline = False
	  )
	await ctx.send(embed = embed)

@client.command(aliases = ['award'])
@commands.has_permissions(administrator = True)
async def __award(ctx, member: discord.Member = None, amount: int = None):
  if member is None:
    await ctx.send(embed = discord.Embed(
      description = f"Укажите пользователя"
      ))
  else:
    if amount is None:
      await ctx.send(embed = discord.Embed(
      description = f"Укажите сумму"
      ))
    elif amount < 1:
      await ctx.send(embed = discord.Embed(
      description = f"Сумма не может быть меньше 1"
      ))
    else:
      cursor.execute("UPDATE users SET cash = cash + {} WHERE id = {}".format(amount, member.id))
      con.commit()
      await ctx.send(embed = discord.Embed(
      description = f"К балансу пользователя **{member}** добавлено **{amount}** монет"
      ))

@client.command(aliases = ['pay'])
async def __pay(ctx, member: discord.Member = None, amount: int = None):
  if member is None:
    await ctx.send(embed = discord.Embed(
      description = f"Укажите пользователя"
      ))
  else:
    if amount is None:
      await ctx.send(embed = discord.Embed(
      description = f"Укажите сумму"
      ))
    elif amount < 1:
      await ctx.send(embed = discord.Embed(
      description = f"Сумма не может быть меньше 1"
      ))
    elif member.id == ctx.author.id:
      await ctx.send(embed = discord.Embed(
      description = f"Вы не можете отправить деньги самому себе"
      ))
    else:
      if cursor.execute("SELECT cash FROM users WHERE id = {}".format(ctx.message.author.id)).fetchone()[0] < amount :
        await ctx.send(embed = discord.Embed(
        description = f"У вас недостаточно средств"
        ))
      else:
        cursor.execute("UPDATE users SET cash = cash + {} WHERE id = {}".format(amount, member.id))
        cursor.execute("UPDATE users SET cash = cash - {} WHERE id = {}".format(amount, ctx.author.id))
        con.commit()
        await ctx.send(embed = discord.Embed(
        description = f"Успешно переведено **{amount}** монет"
        ))

@client.command(aliases = ['subtract', 'subt'])
@commands.has_permissions(administrator = True)
async def __subtract(ctx, member: discord.Member = None, amount: int = None):
  if member is None:
    await ctx.send(embed = discord.Embed(
      description = f"Укажите пользователя"
      ))
  else:
    if amount is None:
      await ctx.send(embed = discord.Embed(
      description = f"Укажите сумму"
      ))
    elif amount < 1:
      await ctx.send(embed = discord.Embed(
      description = f"Сумма не может быть меньше 1"
      ))
    else:
      cursor.execute("UPDATE users SET cash = cash - {} WHERE id = {}".format(amount, member.id))
      con.commit()
      await ctx.send(embed = discord.Embed(
      description = f"Из баланса пользователя **{member}** вычтено **{amount}** монет"
      ))

@client.command(aliases = ['clear', 'purge'])
async def __clear(ctx, amount = 5):
	await ctx.channel.purge(limit=amount+1)