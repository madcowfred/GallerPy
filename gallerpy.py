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
	
	Conf['hide_dirs'] = {}.fromkeys(Conf['hide_dirs'].split('|'), 1)
	
	return Conf

# ---------------------------------------------------------------------------
# Generate thumbnails
def generate_thumbnails(Conf, root, files, sizes=1):
	dirs = []
	images = []
	warnings = []
	newthumbs = 0
	
	for image_name in files:
		image_path = os.path.join(root, image_name)
		
		if os.path.isdir(image_path):
			dirs.append(image_name)
			continue
		
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
		
		# Make a new thumbnail if we have to
		if gen_thumb:
			# Open the image
			try:
				img = OPEN.get(lfext, Image.open)(image_path)
			except IOError, msg:
				warning = "Warning: failed to open '%s' - %s" % (image_name, msg)
				warnings.append(warning)
				continue
			
			image_width, image_height = img.size
			
			# Thumbnail it
			try:
				img.thumbnail((Conf['thumb_width'], Conf['thumb_height']), Image.BICUBIC)
			except IOError, msg:
				warning = "Warning: failed to resize '%s' - %s" % (image_name, msg)
				warnings.append(warning)
				continue
			
			thumb_width, thumb_height = img.size
			
			# Save the thumbnail
			try:
				img.save(thumb_path)
			except Exception, msg:
				warning = "Warning: failed to save '%s' - %s" % (image_name, msg)
				warnings.append(warning)
				continue
			
			newthumbs += 1
		
		# We need to get image size info from the file
		elif sizes == 1:
			image_width, image_height = OPEN.get(fext, Image.open)(image_path).size
			
			x, y = image_width, image_height
			
			if x > Conf['thumb_width']:
				y = y * Conf['thumb_width'] / x
				x = Conf['thumb_width']
			if y > Conf['thumb_height']:
				x = x * Conf['thumb_height'] / y
				y = Conf['thumb_height']
			
			thumb_width, thumb_height = x, y
		
		# They don't care
		else:
			image_width, image_height = 0, 0
			thumb_width, thumb_height = 0, 0
		
		# Get the 'nice' ('45.3KB') file size of the image
		if sizes == 1:
			image_size = NiceSize(image_stat.st_size)
		else:
			image_size = None
		
		# Keep the data for a bit later
		image_data = (image_name, image_path, image_size, image_width, image_height, thumb_name, thumb_width, thumb_height)
		images.append(image_data)
	
	# All done
	return newthumbs, dirs, images, warnings

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
# Useful speedup on larger dirs
try:
	import psyco
	psyco.bind(generate_thumbnails)
	psyco.bind(JpegImagePlugin.JpegImageFile._open)
except ImportError:
	pass
