#coding:utf-8
import urllib
import urllib.request
import http.cookiejar
import json
import time
import os
import sys
import datetime
import time
import service.AssMaker
#import Config
import _thread
import random
import service.GetInfo
import numpy

config = json.load(open('./Config.json', encoding='utf-8'))
path = config['path']
roomid = config['danmu']['roomid']
cookie = config['danmu']['cookie']
csrf_token = config['danmu']['token']
download_api_url = config['musicapi']

dm_lock = False		 #弹幕发送锁，用来排队
encode_lock = False	 #视频渲染锁，用来排队

sensitive_word = ('64', '89') #容易误伤的和谐词汇表，待补充

#用于删除文件，防止报错
def del_file(f):
	try:
		print('delete'+path+'/resource/playlist/'+f)
		os.remove(path+'/resource/playlist/'+f)
	except:
		print('delete error')

#用于删除文件，防止报错
def del_file_default_mp3(f):
	try:
		print('delete'+path+'/resource/music/'+f)
		os.remove(path+'/resource/music/'+f)
	except:
		print('delete error')

#检查已使用空间是否超过设置大小
def check_free():
	files = os.listdir(path+'/resource/playlist')  #获取下载文件夹下所有文件
	size = 0
	for f in files:		  #遍历所有文件
		size += os.path.getsize(path+'/resource/playlist/'+f)  #累加大小
	files = os.listdir(path+'/resource/music')#获取缓存文件夹下所有文件
	for f in files:		 #遍历所有文件
		size += os.path.getsize(path+'/resource/music/'+f)#累加大小
	if(size > int(config['freespace'])*1024*1024):  #判断是否超过设定大小
		print("space size:"+str(size))
		return True
	else:
		return False

#检查已使用空间，并在超过时，自动删除缓存的视频
def clean_files():
	is_boom = True  #用来判断可用空间是否爆炸
	if(check_free()):  #检查已用空间是否超过设置大小
		files = os.listdir(path+'/resource/music') #获取下载文件夹下所有文件
		files.sort()	#排序文件，以便按日期删除多余文件
		for f in files:
			if((f.find('.flv') != -1) & (check_free())):	#检查可用空间是否依旧超过设置大小，flv文件
				del_file_default_mp3(f)   #删除文件
			elif((f.find('.mp3') != -1) & (check_free())):	#检查可用空间是否依旧超过设置大小，mp3文件
				del_file_default_mp3(f)   #删除文件
				del_file_default_mp3(f.replace(".mp3",'')+'.ass')
				del_file_default_mp3(f.replace(".mp3",'')+'.info')
			elif(check_free() == False):	#符合空间大小占用设置时，停止删除操作
				is_boom = False
	else:
		is_boom = False
	return is_boom


#下载歌曲，传入参数：
#s：数值型，传入歌曲/mv的id
#t：type，类型，mv或id
#user：字符串型，点播者
#song：歌名，点播时用的关键字，可选
def get_download_url(s, t, user, song = "nothing"):
	if(clean_files()):  #检查空间是否在设定值以内，并自动删除多余视频缓存
		send_dm_long('Server存储空间已爆炸，请联系up')
		return
	if bool(int(config['gift'])) and check_coin(user, 100) == False:
		send_dm_long('用户'+user+'赠送的瓜子不够点歌哦,还差'+str(100-get_coin(user))+'瓜子的礼物')
		return
	send_dm_long('正在下载ID'+str(s))
	print('[log]getting url:ID'+str(s))
	try:
		filename = str(time.mktime(datetime.datetime.now().timetuple()))	#获取时间戳，用来当作文件名
		urllib.request.urlretrieve(urllib.request.urlopen(download_api_url + "?%s" % urllib.parse.urlencode({'id': s}),timeout=5).read().decode('utf-8'), path+'/resource/playlist/'+filename+'.mp3') #下载歌曲 "http://music.163.com/song/media/outer/url?id="+str(s)+".mp3"
		
		lyric = urllib.request.urlopen(download_api_url + "?%s" % urllib.parse.urlencode({'lyric': s}),timeout=5).read().decode('utf-8')  #设定获取歌词的网址

		tlyric = urllib.request.urlopen(download_api_url + "?%s" % urllib.parse.urlencode({'tlyric': s}),timeout=5).read().decode('utf-8')  #设定获取歌词的网址

		name_w = urllib.request.urlopen(download_api_url + "?%s" % urllib.parse.urlencode({'name': s}),timeout=5).read().decode('utf-8')  #设定获取歌词的网址

		if(song == "nothing"):  #当直接用id点歌时
			service.AssMaker.make_ass(filename,'歌曲网易云ID：'+str(s)+'\\N歌曲名：'+str(name)+"\\N点播人："+user,path,lyric,tlyric)  #生成字幕
			service.AssMaker.make_info(filename,'ID：'+str(s)+',名称：'+str(name)+",点播人："+user,path)	#生成介绍信息，用来查询
		else:   #当用关键字搜索点歌时
			service.AssMaker.make_ass(filename,'歌曲网易云ID：'+str(s)+'\\N歌曲名：'+str(name)+"\\N点播关键词："+song+"\\N点播人："+user,path,lyric,tlyric)   #生成字幕
			service.AssMaker.make_info(filename,'ID：'+str(s)+',名称：'+str(name)+",关键词："+song+",点播人："+user,path)	#生成介绍信息，用来查询
		send_dm_long('ID'+str(s)+'下载完成，已加入播放队列')
		print('[log]已添加排队项目：ID'+str(s))

		try:	#记录日志，已接近废弃
			log_file = open(path+'/log/Downloads.log', 'a')
			log_file.writelines(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())) + ','+user+','+t+str(s)+'\r\n')
			log_file.close()
		except:
			print('[error]log error')
	except: #下载出错
		send_dm_long('出错了：请检查命令或重试')
		if bool(int(config['gift'])):   #归还用掉的瓜子
			give_coin(user,100)
		print('[log]下载文件出错：ID'+str(s))
		del_file(filename+'.mp3')

#下载歌单
def playlist_download(id,user):
	params = urllib.parse.urlencode({'playlist': str(id)}) #格式化参数
	f = urllib.request.urlopen(download_api_url + "?%s" % params,timeout=3)   #设定获取的网址
	try:
		playlist = json.loads(f.read().decode('utf-8'))  #获取结果，并反序化
		if len(playlist['playlist']['tracks'])*100 > get_coin(user) and bool(int(config['gift'])):
			send_dm_long('用户'+user+'赠送的瓜子不够点'+str(len(playlist['playlist']['tracks']))+
			'首歌哦,还差'+str(len(playlist['playlist']['tracks'])*100-get_coin(user))+'瓜子的礼物')
			return
		else:
			send_dm_long('正在下载歌单：'+playlist['playlist']['name']+'，共'+str(len(playlist['playlist']['tracks']))+'首')
	except Exception as e:  #防炸
		print('shit')
		print(e)
		send_dm_long('出错了：请检查命令或重试')
	for song in playlist['playlist']['tracks']:
		print('name:'+song['name']+'id:'+str(song['id']))
		get_download_url(song['id'], 'id', user, song['name'])

#搜索歌曲并下载
def search_song(s,user):
	print('[log]searching song:'+s)
	params = urllib.parse.urlencode({'type': 1, 's': s})	#格式化参数
	f = urllib.request.urlopen("http://s.music.163.com/search/get/?%s" % params,timeout=3)	#设置接口网址
	search_result = json.loads(f.read().decode('utf-8'))	#获取结果
	result_id = search_result["result"]["songs"][0]["id"]   #提取歌曲id
	_thread.start_new_thread(get_download_url, (result_id, 'id', user,s))   #扔到下载那里下载

#获取赠送过的瓜子数量
def get_coin(user):
	gift_count = 0
	try:
		gift_count = numpy.load('../resource/users/'+user+'.npy')
	except:
		gift_count = 0
	return gift_count

#扣除赠送过的瓜子数量
def take_coin(user, take_sum):
	gift_count = 0
	try:
		gift_count = numpy.load('../resource/users/'+user+'.npy')
	except:
		gift_count = 0
	gift_count = gift_count - take_sum
	try:
		numpy.save('../resource/users/'+user+'.npy', gift_count)
	except:
		print('create error')

#检查并扣除指定数量的瓜子
def check_coin(user, take_sum):
	if get_coin(user) >= take_sum:
		take_coin(user, take_sum)
		return True
	else:
		return False

#给予赠送过的瓜子数量
def give_coin(user, give_sum):
	gift_count = 0
	try:
		gift_count = numpy.load('../resource/users/'+user+'.npy')
	except:
		gift_count = 0
	gift_count = gift_count + give_sum
	try:
		numpy.save('../resource/users/'+user+'.npy', gift_count)
	except:
		print('create error')

def check_night():
	print(time.localtime()[3])
	if (time.localtime()[3] <= 5) and config['nightvideo']['use']: #time.localtime()[3] >= 23 or 
		send_dm_long('现在是晚间专场哦~命令无效')
		return True

#切歌请求次数统计
jump_to_next_counter = 0
rp_lock = False
def pick_msg(s, user):
	global jump_to_next_counter #切歌请求次数统计
	global encode_lock  #视频渲染任务锁
	global rp_lock
	if ((user=='FH云彩')):	#debug使用，请自己修改
		if(s=='锁定'):
			rp_lock = True
			send_dm_long('已锁定点播功能，不响应任何弹幕')
		if(s=='解锁'):
			rp_lock = False
			send_dm_long('已解锁点播功能，开始响应弹幕请求')
	if((user == '因缺思厅233333') | rp_lock):  #防止自循环
		return
	#下面的不作解释，很简单一看就懂
	if (s.find('id+') == 0):
		if check_night():
			return
		send_dm_long('已收到'+user+'的指令')
		s = s.replace(' ', '')   #剔除弹幕中的所有空格
		_thread.start_new_thread(get_download_url, (s.replace('id+', '', 1), 'id',user))
	elif (s.find('song+') == 0):
		if check_night():
			return
		try:
			send_dm_long('已收到'+user+'的指令')
			search_song(s.replace('song+', '', 1),user)
		except:
			print('[log]song not found')
			send_dm_long('出错了：没这首歌')
	elif (s.find('id') == 0):
		if check_night():
			return
		send_dm_long('已收到'+user+'的指令')
		s = s.replace(' ', '')   #剔除弹幕中的所有空格
		_thread.start_new_thread(get_download_url, (s.replace('id', '', 1), 'id',user))
	elif (s.find('song') == 0):
		if check_night():
			return
		try:
			send_dm_long('已收到'+user+'的指令')
			search_song(s.replace('song', '', 1),user)
		except:
			print('[log]song not found')
			send_dm_long('出错了：没这首歌')
	elif (s.find('点歌') == 0):
		if check_night():
			return
		try:
			send_dm_long('已收到'+user+'的指令')
			search_song(s.replace('点歌', '', 1),user)
		except:
			print('[log]song not found')
			send_dm_long('出错了：没这首歌')
	elif (s.find('喵') > -1):
		replay = ["喵？？", "喵喵！", "喵。。喵？", "喵喵喵~", "喵！"]
		send_dm_long(replay[random.randint(0, len(replay)-1)])  #用于测试是否崩掉
	elif (s == '切歌'):   #切歌请求
		jump_to_next_counter += 1   #切歌次数统计加一
		if((user=='FH云彩')): #debug使用，请自己修改
			jump_to_next_counter=5
		if(jump_to_next_counter < 5):   #次数未达到五次
			send_dm_long('已收到'+str(jump_to_next_counter)+'次切歌请求，达到五次将切歌')
		else:   #次数未达到五次
			jump_to_next_counter = 0	#次数统计清零
			send_dm_long('已执行切歌动作')
			os.system('killall ffmpeg') #强行结束ffmpeg进程
	elif ((s == '点播列表') or (s == '歌曲列表') or (s == '列表')):
		if check_night():
			return
		send_dm_long('已收到'+user+'的指令，正在查询')
		files = os.listdir(path+'/resource/playlist')   #获取目录下所有文件
		files.sort()	#按文件名（下载时间）排序
		songs_count = 0 #项目数量
		all_the_text = ""
		for f in files:
			if((f.find('.mp3') != -1) and (f.find('.download') == -1)): #如果是mp3文件
				try:
					info_file = open(path+'/resource/playlist/'+f.replace(".mp3",'')+'.info', 'r')  #读取相应的info文件
					all_the_text = info_file.read()
					info_file.close()
				except Exception as e:
					print(e)
				if(songs_count < 10):
					send_dm_long(all_the_text)
				songs_count += 1
		if(songs_count <= 10):
			send_dm_long('点播列表展示完毕，一共'+str(songs_count)+'个')
		else:
			send_dm_long('点播列表前十个展示完毕，一共'+str(songs_count)+'个')
	elif (s.find('歌单') == 0):
		if check_night():
			return
		send_dm_long('已收到'+user+'的指令')
		s = s.replace(' ', '')   #剔除弹幕中的所有空格
		_thread.start_new_thread(playlist_download, (s.replace('歌单', '', 1),user))
	elif (s.find('查询') == 0):
		send_dm_long(user+'的瓜子余额还剩'+str(get_coin(user))+'个')
	# else:
	#	 print('not match anything')





#发送弹幕函数，通过post完成，具体可以自行使用浏览器，进入审查元素，监控network选项卡研究
def send_dm(s):
	global cookie
	global roomid
	global dm_lock
	global csrf_token
	while (dm_lock):
		#print('[log]wait for send dm')
		time.sleep(1)
	dm_lock = True
	try:
		url = "https://api.live.bilibili.com/msg/send"
		postdata =urllib.parse.urlencode({	
		'color':'16777215',
		'fontsize':'25',
		'mode':'1',
		'msg':s,
		'rnd':'1510756027',
		'roomid':roomid,
		'csrf_token':csrf_token
		}).encode('utf-8')
		header = {
		"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
		"Accept-Encoding":"utf-8",
		"Accept-Language":"zh-cn,zh;q=0.8,en-us;q=0.5,en;q=0.3",
		"Connection":"keep-alive",
		"Cookie":cookie,
		"Host":"api.live.bilibili.com",
		"Referer":"http://live.bilibili.com/"+roomid,
		"User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64; rv:32.0) Gecko/20100101 Firefox/32.0"
		}
		req = urllib.request.Request(url,postdata,header)
		dm_result = json.loads(urllib.request.urlopen(req,timeout=3).read().decode('utf-8'))
		if len(dm_result['msg']) > 0:
			print('[error]弹幕发送失败：'+s)
			print(dm_result)
		else:
			print('[log]发送弹幕：'+s)
	except:
		print('[error]send dm error')
	time.sleep(1.5)
	dm_lock = False
	
#每条弹幕最长只能发送20字符，过长的弹幕分段发送
def send_dm_long(s):
	n=int(config['danmu']['size'])
	for hx in sensitive_word:				  #处理和谐词，防止点播机的回复被和谐
		if (s.find(hx) > -1):
			s = s.replace(hx, hx[0]+"-"+hx[1:])	#在和谐词第一个字符后加上一个空格
	for i in range(0, len(s), n):
		send_dm(s[i:i+n])

#获取原始弹幕数组
#本函数不作注释，具体也请自己通过浏览器审查元素研究
def get_dm():
	global temp_dm
	global roomid
	global csrf_token
	url = "http://api.live.bilibili.com/ajax/msg"
	postdata =urllib.parse.urlencode({	
	'token:':'',
	'csrf_token:':csrf_token,
	'roomid':roomid
	}).encode('utf-8')
	header = {
	"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
	"Accept-Encoding":"utf-8",
	"Accept-Language":"zh-cn,zh;q=0.8,en-us;q=0.5,en;q=0.3",
	"Connection":"keep-alive",
	"Host":"api.live.bilibili.com",
	"Referer":"http://live.bilibili.com/"+roomid,
	"User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64; rv:32.0) Gecko/20100101 Firefox/32.0"
	}
	req = urllib.request.Request(url,postdata,header)
	dm_result = json.loads(urllib.request.urlopen(req,timeout=1).read().decode('utf-8'))
	#for t_get in dm_result['data']['room']:
		#print('[log]['+t_get['timeline']+']'+t_get['nickname']+':'+t_get['text'])
	return dm_result

#检查某弹幕是否与前一次获取的弹幕数组有重复
def check_dm(dm):
	global temp_dm
	for t_get in temp_dm['data']['room']:
		if((t_get['text'] == dm['text']) & (t_get['timeline'] == dm['timeline'])):
			return False
	return True

#弹幕获取函数，原理为不断循环获取指定直播间的初始弹幕，并剔除前一次已经获取到的弹幕，余下的即为新弹幕
def get_dm_loop():
	global temp_dm
	temp_dm = get_dm()
	while True:
		dm_result = get_dm()
		for t_get in dm_result['data']['room']:
			if(check_dm(t_get)):
				print('[log]['+t_get['timeline']+']'+t_get['nickname']+':'+t_get['text'])
				#send_dm('用户'+t_get['nickname']+'发送了'+t_get['text']) #别开，会死循环
				text = t_get['text']
				pick_msg(text,t_get['nickname'])   #新弹幕检测是否匹配为命令
		temp_dm = dm_result
		time.sleep(1)

def test():
	print('ok')

print('程序已启动，连接房间id：'+roomid)
# send_dm_long('弹幕监控已启动，可以点歌了')
# while True: #防炸
#	 try:
#		 get_dm_loop()   #开启弹幕获取循环函数
#	 except Exception as e:  #防炸
#		 print('shit')
#		 print(e)
#		 dm_lock = False #解开弹幕锁，以免因炸了而导致弹幕锁没解开，进而导致一直锁着发不出弹幕
