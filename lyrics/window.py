#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from lyrics.player import Player
from lyrics.config import Config
from lyrics import __version__

import curses


class Key:
	def __init__(self):
		self.binds = Config('BINDINGS')

	def input(self, window, key):
		if key == curses.KEY_RESIZE:
			window.update_track()
		elif key == self.binds['down']:
			window.scroll_down()
		elif key == self.binds['step-down']:
			window.scroll_down(self.binds['step-size'])
			window.stdscr.erase()
		elif key == self.binds['up']:
			window.scroll_up()
		elif key == self.binds['step-up']:
			window.scroll_up(self.binds['step-size'])
			window.stdscr.erase()

		elif key == self.binds['azlyrics']:
			window.player.refresh(source='azlyrics', cache=False)
			window.current_pos = 0
			window.update_track()
		elif key == self.binds['google']:
			window.player.refresh(source='google',cache=False)
			window.current_pos = 0
			window.update_track()
			
		# keys to change alignment
		elif key == self.binds['left']:
			window.player.track.alignment=1
			window.player.track.reset_width()
			window.update_track()
		elif key == self.binds['center']:
			window.player.track.alignment=0
			window.player.track.reset_width()
			window.update_track()
		elif key == self.binds['right']:
			window.player.track.alignment=2
			window.player.track.reset_width()
			window.update_track()

		elif key == self.binds['delete']:
			if window.player.track.delete_lyrics():
				window.stdscr.addstr(window.height - 1, window.width - 10,
							' Deleted ', curses.A_REVERSE)
		elif key == self.binds['help']:
			window.stdscr.erase()
			HelpPage(self.binds)
			window.height, window.width = window.stdscr.getmaxyx()
		elif key == self.binds['edit']:
			curses.endwin()
			window.player.track.edit_lyrics()
			window.stdscr = curses.initscr()
			window.current_pos = 0
			window.player.refresh(cache=True)
			window.update_track()
		elif key == self.binds['find']:
			window.find()

		# autoswitch toggle
		elif key == self.binds['autoswitchtoggle']:
			window.player.autoswitch = not window.player.autoswitch
			window.stdscr.addstr(window.height - 1, window.width - 18,
			                     f" Autoswitch: {'on' if window.player.autoswitch else 'off'} ", curses.A_REVERSE)

class HelpPage:
	def __init__(self, keybinds):
		self.keybinds = keybinds
		self.options = Config('OPTIONS')

		self.win = curses.initscr()
		self.win.box()
		self.add_text()
		self.main()

	def add_config(self, i, j, config, _keys):
		# invert keys
		for k, v in config.items():
			# set representable strings to ascii values
			if v in _keys.keys():
				v = _keys[v]
			elif k not in ['step-size', 'interval', 'mpd_port']:
				if isinstance(v, int):
					v = chr(v) # character values
			self.win.addstr(i, j, f'{k:18} {v}')
			# self.win.addstr(i, j, f'{k} \t {v}')
			i += 1
		return i

	def add_text(self):
		self.win.refresh()

		h, w = self.win.getmaxyx()
		self.win.addstr(2, 3, f"{'v' + __version__:>{w-5}}")
		self.win.addstr(3, 3, 'Help Page', curses.A_BOLD | curses.A_UNDERLINE)
		self.win.addstr(h - 2, 3, f"{'Press any key to exit...':>{w-5}}")

		keys = {  curses.KEY_UP : '↑',
			curses.KEY_DOWN : '↓',
			curses.KEY_LEFT: '←',
			curses.KEY_RIGHT: '→',
		}
		# keybinds
		i, j = 6, 3
		self.win.addstr(i, j, 'Keybindings', curses.A_UNDERLINE)
		i += 2
		i = self.add_config(i, j, self.keybinds, keys)
		# options
		if w // 2 >= 30:
			i, j = 6, w // 2 
		else:
			i += 2

		self.win.addstr(i, j, 'Default Options', curses.A_UNDERLINE)
		i+= 2
		self.add_config(i, j, self.options, keys)

	def main(self):
		# wait for key input to exit
		self.win.timeout(-1)
		self.win.getch()

		self.win.timeout(self.options['interval'])
		self.win.erase()


class Window:
	def __init__(self, stdscr, player, timeout):
		self.stdscr = stdscr
		self.height, self.width = stdscr.getmaxyx()
		self.player = player
		self.scroll_pad = curses.newpad(self.player.track.length + 2,
					self.player.track.width + 2)
		self.current_pos = 0
		self.pad_offset = 1
		self.text_padding = 5
		self.keys = Key()
		self.find_position = 0
		self.find_string = ''

		curses.use_default_colors()
		self.stdscr.timeout(timeout)
		self.set_up()

	def set_up(self):
		self.stdscr.clear()
		curses.curs_set(0)
		self.current_pos = 0
		
		if self.player.running:
			self.update_track()
			self.set_titlebar()
			self.stdscr.refresh()
			self.scroll_pad.refresh(self.current_pos, 0, 4, 
					self.pad_offset, self.height - 2, self.width - 1)
		else:
			self.stdscr.addstr(0, 1, f'{self.player.player_name} is not running!')
			self.stdscr.refresh()

	def set_titlebar(self):
		track_info = self.player.track.track_info(self.width - 1)
		# track_info -> ['title', 'artist', 'album'] - all algined
		self.stdscr.addstr(0, 1, track_info[0], curses.A_REVERSE)
		self.stdscr.addstr(1, 1, track_info[1], 
					curses.A_REVERSE | curses.A_BOLD | curses.A_DIM)
		self.stdscr.addstr(2, 1, track_info[2], curses.A_REVERSE)

	def set_statusbar(self):
		text = self.player.track.get_text(wrap=True, width=self.width - self.text_padding).lower()
		lines = text.split('\n')
		if self.current_pos < 0:
			self.current_pos = 0
		pct_progress = f' {int(self.current_pos * 100 / len(lines)) + 1}% '
		self.stdscr.move(self.height - 1, 0)
		self.stdscr.clrtoeol()
		self.stdscr.insstr(self.height - 1, self.width - len(pct_progress), pct_progress, curses.A_REVERSE)
		
	def set_offset(self):
		if self.player.track.alignment == 0:
				# center align
			self.pad_offset = (self.width - self.player.track.width) // 2
		elif self.player.track.alignment == 1:
			self.pad_offset = 2
		else:
			self.pad_offset = (self.width - self.player.track.width)
	
	def scroll_down(self, step=1):
		if self.current_pos < self.player.track.length - (self.height * 0.5):
			self.current_pos += step
		else:
			self.stdscr.addstr(self.height - 1, 1, 'END', curses.A_REVERSE)

	def scroll_up(self, step=1):
		if self.current_pos > 0:
			if self.current_pos >= self.player.track.length - \
				(self.height * 0.5):
				self.stdscr.move(self.height - 1, 0)
				self.stdscr.clrtoeol()
			self.current_pos -= step

	def find(self):
		# wait for input
		self.stdscr.timeout(-1)
		prompt = ':'
		self.stdscr.addstr(self.height - 1, self.pad_offset, prompt)
		# show cursor and key presses
		curses.echo()
		curses.curs_set(1)

		# (y, x, input max length)
		find_string = self.stdscr.getstr(self.height - 1, len(prompt)+self.pad_offset, 100).decode(encoding="utf-8").lower().strip()

		if find_string:
			# use word wrap which covers both wrap/nowrap and ensures line count is accurate
			text = self.player.track.get_text(wrap=True, width=self.width - self.text_padding).lower()
			lines = text.split('\n')

			# [0,2,4] list of lines that contain a match
			lines_map = []
			for line_num, line in enumerate(lines):
				if find_string in line:
					lines_map.append(line_num)

			# print(lines_map)
			# self.stdscr.timeout(3000)
			# self.stdscr.getch()

			# self.player.track.text = '\n'.join(lines)


			# hide cursor and key presses
			# curses.curs_set(0)
			# curses.noecho()

			# TODO: highlight some/all matches
			# TODO: show n/p on screen
			# TODO: show scroll percentage always?
			# TODO: make up scroll go further
			# TODO: show actual text from the line?
			# indices = [index for index in range(len(text)) if text.startswith(find, index)]
			# # indices = [index for index in range(len(text)) if text.startswith('\n', index)]
			# output = ''
			if len(lines_map) > 0:

				# new find
				if self.find_string != find_string:
					self.find_string = find_string
					# TODO: search from current position
					# if max(lines_map) > self.find_position:
					# 	for line in lines_map:
					# 		if line > self.find_position:
					# 			self.find_position = line
					# 			break
					# or loop back to start
					# else:
					self.find_position = 0


				while True:
					self.current_pos = lines_map[self.find_position]
					# duplicated from main()
					self.stdscr.clear()
					self.set_titlebar()
					self.stdscr.refresh()
					self.scroll_pad.refresh(self.current_pos, 0, 4, self.pad_offset, self.height - 2, self.width - 1)

					# temp stats
					pct_progress = int(self.current_pos * 100 / len(lines)) + 1

					find_string_output = f' {find_string} '
					find_count_output = f" {self.find_position + 1}/{len(lines_map)} "
					help_output = f"[{chr(self.keys.binds['find-next'])}]=next, [{chr(self.keys.binds['find-prev'])}]=prev"
					self.stdscr.addstr(self.height - 1, self.pad_offset, find_string_output, curses.A_REVERSE)
					self.stdscr.insstr(self.height - 1, self.width - len(find_count_output), find_count_output, curses.A_REVERSE)

					# single match, show brief status and exit
					if len(lines_map) == 1:
						self.find_position = 0
						self.stdscr.timeout(5000)
						self.stdscr.getch()
						break
					else:
						self.stdscr.addstr(self.height - 1, self.width - len(find_count_output) - len(help_output) - 2, help_output)

					# after finding a match in a line, stop, wait for input
					self.stdscr.timeout(-1)
					key = self.stdscr.getch()

					if key == self.keys.binds['find-next']:
						self.stdscr.addstr(self.height - 1, self.width - 3, 'n ')
						self.stdscr.clrtoeol()
						# reached end of matches, loop back to start
						if self.find_position+1 >= len(lines_map):
							self.find_position = 0
						else:
							self.find_position += 1
					elif key == self.keys.binds['find-prev']:
						self.stdscr.addstr(self.height - 1, self.width - 3, 'p ')
						self.stdscr.clrtoeol()
						if self.find_position-1 < 0:
							self.find_position = len(lines_map)-1
						else:
							self.find_position -= 1
					# Esc
					# elif key == 27 or key == self.keys.binds['quit']:
					# 	break
					else:
						break

			else:
				output = ' NOT FOUND! '
				self.stdscr.insstr(self.height - 1, self.width - len(output), output, curses.A_REVERSE)
				# timeout or key press
				self.stdscr.timeout(5000)
				self.stdscr.getch()

		# clear search line
		self.stdscr.clear()

	def update_track(self):
		self.stdscr.clear()
		self.scroll_pad.clear()

		if self.player.track.width > self.width - self.text_padding:
			text = self.player.track.get_text(wrap=True, 
						width=self.width - self.text_padding)
		else:
			text = self.player.track.get_text()

		pad_height = max(self.height, self.player.track.length) + 2
		pad_width = max(self.width, self.player.track.width) + 2

		self.scroll_pad.resize(pad_height, pad_width)
		self.scroll_pad.addstr(text)
		self.set_offset()	
		
	def main(self):
		self.options = Config('OPTIONS')
		key = ''

		while key != self.keys.binds['quit']:
			key = self.stdscr.getch()

			self.height, self.width = self.stdscr.getmaxyx()

			if key == -1:
				if self.player.update():
					self.current_pos = 0
					self.update_track()
					
			if self.player.running:
				self.keys.input(self, key)

				self.set_titlebar()
				if self.options['statusbar'] == 'on':
					self.set_statusbar()
				self.stdscr.refresh()
				self.scroll_pad.refresh(self.current_pos, 0, 4, 
							self.pad_offset, self.height - 2, self.width - 1)
			else:
				self.stdscr.clear()
				self.stdscr.addstr(0, 1, f'{self.player.player_name} player is not running.')
				self.stdscr.refresh()
