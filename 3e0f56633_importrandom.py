import tkinter as tk
from tkinter import font as tkfont
import json as jsn
import shutil
from pathlib import Path
import os

fg = "#CA9EE6"
bg = "#303446"

# Check for dictionaries in AppData first (for installed version), then next to script (for dev)
APPDATA_DIR = Path(os.getenv('LOCALAPPDATA')) / "DictionaryApp" / "dictionaries"
LOCAL_DIR = Path(__file__).resolve().parent / "dictionaries"

if APPDATA_DIR.exists() and any(APPDATA_DIR.glob('*.json')):
	DATA_DIR = APPDATA_DIR
else:
	DATA_DIR = LOCAL_DIR

# current selected data file (will be initialized)
CURRENT_DATA_FILE = None

def get_word_text():
	try:
		if CURRENT_DATA_FILE is None:
			return "No dictionary selected"
		with CURRENT_DATA_FILE.open('r', encoding='utf-8') as f:
			data = jsn.load(f)
		# Accept either a dict with a "words" key or a top-level list
		if isinstance(data, dict):
			words = data.get('words', [])
		elif isinstance(data, list):
			words = data
		else:
			return "Unrecognized words.json structure"

		if not words:
			return "No words found in words.json"

		first = words[0]
		if isinstance(first, dict):
			word = first.get('word', '<unknown>')
			desc = first.get('description', '')
			return f"{word} — {desc}"
		else:
			# If entries are simple strings
			return str(first)
	except FileNotFoundError:
		return f"words.json not found at {DATA_FILE}"
	except Exception as e:
		return f"Error reading words.json: {e}"

def get_words():
	"""Return a normalized list of word entries. Each entry is a dict
	with at least 'word' and optional 'description'."""
	try:
		if CURRENT_DATA_FILE is None:
			return []
		with CURRENT_DATA_FILE.open('r', encoding='utf-8') as f:
			data = jsn.load(f)
		if isinstance(data, dict):
			raw = data.get('words', [])
		elif isinstance(data, list):
			raw = data
		else:
			return []

		normalized = []
		for item in raw:
			if isinstance(item, dict):
				normalized.append({
					'word': str(item.get('word', '<unknown>')),
					'description': str(item.get('description', ''))
				})
			else:
				normalized.append({'word': str(item), 'description': ''})
		return normalized
	except Exception:
		return []

root_tk = tk.Tk()
root_tk.overrideredirect(True)
root_tk.title()
root_tk.geometry("450x450")
root_tk.configure(bg=bg)

# Title bar (top) — use a Frame to host the close button
titlebar = tk.Frame(root_tk, bg="#1E212D", height=30)
titlebar.pack(side='top', fill='x')

# Dictionary selector (left of titlebar)
dict_var = tk.StringVar()
dict_menu = tk.OptionMenu(titlebar, dict_var, '')
dict_menu.config(bg="#1E212D", fg=fg, activebackground="#1E212D", highlightthickness=0)
dict_menu['menu'].config(bg="#1E212D", fg=fg)
dict_menu.pack(side='left', padx=6, pady=4)

# Small description label next to the selector
dict_desc_label = tk.Label(titlebar, text='', bg="#1E212D", fg=fg, font=("JetBrains Mono", 10), anchor='w')
dict_desc_label.pack(side='left', padx=(6,12))

# Close button inside the titlebar, aligned right
quit_button = tk.Button(
	titlebar,
	text="✕",
	command=root_tk.quit,
	bg="#1E212D",
	fg=fg,
	font=("JetBrains Mono", 12, "bold"),
	relief="flat",
	bd=0,
	highlightthickness=0,
	activebackground="#1E212D",
	activeforeground=fg,
	cursor="hand2",
)
 
# Maximize / restore state
is_maximized = False
_prev_geometry = None

def _toggle_maximize(event=None):
	global is_maximized, _prev_geometry
	try:
		if not is_maximized:
			# save current geometry
			_prev_geometry = root_tk.geometry()
			sw = root_tk.winfo_screenwidth()
			sh = root_tk.winfo_screenheight()
			# set to a larger readable size (70% of screen, with margins)
			w = max(600, int(sw * 0.7))
			h = max(500, int(sh * 0.7))
			x = max(0, int((sw - w) / 2))
			y = max(0, int((sh - h) / 4))
			root_tk.geometry(f"{w}x{h}+{x}+{y}")
			# increase fonts for readability
			_set_font_size(DEFAULT_FONT_SIZE + 4)
			is_maximized = True
		else:
			# restore
			if _prev_geometry:
				root_tk.geometry(_prev_geometry)
			_set_font_size(DEFAULT_FONT_SIZE)
			is_maximized = False
	except Exception:
		pass

# Maximize button (placed before quit)
max_button = tk.Button(
	titlebar,
	text="⛶",
	command=_toggle_maximize,
	bg="#1E212D",
	fg=fg,
	font=("JetBrains Mono", 11, "bold"),
	relief="flat",
	bd=0,
	highlightthickness=0,
	activebackground="#1E212D",
	activeforeground=fg,
	cursor="hand2",
)
max_button.pack(side='right', padx=(6,0), pady=4)

quit_button.pack(side='right', padx=6, pady=4)

# Content area: list of words (left) and detail pane (right)
content = tk.Frame(root_tk, bg=bg)
content.pack(fill='both', expand=True, padx=8, pady=(6,12*2))

left_frame = tk.Frame(content, bg=bg)
left_frame.pack(side='left', fill='y', padx=(6,8))

scrollbar = tk.Scrollbar(left_frame)
scrollbar.pack(side='right', fill='y')

# use Font objects so we can resize dynamically
DEFAULT_FONT_SIZE = 12
listbox_font = tkfont.Font(family="JetBrains Mono", size=DEFAULT_FONT_SIZE)
detail_font = tkfont.Font(family="JetBrains Mono", size=DEFAULT_FONT_SIZE)

listbox = tk.Listbox(
	left_frame,
	yscrollcommand=scrollbar.set,
	bg=bg,
	fg=fg,
	font=listbox_font,
	bd=0,
	highlightthickness=0,
	selectbackground="#2A2E3A",
	activestyle='none'
)
listbox.pack(side='left', fill='y')
scrollbar.config(command=listbox.yview)

right_frame = tk.Frame(content, bg=bg)
right_frame.pack(side='left', fill='both', expand=True, padx=(4,6))

detail = tk.Label(right_frame, text='', bg=bg, fg=fg, font=detail_font, wraplength=240, justify='left')
detail.pack(fill='both', expand=True, padx=6, pady=6)

# Populate listbox with all words
words = []

def ensure_dictionaries():
	"""Ensure the dictionaries directory exists and has at least one JSON file."""
	DATA_DIR.mkdir(parents=True, exist_ok=True)
	# if there's a top-level words.json, copy it as default.json into DATA_DIR
	top_words = Path(__file__).resolve().parent / 'words.json'
	if top_words.exists():
		dst = DATA_DIR / 'default.json'
		try:
			shutil.copy2(top_words, dst)
		except Exception:
			pass
	# if DATA_DIR has no json files, create a default one
	if not any(DATA_DIR.glob('*.json')):
		sample = DATA_DIR / 'default.json'
		sample.write_text(jsn.dumps({
			'words': [
				{'word': 'if', 'description': 'A conditional statement.'}
			]
		}, indent=2), encoding='utf-8')

def list_dictionaries():
	return sorted(DATA_DIR.glob('*.json'))

def _reload_dictionary_menu():
	files = list_dictionaries()
	menu = dict_menu['menu']
	menu.delete(0, 'end')
	name_map.clear()
	for p in files:
		name = p.stem
		name_map[name] = p
		menu.add_command(label=name, command=lambda n=name: dict_var.set(n))
	# set default selection
	if files:
		first_name = files[0].stem
		dict_var.set(first_name)

def _on_dictionary_change(*args):
	global CURRENT_DATA_FILE, words
	name = dict_var.get()
	path = name_map.get(name)
	if not path:
		return
	CURRENT_DATA_FILE = path
	# set window title from dictionary 'name' field when available
	try:
		with path.open('r', encoding='utf-8') as df:
			info = jsn.load(df)
		if isinstance(info, dict) and info.get('name'):
			title_text = str(info.get('name'))
		else:
			title_text = name
		# set description label if present
		if isinstance(info, dict) and info.get('description'):
			dict_desc_label.config(text=str(info.get('description')))
		else:
			dict_desc_label.config(text='')
	except Exception:
		title_text = name
		dict_desc_label.config(text='')
	root_tk.title(title_text)
	words = get_words()
	listbox.delete(0, 'end')
	for item in words:
		listbox.insert('end', item.get('word', str(item)))
	if words:
		listbox.selection_set(0)
		listbox.event_generate('<<ListboxSelect>>')

# mapping of display name -> Path
name_map = {}

ensure_dictionaries()
_reload_dictionary_menu()
dict_var.trace_add('write', _on_dictionary_change)

def _on_select(event):
	sel = listbox.curselection()
	if not sel:
		return
	i = sel[0]
	item = words[i]
	detail.config(text=item.get('description', ''))

listbox.bind('<<ListboxSelect>>', _on_select)
if words:
	listbox.selection_set(0)
	listbox.event_generate('<<ListboxSelect>>')

# Allow dragging the window by the titlebar (since decorations are hidden)
def _start_move(event):
	# store pointer and window start positions so we can scale deltas
	root_tk._start_pointer_x = root_tk.winfo_pointerx()
	root_tk._start_pointer_y = root_tk.winfo_pointery()
	# try to parse geometry for current window position; fallback to winfo_x/winfo_y
	try:
		geom = root_tk.geometry()  # e.g. '400x400+100+200'
		parts = geom.split('+')
		if len(parts) >= 3:
			root_tk._start_win_x = int(parts[1])
			root_tk._start_win_y = int(parts[2])
		else:
			root_tk._start_win_x = root_tk.winfo_x()
			root_tk._start_win_y = root_tk.winfo_y()
	except Exception:
		root_tk._start_win_x = root_tk.winfo_x()
		root_tk._start_win_y = root_tk.winfo_y()

def _do_move(event):
	# scale movement relative to the start window position:
	# new = start_win_pos + (pointer_delta * 1.5)
	cur_px = root_tk.winfo_pointerx()
	cur_py = root_tk.winfo_pointery()
	dx = cur_px - getattr(root_tk, '_start_pointer_x', cur_px)
	dy = cur_py - getattr(root_tk, '_start_pointer_y', cur_py)
	new_x = int(getattr(root_tk, '_start_win_x', root_tk.winfo_x()) + dx * 1.5)
	new_y = int(getattr(root_tk, '_start_win_y', root_tk.winfo_y()) + dy * 1.5)
	root_tk.geometry(f"+{new_x}+{new_y}")

titlebar.bind("<Button-1>", _start_move)
titlebar.bind("<B1-Motion>", _do_move)
titlebar.bind("<Double-Button-1>", _toggle_maximize)

# Keyboard shortcuts to resize text:
def _set_font_size(size):
	listbox_font.configure(size=size)
	detail_font.configure(size=size)

def _increase_font(event=None):
	sz = listbox_font['size']
	_set_font_size(sz + 1)

def _decrease_font(event=None):
	sz = listbox_font['size']
	if sz > 6:
		_set_font_size(sz - 1)

def _reset_font(event=None):
	_set_font_size(DEFAULT_FONT_SIZE)

# Bind keys globally; '-' to decrease, '=' or '+' to increase, 'n' to reset
root_tk.bind_all('<KeyPress-minus>', _decrease_font)
root_tk.bind_all('<KeyPress-underscore>', _decrease_font)
root_tk.bind_all('<KeyPress-plus>', _increase_font)
root_tk.bind_all('<KeyPress-equal>', _increase_font)
root_tk.bind_all('<KeyPress-n>', _reset_font)

# ensure the window receives key events
root_tk.focus_force()

root_tk.mainloop()