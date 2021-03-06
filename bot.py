# -*- coding: utf-8 -*-
import urllib.request
import json
import re
import config
import time
import datetime
import codecs
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool

import discord
import asyncio



# инициализируемся
client = discord.Client()
chat_ids = []
ids = open('ids', 'r')
ids_arr = ids.read().split(',')
for i in ids_arr:
	if len(i) > 1:
		print(i)
		chat_ids.append(int(i))
ids.close()
pool = ThreadPool(4)

@client.event
@asyncio.coroutine
def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)
	print('------')

@client.event
@asyncio.coroutine
def on_message(message):
	# парсим /start и подписываем новые ид на раздачу новостей
	if message.content.startswith('!start'):
		yield from client.send_message(message.channel, config.greeting)
		print(str(message.channel.id) + " !start")

		if not message.channel.id in chat_ids:
			# если исполнившего команду нет в списке - записываем
			# в файл и добпаляем в массив
			with open('ids', 'a') as ids:
				ids.write(str(message.channel.id) + ",")
			chat_ids.append(message.channel.id)

		print(chat_ids)


# получаем пост с заданым сдвигом
def get_post(number=1):
	news_off = number

	cooked = []
	a = urllib.request.urlopen(
		'https://api.vk.com/method/wall.get?owner_id=-' + str(config.group_id) + '&filter=owner&count=1&offset=' + str(
			news_off))

	out = a.read().decode('utf-8')
	json_data = json.loads(out)
	# получаем сырой текст
	text = json_data['response'][1]["text"]
	id_from_id = str(json_data['response'][1]["from_id"]) + "_" + str(json_data['response'][1]["id"])
	# убираем html требуху
	text = text.replace('<br>', '\n')
	text = text.replace('&amp', '&')
	text = text.replace('&quot', '"')
	text = text.replace('&apos', "'")
	text = text.replace('&gt', '>')
	text = text.replace('&lt', '<')

	# если встречается ссылка на профиль
	profile_to_replace = re.findall(r'\[(.*?)\]', text)
	profile_link = re.findall(r'\[(.*?)\|', text)
	profile_name = re.findall(r'\|(.*?)\]', text)
	profiles = []

	# заменаем ссылку на профиль в тексте
	try:
		for i in range(len(profile_link)):
			profiles.append(profile_name[i] + " (@" + profile_link[i] + ")")
		counter = 0
		for i in profile_to_replace:
			text = text.replace("[" + i + "]", profiles[counter])
			counter += 1
	except:
		pass

	text += u"\n\nКомментарии: http://vk.com/wall" + id_from_id
	cooked.append(text)
	cooked.append(json_data['response'][1]["date"])

	# на случай встречи с медиафайлами (пока что реализованы фото и тамб к видео)
	try:
		media = json_data['response'][1]["attachments"]

		media_arr = []
		for i in media:
			if "photo" in i:
				media_arr.append(i["photo"]["src_xbig"])
			if "video" in i:
				media_arr.append("http://vk.com/video" + i["video"]["owner_id"] + "_" + i["video"]["vid"])
			if "doc" in i:
				media_arr.append(i["doc"]["url"])
		cooked.append(media_arr)
	except:
		pass
	return cooked


# проверяем новые посты
@asyncio.coroutine
def checker():
	yield from client.wait_until_ready()
	if len(chat_ids) < 1:
		return
	with open('timestamp', 'r') as t:
		timestamp = int(t.read())
	while not client.is_closed:
		print('checking... ' + str(datetime.datetime.now()))
		last_posts = 1
		end = False
		# проверяем новые новости по таймстампу и получаем количество новых
		while not end:
			post = get_post(last_posts)
			if post[1] > timestamp:
				last_posts += 1
			else:
				last = get_post()
				timestamp = last[1]
				with open('timestamp', 'w') as t:
					t.write(str(timestamp))
				end = True

		print('found ' + str(last_posts - 1) + ' new posts!')

		# рассылаем каждому нужное кол-во новых постов
		if last_posts > 1:
			for post_c in range(last_posts - 1):
				post = get_post(last_posts - 1 - post_c)
				text_to_send = post[0]
			photo_to_send = []
			if len(post) > 2:
				for i in post[2]:
					photo_to_send.append(i)
			for id_ in chat_ids:
				try:
					yield from client.send_message(client.get_channel(str(id_)), text_to_send)
					if photo_to_send:
						for i in photo_to_send:
							yield from client.send_message(client.get_channel(str(id_)), str(i))
								#yield from client.send_file(client.get_channel(str(id_)), str(i))

				except:
					pass
		# спим 1 минут
		yield from asyncio.sleep(1 * 60)

client.loop.create_task(checker())
client.run(config.token)