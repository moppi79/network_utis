import os,sys, MySQLdb ,re, datetime, time, subprocess, pathlib , json



'''
-- apt install python3-mysqldb
-- apt install nfs-kernel-server


Wichtig der Server darf keine IP Interface bindung haben in der konfig 

CREATE USER 'nfs_user'@'192.168.1.%' IDENTIFIED BY 'testtesttest';
GRANT ALL PRIVILEGES ON * . * TO nfs_user@'192.168.1.%';
FLUSH PRIVILEGES;

CREATE DATABASE nfs_call;
USE nfs_call;
CREATE TABLE nfs_client (id int(40) NOT NULL AUTO_INCREMENT,name varchar(255),time varchar(255),ip varchar(255),PRIMARY KEY (id));


####

INSERT INTO nfs_client (name,time,ip) VALUES ('raspi42',0,'192.168.1.35');



############ install datei #######
vi nfs_cron.py


###############
crontab -e


*/2 * * * * python3 /root/nfs_cron.py >/dev/null 2>&1

@reboot python3 /root/nfs_cron.py reset >/dev/null 2>&1



'''
#datenbank data
host = '192.168.0.xxx'
user = 'nfs_user'
pw = 'testtesttest'
db = 'nfs_call'


path = '/net/nfs' #Muss schon erstellt sein !!!!
freigabe = '/net'


################################
now = str(time.time()).split('.')[0] #unix time stamp

exports = freigabe+' *(rw,sync,no_root_squash)'  #complete code for NFS Export file 
export_file = '/etc/exports' #Export file

#Get SELF IP 

save_1 = subprocess.run(["hostname", '-I'],stdout=subprocess.PIPE, text=True) 
own_ip_1 = save_1.stdout.split(' ')

for x in own_ip_1:
	x_1 = x.split('.')
	if len(x_1) == 4:
		if x_1[0] != 127:
			own_ip = x

### Read Host IP
save_1 = subprocess.run(["hostname"],stdout=subprocess.PIPE, text=True)
own_name = str(save_1.stdout).split('\n')[0]

###### Open NFS Export File #####
export_read = open (export_file,'r')
not_insert = 0
for x in export_read:
	line = x.split('\n')[0]
	#print (line)
	if line ==  exports:
		#print ("yes")
		not_insert = 1
export_read.close()

if not_insert == 0: ### Add String to File 
	#print ('not insert')
	write_f = open (export_file,'a')
	write_f.write(exports+'\n')
	write_f.close()
	subprocess.run(["/etc/init.d/nfs-kernel-server", 'reload'])  ### Reload NFS Sever

#Try contakt SQL server	
try:
	dbcon=MySQLdb.Connect(host=host,user=user ,passwd=pw,db=db)
except:
	print ('error')
else:
	
	cursor = dbcon.cursor()
	abfrage = 'select * from nfs_client WHERE name = \''+own_name+'\' AND ip = \''+own_ip+'\';' #Read Own data from SQL
	cursor.execute(abfrage)
	fields=cursor.fetchall()
	
	
	not_insert = 0
	for x in fields: #check he is in the Database
		#print (x)
		not_insert = x
	
	
	if not_insert == 0: #is not in database, Create a new entry
		mount = {}
		abfrage = 'INSERT INTO nfs_client (name,time,ip,mounted) VALUES (\''+own_name+'\',\''+now+'\',\''+own_ip+'\',\''+json.dumps(mount)+'\');'
		cursor.execute(abfrage)
		dbcon.commit()
	else: 
		#print(x)
		#print (sys.argv)
	
		if 'reset' in sys.argv: #on reboot to clear the Mount values
			#print ('mach reset scheisse')
			mount = json.loads(x[4])
			for m_t in mount:
				mount[m_t] = 0
		else:
			mount = json.loads(x[4])
	
	abfrage = 'select * from nfs_client;' #get all data from database
	
	cursor.execute(abfrage)
	fields=cursor.fetchall()
	
	os.chdir(path) #go to the NFS Folder
	#print(pathlib.Path.cwd())
	path_list = sorted(pathlib.Path('.').glob('*')) #get Folder list in NFS Mount
	
	var = []
	
	for x in path_list: #to get only strings
		var.append(str(x))
	
	for x in fields: #database Walk
		
		if x[1] != own_name : #when the entry is not himself 
			#print ('false')
			#print (var)
			if x[1] not in var: #is Folder not created, create a new
				pathlib.Path(x[1]).mkdir(mode=0o777)
				os.system('chmod 766 '+x[1])
			
			if x[1] not in mount: #when the client in the list is new, create a new point
				mount[x[1]] = 0

			if mount[x[1]] == 0: #when target not mountet
				if int(x[2]) > (int(now)-380): #is the last calls under 5 minutes
					os.system ('mount '+x[1]+':'+freigabe+' '+path+'/'+x[1]) #Mount NFS
					mount[x[1]] = 1
				
			else:
				if int(x[2]) < (int(now)-380): #is the last calls over 5 minutes
					os.system ('umount '+path+'/'+x[1]+' -f') #Unmount with Force
					mount[x[1]] = 0
					
					##### Delete data for the Target Client #######
					
					mount_target = json.loads(x[4]) #Load data from the offline system to Force him Later to new mount all his points
					
					print (mount_target)
					for m_t in mount_target:
						mount_target[m_t] = 0
					print (mount_target)
					mount_j = json.dumps(mount_target)
					abfrage = 'UPDATE nfs_client set mounted = \''+mount_j+'\' WHERE name = \''+x[1]+'\' AND ip = \''+x[3]+'\';'
					cursor.execute(abfrage)
					dbcon.commit()
			
			#####

		else: ### am schluss raus nehemen, man kann sich nicht selbst mounten !!!
			a_1 = 1

	## Update Table ####
	mount_j = json.dumps(mount) #save all Mount Data und setting new Time stamp
	abfrage = 'UPDATE nfs_client set time = \''+now+'\', mounted = \''+mount_j+'\' WHERE name = \''+own_name+'\' AND ip = \''+own_ip+'\';'
	cursor.execute(abfrage)
	dbcon.commit()
