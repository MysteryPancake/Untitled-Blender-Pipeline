import bpy, os, re
from typing import Any, Iterable

class SourceFile:
	"""
	Struct representing a Blender asset layer file.\n
	Path: Full path to layer file, eg. `"path\\to\\cube_model_v001.blend"`
	Name: Asset name, eg. `"cube"`
	Layer: Layer name, eg. `"models"`
	Version: Layer version, starting at 1.
	"""
	def __init__(self, path: str, name: str, layer: str, version: int):
		self.path = path
		self.name = name
		self.layer = layer
		self.version = version

# ---------------------------------------------------------------------------
# Preferences / paths
# ---------------------------------------------------------------------------

def get_prefs(context: bpy.types.Context | None = None) -> Any:
	"""Addon preferences, or `None` when the addon isn't enabled"""
	context = context or bpy.context
	addon = context.preferences.addons.get(__package__)
	return addon.preferences if addon else None

ENV_VAR = "SG_DATABASE"

def get_database() -> str:
	"""Absolute path of the database folder from the `SG_DATABASE` environment variable"""
	path = os.environ.get(ENV_VAR, "").strip()
	if not path:
		return ""
	# Allow "~" and %VARS% / $VARS
	path = os.path.expandvars(os.path.expanduser(path))
	return os.path.normpath(bpy.path.abspath(path))

# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

_VERSION_RE = re.compile(r"_v(\d+)\.blend$")

def list_versions(folder: str) -> list[tuple[int, str]]:
	"""All versioned `.blend` files in a folder as `(version, full_path)`"""
	if not os.path.isdir(folder):
		return []
	found = []
	for name in os.listdir(folder):
		match = _VERSION_RE.search(name)
		if match:
			found.append((int(match.group(1)), os.path.join(folder, name)))
	return sorted(found)

def latest_version(folder: str) -> int:
	"""Highest version number in a folder (0 if there's none)"""
	versions = list_versions(folder)
	return versions[-1][0] if versions else 0

# ---------------------------------------------------------------------------
# Asset names (shared with the website, see server/assetRouter.js and blendDb.js)
# ---------------------------------------------------------------------------

# Same rule as the website: letters, numbers, spaces, hyphens and underscores
_ASSET_NAME_RE = re.compile(r"[\w\- ]+", re.ASCII)

def clean_asset_name(name: str) -> str:
	"""Trims and validates an asset name"""
	name = name.strip()
	if not name:
		raise ValueError("Please type in an asset!")
	if not _ASSET_NAME_RE.fullmatch(name):
		raise ValueError("Asset names can only contain letters, numbers, spaces, hyphens and underscores!")
	if len(name) > 255:
		raise ValueError("Asset name is too long! Keep it under 256 characters.")
	return name

def _subfolders(folder: str) -> list[str]:
	if not os.path.isdir(folder):
		return []
	return [e for e in os.listdir(folder) if os.path.isdir(os.path.join(folder, e))]

def list_assets() -> list[str]:
	"""Every asset with a `wip` or `build` folder, including assets added on the website"""
	database = get_database()
	if not database:
		return []
	found: dict[str, str] = {}
	for sub in ("wip", "build"):
		for name in _subfolders(os.path.join(database, sub)):
			found.setdefault(name.lower(), name)
	return sorted(found.values(), key=str.lower)

def resolve_asset(name: str) -> str:
	"""Returns the spelling of an asset name, since "Rock" and "rock" are one folder on Windows but different in the website's database"""
	name = name.strip()
	for existing in list_assets():
		if existing.lower() == name.lower():
			return existing
	return name

def search_assets(self, context, edit_text: str) -> list[str]:
	"""Autocomplete list for asset name fields"""
	return list_assets()

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def get_blocks(data_type: str) -> Iterable[Any]:
	"""`bpy.data.<data_type>`, or nothing if this Blender version doesn't have it"""
	return getattr(bpy.data, data_type, ())

# Pointers of every data block that existed before each scene was loaded
_preexisting: dict[int, set[int]] = {}

def _all_ids() -> list[bpy.types.ID]:
	return list(bpy.data.user_map().keys())

def load_scene(path: str) -> bpy.types.Scene:
	"""Loads the first scene of the file into our scene"""
	before = {i.as_pointer() for i in _all_ids()}
	with bpy.data.libraries.load(path, link=False) as (source_data, target_data):
		if not source_data.scenes:
			raise ValueError(f"No scenes found in {path}")
		target_data.scenes = [source_data.scenes[0]]
	scene = target_data.scenes[0]
	_preexisting[scene.as_pointer()] = before
	return scene

def unload_scene(scene: bpy.types.Scene) -> None:
	"""
	Removes the scene and the data it brought with it.\n
	Only data loaded alongside the scene is purged, the user's own orphans aren't purged.
	"""
	key = scene.as_pointer()
	before = _preexisting.pop(key, None)

	for obj in scene.collection.all_objects:
		obj.use_fake_user = False
	for col in scene.collection.children_recursive:
		col.use_fake_user = False
	# This keeps the scene data block
	bpy.data.scenes.remove(scene)

	# Unknown origin, do a full purge
	if before is None:
		bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
		return

	# Kill the orphans until nothing is left
	while True:
		orphans = [i for i in _all_ids() if i.as_pointer() not in before and i.users == 0]
		if not orphans:
			break
		bpy.data.batch_remove(orphans)

def transfer_version(source: Any, target: Any) -> None:
	"""Transfers the version number between data blocks, useful when updating data"""
	source_version = source.get("sg_version")
	target_version = target.get("sg_version")
	
	if source_version is not None and target_version is not None:
		target["sg_version"] = source_version
