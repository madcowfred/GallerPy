#!/usr/bin/env python 

"An SCGI handler for GallerPy"

# Copyright (c) 2004, Freddie
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

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
		
		# Test
		if 0:
			print 'Content-type: text/plain'
			print
			
			for k, v in env.items():
				print k, '==>', v
		
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

# ---------------------------------------------------------------------------

def main(handler=GallerPyHandler):
	usage = """Usage: %s [options]

    -F -- stay in foreground (don't fork)
    -P -- PID filename
    -l -- log filename
    -m -- max children
    -p -- TCP port to listen on
""" % sys.argv[0]
	
	nofork = 0
	pidfilename = "/tmp/gallerpy.pid"
	logfilename = "/tmp/gallerpy.log"
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
