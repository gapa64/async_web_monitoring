''' Получение информации об установленных пакетах '''

import os
import os.path
import re
import sys


class DistNotFound(Exception):
	pass

# class EggLinkIsBad(DistNotFound):
# 	pass


# def read_egg_link(egg_dir):
# 	with open(egg_dir) as f:
# 		src, dist_dir = f.readlines()
# 		src = src.rstrip("\r\n")

# 		for file_src in os.listdir(src):
# 			if file_src.endswith(".egg-info"):
# 				return src, file_src, dist_dir
# 	raise EggLinkIsBad(egg_dir)


def read_file(egg_dir, files):
	''' Считывает первый попавшийся в виде строк '''

	# if egg_dir.endswith('.egg-link'):
	# 	try:
	# 		src, file_src, dist_dir = read_egg_link(egg_dir)
	# 		egg_dir = os.path.join(src, file_src)
	# 	except EggLinkIsBad:
	# 		print(f"Ошибка: в {egg_dir} нет яйца", file=sys.stderr)

	for i in files:
		path = os.path.join(egg_dir, i) if i != '' else egg_dir
		if os.path.isfile(path):
			with open(path) as f:
				return [ line.rstrip("\r\n") for line in f.readlines() ]
	return []


RE_TWICE = re.compile(r'^([\w\-]+): (.*)')
def metadata(egg_dir):
	x = {}

	for line in read_file(egg_dir, ['', 'METADATA', 'PKG-INFO']):
		m = RE_TWICE.match(line)
		if m:
			x[ m.group(1) ] = m.group(2)
	return x


RE_DIST_EXT = re.compile(r'\.(dist-info|egg-info)$')
def dists():
	''' Список установленных пакетов '''
	
	ret = []
	for syspath in sys.path:
		if os.path.isdir(syspath):
			for file in os.listdir(syspath):
				if RE_DIST_EXT.search(file):
					m = metadata(os.path.join(syspath, file))
					if 'Name' in m:
						ret.append(m['Name'])
					else:
						r, ext = os.path.splitext(file)
						ret.append(r)

	return list(sorted(ret))


def dist_info_paths(dist):
	''' Возвращает путь к информации о пакете и папке с исходниками '''
	re_dist = re.compile(r'^' + dist.replace('-', '[_-]') + r'[-.]', re.I)

	for syspath in sys.path:
		if os.path.isdir(syspath):
			for file in os.listdir(syspath):

				if re_dist.match(file):
					path = os.path.join(syspath, file)
					if file.endswith(".dist-info"):
						return syspath, path
					if file.endswith(".egg-info"):
						return syspath, path
					# if file.endswith(".egg-link"):
					# 	src, file_src, dist_dir = read_egg_link(path)
					# 	return(
					# 		os.path.abspath(os.path.join(src, dist_dir)),
					# 		os.path.join(src, file_src), 
					# 	)									
	raise DistNotFound(dist)


def dist_path(dist):
	''' Возвращает путь к каталогу с яйцом '''
	dist_dir, egg_dir = dist_info_paths(dist)
	return dist_dir


def egg(dist):
	''' Возвращает путь к каталогу яйца '''
	dist_dir, egg_dir = dist_info_paths(dist)
	return egg_dir



RE_DIST_NAME = re.compile(r'^(\w+)')
def get_dist_name(egg_dir):
	m = RE_DIST_NAME.match( os.path.basename(egg_dir) )
	return m.group(1)


def find_link(dist):
	''' Находит ссылку на яйцо '''

	maybe = dist + '.egg-link'

	for syspath in sys.path:
		if os.path.isdir(syspath):
			for s in os.listdir(syspath):
				if s == maybe:
					with open(os.path.join(syspath, s)) as f:
						return [ l.rstrip("\r\n") for l in f.readlines() ]
	return None


def files_in_dir(root_dir):
	ret = []
	for catalog, dirs, files in os.walk(root_dir):
		for i in files:
			path = os.path.join(catalog, i)
			if os.path.isfile(path):
				ret.append(path)
	return ret


def src(dist):
	''' Относительные пути к каталогам с файлами пакета '''
	dist_dir, egg_dir = dist_info_paths(dist)
	dirs = read_file(egg_dir, ["top_level.txt"])
	if dirs:
		return [os.path.join(dist_dir, i) for i in dirs]
	src_dir = os.path.join(dist_dir, get_dist_name(egg_dir))
	return [src_dir] if os.path.is_dir(src_dir) else []


def src_path(dist):
	''' Путь к последнему каталогу с файлами пакета '''
	src_dirs = src(dist)
	return src_dirs[-1] if src_dirs else None


def files(dist):
	''' Файлы с абсолютными путями '''
	dist_dir, egg_dir = dist_info_paths(dist)

	ret = read_file(egg_dir, ['installed-files.txt'])
	if ret:
		ret = [ os.path.abspath(os.path.join(egg_dir, f)) for f in ret ]

	if not ret:
		ret = [ os.path.join(dist_dir, s.split(",")[0]) 
			for s in read_file(egg_dir, ['RECORD']) ]

	if not ret:
		egg_link = find_link(dist)
		if egg_link:
			dist_dir, src_dir = egg_link
			package_dir = os.path.abspath( os.path.join(dist_dir, src_dir) )
			for s in read_file(egg_dir, ['SOURCES.txt']):
				path = os.path.join(package_dir, s)
				ret.append(path)

	if not ret:
		for src_dir in src(dist):
			ret += files_in_dir(src_dir)

	return list(sorted(ret))


def modules_in_dir(dist_dir, ls = None):
	''' Модули в директории '''
	if not ls:
		ls = files_in_dir(dist_dir)

	count = len(dist_dir)+1
	ls = [ s[count:] for s in ls if s.startswith(dist_dir) ]

	ls = ( (file[:-12] if file.endswith('/__init__.py') else file[:-3] )
		.replace('/', '.')
			for file in ls if file.endswith(".py") )

	return ls


def modules(dist):
	''' Возвращает модули установленного пакета '''
	dist_dir, egg_dir = dist_info_paths(dist)
	ls = files(dist)
	return modules_in_dir(dist_dir, ls)


def modules_from(module):
	''' выводит все модули от рутового модуля '''
	root = module.replace('.', '/')
	ret = []
	for syspath in sys.path:
		if os.path.isdir(syspath):
			path = os.path.join(syspath, root)
			if os.path.isdir(path):
				for i in modules_in_dir(path):
					if i == '__init__':
						ret.append( module )
					else:
						ret.append( f"{module}.{i}" )
	return ret


def imports(modules, *av, **kw):
	''' импортирует все указанные модули '''
	return [__import__(module, *av, **kw) for module in modules ]


def imports_from(module, **kw):
	''' импортирует все указанные модули '''
	mod = modules_from(module)
	imp = imports(mod, *av, **kw )
	return mod, imp 
