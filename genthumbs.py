#!/usr/bin/env python

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

import base64
import os
import sys
import time

from gallerpy import load_config, generate_thumbnails, walk

# ---------------------------------------------------------------------------

def main():
	# Parse our config
	Conf = load_config('gallerpy.conf')
	
	if 'thumbs_local' not in Conf:
		Conf['thumbs_local'] = 'thumbs'
	if 'resized_local' not in Conf:
		Conf['resized_local'] = '_resized'
	
	started = time.time()
	
	# Work out where we're going
	if len(sys.argv) == 2:
		walkdir = os.path.abspath(sys.argv[1])
	else:
		walkdir = os.path.abspath('.')
	walklen = len(os.sep) + len(walkdir)
	
	# Make sure our thumbs dir exists
	thumb_path = os.path.join(walkdir, 'thumbs')
	if not os.path.exists(thumb_path):
		print "ERROR: %s doesn't exist!" % (thumb_path)
		sys.exit(1)
	
	# Change to the root dir
	os.chdir(walkdir)
	
	# And off we go
	os.umask(0000)
	
	made = 0
	
	for root, dirs, files in walk(walkdir):
		for hide in Conf['hide_dirs']:
			if hide in dirs:
				dirs.remove(hide)
		
		dirs.sort()
		files.sort()
		
		if root == walkdir:
			continue
		
		print '> Entering %s' % (root[walklen:])
		
		newthumbs, _, _, warnings = generate_thumbnails(Conf, root[walklen:], files, sizes=0)
		for warning in warnings:
			print warning
		
		made += newthumbs
	
	# Done
	print
	print 'Generated %d thumbnail(s) in %.1fs' % (made, time.time() - started)
	
	# Now clean up any missing thumbs
	killed = 0
	for filename in os.listdir(thumb_path):
		root, ext = os.path.splitext(filename)
		decoded = '%s%s' % (base64.decodestring(root).replace('\n', ''), ext)
		
		if not os.path.exists(decoded) or decoded.startswith(os.sep):
			filepath = os.path.join(thumb_path, filename)
			os.remove(filepath)
			killed += 1
	
	if killed:
		print 'Removed %d stale thumbnails' % (killed)
	
# ---------------------------------------------------------------------------

if __name__ == '__main__':
	main()
