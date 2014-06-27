import socket, threading, sys, time

from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg

host = '123.456.789.000'
port = 59997

app = QtGui.QApplication([])

x_num_plots = 10
x_range = 24.0

#avg hits
coordinates_x_avg = np.zeros(x_num_plots)
coordinates_y_avg = np.zeros(x_num_plots)

#min hits/min
coordinates_x_min = np.zeros(x_num_plots)
coordinates_y_min = np.zeros(x_num_plots)

#max hits/min
coordinates_x_max = np.zeros(x_num_plots)
coordinates_y_max = np.zeros(x_num_plots)

for i in range(0,x_num_plots):
    coordinates_x_avg[i] =  -1 * i * (x_range/x_num_plots)
    coordinates_x_min[i] =  -1 * i * (x_range/x_num_plots)
    coordinates_x_max[i] =  -1 * i * (x_range/x_num_plots)

#win = pg.GraphicsWindow(title="Access Log Hits/s 1 Hour")
win = pg.GraphicsWindow(title="Skins Server Device Guide Hits/s")
win.resize(1000,600)
ptr = 0

update_available = False

def update():
    global dynamic_plot_avg, dynamic_plot_min, dynamic_plot_max, data, ptr, p1, x_num_plots, coordinates_x_avg, coordinates_y_avg , coordinates_x_min, coordinates_y_min, coordinates_x_max, coordinates_y_max, update_available
    
    if update_available==True:
        dynamic_plot_avg.setData(coordinates_x_avg,coordinates_y_avg, fillLevel=-0.01, brush=(0,0,255))
        dynamic_plot_min.setData(coordinates_x_min,coordinates_y_min)
        dynamic_plot_max.setData(coordinates_x_max,coordinates_y_max)
        if ptr == x_num_plots-1:
            ptr=0    
        ptr += 1
        update_available=False
 
#p1 = win.addPlot(title="Access Log Hits/s on " + host + ":" + str(port))
sii_plot = win.addPlot(title="Skins Server Device Guide Hits/s")

label_style = {'color': '#FFF', 'font-size': '13pt'}
legend_style = {'color': '#FFF', 'font-size': '13pt'}
sii_plot.setLabel('left', "Hits/s", **label_style)
sii_plot.setLabel('bottom', "Total time=24 hours | 10 minute intervals", **label_style)
sii_plot.addLegend()

dynamic_plot_min = sii_plot.plot(pen='y', name='Maximum hits/s')
dynamic_plot_avg = sii_plot.plot(pen='g', fillLevel=-0.01, brush=(50,50,200,100), name='Average hits/s')
dynamic_plot_max = sii_plot.plot(pen='r', name='Minimum hits/s')

dynamic_plot_avg = sii_plot.plot(pen='g', fillLevel=-0.01, brush=(50,50,200,100))
dynamic_plot_min = sii_plot.plot(pen='y')
dynamic_plot_max = sii_plot.plot(pen='r')

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(100)   

def client():
    global x_num_plots, coordinates_y_avg, coordinates_y_min, coordinates_y_max, update_available, host, port    
    
    client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    client_socket.setblocking(1)
    client_socket.settimeout(None)
    #client_socket.settimeout(3.0)
    
    try:
        client_socket.connect((host,port))
    except socket.error:
        print host,'is offline...'
        exit()
    else:
        print "Connected to server..."
    
    try:           
        data = "start"
        client_socket.send(data.encode('utf-8'))
        #data = client_socket.recv(1024)
        
        client_socket.setblocking(0)
        timeout = 5
        data_arr=[];

        #beginning time
        begin=time.time()
        while 1:
            #if you got some data, then break after timeout
            if data_arr and time.time()-begin > timeout:
                break
    
            #if you got no data at all, wait a little longer, twice the timeout
            elif time.time()-begin > timeout:
                break
    
            #recv something
            try:
                data = client_socket.recv(8192)
                if data:
                    data_arr.append(data)
                    #change the beginning time for measurement
                    begin=time.time()
                else:
                    #sleep for sometime to indicate a gap
                    time.sleep(0.1)
            except:
                pass              
        
        client_socket.setblocking(1)
          
        #join all parts to make final string
        data = ''.join(data_arr)
        
        if data=="start":
            print "Receiving data (no history to load)..." 
        else: 
            print "Receiving history..."             
            print data 
            
            #parse data
            parsed_history_data = data.split('|')

            for x in range(0, x_num_plots):
                result_arr = parsed_history_data[x].split(',')                
                coordinates_y_avg = np.roll(coordinates_y_avg, 1)
                coordinates_y_min = np.roll(coordinates_y_min, 1)
                coordinates_y_max = np.roll(coordinates_y_max, 1)
                coordinates_y_avg[0] = int(result_arr[0])
                coordinates_y_min[0] = int(result_arr[2])
                coordinates_y_max[0] = int(result_arr[1])
            update_available = True            
            print "Receiving Data..."
            
        #prev_counter = 0  
        while 1:
            try:
                data = client_socket.recv(1024)
            except socket.error:
                break
            else: 
                pass
                #response = "ok"
                #client_socket.send(response.encode('utf-8')) 
               
            if data:  
                print data                 
                counter = data.decode('utf-8') 
                #prev_counter = counter = (prev_counter+int(counter))/2         
                result_arr = counter.split(',')                
                coordinates_y_avg = np.roll(coordinates_y_avg, 1)
                coordinates_y_min = np.roll(coordinates_y_min, 1)
                coordinates_y_max = np.roll(coordinates_y_max, 1)
                coordinates_y_avg[0] = int(result_arr[0])
                coordinates_y_min[0] = int(result_arr[2])
                coordinates_y_max[0] = int(result_arr[1])
                update_available = True       
                
        data = "shutdown"
        client_socket.send(data.encode('utf-8'))
        data = client_socket.recv(1024)
        
        if data=="shutdown":
            print "Shutting down..."
        
    except socket.error:
        print host,'Having trouble recieving/sending data...'
        exit()
        
    client_socket.shutdown(socket.SHUT_RDWR)
    client_socket.close()

t1 = threading.Thread(target=client)
t1.start()
    
if __name__ == '__main__':
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()