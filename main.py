import makubot
import threading
import time
import conf
import imp
from conf import *

def main():
	bot = makubot.bot
	#tokenTuple = (makubotToken,)
	#Trailing comma so that it treats the string as one element
	#botThread = threading.Thread(target=bot.run,args=tokenTuple)
	#botThread.daemon = True
	while(True):
		bot.run(makubotToken)
		imp.reload(makubot)
	#botThread.start()
	# while True:
		# if bot.shouldReboot:
			# print("1")
			# botThread.shutdown = True
			# botThread.join()
			# print("2")
			# #This should kill it, I think? Also it might lag a bit on the current thread
			# reload(makubot)
			# print("3")
			# main()
			# print("4")
		# time.sleep(1)
		# #print("heheh")
		
main()