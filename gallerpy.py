"This file contains the various common code that we would liek to use."

from __future__ import generators

import base64
import os
import sys

from ConfigParser import ConfigParser

# Faster way to make images load :|
sys.path.append(os.path.expanduser('~/lib/python/PIL'))

import Image
import GifImagePlugin
import JpegImagePlugin
import PngImagePlugin

OPEN = {
	'.gif': GifImagePlugin.GifImageFile,
	'.jpe': JpegImagePlugin.JpegImageFile,
	'.jpg': JpegImagePlugin.JpegImageFile,
	'.jpeg': JpegImagePlugin.JpegImageFile,
	'.png': PngImagePlugin.PngImageFile,
}

# ---------------------------------------------------------------------------
# Load our config
def load_config(filepath):
	c = ConfigParser()
	c.read(filepath)
	
	Conf = {}
	for option in c.options('options'):
		Conf[option] = c.get('options', option)
		if Conf[option].isdigit():
			Conf[option] = int(Conf[option])
	
	Conf['hide_dirs'] = Conf['hide_dirs'].split('|')
	
	return Conf

# ---------------------------------------------------------------------------
# Generate thumbnails
def generate_thumbnails(Conf, root, files, sizes=1):
	images = []
	newthumbs = 0
	warnings = []
	
	for image_name in files:
		image_path = os.path.join(root, image_name)
		
		# Skip images we don't know about
		froot, fext = os.path.splitext(image_path)
		lfext = fext.lower()
		if lfext not in OPEN:
			continue
		
		# Work out our thumbnail filename
		b64 = base64.encodestring(froot).replace('\n', '')
		thumb_name = '%s.%s' % (b64, fext)
		thumb_path = os.path.join(Conf['thumbs_local'], thumb_name)
		
		# If it exists and is old, delete it
		image_stat = os.stat(image_path)
		try:
			thumb_stat = os.stat(thumb_path)
		except OSError:
			gen_thumb = 1
		else:
			if image_stat.st_mtime > thumb_stat.st_mtime:
				try:
					os.remove(thumb_path)
				except OSError:
					continue
				else:
					gen_thumb = 1
			else:
				gen_thumb = 0
		
		# Get the image dimensions
		if sizes == 1:
			try:
				img = OPEN.get(lfext, Image.open)(image_path)
			except IOError, msg:
				warning = "Warning: failed to open '%s' - %s" % (image_name, msg)
				warnings.append(warning)
				continue
			
			image_width, image_height = img.size
		else:
			image_width, image_height = 0, 0
		
		# Make a new thumbnail if we have to
		if gen_thumb:
			try:
				img.thumbnail((Conf['thumb_width'], Conf['thumb_height']), Image.BICUBIC)
			except IOError, msg:
				warning = "Warning: failed to resize '%s' - %s" % (image_name, msg)
				warnings.append(warning)
				continue
			
			thumb_width, thumb_height = img.size
			
			try:
				img.save(thumb_path)
			except Exception, msg:
				warning = "Warning: failed to save '%s' - %s" % (image_name, msg)
				warnings.append(warning)
				continue
			
			newthumbs += 1
		
		# Or get thumbnail info
		else:
			if sizes == 1:
				try:
					img = OPEN.get(lfext, Image.open)(thumb_path)
				except IOError, msg:
					warning = "Warning: failed to open '%s' - %s" % (thumb_path, msg)
					warnings.append(warning)
					continue
				
				thumb_width, thumb_height = img.size
			else:
				thumb_width, thumb_height = 0, 0
		
		# Get the 'nice' ('45.3KB') file size of the image
		if sizes == 1:
			image_size = NiceSize(image_stat.st_size)
		else:
			image_size = None
		
		# Keep the data for a bit later
		image_data = (image_path, image_name, image_size, image_width, image_height, thumb_name, thumb_width, thumb_height)
		images.append(image_data)
	
	# All done
	return newthumbs, images, warnings

# ---------------------------------------------------------------------------
# Borrowed from Python 2.3 so we still work with 2.2
def walk(top):
	from os.path import join, isdir, islink, normpath
	
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
# Return a nicely formatted size
def NiceSize(bytes):
	if bytes < 1024:
		return '%dB' % (bytes)
	elif bytes < (1024 * 1024):
		return '%.1fKB' % (bytes / 1024.0)
	else:
		return '%.1fMB' % (bytes / 1024.0 / 1024.0)

# ---------------------------------------------------------------------------
