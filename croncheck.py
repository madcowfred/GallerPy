#!/usr/bin/env python

"""
Script to run from crontab to make sure your various SCGI processes are
still running.
"""

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

import os
import signal
import sys

# ---------------------------------------------------------------------------
# Tuple of (pidfile, path, command) tuples
CHECKME = (
	(
		'/home/freddie/scgi/test.pid',
		'/home/freddie/www/test.home',
		'python scgi_daemon.py -P /home/freddie/scgi/test.pid -l /home/freddie/scgi/test.log',
	),
	(
		'/home/freddie/scgi/test2.pid',
		'/home/freddie/www/test2.home',
		'python scgi_daemon.py -P /home/freddie/scgi/test2.pid -l /home/freddie/scgi/test2.log',
	),
)

# ---------------------------------------------------------------------------

def main():
	for pidfile, cmdpath, cmdline in CHECKME:
		start = 0
		
		# If the pidfile is real, check the pid
		if os.path.isfile(pidfile):
			pid = int(open(pidfile, 'r').read())
			
			try:
				os.kill(pid, signal.SIGCHLD)
			except OSError:
				start = 1
		
		else:
			start = 1
		
		# If we have to, start it up
		if start:
			print 'Starting in %s...' % (cmdpath),
			sys.stdout.flush()
			
			os.chdir(cmdpath)
			os.system(cmdline)
			
			print 'done.'

# ---------------------------------------------------------------------------

if __name__ == '__main__':
	main()
