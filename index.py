#!/usr/bin/env python

'A simple web gallery written in Python. Supports GIF/JPEG/PNG images so far.'

__author__ = 'freddie@madcowdisease.org'
__version__ = '0.3.0'

# ---------------------------------------------------------------------------
# We need to know when we started for later
import time
Started = time.time()

import base64
import Image
import os
import re
import sys
import traceback

from ConfigParser import ConfigParser
from yats import TemplateDocument

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

SCRIPT_NAME = os.getenv('SCRIPT_NAME')

# ---------------------------------------------------------------------------
# Spit out a traceback in a sane manner
def ExceptHook(etype, evalue, etb):
	tmpl = GetTemplate('Error!')
	
	tmpl.extract('show_dirs')
	tmpl.extract('show_images')
	tmpl.extract('show_image')
	
	lines = []
	
	for entry in traceback.extract_tb(etb):
		line = '&nbsp;&nbsp;File "<b>%s</b>", line <b>%d</b>, in <b>%s</b><br>' % entry[:-1]
		lines.append(line)
		line = '&nbsp;&nbsp;&nbsp;&nbsp;%s<br><br>' % entry[-1]
		lines.append(line)
	
	for line in traceback.format_exception_only(etype, evalue):
		line = line.replace('\n', '')
		lines.append(line)
	
	# Build the error string
	tmpl['error'] = '\n'.join(lines)
	
	# Spit it out
	print tmpl
	
	sys.exit(0)

# ---------------------------------------------------------------------------

def ShowError(text, *args):
	if args:
		text = text % args
	
	tmpl = GetTemplate('Error!')
	
	tmpl.extract('show_dirs')
	tmpl.extract('show_images')
	tmpl.extract('show_image')
	
	tmpl['error'] = text
	print tmpl
	
	sys.exit(0)

# ---------------------------------------------------------------------------

def main():
	# Some naughty globals
	global Conf, Paths, Warnings
	Conf = {}
	Paths = {}
	Warnings = []
	
	# Find our config
	config_file = os.path.join(os.path.dirname(os.getenv('SCRIPT_FILENAME')), 'gallerpy.conf')
	if not os.path.isfile(config_file):
		ShowError('config file is missing!')
	
	# Parse our config
	c = ConfigParser()
	c.read(config_file)
	
	for option in c.options('options'):
		if option.startswith('thumb_') or option.startswith('image_'):
			Conf[option] = int(c.get('options', option))
		else:
			Conf[option] = c.get('options', option)
	
	# Use a dictionary for speedy lookup of hidden stuff?
	hide = {}
	for h in Conf.get('hide_dirs', '').split('|'):
		hide[h] = 1
	Conf['hide_dirs'] = hide
	
	del c
	
	# Work out some paths
	if 'thumbs_local' in Conf and 'thumbs_web' in Conf:
		Paths['thumbs_local'] = Conf['thumbs_local']
		Paths['thumbs_web'] = Conf['thumbs_web']
	else:
		Paths['thumbs_web'], Paths['thumbs_local'] = GetPaths('thumbs')
		if Paths['thumbs_local'] is None:
			ShowError("Can't find your thumbnail directory!")
	
	Paths['folder_image'] = GetPaths(Conf['folder_image'])[0] or 'folder.png'
	
	# Work out what they're after
	path_info = os.getenv('PATH_INFO') or '.'
	
	# Don't want a starting or ending seperator
	if path_info.startswith('/'):
		path_info = path_info[1:]
	
	if path_info.endswith('/'):
		path_info = path_info[:-1]
	
	# If there's an image on the end, we want it
	image_name = None
	
	bits = list(os.path.split(path_info))
	m = IMAGE_RE.match(bits[-1])
	if m:
		image_name = bits.pop(-1)
		path_info = '/'.join(bits) or '.'
	
	# Don't let people go into hidden dirs
	if len(bits) > 0:
		if bits[-1] in Conf['hide_dirs']:
			ShowError('Path does not exist: %s', path_info)
	
	# Check the path to make sure it's valid
	image_dir = GetPaths(path_info)[1]
	if image_dir is None:
		ShowError('Path does not exist: %s', path_info)
	
	
	# We need to know what the current dir is
	Paths['current'] = path_info or '.'
	
	# Now that we've done all that, update the thumbnails
	data = UpdateThumbs(image_name)
	
	# If we have an image name, try to display it
	if image_name:
		tmpl = DisplayImage(data, image_name)
	
	# Or we could just display the directory
	else:
		tmpl = DisplayDir(data)
	
	# Work out how long it took
	elapsed = '%.3fs' % (time.time() - Started)
	tmpl['elapsed'] = elapsed
	
	# If we had any warnings, add those
	if Warnings:
		tmpl['error'] = '<br>\n'.join(Warnings)
	else:
		tmpl.extract('show_error')
	
	# And spit it out
	print tmpl

# ---------------------------------------------------------------------------
# Update the thumbnails for a directory. Returns a dictionary of data
def UpdateThumbs(image_name):
	# Initialise the data structure
	data = {
		'dirs': [],
		'images': [],
	}
	
	# If it's not the root dir, add '..' to the list of dirs
	if Paths['current'] != '.':
		data['dirs'].append('..')
	
	# Shortcuts
	_b64_enc = base64.encodestring
	_nicesize = NiceSize
	_stat = os.stat
	
	# Get a sorted list of filenames
	files = os.listdir(Paths['current'])
	files.sort()
	
	images = []
	
	for filename in files:
		now = time.time()
		
		if Paths['current'] == '.':
			image_file = filename
		else:
			image_file = os.path.join(Paths['current'], filename)
		
		# It's a directory!
		if os.path.isdir(image_file):
			data['dirs'].append(filename)
		
		# It's our folder image, nooo
		elif Paths['current'] == '.' and filename == Conf['folder_image']:
			continue
		
		else:
			# It's not an image format we know about
			m = IMAGE_RE.match(image_file)
			if not m:
				continue
			
			root = m.group(1)
			ext = m.group(2).lower()
			
			images.append([filename, image_file, root, ext])
	
	# If they want just a single image, we only have to update 1-3 thumbs
	only_update = []
	
	if image_name:
		matches = [i for i in images if i[0] == image_name]
		if matches:
			n = images.index(matches[0])
			if n > 0:
				only_update.append(images[n-1][0])
			only_update.append(matches[0][0])
			if n < (len(images) - 1):
				only_update.append(images[n+1][0])
	
	# Now we do the thumbnail stuff
	for filename, image_file, root, ext in images:
		# Skippity skip
		if only_update and filename not in only_update:
			continue
		
		# Work out our goofy thumbnail name
		b64 = _b64_enc(root).replace('\n', '')
		thumb_name = '%s.%s' % (b64, ext)
		thumb_file = os.path.join(Paths['thumbs_local'], thumb_name)
		
		# If it exists and is old, delete it
		image_stat = _stat(image_file)
		try:
			thumb_stat = _stat(thumb_file)
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
		
		# Make a new thumbnail if we have to
		if gen_thumb:
			try:
				img = OPEN.get(ext, Image.open)(image_file)
			except IOError, msg:
				warning = "Warning: failed to open '%s' - %s" % (filename, msg)
				Warnings.append(warning)
				continue
			
			image_width, image_height = img.size
			
			# Resize and save it
			try:
				img.thumbnail((Conf['thumb_width'], Conf['thumb_height']), Image.BICUBIC)
			except IOError, msg:
				warning = "Warning: failed to resize '%s' - %s" % (filename, msg)
				Warnings.append(warning)
				continue
			
			thumb_width, thumb_height = img.size
			
			try:
				img.save(thumb_file)
			except:
				warning = "Warning: failed to resize '%s'!<br>" % (filename)
				Warnings.append(warning)
				continue
		
		# Get some info on the image/thumbnail if we need to
		else:
			image_width, image_height = OPEN.get(ext, Image.open)(image_file).size
			
			x, y = image_width, image_height
			
			if x > Conf['thumb_width']:
				y = y * Conf['thumb_width'] / x
				x = Conf['thumb_width']
			if y > Conf['thumb_height']:
				x = x * Conf['thumb_height'] / y
				y = Conf['thumb_height']
			
			thumb_width, thumb_height = x, y
		
		# Get the 'nice' ('45.3KB') size of the image
		image_size = _nicesize(image_stat.st_size)
		
		# Keep the data for a bit later
		image_data = (filename, image_file, image_size, image_width, image_height, thumb_name, thumb_width, thumb_height)
		data['images'].append(image_data)
	
	# If we had any warnings, stick them into the errors thing
	
	
	# Throw the info back
	return data

# ---------------------------------------------------------------------------
# Spit out a nicely formatted listing of a directory
def DisplayDir(data):
	# Get our template
	if Paths['current'] == '.':
		nicepath = '/'
	else:
		nicepath = '/%s' % Paths['current']
	
	tmpl = GetTemplate(nicepath)
	
	# Extract stuff we don't need
	tmpl.extract('show_image')
	
	shown = 0
	
	# If we have some dirs, display them
	dirs = []
	
	if data['dirs']:
		for directory in data['dirs']:
			# Skip hidden dirs
			if directory in Conf['hide_dirs']:
				continue
			
			# Parent dir
			elif directory == '..':
				shown = 1
				
				blat = os.path.join(Paths['current'], '..')
				dir_link = os.path.normpath(blat)
			
			else:
				shown = 1
				if Paths['current'] == '.':
					dir_link = directory
				else:
					dir_link = '%s/%s' % (Paths['current'], directory)
			
			row = {
				'dir_desc': directory.replace('_', ' '),
				'dir_link': '%s/%s' % (SCRIPT_NAME, dir_link),
				'folder_img': Paths['folder_image'],
			}
			
			dirs.append(row)
	
	tmpl['dirs'] = tuple(dirs)
	if not dirs:
		tmpl.extract('show_dirs')
	
	
	# If we have some images, display those
	images = []
	
	if data['images']:
		for image_name, image_file, image_size, image_width, image_height, thumb_name, thumb_width, thumb_height in data['images']:
			row = {}
			
			# Maybe add some extra stuff
			parts = []
			
			if Conf['thumb_name']:
				part = '<br>%s' % image_name.replace('_', ' ')
				parts.append(part)
			
			if Conf['thumb_dimensions']:
				part = '<br><span>(%s x %s)</span>' % (image_width, image_height)
				parts.append(part)
			
			if Conf['thumb_size']:
				part = '<br><span>%s</span>' % (image_size)
				parts.append(part)
			
			row['extra'] = ''.join(parts)
			
			row['image_link'] = '%s/%s' % (SCRIPT_NAME, Quote(image_file))
			
			row['thumb_img'] = '%s/%s' % (Paths['thumbs_web'], thumb_name)
			row['thumb_params'] = ThumbImgParams(thumb_width, thumb_height)
			
			images.append(row)
	
	tmpl['images'] = tuple(images)
	if not images:
		tmpl.extract('show_images')
	
	return tmpl

# ---------------------------------------------------------------------------
# Display an image page
def DisplayImage(data, image_name):
	# See if it's really there
	matches = [i for i in data['images'] if i[0] == image_name]
	if not matches:
		ShowError('file does not exist!')
	
	if Paths['current'] == '.':
		nicepath = '/'
	else:
		nicepath = '/%s' % Paths['current']
	nicepath = '%s/%s' % (nicepath, image_name)
	
	tmpl = GetTemplate(nicepath)
	
	# Extract stuff we don't need
	tmpl.extract('show_dirs')
	tmpl.extract('show_images')
	
	# Work out the prev/next images too
	this = matches[0]
	prevlink = ''
	nextlink = ''
	
	n = data['images'].index(this)
	
	# filename, path+filename, img_size, img_width, img_height, thumb_name, thumb_width, thumb_height
	
	# Previous image
	if n > 0:
		prev = data['images'][n-1]
		prev_enc = Quote(prev[0])
		img_params = ThumbImgParams(prev[6], prev[7])
		
		tmpl['prevlink'] = '<a href="%s/%s"><img src="%s/%s" %s><br>%s</a>' % (
			SCRIPT_NAME, prev[1], Paths['thumbs_web'], prev[5], img_params, prev_enc)
	
	# Next image
	if n < (len(data['images']) - 1):
		next = data['images'][n+1]
		next_enc = Quote(next[0])
		img_params = ThumbImgParams(next[6], next[7])
		
		tmpl['nextlink'] = '<a href="%s/%s"><img src="%s/%s" %s><br>%s</a>' % (
			SCRIPT_NAME, next[1], Paths['thumbs_web'], next[5], img_params, next_enc)
	
	# This image
	tmpl['this_img'] = '<img src="%s" width="%s" height="%s" alt="%s">' % (
		Quote(GetPaths(this[1])[0]), this[3], this[4], this[0])
	
	# Work out what extra info we need to display
	parts = []
	
	if Conf['image_name']:
		part = '<h2>%s</h2><br>\n' % (this[0])
		parts.append(part)
	if Conf['image_dimensions']:
		part = '<span>%s x %s</span><br>\n' % (this[3], this[4])
		parts.append(part)
	if Conf['image_size']:
		part = '<span>%s</span><br>\n' % (this[2])
		parts.append(part)
	
	tmpl['extra'] = ''.join(parts)
	
	tmpl['dir_path'] = '%s/%s' % (SCRIPT_NAME, Paths['current'])
	tmpl['folder_img'] = Paths['folder_image']
	
	#prevlink, SCRIPT_NAME, Paths['current'], Paths['folder_image'], nextlink, extra, this_img)
	
	return tmpl

# ---------------------------------------------------------------------------
# Get a (URL, local) path for something
def GetPaths(path):
	dsf = os.path.dirname(os.getenv('SCRIPT_FILENAME'))
	dsn = os.path.dirname(SCRIPT_NAME)
	
	# Absolute path
	if path.startswith(os.sep):
		return (path, None)
	# HTTP URL
	elif path.startswith('http://'):
		return (path, None)
	# Relative path
	else:
		localpath = os.path.normpath(os.path.join(dsf, path))
		
		# They're going wandering, or it doesn't exist
		if not localpath.startswith(dsf) or not os.path.exists(localpath):
			return (None, None)
		
		else:
			remotepath = os.path.join(dsn, path)
			return (remotepath, localpath)

# ---------------------------------------------------------------------------
# Return a string usable as <img> tag parameters
def ThumbImgParams(width, height):
	params = 'width="%s" height="%s"' % (width, height)
	
	if Conf['thumb_pad']:
		pad_top = Conf['thumb_height'] - height
		if pad_top > 0:
			params += ' style="padding-top: %spx;"' % pad_top
	
	return params

# ---------------------------------------------------------------------------
# Return a nicely formatted size
def NiceSize(bytes):
	if bytes < 1024:
		return '%dB' % (bytes)
	elif bytes < (1024 * 1024):
		return '%.1fKB' % (bytes / 1024.0)
	else:
		return '%.1fMB' % (bytes / 1024.0 / 1024.0)

# Safely quote a string for a URL
def Quote(s):
	for char in (';?:@&=+$, '):
		s = s.replace(char, '%%%02X' % ord(char))
	return s

# ---------------------------------------------------------------------------

def GetTemplate(title=None):
	tmpl = TemplateDocument(Conf['template'])
	
	# Build our shiny <title>
	gallery_name = Conf.get('gallery_name', 'GallerPy %s' % __version__)
	
	if title:
		tmpl['title'] = '%s :: %s' % (gallery_name, title)
	else:
		tmpl['title'] = '%s' % (gallery_name)
	
	# Find our CSS file
	css_file = GetPaths(Conf['css_file'])[0]
	if css_file is None:
		css_file = 'default.css'
	tmpl['css_file'] = css_file
	
	# Work out the box size for thumbnails
	tmpl['thumb_width'] = Conf['thumb_width'] + 10
	
	add = (Conf['thumb_name'] + Conf['thumb_dimensions'] + Conf['thumb_size']) * 15
	tmpl['thumb_height'] = Conf['thumb_height'] + 15 + add
	
	# Our version!
	tmpl['version'] = __version__
	
	# And send it back
	return tmpl

# ---------------------------------------------------------------------------

if __name__ == '__main__':
	# Replace our exception handler with a magic one
	sys.excepthook = ExceptHook
	
	# Useful speedup
	try:
		#pass
		import psyco
		#psyco.bind(DisplayDir)
		psyco.bind(UpdateThumbs)
		psyco.bind(JpegImagePlugin.JpegImageFile._open)
	except:
		pass
	
	#import profile
	#profile.run('main()', 'profile.data')
	
	SentHeader = 0
	SentFooter = 0
	
	main()
