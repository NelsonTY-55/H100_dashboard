import ftplib
import io
import sys
#MyFTP_TLS is derieved to support TLS_RESUME(filezilla server)
class MyFTP_TLS(ftplib.FTP_TLS):
    """
    A subclass of ftplib.FTP_TLS that reuses the TLS session for data connections.
    This class is specifically designed for compatibility with Filezilla, which requires
    the same TLS session to be reused for data transfers. Normally, reusing TLS sessions
    in this way is not recommended due to security concerns, as it may weaken the security
    guarantees provided by the TLS protocol. Use this class only when interoperability
    with Filezilla is required and you understand the associated risks.
    """
    """Explicit FTPS, with shared TLS session"""
 
    def ntransfercmd(self, cmd, rest=None):
        conn, size =ftplib.FTP.ntransfercmd(self,cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn,
                                            server_hostname=self.host,
                                            session=self.sock.session)  # reuses TLS session
            
        return conn,size

def ftpCheckStatus(ip, proxy, user, passwd):
	print('Hostname: '+ip)
	print('Proxy: '+proxy)
	print('user: '+user)
	print('password: '+passwd)
	print('')
	print('=====Test Result=====')
	fileName = "testFile"
	try:
		# # Connect to FTP server with optional TLS support
		if ip.startswith("ftps://") or ip.startswith("ftpes://"):
			host_parts = ip.replace("ftps://", "").replace("ftpes://", "").split(":")
			host_address = host_parts[0]
			port = int(host_parts[1]) if len(host_parts) > 1 else 21
			ftp = MyFTP_TLS(host = host_address, timeout=15)
			ftp.auth()
			ftp.port = port
			ftp.login(user, passwd)
			ftp.prot_p()  # Switch to secure data connection
			ftp.set_pasv(1) # Default is passive mode
		else:
			host_parts = ip.split(":")
			host_address = host_parts[0]
			port = int(host_parts[1]) if len(host_parts) > 1 else 21
			ftp = ftplib.FTP()
			ftp.connect(host_address, port)
			if user:
				ftp.login(user, passwd)
			else:
				ftp.login()

		# ftp = ftplib.FTP(ip, user, passwd, timeout=3)
		print("FTP connect success.")
		ftp.encoding = "utf-8"
	except:
		print("FTP connect failed.")
		return 1
	try:
		try:
			ftp.cwd("/createTest")
		except:
			ftp.mkd("/createTest")
		print("Create dir success.")
	except:
		print("Dir create failed.")
		return 2
	try:
		ftp.rmd("/createTest")
		print("Delete dir success.")
	except:
		print("Dir delete failed.")
		return 3
	try:
		x = "Test String"
		bio = io.BytesIO(bytes(x,encoding='utf8'))
		ftp.storbinary("STOR /" + fileName, bio)
		print("File create success.")
	except:
		print("File create failed.")
		return 4
	try:
		ftp.delete(fileName)
		print("File delete success.")
	except:
		print("File delete failed.")
		return 5
	return 0

if __name__=="__main__":
	# 檢查命令列參數數量
	if len(sys.argv) < 4:
		print("Usage: python ftpCheck.py <ip> <username> <password>")
		print("Example: python ftpCheck.py 192.168.1.100:21 admin password123")
		print("Example with FTPS: python ftpCheck.py ftps://192.168.1.100:21 admin password123")
		sys.exit(1)
	
	ip = str(sys.argv[1])
	user = str(sys.argv[2])
	pwd = str(sys.argv[3])
	
	ftpCheckStatus(ip, '1', user, pwd)
