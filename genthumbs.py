#!/usr/bin/env python

from __future__ import generators

import base64
import os
import re
import sys
import time

sys.path.append(os.path.expanduser('~/lib/python/PIL'))

from ConfigParser import ConfigParser

import Image

# Faster way to make images load :|
import GifImagePlugin
import JpegImagePlugin
import PngImagePlugin

OPEN = {
	'gif': GifImagePlugin.GifImageFile,
	'jpe': JpegImagePlugin.JpegImageFile,
	'jpg': JpegImagePlugin.JpegImageFile,
	'jpeg': JpegImagePlugin.JpegImageFile,
	'png': PngImagePlugin.PngImageFile,
}

# ---------------------------------------------------------------------------

IMAGE_RE = re.compile(r'^(.*)\.(gif|jpe|jpg|jpeg|png)$', re.I)

# ---------------------------------------------------------------------------

def main():
	# Parse our config
	Conf = {}
	
	c = ConfigParser()
	c.read('gallerpy.conf')
	
	for option in c.options('options'):
		if option.startswith('thumb_') or option.startswith('image_'):
			Conf[option] = int(c.get('options', option))
		else:
			Conf[option] = c.get('options', option)
	
	Conf['hide_dirs'] = Conf['hide_dirs'].split('|')
	
	del c
	
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
		
		for filename in files:
			image_file = os.path.join(root, filename)
			image_name = image_file[walklen:]
			
			# We only want images
			m = IMAGE_RE.match(image_name)
			if not m:
				continue
			
			froot = m.group(1)
			fext = m.group(2).lower()
			
			# Work out our goofy thumbnail name
			b64 = base64.encodestring(froot).replace('\n', '')
			thumb_name = '%s.%s' % (b64, fext)
			thumb_file = os.path.join(thumb_path, thumb_name)
			
			# If it exists and is old, delete it
			image_stat = os.stat(image_file)
			try:
				thumb_stat = os.stat(thumb_file)
			except OSError:
				gen_thumb = 1
			else:
				if image_stat.st_mtime > thumb_stat.st_mtime:
					try:
						os.remove(thumb_file)
					except OSError:
						continue
					else:
						gen_thumb = 1
				else:
					gen_thumb = 0
			
			# Make a new thumbnail now
			if gen_thumb:
				print '-> Thumbnailing %s...' % (filename),
				sys.stdout.flush()
				
				# Open it
				img = OPEN.get(fext, Image.open)(image_file)
				image_width, image_height = img.size
				
				# Resize and save it
				try:
					img.thumbnail((Conf['thumb_width'], Conf['thumb_height']), Image.BICUBIC)
				except IOError, msg:
					print 'failed: %s' % msg
					continue
				
				thumb_width, thumb_height = img.size
				
				try:
					img.save(thumb_file)
				except Exception, msg:
					print 'failed: %s' % (msg)
					continue
				
				print 'OK.'
				
				made += 1
	
	# Done
	now = time.time()
	print
	print 'Generated %d thumbnails in %.1fs' % (made, now - started)
	
	# Now clean up any missing thumbs
	killed = 0
	for filename in os.listdir(thumb_path):
		root, ext = os.path.splitext(filename)
		decoded = '%s%s' % (base64.decodestring(root).replace('\n', ''), ext)
		
		if not os.path.exists(decoded):
			filepath = os.path.join(thumb_path, filename)
			os.remove(filepath)
			killed += 1
	
	if killed:
		print 'Removed %d stale thumbnails in %.1fs' % (killed, time.time() - now)

# ---------------------------------------------------------------------------

def walk(top):
	from os.path import join, isdir, islink
	
	try:
		names = os.listdir(top)
	except OSError:
		return
	
	dirs, nondirs = [], []
	for name in names:
		topname = join(top, name)
		
		if isdir(topname):
			dirs.append(name)
		elif islink(topname) and isdir(normpath(topname)):
			dirs.append(name)
		else:
			nondirs.append(name)
	
	yield top, dirs, nondirs
	
	for name in dirs:
		path = join(top, name)
		#if not islink(path):
		for x in walk(path):
			yield x

# ---------------------------------------------------------------------------

if __name__ == '__main__':
	# Useful speedup
	try:
		import psyco
		psyco.bind(main)
		psyco.bind(JpegImagePlugin.JpegImageFile._open)
	except ImportError:
		pass
	
	main()
