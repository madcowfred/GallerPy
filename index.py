#!/usr/bin/env python

"""
A simple web gallery written in Python. Supports GIF/JPEG/PNG images so far.
"""

__author__ = 'freddie@madcowdisease.org'
__version__ = '0.1'

# SET THIS!
CONFIG_FILE = '/home/freddie/source/python/GallerPy/test.conf'

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

def ExceptHook(etype, evalue, etb):
	html_header('Error!')
	traceback.print_exception(etype, evalue, etb)
	html_footer()
	sys.exit(0)

# ---------------------------------------------------------------------------

def ShowError(text, *args):
	if args:
		text = text % args
	html_header('Error!')
	print text
	html_footer()
	sys.exit(0)

# ---------------------------------------------------------------------------

def main():
	# Some naughty globals
	global Conf, Paths
	Conf = {}
	Paths = {}
	
	# Parse our config
	c = ConfigParser()
	c.read(CONFIG_FILE)
	
	for option in c.options('options'):
		if option.startswith('thumb_') or option.startswith('image_'):
			Conf[option] = int(c.get('options', option))
		else:
			Conf[option] = c.get('options', option)
	
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
	
	# Spit out a header
	html_header()
	
	#for k, v in os.environ.items():
	#	print '%s == %s<br>' % (k, v)
	
	# Work out what they're after
	path_info = os.getenv('PATH_INFO') or '.'
	
	# Don't want a starting seperator
	if path_info.startswith(os.sep):
		path_info = path_info[len(os.sep):]
	
	# If there's an image on the end, we wants it
	image_name = None
	
	bits = os.path.split(path_info)
	m = IMAGE_RE.match(bits[-1])
	if m:
		image_name = bits[-1]
		path_info = os.path.join(*bits[:-1]) or '.'
	
	# Check the path to make sure it's valid
	image_dir = GetPaths(path_info)[1]
	if image_dir is None:
		ShowError('Path does not exist: %s', path_info)
	
	# We need to know what the current dir is
	Paths['current'] = path_info or '.'
	
	# Now that we've done all that, update the thumbnails
	data = UpdateThumbs(image_name)
	#print 'UpdateThumbs: %.5fs<br>' % (time.time() - Started)
	
	# If we have an image name, try to display it
	if image_name:
		fudgeval = DisplayImage(data, image_name)
	
	# Or we could just display the directory
	else:
		fudgeval = DisplayDir(data)
	
	#print 'Display: %.5fs' % (time.time() - Started)
	
	# Spit out a footer
	html_footer(fudgeval)

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
			img = OPEN.get(ext, Image.open)(image_file)
			image_width, image_height = img.size
			
			# Resize and save it
			img.thumbnail((Conf['thumb_width'], Conf['thumb_height']), Image.BICUBIC)
			thumb_width, thumb_height = img.size
			try:
				img.save(thumb_file)
			except:
				print 'Warning: failed to resize %s!<br>' % (filename)
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
	
	# Throw the info back
	return data

# ---------------------------------------------------------------------------
# Spit out a nicely formatted listing of a directory
def DisplayDir(data):
	shown = 0
	
	# If we have some dirs, display them
	if data['dirs']:
		# Use a dictionary for speedy lookup
		hidden = {}
		for h in Conf.get('hide_dirs', '').split('|'):
			hidden[h] = 1
		
		for directory in data['dirs']:
			# Skip hidden dirs
			if directory in hidden:
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
			
			dir_desc = directory.replace('_', ' ')
			
			# Spit it out
			print \
"""<div class="folder"><a href="%s/%s"><img src="%s" alt="folder"><br>%s</a></div>""" % (
	SCRIPT_NAME, dir_link, Paths['folder_image'], dir_desc)
	
	# If we have some images, display those
	if data['images']:
		# If we spat out some dirs, put a seperator in
		if shown:
			print \
"""
<div class="spacer"></div>
</div>
<div class="container">
<div class="spacer"></div>
"""
		
		# Lines we want to print
		lines = []
		
		# Save on function lookups
		_quote = Quote
		_tip = ThumbImgParams
		for image_name, image_file, image_size, image_width, image_height, thumb_name, thumb_width, thumb_height in data['images']:
			# Work out the <img> parameters
			img_params = _tip(thumb_width, thumb_height)
			
			# Maybe add some extra stuff
			extras = []
			
			if Conf['thumb_name']:
				nice_name = image_name.replace('_', ' ')
				extras.append(nice_name)
			
			if Conf['thumb_dimensions']:
				extra = '<span>(%s x %s)</span>' % (image_width, image_height)
				extras.append(extra)
			
			if Conf['thumb_size']:
				extra = '<span>%s</span>' % (image_size)
				extras.append(extra)
			
			if extras:
				extra = '<br>' + '<br>'.join(extras)
			
			# Build the line and keep it for later
			line = \
"""<div class="thumbnail"><a href="%s/%s"><img src="%s/%s" %s></a>%s</div>""" % (
	SCRIPT_NAME, _quote(image_file), Paths['thumbs_web'], thumb_name, img_params, extra)
			
			lines.append(line)
		
		t = time.time()
		
		if lines:
			print '\n'.join(lines)
		
		return time.time() - t

# ---------------------------------------------------------------------------
# Display an image page
def DisplayImage(data, image_name):
	# See if it's really there
	matches = [i for i in data['images'] if i[0] == image_name]
	if not matches:
		print 'ERROR: file does not exist!'
		return
	
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
		
		prevlink = '<a href="%s/%s"><img src="%s/%s" %s><br>%s</a>' % (
			SCRIPT_NAME, prev[1], Paths['thumbs_web'], prev[5], img_params, prev_enc)
	
	# Next image
	if n < (len(data['images']) - 1):
		next = data['images'][n+1]
		next_enc = Quote(next[0])
		img_params = ThumbImgParams(next[6], next[7])
		
		nextlink = '<a href="%s/%s"><img src="%s/%s" %s><br>%s</a>' % (
			SCRIPT_NAME, next[1], Paths['thumbs_web'], next[5], img_params, next_enc)
	
	# This image
	this_img = '<img src="%s" width="%s" height="%s" alt="%s">' % (
		Quote(GetPaths(this[1])[0]), this[3], this[4], this[0])
	
	# Work out what extra info we need to display
	parts = []
	if Conf['image_name']:
		part = '<h2>%s</h2>' % (this[0])
		parts.append(part)
	if Conf['image_dimensions']:
		part = '<span>%s x %s</span>' % (this[3], this[4])
		parts.append(part)
	if Conf['image_size']:
		part = '<span>%s</span>' % (this[2])
		parts.append(part)
	
	if parts:
		extra = '<br>\n'.join(parts)
	else:
		extra = ''
	
	
	t = time.time()
	
	print \
"""<table border="0" cellpadding="0" cellspacing="0" align="center">
<tr>
<td width="300" valign="bottom" align="center">%s</td>
<td width="100" valign="bottom" align="center"><a href="%s/%s"><img src="%s" alt="folder"><br>Back</a></td>
<td width="300" valign="bottom" align="center">%s</td>
</tr>
</table>
</div>
<div class="container">
<div class="spacer"></div>
<div class="image">
%s
%s
</div>""" % (
	prevlink, SCRIPT_NAME, Paths['current'], Paths['folder_image'], nextlink, extra, this_img)
	
	return time.time() - t

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

def html_header(title=None):
	global SentHeader
	if SentHeader:
		return
	SentHeader = 1
	
	if title:
		title = 'GallerPy %s: %s' % (__version__, title)
	else:
		title = 'GallerPy %s' % (__version__)
	
	# Find our CSS file
	css_file = GetPaths(Conf['css_file'])[0]
	if css_file is None:
		css_file = 'default.css'
	
	# Work out the box size for thumbnails
	thumb_width = Conf['thumb_width'] + 10
	
	add = (Conf['thumb_name'] + Conf['thumb_dimensions'] + Conf['thumb_size']) * 15
	thumb_height = Conf['thumb_height'] + 15 + add
	
	# Standard header
	print 'Content-type: text/html'
	print
	
	# HTML junk
	print \
"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title>%s</title>
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">
<link rel="stylesheet" title="Default" href="%s">
<style type="text/css">
div.thumbnail {
	float: left;
	width: %dpx;
	height: %dpx;
	padding: 3px 3px 0px 3px;
	text-align: center;
}
</style>
</head>

<body>
<div class="container">
<div class="spacer"></div>
""" % (title, css_file, thumb_width, thumb_height)

# ---------------------------------------------------------------------------

def html_footer(fudgeval=None):
	global SentFooter
	if SentFooter:
		return
	SentFooter = 1
	
	if fudgeval is None:
		fudgeval = 0.0
	elapsed = '%.3fs' % (max(0.0, time.time() - Started - fudgeval))
	
	print \
"""<div class="spacer"></div>
</div>
<p class="footer">Generated in %s by <a href="http://www.madcowdisease.org/projects.php/GallerPy">GallerPy</a> %s</p>
</body>
</html>
""" % (elapsed, __version__)

# ---------------------------------------------------------------------------

if __name__ == '__main__':
	# Replace our exception handler with a magic one
	sys.excepthook = ExceptHook
	
	# Useful speedup
	try:
		#pass
		import psyco
		psyco.bind(DisplayDir)
		psyco.bind(UpdateThumbs)
		psyco.bind(JpegImagePlugin.JpegImageFile._open)
	except:
		pass
	
	#import profile
	#profile.run('main()', 'profile.data')
	
	SentHeader = 0
	SentFooter = 0
	
	main()
