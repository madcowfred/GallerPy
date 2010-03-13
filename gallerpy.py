# Copyright (c) 2004-2008, Freddie
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

from __future__ import generators

"This file contains the various common code that we would like to use."

__author__ = 'Freddie (freddie@madcowdisease.org)'
__version__ = '0.8.0svn'

import hashlib
import os
import sys

from ConfigParser import ConfigParser

# Slightly faster way to make images load
sys.path.append(os.path.expanduser('~/lib/python/PIL'))

import Image
import GifImagePlugin
import JpegImagePlugin
import PngImagePlugin

OPEN = {
	'.gif': GifImagePlugin.GifImageFile,
	'.jpe': JpegImagePlugin.JpegImageFile,
	'.jpeg': JpegImagePlugin.JpegImageFile,
	'.jpg': JpegImagePlugin.JpegImageFile,
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
	
	hide_dirs = {}
	for k in Conf['hide_dirs'].split('|'):
		hide_dirs[k] = 1
	Conf['hide_dirs'] = hide_dirs
	
	return Conf

# ---------------------------------------------------------------------------
# Generate thumbnails
def generate_thumbnails(Conf, root, files, sizes=1):
	dirs = []
	images = []
	warnings = []
	newthumbs = 0
	
	# Work out what resize mode we're supposed to use
	if Conf['resize_method'] == 'antialias':
		resize_method = Image.ANTIALIAS
	else:
		resize_method = Image.BICUBIC
	
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
		
		# We use an MD5 digest of the file path+name for the thumbnail name
		md5sum = hashlib.md5(image_path).hexdigest()
		
		# Work out our thumbnail filename
		if Conf['thumb_jpeg']:
			thumb_name = '%s.jpg' % (md5sum)
		else:
			thumb_name = '%s%s' % (md5sum, fext)
		thumb_path = os.path.join(Conf['thumbs_local'], thumb_name)
		
		# See if we need to generate a new thumbnail
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
		
		# If resized is enabled, I guess we do that
		if Conf['use_resized']:
			# Work out our resized filename
			resized_path = os.path.join(Conf['resized_local'], thumb_name)
			
			# See if we need to generate a new resized image
			try:
				resized_stat = os.stat(resized_path)
			except OSError:
				gen_resized = 1
			else:
				if image_stat.st_mtime > resized_stat.st_mtime:
					try:
						os.remove(resized_path)
					except OSError:
						continue
					else:
						gen_resized = 1
				else:
					gen_resized = 0
		# Or not
		else:
			gen_resized = 0
		
		
		# Make a new thumbnail if we have to
		if gen_thumb:
			# Open the image
			try:
				img = OPEN.get(lfext, Image.open)(image_path)
			except Exception, msg:
				warning = "Warning: failed to open '%s' - %s" % (image_name, msg)
				warnings.append(warning)
				continue
			
			image_width, image_height = img.size
			
			# If it's not a truecolor image, make it one
			if Conf['thumb_jpeg'] and img.mode != 'RGB':
				img = img.convert('RGB')
			
			# Thumbnail it
			try:
				img.thumbnail((Conf['thumb_width'], Conf['thumb_height']), resize_method)
			except Exception, msg:
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
		
		# Or we need to get image size info from the file
		elif sizes == 1:
			image_width, image_height = OPEN.get(lfext, Image.open)(image_path).size
			
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
		
		
		# Make a new resized image if we have to
		if gen_resized:
			# Open the image
			try:
				img = OPEN.get(lfext, Image.open)(image_path)
			except Exception, msg:
				warning = "Warning: failed to open '%s' - %s" % (image_name, msg)
				warnings.append(warning)
				continue
			
			image_width, image_height = img.size
			
			# See if it's worth resizing
			if image_width > Conf['resized_width'] or image_height > Conf['resized_height']:
				# Resize it
				try:
					img.thumbnail((Conf['resized_width'], Conf['resized_height']), resize_method)
				except Exception, msg:
					warning = "Warning: failed to resize '%s' - %s" % (image_name, msg)
					warnings.append(warning)
					continue
				
				resized_width, resized_height = img.size
				
				# Save the resized image
				try:
					img.save(resized_path)
				except Exception, msg:
					warning = "Warning: failed to save '%s' - %s" % (image_name, msg)
					warnings.append(warning)
					continue
			
			else:
				resized_width, resized_height = 0, 0
		
		# Or we need to get image size info from the file
		elif sizes == 1:
			if (image_width, image_height) == (0, 0):
				image_width, image_height = OPEN.get(lfext, Image.open)(image_path).size
			
			x, y = image_width, image_height
			
			if x > Conf['resized_width']:
				y = y * Conf['resized_width'] / x
				x = Conf['resized_width']
			if y > Conf['resized_height']:
				x = x * Conf['resized_height'] / y
				y = Conf['resized_height']
			
			resized_width, resized_height = x, y
		
		# They don't care
		else:
			image_width, image_height = 0, 0
			thumb_width, thumb_height = 0, 0
			resized_width, resized_height = 0, 0
		
		
		# Get the 'nice' ('45.3KB') file size of the image
		if sizes == 1:
			image_size = NiceSize(image_stat.st_size)
		else:
			image_size = None
		
		# Keep the data for a bit later
		image_data = (image_name, image_path, image_size, image_width, image_height, thumb_name, thumb_width, thumb_height, resized_width, resized_height)
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
MB = 1024.0 * 1024
def NiceSize(bytes):
	if bytes < 1024:
		return '%dB' % (bytes)
	elif bytes < MB:
		return '%.1fKB' % (bytes / 1024.0)
	else:
		return '%.1fMB' % (bytes / MB)

# ---------------------------------------------------------------------------
# Useful speedup on larger dirs
try:
	import psyco
	psyco.bind(generate_thumbnails)
	psyco.bind(JpegImagePlugin.JpegImageFile._open)
except ImportError:
	pass
