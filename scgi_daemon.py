#!/usr/bin/env python 

"An SCGI handler for GallerPy"

import getopt
import os
import sys
import time

from scgi import scgi_server 

import index

# ---------------------------------------------------------------------------

class GallerPyHandler(scgi_server.SCGIHandler):
	prefix = '/gp'
	
	def handle_connection(self, conn):
		started = time.time()
		
		_in = conn.makefile('r')
		_out = conn.makefile('w')
		
		env = self.read_env(_in)
		
		# Replace stdin/stdout so we can be lazy
		sys.__stdin__ = sys.stdin = _in
		sys.__stdout__ = sys.stdout = _out
		
		# Work out wtf our PATH_INFO and SCRIPT_NAME should be
		env['PATH_INFO'] = env['SCRIPT_NAME'][len(self.prefix):]
		env['SCRIPT_FILENAME'] = sys.argv[0]
		env['SCRIPT_NAME'] = self.prefix
		
		# Do stuff here
		if 0:
			print 'Content-type: text/plain'
			print
			print 'moo'
			
			for k, v in env.items():
				print k, '==>', v
			
			print 'baa'
		
		# Show the page
		if 1:
			index.main(env, started)
		
		# Clean up
		try:
			_in.close()
			_out.close()
			conn.close()
		except IOError:
			pass


def main(handler=GallerPyHandler):
	usage = """Usage: %s [options]

    -F -- stay in foreground (don't fork)
    -P -- PID filename
    -l -- log filename
    -m -- max children
    -p -- TCP port to listen on
""" % sys.argv[0]
	
	nofork = 0
	pidfilename = "/tmp/gallerpy-wp.pid"
	logfilename = "/var/gallerpy-wp.log"
	max_children = 2    # scgi default
	port = 35001
	host = "127.0.0.1"
	
	try:
		opts, args = getopt.getopt(sys.argv[1:], 'FP:l:m:p:')
	except getopt.GetoptError, exc:
		print >>sys.stderr, exc
		print >>sys.stderr, usage
		sys.exit(1)
	
	for o, v in opts:
		if o == "-F":
			nofork = 1
		elif o == "-P":
			pidfilename = v
		elif o == "-l":
			logfilename = v
		elif o == "-m":
			max_children = int(v)
		elif o == "-p":
			port = int(v)
	
	log = open(logfilename, "a", 1)
	os.dup2(log.fileno(), 1)
	os.dup2(log.fileno(), 2)
	os.close(0)
	
	if nofork:
		print 'serving'
		scgi_server.SCGIServer(
			handler, host=host, port=port, max_children=max_children
		).serve() 
	else: 
		pid = os.fork()
		if pid == 0:
			pid = os.getpid()
			#pidfile = open(pidfilename, 'w')
			#pidfile.write(str(pid))
			#pidfile.close()
			try:
				scgi_server.SCGIServer(
					handler, host=host, port=port, max_children=max_children
				).serve()
			finally:
				# grandchildren get here too, don't let them unlink the pid
				if pid == os.getpid():
					try:
						os.unlink(pidfilename)
					except OSError:
						pass


if __name__ == '__main__':
	main()
