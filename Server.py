import socket, datetime, threading, os, time, sys

###############################
#      Object Lock Class
###############################
class BoolLock(object):
    def __init__(self, b_value):
        self._lock = threading.RLock()
        self._value = b_value
    def __bool__(self):
        self.acquire() 
        try: 
            return self._value
        finally: 
            self.release()
    def __str__(self):
        self.acquire() 
        try: 
            return str(self._value)
        finally: 
            self.release() 
    def __enter__(self):
        self.acquire()
    def __exit__(self, type, value, traceback):
        self.release()
        
    def acquire(self):  
        self._lock.acquire()
    def release(self):
        self._lock.release() 
    def value(self):
        self.acquire()
        try: 
            return self._value
        finally: 
            self.release()
    def on(self):
        self.acquire()
        try: 
            self._value = True
        finally: 
            self.release()
    def off(self):
        self.acquire()
        try: 
            self._value = False
        finally: 
            self.release()
            
class EventLock(object):
    def __init__(self, s_value):
        self._lock = threading.RLock()
        self._event = threading.Event()
        self._value = s_value
    def __bool__(self):
        self.acquire() 
        try: 
            return self._event.is_set()
        finally: 
            self.release()
    def __str__(self):
        self.acquire() 
        try: 
            return str(self._value)
        finally: 
            self.release() 
    def __enter__(self):
        self.acquire()
    def __exit__(self, type, value, traceback):
        self.release()
        
    def acquire(self):  
        self._lock.acquire()
    def release(self):
        self._lock.release() 
    def value(self):
        self.acquire()
        try: 
            return self._value
        finally: 
            self.clearEvent()
            self.release()
    def setValue(self, s_value):
        self.acquire()
        try: 
            self._value = s_value
        finally: 
            self.setEvent()
            self.release()
    def setEvent(self):
        self.acquire()
        try: 
            self._event.set()
        finally: 
            self.release()
    def clearEvent(self):
        self.acquire()
        try: 
            self._event.clear()
        finally: 
            self.release()

###############################
#        Server Class
###############################
class Server(threading.Thread):                  
    def __init__(self, port, report_size, server_log, ACCESS_LOG_LIVE_FLAG, ACCESS_LOG_MAIN_LOOP_FLAG, NEW_DATA_EVENT):        
        threading.Thread.__init__(self) 
        
        self.ACCESS_LOG_LIVE_FLAG       = ACCESS_LOG_LIVE_FLAG
        self.ACCESS_LOG_MAIN_LOOP_FLAG  = ACCESS_LOG_MAIN_LOOP_FLAG
        self.SERVER_MAIN_LOOP_FLAG      = BoolLock(True)
        self.SERVER_LOG_OPEN            = BoolLock(False)
        self.CLIENT_CONNECTION          = BoolLock(False)
        
        self.NEW_DATA_EVENT             = NEW_DATA_EVENT       
        
        self.report_size = report_size
        
        self.server_log = server_log         
         
        self.port = port 
        self.conn = None
        self.addr = None 
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('', self.port))
        self.server_socket.setblocking(1)
        self.server_socket.settimeout(None)
        
        self.start()        
        
    def now(self):
        date = datetime.datetime.now()
        return date.strftime("%d/%m/%y %H:%M:%S")
        
    def run(self): 
        print ('Server thread started...')
                
        print ('Waiting for access log to be live...')
        while self.ACCESS_LOG_LIVE_FLAG:
            time.sleep(1)
        
        if self.ACCESS_LOG_MAIN_LOOP_FLAG: 
            print ('Server successfully started, awaiting connection...')
            
            #listen on port for a connection from client
            self.server_socket.listen(1)        
            try:        
                self.conn, self.addr = self.server_socket.accept()
            except socket.error as e:
                print (e)
            else:        
                print ('Contact', self.addr, 'on', self.now(), '...') 
                self.CLIENT_CONNECTION.on()                       
            
            while self.SERVER_MAIN_LOOP_FLAG and self.ACCESS_LOG_MAIN_LOOP_FLAG: 
                try:
                    data = self.conn.recv(1024)
                except socket.error:                
                    continue
                
                #if no data, lost connection, listen again on port for a connection from client
                #else parse
                if not data:                 
                    print ('Lost', self.addr, ', waiting...') 
                    self.CLIENT_CONNECTION.off()               
                    self.server_socket.listen(1)                
                    try:
                        self.conn, self.addr = self.server_socket.accept() 
                    except socket.error as e:
                        pass              
                    else:        
                       print ('Contact', self.addr, 'on', self.now(), '...')   
                       self.CLIENT_CONNECTION.on()                                
                else:   
                    #check message action 
                    action = data.decode('utf-8')                
                    if action=="start":
                        
                        #get last report_size lines of server_log to prepend live data
                        self.getServerLog()
                                                
                        print ("Starting access log stream...") 
                        
                        while self.CLIENT_CONNECTION:                         
                            #check event variable for data to grab
                            if NEW_DATA_EVENT:                            
                                send_text = str(NEW_DATA_EVENT.value())
                                
                                try:
                                    self.conn.send(str(send_text).encode('utf-8'))
                                except socket.error: 
                                    self.CLIENT_CONNECTION.off()               
                                    break 
                            
                            time.sleep(0.1)   
                        
        
    def getServerLog(self):
        print ("Opening "+self.server_log+"...")                                        
        try:            
            #open file
            self.handle_server_log = open(self.server_log, "r")
            
            #set flag
            self.SERVER_LOG_OPEN.on()
            
            #arrays for avg, min, max values            
            history_array_avg = []
            history_array_min = []
            history_array_max = []
            
            #set them all to 0                       
            for x in range(0, self.report_size):
                history_array_avg.append(0)
                history_array_min.append(0)
                history_array_max.append(0)
                
            print ("Parsing "+self.server_log+"...")
            while 1:#######################################################flag
                line = self.handle_server_log.readline().strip('\n')                        
                if not line:
                    break
                result_line = line.split(',')                       
                history_array_avg.append(int(result_line[0]))
                history_array_min.append(int(result_line[2]))
                history_array_max.append(int(result_line[1]))
                history_array_avg.pop(0)
                history_array_min.pop(0)
                history_array_max.pop(0)
            
            #take parsed results and form an object to be deconstructed after sent to client
            response = ""
            for x in range(0, self.report_size):
                if x != 0:
                    response += "|"
                response += str(history_array_avg[x])+"," + str(history_array_max[x]) +"," + str(history_array_min[x])
            
            response += "%"
            
            #send history to client
            print ("Sending "+self.server_log+" history...")    
            self.conn.send(response.encode('utf-8')) 
            print(response)
            #close server log
            try:
                self.handle_server_log.close()
                print ("Closing sii_server.log...")
                
                #set flag
                self.SERVER_LOG_OPEN.off()
            except AttributeError:
                pass
                 
        except IOError:
            response = "start"            
            print ("Could not open "+self.server_log+"...")
            self.conn.send(response.encode('utf-8'))            
        except socket.error: 
            self.SERVER_MAIN_LOOP_FLAG.off()
            self.ACCESS_LOG_MAIN_LOOP_FLAG.off()       
            
    def exit(self): 
        self.SERVER_MAIN_LOOP_FLAG.off()    
        self.ACCESS_LOG_LIVE_FLAG.off()
        self.ACCESS_LOG_MAIN_LOOP_FLAG.off()
        self.CLIENT_CONNECTION.off()
        
        try:
            self.file_history.close()
            print ("Closing "+self.server_log+"...")
            self.SERVER_LOG_OPEN.off()
        except AttributeError:
            pass            
        
        print ("Closing server...")
        self.server_socket.shutdown(socket.SHUT_RDWR)
        print ("Closing socket...")
        self.server_socket.close()
        
###############################
#      Log Monitor Class
###############################
class LogMonitor(threading.Thread):
                  
    def __init__(self, access_log, server_log, report_time_interval, ACCESS_LOG_LIVE_FLAG, ACCESS_LOG_MAIN_LOOP_FLAG, NEW_DATA_EVENT):
        threading.Thread.__init__(self)
        
        self.ACCESS_LOG_LIVE_FLAG       = ACCESS_LOG_LIVE_FLAG
        self.ACCESS_LOG_MAIN_LOOP_FLAG  = ACCESS_LOG_MAIN_LOOP_FLAG
        self.ACCESS_LOG_OPEN_FLAG       = BoolLock(False)
        self.SERVER_LOG_OPEN_FLAG       = BoolLock(False)
        
        self.NEW_DATA_EVENT             = NEW_DATA_EVENT
        
        self.access_log = access_log
        self.server_log = server_log
        
        self.report_time_interval = report_time_interval
        
        self.hits_max = 0
        self.hits_min = 10000000
        self.hits_counter_current = 0
        self.hits_counter_total = 0
        
        self.start_time = None
        self.elapsed_time = None
        self.current_second = 1 #ceiling of current second of start_time
        
        self.handle_access_log = None
        self.handle_server_log = None
        
        self.start()      
    
    def run(self):        
        print ('LogMonitor thread started...') 
        self.ACCESS_LOG_MAIN_LOOP_FLAG.on()
                
        #open access log
        print ("Opening "+self.access_log+"...")        
        try:                       
            self.handle_access_log = open(self.access_log, "r")                                    
        except IOError:            
            print ("Error opening "+access_log+"...")
            self.ACCESS_LOG_LIVE_FLAG.off()
        else:
            #read each line of access log until found last
            print ("Finding end of "+self.access_log+"...")        
            line_counter = 0
            while self.ACCESS_LOG_MAIN_LOOP_FLAG:
                line = self.handle_access_log.readline()                        
                if not line:
                    break                        
                if line_counter%500000==0:
                    print("line: ", line_counter)                        
                line_counter+=1 
           
            if self.ACCESS_LOG_MAIN_LOOP_FLAG:
                #release flag for server                                     
                print ("Found live data...")
                self.ACCESS_LOG_LIVE_FLAG.off()
                
                #start stop watch to monitor hits per second            
                self.start_time = time.time() 
                
                #keep parsing access log and outputting access log stats to server_log until flag==False        
                while self.ACCESS_LOG_MAIN_LOOP_FLAG:  
                    #read line from access log  
                    try:                                              
                        line = self.handle_access_log.readline()
                    except ValueError:
                        self.ACCESS_LOG_MAIN_LOOP_FLAG.off()
                        break
                    
                    #if no line found to read, sleep
                    #else increment hit counters    
                    if not line: 
                        time.sleep(.1)                                       
                    else:
                        self.hits_counter_total +=1
                        self.hits_counter_current +=1
                        
                    #update time since start        
                    self.elapsed_time = (time.time() - self.start_time)                       
                    
                    #if new second reached, check if new high/low reached for a single second
                    if self.elapsed_time >= self.current_second:
                        if self.hits_counter_current > self.hits_max:
                            self.hits_max = self.hits_counter_current
                        if self.hits_counter_current < self.hits_min:
                            self.hits_min = self.hits_counter_current
                        self.current_second+=1
                        self.hits_counter_current = 0
                        
                    #if reporting time reached, output stats to server log
                    if self.elapsed_time >= self.report_time_interval:                        
                        send_text = str(int(self.hits_counter_total/self.report_time_interval))+ ","+ str(self.hits_max) +","+str(self.hits_min)
                        
                        if(int(self.hits_counter_total/self.report_time_interval) == 0 and self.hits_max == 0 and self.hits_min == 0):
                            print ("No data read, re-opening access log...")  
                        
                            #close access_log        
                            try:
                                self.handle_access_log.close()
                                print ("Closing "+self.access_log+"...")
                            except AttributeError:
                                pass                            
                        
                            #open access log
                            print ("Opening "+self.access_log+"...")        
                            try:                       
                                self.handle_access_log = open(self.access_log, "r")                                    
                            except IOError:            
                                print ("Error opening "+access_log+"...")
                            else:
                                #read each line of access log until found last
                                print ("Finding end of "+self.access_log+"...")        
                                line_counter = 0
                                while self.ACCESS_LOG_MAIN_LOOP_FLAG:
                                    line = self.handle_access_log.readline()                        
                                    if not line:
                                        break                        
                                    if line_counter%500000==0:
                                        print("line: ", line_counter)                        
                                    line_counter+=1 
                                    
                                print ("Found live data...")
                        
                        else:                        
                            #set variable for server to grab
                            NEW_DATA_EVENT.setValue(str(send_text))
                            
                            '''
                            try:
                                #conn.send(str(send_text).encode('utf-8'))
                                ######################################################################################################## hmm
                            except socket.error: 
                                self.ACCESS_LOG_MAIN_LOOP_FLAG.off()               
                                break 
                            '''
                            
                            #open server log for appending 
                            #print ("Opening "+self.server_log+" (append)...")        
                            try:        
                                #open server log to append
                                self.handle_server_log = open(self.server_log, "a")  
                                self.SERVER_LOG_OPEN_FLAG.on()   
                                
                                #append stats to server_log
                                self.handle_server_log.write("%s\n" % send_text)
                                
                                #close server log
                                self.handle_server_log.close()  
                                self.SERVER_LOG_OPEN_FLAG.off()                                    
                            except IOError:                     
                                print ("Error opening/closing "+self.server_log+" for appending...")
                                self.SERVER_LOG_OPEN_FLAG.off()
                                self.ACCESS_LOG_MAIN_LOOP_FLAG.off()
                                                
                        #reset statistics             
                        self.resetStats() 
                                                                
    def resetStats(self):
        self.start_time = time.time()
        self.hits_counter_total = 0
        self.hits_counter_current = 0
        self.hits_max = 0
        self.hits_min = 10000000                
        self.current_second = 1
                        
    def exit(self):
        self.ACCESS_LOG_MAIN_LOOP_FLAG.off()
                
        #close access_log        
        try:
            self.handle_access_log.close()
            print ("Closing "+self.access_log+"...")
        except AttributeError:
            pass
        else:
            self.ACCESS_LOG_OPEN_FLAG.off()
        
        #close server_log        
        try:
            self.handle_server_log.close()
            print ("Closing write handle on "+self.server_log+"...")
        except AttributeError:
            pass 
        else:
            self.SERVER_LOG_OPEN_FLAG.off()                        

report_time_interval        = 600
num_data_points             = 144

access_log                  = "/var/log/apache2/other_vhosts_access.log"
server_log                  = "sii_server.log"
                    
ACCESS_LOG_LIVE_FLAG        = BoolLock(True)
ACCESS_LOG_MAIN_LOOP_FLAG   = BoolLock(False)
NEW_DATA_EVENT              = EventLock(False)

server_thread           = Server(59997, num_data_points, server_log, ACCESS_LOG_LIVE_FLAG, ACCESS_LOG_MAIN_LOOP_FLAG, NEW_DATA_EVENT) 
log_monitor_thread      = LogMonitor(access_log, server_log, report_time_interval, ACCESS_LOG_LIVE_FLAG, ACCESS_LOG_MAIN_LOOP_FLAG, NEW_DATA_EVENT) 

while 1:
    if input() == 'q':
        server_thread.exit()
        log_monitor_thread.exit()
        break

print('Closing log monitor thread...')
log_monitor_thread.join()

print ("Closing server thread...")
server_thread.join()

print('Closing main thread...')