#!/usr/bin/env python

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
