#!/usr/bin/env python

# Copyright (c) 2004-2006, Freddie
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
import sys
import time

from gallerpy import load_config, generate_thumbnails, walk

# ---------------------------------------------------------------------------

def main():
	# Parse our config
	Conf = load_config('gallerpy.conf')
	
	started = time.time()
	
	# Work out where we're going
	if len(sys.argv) == 2:
		walkdir = os.path.abspath(sys.argv[1])
	elif 'root_local' in Conf:
		walkdir = os.path.abspath(Conf['root_local'])
	else:
		walkdir = os.path.abspath('.')
	
	walklen = len(os.sep) + len(walkdir)
	
	if 'thumbs_local' not in Conf:
		Conf['thumbs_local'] = os.path.join(walkdir, 'thumbs')
	if 'resized_local' not in Conf:
		Conf['resized_local'] = os.path.join(walkdir, '_resized')
	
	# Make sure our thumbs dir exists
	if not os.path.exists(Conf['thumbs_local']):
		print "ERROR: %s doesn't exist!" % (Conf['thumbs_local'])
		sys.exit(1)
	
	# Change to the root dir and off we go
	os.chdir(walkdir)
	os.umask(0000)
	
	made = 0
	thumbs = {}
	
	for root, dirs, files in walk(walkdir):
		for hide in Conf['hide_dirs']:
			if hide in dirs:
				dirs.remove(hide)
		
		dirs.sort()
		files.sort()
		
		if root == walkdir:
			continue
		
		print '> Entering %s' % (root[walklen:])
		
		newthumbs, _, images, warns = generate_thumbnails(Conf, root[walklen:], files, sizes=0)
		for warning in warns:
			print warning
		
		made += newthumbs
		
		for img in images:
			thumbs[img[5]] = None
	
	# Done
	print
	print 'Generated %d thumbnail(s) in %.1fs' % (made, time.time() - started)
	
	# Now clean up any missing thumbs
	deadthumbs = 0
	for filename in os.listdir(Conf['thumbs_local']):
		if filename in thumbs:
			continue
		
		filepath = os.path.join(Conf['thumbs_local'], filename)
		if not os.path.isfile(filepath):
			continue
		
		os.remove(filepath)
		deadthumbs += 1
	
	if deadthumbs:
		print 'Removed %d stale thumbnails' % (deadthumbs)
	
	# FIXME: clean up resized images dir too

# ---------------------------------------------------------------------------

if __name__ == '__main__':
	main()
