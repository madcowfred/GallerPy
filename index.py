#!/usr/bin/env python

'A simple web gallery written in Python. Supports GIF/JPEG/PNG images so far.'

__author__ = 'freddie@madcowdisease.org'
__version__ = '0.5.1'

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

# ---------------------------------------------------------------------------

import time
Started = time.time()

import cgitb
cgitb.enable()

import os
import re
import sys
import traceback

from gallerpy import load_config, generate_thumbnails, walk
from yats import TemplateDocument

# ---------------------------------------------------------------------------

import dircache
CACHE = {}

IMAGE_RE = re.compile(r'\.(gif|jpe?g|png)$', re.I)

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

def main(env=os.environ, started=Started):
	t1 = time.time()
	
	# We need these
	global SCRIPT_FILENAME, SCRIPT_NAME
	SCRIPT_FILENAME = env['SCRIPT_FILENAME']
	SCRIPT_NAME = env['SCRIPT_NAME']
	
	# Some naughty globals
	global Conf, Paths, Warnings
	Paths = {}
	Warnings = []
	
	# Find our config
	if SCRIPT_FILENAME is None:
		ShowError('CGI environment is broken!')
	
	config_file = os.path.join(os.path.dirname(SCRIPT_FILENAME), 'gallerpy.conf')
	if not os.path.isfile(config_file):
		ShowError('config file is missing!')
	
	# Parse our config
	Conf = load_config(config_file)
	
	# Work out some paths
	if not ('thumbs_local' in Conf and 'thumbs_web' in Conf):
		Conf['thumbs_web'], Conf['thumbs_local'] = GetPaths('thumbs')
		if Conf['thumbs_local'] is None:
			ShowError("Can't find your thumbnail directory!")
	
	if Conf['use_resized']:
		if not ('resized_local' in Conf and 'resized_web' in Conf):
			Conf['resized_web'], Conf['resized_local'] = GetPaths('_resized')
			if Conf['resized_local'] is None:
				ShowError("Can't find your resized image directory!")
	
	Paths['folder_image'] = GetPaths(Conf['folder_image'])[0] or 'folder.png'
	
	Conf['template'] = os.path.join(os.path.dirname(SCRIPT_FILENAME), Conf['template'])
	
	# Work out what they're after
	path_info = env.get('PATH_INFO', '') or '.'
	
	# Don't want a starting or ending seperator
	if path_info.startswith('/'):
		path_info = path_info[1:]
	
	if path_info.endswith('/'):
		path_info = path_info[:-1]
	
	# If there's an image on the end, we want it
	image_name = None
	
	bits = list(path_info.split('/'))
	
	# See if they want a full image
	global FullImage
	FullImage = 0
	
	if bits[-1] == '_full_':
		blah = bits.pop(-1)
		FullImage = 1
	
	# See if they're after an image
	m = IMAGE_RE.search(bits[-1])
	if m:
		image_name = bits.pop(-1)
		path_info = '/'.join(bits) or '.'
	
	# Don't let people go into hidden dirs
	if len(bits) > 0:
		if bits[-1] in Conf['hide_dirs']:
			ShowError('Access denied: %s', path_info)
	
	# Check the path to make sure it's valid
	image_dir = GetPaths(path_info)[1]
	if image_dir is None:
		ShowError('Path does not exist: %s', path_info)
	
	
	# We need to know what the current dir is
	Paths['current'] = path_info or '.'
	
	t2 = time.time()
	
	# Now that we've done all that, update the thumbnails
	data = UpdateThumbs(image_name)
	
	t3 = time.time()
	
	# If we have an image name, try to display it
	if image_name:
		tmpl = DisplayImage(data, image_name)
	
	# Or we could just display the directory
	else:
		tmpl = DisplayDir(data)
	
	# Work out how long it took
	elapsed = '%.3fs' % (time.time() - started)
	tmpl['elapsed'] = elapsed
	
	# If we had any warnings, add those
	if Warnings:
		tmpl['error'] = '<br>\n'.join(Warnings)
	else:
		tmpl.extract('show_error')
	
	# And spit it out
	print tmpl
	
	# Timing info
	if 0:
		print 't1: %.4fs<br>\n' % (t1 - Started)
		print 't2: %.4fs<br>\n' % (t2 - t1)
		print 't3: %.4fs<br>\n' % (t3 - t2)
		print 't4: %.4fs<br>\n' % (time.time() - t3)

# ---------------------------------------------------------------------------
# Update the thumbnails for a directory. Returns a dictionary of data
def UpdateThumbs(image_name):
	# Ask dircache for a list of files
	files = dircache.listdir(Paths['current'])
	
	if Paths['current'] in CACHE:
		if files is CACHE[Paths['current']][0]:
			data = CACHE[Paths['current']][1]
			# If they just wanted an image, return only the 1-3 they need
			if image_name:
				try:
					n = files.index(image_name)
				except ValueError:
					pass
				else:
					if n > 0:
						return { 'dirs': [], 'images': data['images'][n-1:n+2] }
					else:
						return { 'dirs': [], 'images': data['images'][n:n+2] }
			# Guess they want the whole lot
			else:
				return data
	
	# Get a sorted list of filenames
	lfiles = list(files)
	if Conf['sort_alphabetically']:
		temp = [(f.lower(), f) for f in lfiles]
		temp.sort()
		lfiles = [f[1] for f in temp]
		del temp
	else:
		lfiles.sort()
	
	# Initialise the data structure
	data = {
		'dirs': [],
		'images': [],
	}
	
	if Paths['current'] == '.':
		try:
			lfiles.remove(Conf['folder_image'])
		except ValueError:
			pass
	
	# If they want just a single image, we only have to update 1-3 thumbs...
	# but we do have to sort out files/dirs here
	n = None
	if image_name:
		realfiles = [f for f in lfiles if os.path.isfile(os.path.join(Paths['current'], f))]
		
		try:
			n = realfiles.index(image_name)
		except ValueError:
			pass
		else:
			if n > 0:
				lfiles = realfiles[n-1:n+2]
			else:
				lfiles = realfiles[n:n+2]
	
	newthumbs, data['dirs'], data['images'], warnings = generate_thumbnails(Conf, Paths['current'], lfiles)
	
	# If it's not the root dir, add '..' to the list of dirs
	if Paths['current'] != '.':
		data['dirs'].insert(0, '..')
	
	# If we had any warnings, stick them into the errors thing
	Warnings.extend(warnings)
	
	# If it was a full visit, save the cache info
	if n is None:
		CACHE[Paths['current']] = [files, data]
	
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
		for image_name, image_file, image_size, image_width, image_height, thumb_name, thumb_width, thumb_height, resized_width, resized_height in data['images']:
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
			
			row['thumb_img'] = '%s/%s' % (Conf['thumbs_web'], thumb_name)
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
		open('/tmp/silly.log', 'a').write(repr(Paths['current']) + '\n')
		open('/tmp/silly.log', 'a').write(repr(image_name) + '\n')
		open('/tmp/silly.log', 'a').write(repr(data['images']) + '\n')
		ShowError('File does not exist: %s' % image_name)
	
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
			SCRIPT_NAME, prev[1], Conf['thumbs_web'], prev[5], img_params, prev_enc)
	
	# Next image
	if n < (len(data['images']) - 1):
		next = data['images'][n+1]
		next_enc = Quote(next[0])
		img_params = ThumbImgParams(next[6], next[7])
		
		tmpl['nextlink'] = '<a href="%s/%s"><img src="%s/%s" %s><br>%s</a>' % (
			SCRIPT_NAME, next[1], Conf['thumbs_web'], next[5], img_params, next_enc)
	
	# for image_name, image_file, image_size, image_width, image_height, thumb_name, thumb_width,
	# thumb_height, resized_width, resized_height in data['images']:
	
	# If there's a resized one, we'll display that
	if Conf['use_resized'] and this[-2] and this[-1] and not FullImage:
		tmpl['this_img'] = '(resized)<br><a href="%s/%s/_full_"><img src="%s/%s" width="%s" height="%s" alt="%s"></a>' % (
			SCRIPT_NAME, this[1], Conf['resized_web'], this[5], this[-2], this[-1], this[0]
		)
	# Guess not, just display the image
	else:
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
	dsf = os.path.dirname(SCRIPT_FILENAME)
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
# Safely quote a string for a URL
def Quote(s):
	for char in (';?:@&=+$, '):
		s = s.replace(char, '%%%02X' % ord(char))
	return s

# ---------------------------------------------------------------------------

def GetTemplate(title=None):
	if title == 'Error!':
		tmpl = TemplateDocument('default.tmpl')
	else:
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
	
	SentHeader = 0
	SentFooter = 0
	
	main()
