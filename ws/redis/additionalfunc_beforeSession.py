from rejson import Client, Path
from dotenv import load_dotenv
from redis.exceptions import ResponseError
# import redis
import pickle
import timeit
import json
import time
import os

load_dotenv()

# Get Redis Client
def RedisClient():
	host = os.getenv('REDISHOST')
	port = os.getenv('REDISPORT')
	password = os.getenv('REDISPASS')
	try: 
		RC = Client(host=host, port=port, decode_responses=True, password=password)
		return RC
	except Exception as e:
		print(f"Couldn't connect to Redis Server \n {e}")
		return None

# 
# def RC:
# 	pass
# Check if the basic jsons exists in Redis
# - Agent List (Active & Inactive)
# - Agent login details json (24 hours) For total hour worked
def CheckJSON():
	jsonneeded = ["loginactivity", "visitorTalkto"]

	try:
		RC = RedisClient()
		for reqjson in jsonneeded:
			rj_json = RC.jsonget(reqjson)
			if rj_json is None:
				RC.jsonset(reqjson, Path.rootPath(), {})
			else:
				pass
	except Exception as e:
		print(f"Couldn't connect to Redis Server \n {e}")

CheckJSON()


# Maintaining agent activities
# Login
# Logout
# Availability
class agentactivities:
	def __init__(self, layer = 'default'):
		self.RC = RedisClient()

	# async def addjson(self, jsonname, jsonobj, path = Path.rootPath()):
	def addjson(self, jsonname, jsonobj, path = Path.rootPath()):
		try:
			res = self.RC.jsonset(jsonname, path, jsonobj)
			return res
		except Exception as e:
			return str(e)

	# async def getjson(self, jsonname, path='.'):
	def getjson(self, jsonname, path='.'):
		try:
			jsonobj = self.RC.jsonget(jsonname, Path(path))
			return jsonobj
		except Exception as e:
			return str(e)
	
	# Retrieving available agents
	# - add total chats
	def get_agent(self):
		# TODO: Update agent json
		availableAgent = {
						'agentAvailable': True,
						'agentDetails': {
							'id': 'bhavana4339gmailcom',
							'name': 'Bhavana',
							'photo': 'data:image/jpeg;base64,/9j/4AAQSkZJRgABA'
							}
						}
		#else: availableAgent = {'agentAvailable': False}
		return availableAgent
		availableAgent = self.getjson("available_agent") # Create a list name available_agent (Update using ranking)
		availableAgent = availableAgent.pop()
		if availableAgent is None:
			return {"Available": Fals}
		# Increment the chat
		# Send the agents to front end
		# Insert the new stats for the agent (means the new allocated chat)
		# Run the ranking
		return {"Available": False, "Agent" : allocate_agent}

	# Updating the 
	async def ranking(self, agentname):
		# Rank the available agents
		pass

	# async def login(self, agentname):
	def login(self, agentname):
		# Run when websocket is connected
		# - Check if the agent json exists if not addit
		# - If exist, the agent should be in active json
		agentjson = {"clients":[]}
		try:
			self.RC.jsondel(RedisJSONName, Path(f'.inactive.{agentname}'))
			self.RC.jsonset(RedisJSONName, Path(f'.active.{agentname}'), agent)
		except:
			# Logit
			return False

	# async def logout(self, agentname):
	def logout(self, agentname):
		# Run when websocket is disconnected
		try:
			self.RC.jsondel(RedisJSONName, Path(f'.active.{agentname}'))
			self.RC.jsonset(RedisJSONName, Path(f'.inactive.{agentname}'), agent)
		except:
			pass


	# async def switch_availability(self, agentname, status = False):
	def switch_availability(self, agentname, to_status = False):
		RedisJSONName = 'agents' 
		if to_status: # True means turn from inactive to active
			agents = self.getjson(RedisJSONName) # Full JSON
			agent = agents.get('inactive').get(agentname, None)
			print(f"AGENT: {agent}")
			if agent is None:
				# print("JSON unavailable")
				return False
			self.RC.jsonset(RedisJSONName, Path(f'.active.{agentname}'), agent)
			self.RC.jsondel(RedisJSONName, Path(f'.inactive.{agentname}'))
			return True
		else:
			agents = self.getjson(RedisJSONName) # Full JSON
			agent = agents.get('active').get(agentname, None)
			print(f"AGENT: {agent}")
			if agent is None:
				# print("JSON unavailable")
				return False
			self.RC.jsonset(RedisJSONName, Path(f'.inactive.{agentname}'), agent)
			self.RC.jsondel(RedisJSONName, Path(f'.active.{agentname}'))
			return True


	# Maintaining last talkto & until when
	# Status of last message
	# Status of last connect
	def visitorTalkto(self, visitorID):
		RedisJSONName = 'visitorTalkto' 
		visitor = self.getjson(RedisJSONName).get(visitorID, None)
		newlasttime = int(time.time())
		welcomeMessage = True
		if visitor:
			lasttime = visitor.get('lasttime', None)
			if (lasttime + 1800) > newlasttime: # 1800 (seconds i.e 30 mins) can come from DB 
				talkto = visitor.get('talkto', None)
				welcomeMessage = False
			else:
				talkto = "bot"
				jsonobj = {"lasttime": newlasttime, "talkto":talkto, "agent":None}
				self.RC.jsonset(RedisJSONName, Path(f'{visitorID}'), jsonobj)
			
			return ({"talkto": talkto, "welcomeMessage": welcomeMessage})
		else:
			jsonobj = {"lasttime": newlasttime, "talkto":"bot", "agent":None}
			self.RC.jsonset(RedisJSONName, Path(f'.{visitorID}'), jsonobj)
			return ({"talkto": "bot", "welcomeMessage": welcomeMessage})

	def updateVisitorLasttime(self, visitorID):
		RedisJSONName = 'visitorTalkto'
		newlasttime = int(time.time())
		try:
			self.RC.jsonset(RedisJSONName, Path(f'.{visitorID}.lasttime'), newlasttime)
		except Exception as e:
			print(f"REDIS Some Issue: {e}")
	
	def updateVisitorAgent(self, visitorID, agentID):
		RedisJSONName = 'visitorTalkto'
		try:
			self.RC.jsonset(RedisJSONName, Path(f'.{visitorID}.talkto'), "agent")
			self.RC.jsonset(RedisJSONName, Path(f'.{visitorID}.agent'), agentID)
		except Exception as e:
			print(f"REDIS Some Issue: {e}")
	
	def getLastAgent(self, visitorID):
		RedisJSONName = 'visitorTalkto'
		try:
			allocatedAgent = self.RC.jsonget(RedisJSONName, Path(f'.{visitorID}.agent'))
			return allocatedAgent
		except Exception as e:
			print(f"REDIS Some Issue: {e}")

# class ConversationManager:
# 	RC = RedisClient()
# 	agentWSJSON = 'agentsWS'
# 	visitorsWSJSON = 'visitorsWS'
	
# 	def addWS(self, mid, ws, wstype):
# 		ws = pickle.dumps(ws)
# 		if wstype == 'agent':
# 			try:
# 				mid='Kunal'
# 				agentsWS = self.RC.jsonget(self.agentWSJSON, Path(f'.{mid}.WS'))
# 				agentsWS.append(ws)
# 				self.RC.jsonset(self.agentWSJSON, Path(f'.{mid}.WS'), agentsWS)
# 			except ResponseError:	
# 				self.RC.jsonset(self.agentWSJSON, Path(f'.{mid}'), {'WS':[ws]})
# 			except Exception as e:
# 				print(f"Error: {e}")
# 		else:
# 			visitorsWS = self.RC.jsonget(self.visitorsWSJSON, Path(f'.WS'))

# 	def removeWS(self, mid, ws, wstype):
# 		if wstype == 'agent':
# 			agentsWS = self.RC.jsonget(self.agentWSJSON, Path(f'.{mid}.WS'))
# 			agentsWS = [json.loads(wsadd) for wsadd in agentsWS]
# 			# ws = json.dumps(ws)
# 			if True: #(ws in agentsWS):
# 				print("came here")
# 				try:
# 					agentsWS.remove(ws)
# 					self.RC.jsonset(self.agentWSJSON, Path(f'.{mid}.WS'), agentsWS)
# 				except Exception as e:
# 					print(f"Agent: No WS to remove {e}")
# 			else:
# 				print(type(agentsWS))
# 				print(agentsWS)
# 				print(type(ws))
# 				print(ws)

# 		else:
# 			visitorsWS = self.RC.jsonget(self.visitorsWSJSON, Path(f'.{mid}.WS'))

# ll = ConversationManager()
# mid = 'Kunal'
# # ws = pickle.dumps("MyStriung")
# ws = json.dumps("MyStriung")
# # ll.addWS(mid, ws,'agent')
# ll.removeWS(mid, ws,'agent')