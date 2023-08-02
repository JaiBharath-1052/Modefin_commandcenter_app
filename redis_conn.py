from rejson import Client, Path


CHANNEL_LAYERS = {
    "default": {
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
            # "hosts": [("192.168.145.75", 6379)],
        },
    },
}

def RedisClient():
	try: 
		layer = 'default'
		uri = CHANNEL_LAYERS.get(layer).get("CONFIG").get('hosts')[0]
		host = uri[0]
		port = uri[1]
		RC = Client(host=host, port=port, decode_responses=True)
		return RC
	except Exception as e:
		print(f"Couldn't connect to redis server ({host}:{port}) \n {e}")
		return None

RC = RedisClient()
jp = RC.pipeline()
print(dir(jp))
jp.jsonset('VisitorTalkTo', Path('.'), {})
print(RC.jsonget('visitorTalkto'))
